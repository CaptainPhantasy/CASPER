"""
LLM Service wrapper for CASPER Prime.
Uses Anthropic by default if ANTHROPIC_API_KEY is present.
Falls back gracefully when no key is configured.
Includes comprehensive error recovery and retry logic.
"""

import os
import asyncio
import logging
import time
from typing import Optional, Union, Dict, Any
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
        # Get API keys from user-specific secure storage, with fallback to environment
        self.anthropic_key = user_config.get_api_key("anthropic") or os.environ.get("ANTHROPIC_API_KEY")
        self.openai_key = user_config.get_api_key("openai") or os.environ.get("OPENAI_API_KEY")
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

        # Map to appropriate OpenAI model
        openai_model = "gpt-4" if "claude" in model else model

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

    async def complete(self, prompt: str, system: str = "", model: str = "claude-3-5-sonnet-20241022", max_tokens: int = 1000) -> str:
        """
        Generate text completion with comprehensive error recovery.
        Tries Anthropic first, falls back to OpenAI if configured.
        """
        if not self.available():
            logger.warning("No LLM providers available")
            return ""

        # Try Anthropic first if available
        if self._anthropic:
            result = await self._call_anthropic_with_retry(prompt, system, model, max_tokens)
            if result is not None:
                return result

        # Fallback to OpenAI if Anthropic failed or unavailable
        if self._openai:
            logger.info("Falling back to OpenAI API")
            result = await self._call_openai_with_retry(prompt, system, model, max_tokens)
            if result is not None:
                return result

        logger.error("All LLM providers failed or circuit breakers are open")
        return ""  # Return empty string if all providers fail


llm_service = LLMService()

