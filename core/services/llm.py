"""
LLM Service wrapper for CASPER Prime.
Uses Anthropic by default if ANTHROPIC_API_KEY is present.
Falls back gracefully when no key is configured.
Includes comprehensive error recovery and retry logic.
"""

import os
import re
import asyncio
import logging
import time
from typing import Optional, Union, Dict, Any, List
from dataclasses import dataclass
from enum import Enum

from core.services.user_config import user_config

try:
    from anthropic import AsyncAnthropic
    from anthropic import APIConnectionError, RateLimitError, APIStatusError
except Exception:  # pragma: no cover - optional import
    AsyncAnthropic = None  # type: ignore
    APIConnectionError = Exception  # type: ignore
    RateLimitError = Exception  # type: ignore
    APIStatusError = Exception  # type: ignore

try:
    import openai
    from openai import OpenAI, AsyncOpenAI
except Exception:  # pragma: no cover - optional import
    openai = None  # type: ignore
    OpenAI = None  # type: ignore
    AsyncOpenAI = None  # type: ignore

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Dynamic model resolution
# ---------------------------------------------------------------------------
# CASPER no longer hardcodes specific model ids. At runtime we query each
# provider's /models endpoint, filter out deprecated/legacy families, and rank
# what's actually available to the account. These constants are last-resort
# fallbacks used ONLY when live discovery fails — and they are deliberately
# current-generation, never the deprecated claude-3 / gpt-3 families.
# Tiers/classes: primary+worker are the legacy two-tier names; frontier/standard/
# cheap/tiny are the task-aware model classes used by the router (Feature 4).
_ANTHROPIC_FALLBACK = {
    "primary": "claude-sonnet-4-6",
    "worker": "claude-haiku-4-5-20251001",
    "frontier": "claude-opus-4-8",
    "standard": "claude-sonnet-4-6",
    "cheap": "claude-haiku-4-5-20251001",
    "tiny": "claude-haiku-4-5-20251001",
}
_OPENAI_FALLBACK = {
    "primary": "gpt-4o",
    "worker": "gpt-4o-mini",
    "frontier": "gpt-4o",
    "standard": "gpt-4o",
    "cheap": "gpt-4o-mini",
    "tiny": "gpt-4o-mini",
}

# Matches deprecated / legacy model ids that should be auto-upgraded if a
# caller still passes one (e.g. older hardcoded "claude-3-5-sonnet-...").
_LEGACY_MODEL_RE = re.compile(
    r"claude-(?:instant|1|2|3)[._-]|^claude-instant|^gpt-3|^text-|davinci|babbage",
    re.IGNORECASE,
)


def _is_legacy_model(model_id: Optional[str]) -> bool:
    return bool(model_id) and bool(_LEGACY_MODEL_RE.search(model_id))


def _anthropic_rank(model_id: str):
    """Sortable key (tier, version_tuple) for an Anthropic model id.
    Higher = more capable / newer. No specific ids are hardcoded — ranking is
    derived from the family name and embedded version numbers."""
    mid = model_id.lower()
    if "mythos" in mid or "fable" in mid:
        tier = 5  # Mythos-class — above Opus
    elif "opus" in mid:
        tier = 4
    elif "sonnet" in mid:
        tier = 3
    elif "haiku" in mid:
        tier = 2
    else:
        tier = 1
    version = tuple(int(n) for n in re.findall(r"\d+", mid))
    return (tier, version)


def _select_anthropic(ids: List[str], tier: str) -> Optional[str]:
    ids = [i for i in ids if not _is_legacy_model(i)]
    if not ids:
        return None
    low = str.lower
    t = (tier or "primary").lower()
    if t in ("worker", "cheap", "tiny"):
        pool = [i for i in ids if "haiku" in low(i)] or ids
    elif t == "standard":
        pool = [i for i in ids if "sonnet" in low(i)] or [i for i in ids if "opus" in low(i)] or ids
    elif t == "frontier":
        pool = [i for i in ids if "opus" in low(i)] or [i for i in ids if "sonnet" in low(i)] or ids
    else:  # primary — most capable; prefer Opus/Sonnet, avoid the fast tier
        pool = [i for i in ids if "opus" in low(i) or "sonnet" in low(i)] or ids
    return max(pool, key=_anthropic_rank)


def _select_openai(ids: List[str], tier: str) -> Optional[str]:
    ids = [i for i in ids if not _is_legacy_model(i)]
    if not ids:
        return None
    t = (tier or "primary").lower()
    if t in ("worker", "cheap", "tiny"):
        prefs = ["gpt-4o-mini", "gpt-4.1-mini", "o4-mini", "gpt-4o"]
    else:  # primary / standard / frontier
        prefs = ["gpt-4o", "gpt-4.1", "o4", "gpt-4-turbo", "gpt-4"]
    for p in prefs:
        for i in ids:
            if i == p or i.startswith(p):
                return i
    return ids[0]


class LLMProvider(Enum):
    ANTHROPIC = "anthropic"
    OPENAI = "openai"


@dataclass
class RetryConfig:
    max_retries: int = 3
    base_delay: float = 1.0
    max_delay: float = 60.0
    exponential_base: float = 2.0
    jitter: bool = True


@dataclass
class CircuitBreakerConfig:
    failure_threshold: int = 5
    recovery_timeout: int = 60
    half_open_max_calls: int = 3


class CircuitBreakerState(Enum):
    CLOSED = "closed"      # Normal operation
    OPEN = "open"         # Failing, reject calls
    HALF_OPEN = "half_open"  # Testing recovery


class CircuitBreaker:
    """Circuit breaker pattern implementation for LLM providers."""

    def __init__(self, config: CircuitBreakerConfig):
        self.config = config
        self.state = CircuitBreakerState.CLOSED
        self.failure_count = 0
        self.last_failure_time = 0
        self.half_open_calls = 0

    def can_call(self) -> bool:
        """Check if calls are allowed based on circuit breaker state."""
        now = time.time()

        if self.state == CircuitBreakerState.CLOSED:
            return True
        elif self.state == CircuitBreakerState.OPEN:
            if now - self.last_failure_time > self.config.recovery_timeout:
                self.state = CircuitBreakerState.HALF_OPEN
                self.half_open_calls = 0
                return True
            return False
        elif self.state == CircuitBreakerState.HALF_OPEN:
            return self.half_open_calls < self.config.half_open_max_calls

        return False

    def record_success(self):
        """Record successful call."""
        if self.state == CircuitBreakerState.HALF_OPEN:
            self.state = CircuitBreakerState.CLOSED
        self.failure_count = 0
        self.half_open_calls = 0

    def record_failure(self):
        """Record failed call."""
        self.failure_count += 1
        self.last_failure_time = time.time()

        if self.state == CircuitBreakerState.HALF_OPEN:
            self.state = CircuitBreakerState.OPEN
        elif self.failure_count >= self.config.failure_threshold:
            self.state = CircuitBreakerState.OPEN

        if self.state == CircuitBreakerState.HALF_OPEN:
            self.half_open_calls += 1


class LLMService:
    def __init__(self):
        # Get API keys. Environment variables take precedence over stored keys so
        # a freshly-rotated key in the environment/.env always overrides a stale
        # value in encrypted local storage.
        self.anthropic_key = os.environ.get("ANTHROPIC_API_KEY") or user_config.get_api_key("anthropic")
        self.openai_key = os.environ.get("OPENAI_API_KEY") or user_config.get_api_key("openai")
        self._anthropic: Optional[AsyncAnthropic] = None
        self._openai: Optional[AsyncOpenAI] = None

        # Initialize clients
        if self.anthropic_key and AsyncAnthropic is not None:
            try:
                self._anthropic = AsyncAnthropic(api_key=self.anthropic_key)
            except Exception as e:
                logger.warning(f"Failed to initialize Anthropic client: {e}")
                self._anthropic = None

        if self.openai_key and AsyncOpenAI is not None:
            try:
                self._openai = AsyncOpenAI(api_key=self.openai_key)
            except Exception as e:
                logger.warning(f"Failed to initialize OpenAI client: {e}")
                self._openai = None

        # Circuit breakers for each provider
        self.anthropic_breaker = CircuitBreaker(CircuitBreakerConfig())
        self.openai_breaker = CircuitBreaker(CircuitBreakerConfig())

        # Retry configuration
        self.retry_config = RetryConfig()

        # Resolved-model cache: {provider: {"primary": id, "worker": id}}.
        # Populated lazily from each provider's live /models listing.
        self._resolved_models: Dict[str, Dict[str, str]] = {}
        self._resolve_lock = asyncio.Lock()

    async def _discover_models(self, provider: str) -> Dict[str, str]:
        """Query a provider's live model list and pick current (non-deprecated)
        primary + worker models. Falls back to current-gen constants on error."""
        try:
            tiers = ("primary", "worker", "frontier", "standard", "cheap", "tiny")
            if provider == "anthropic" and self._anthropic is not None:
                page = await self._anthropic.models.list()
                ids = [getattr(m, "id", None) for m in getattr(page, "data", [])]
                ids = [i for i in ids if i]
                chosen = {t: (_select_anthropic(ids, t) or _ANTHROPIC_FALLBACK[t]) for t in tiers}
                logger.info(f"Resolved Anthropic models from {len(ids)} available: {chosen}")
                return chosen
            if provider == "openai" and self._openai is not None:
                page = await self._openai.models.list()
                ids = [getattr(m, "id", None) for m in getattr(page, "data", [])]
                ids = [i for i in ids if i]
                chosen = {t: (_select_openai(ids, t) or _OPENAI_FALLBACK[t]) for t in tiers}
                logger.info(f"Resolved OpenAI models from {len(ids)} available: {chosen}")
                return chosen
        except Exception as e:
            logger.warning(f"Live model discovery failed for {provider}: {e}; using current-gen fallback")
        return dict(_ANTHROPIC_FALLBACK if provider == "anthropic" else _OPENAI_FALLBACK)

    async def resolve_model(self, provider: str, tier: str = "primary") -> Optional[str]:
        """Return a current model id for the given provider + tier
        ('primary' or 'worker'), discovering and caching on first use."""
        async with self._resolve_lock:
            if provider not in self._resolved_models:
                self._resolved_models[provider] = await self._discover_models(provider)
        return self._resolved_models[provider].get(tier)

    async def list_available_models(self) -> Dict[str, Dict[str, str]]:
        """Expose the resolved model selection for both providers (for /api/status, diagnostics)."""
        out: Dict[str, Dict[str, str]] = {}
        if self._anthropic is not None:
            out["anthropic"] = {**await self._discover_models("anthropic")}
        if self._openai is not None:
            out["openai"] = {**await self._discover_models("openai")}
        return out

    def available(self) -> bool:
        return self._anthropic is not None or self._openai is not None

    def _calculate_delay(self, attempt: int) -> float:
        """Calculate delay with exponential backoff and jitter."""
        delay = min(
            self.retry_config.base_delay * (self.retry_config.exponential_base ** attempt),
            self.retry_config.max_delay
        )

        if self.retry_config.jitter:
            # Add random jitter ±25%
            jitter_range = delay * 0.25
            delay += (asyncio.get_event_loop().time() % 1 - 0.5) * 2 * jitter_range

        return max(0, delay)

    def _is_retryable_error(self, error: Exception) -> bool:
        """Determine if an error should be retried."""
        if isinstance(error, (APIConnectionError, RateLimitError)):
            return True
        if isinstance(error, APIStatusError) and 500 <= error.status_code < 600:
            return True
        if hasattr(error, 'status_code') and error.status_code in [429, 502, 503, 504]:
            return True
        return False

    async def _call_anthropic_with_retry(self, prompt: str, system: str, model: str, max_tokens: int) -> Optional[str]:
        """Call Anthropic API with retry logic and circuit breaker."""
        if not self._anthropic or not self.anthropic_breaker.can_call():
            return None

        for attempt in range(self.retry_config.max_retries + 1):
            try:
                resp = await self._anthropic.messages.create(
                    model=model,
                    max_tokens=max_tokens,
                    system=system or "You are CASPER Prime, a precise software-engineering assistant.",
                    messages=[{"role": "user", "content": prompt}],
                )

                # Successful call
                self.anthropic_breaker.record_success()

                # Extract text content
                parts = []
                for block in resp.content:
                    if hasattr(block, 'text') and block.text:
                        parts.append(block.text)
                    elif isinstance(block, dict) and block.get('type') == 'text':
                        parts.append(block.get('text', ''))

                result = "\n".join([p for p in parts if p])
                logger.debug(f"Anthropic API success on attempt {attempt + 1}")
                return result

            except Exception as e:
                logger.warning(f"Anthropic API attempt {attempt + 1} failed: {e}")
                self.anthropic_breaker.record_failure()

                if not self._is_retryable_error(e) or attempt == self.retry_config.max_retries:
                    break

                delay = self._calculate_delay(attempt)
                await asyncio.sleep(delay)

        return None

    async def _call_openai_with_retry(self, prompt: str, system: str, model: str, max_tokens: int) -> Optional[str]:
        """Call OpenAI API with retry logic and circuit breaker."""
        if not self._openai or not self.openai_breaker.can_call():
            return None

        # `model` here is already a resolved OpenAI model id (see complete()).
        openai_model = model

        for attempt in range(self.retry_config.max_retries + 1):
            try:
                messages = []
                if system:
                    messages.append({"role": "system", "content": system})
                messages.append({"role": "user", "content": prompt})

                resp = await self._openai.chat.completions.create(
                    model=openai_model,
                    messages=messages,
                    max_tokens=max_tokens,
                )

                # Successful call
                self.openai_breaker.record_success()

                result = resp.choices[0].message.content or ""
                logger.debug(f"OpenAI API success on attempt {attempt + 1}")
                return result

            except Exception as e:
                logger.warning(f"OpenAI API attempt {attempt + 1} failed: {e}")
                self.openai_breaker.record_failure()

                if not self._is_retryable_error(e) or attempt == self.retry_config.max_retries:
                    break

                delay = self._calculate_delay(attempt)
                await asyncio.sleep(delay)

        return None

    async def complete(
        self,
        prompt: str,
        system: str = "",
        model: Optional[str] = None,
        max_tokens: int = 1000,
        tier: str = "primary",
    ) -> str:
        """
        Generate text completion with comprehensive error recovery.
        Tries Anthropic first, falls back to OpenAI if configured.

        Model selection is dynamic: if `model` is None or a deprecated/legacy id,
        CASPER resolves a current model from the provider's live model list for
        the requested `tier` ("primary" or "worker"). No model ids are hardcoded
        in the hot path.
        """
        if not self.available():
            logger.warning("No LLM providers available")
            return ""

        requested = model

        # Try Anthropic first if available
        if self._anthropic:
            anth_model = requested
            if not anth_model or _is_legacy_model(anth_model) or "claude" not in anth_model.lower():
                anth_model = await self.resolve_model("anthropic", tier) or _ANTHROPIC_FALLBACK[tier]
            result = await self._call_anthropic_with_retry(prompt, system, anth_model, max_tokens)
            if result is not None:
                return result

        # Fallback to OpenAI if Anthropic failed or unavailable
        if self._openai:
            logger.info("Falling back to OpenAI API")
            oai_model = requested
            if not oai_model or _is_legacy_model(oai_model) or "gpt" not in (oai_model or "").lower():
                oai_model = await self.resolve_model("openai", tier) or _OPENAI_FALLBACK[tier]
            result = await self._call_openai_with_retry(prompt, system, oai_model, max_tokens)
            if result is not None:
                return result

        logger.error("All LLM providers failed or circuit breakers are open")
        return ""  # Return empty string if all providers fail


llm_service = LLMService()

