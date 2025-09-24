"""
LLM Service wrapper for CASPER Prime.
Uses Anthropic by default if ANTHROPIC_API_KEY is present.
Falls back gracefully when no key is configured.
"""

import os
from typing import Optional

try:
    from anthropic import AsyncAnthropic
except Exception:  # pragma: no cover - optional import
    AsyncAnthropic = None  # type: ignore


class LLMService:
    def __init__(self):
        self.anthropic_key = os.environ.get("ANTHROPIC_API_KEY")
        self._anthropic: Optional[AsyncAnthropic] = None

        if self.anthropic_key and AsyncAnthropic is not None:
            try:
                self._anthropic = AsyncAnthropic(api_key=self.anthropic_key)
            except Exception:
                self._anthropic = None

    def available(self) -> bool:
        return self._anthropic is not None

    async def complete(self, prompt: str, system: str = "", model: str = "claude-3-5-sonnet-20241022", max_tokens: int = 1000) -> str:
        """
        Generate text completion using Anthropic Messages API.
        """
        if not self._anthropic:
            return ""  # no-op if not configured

        resp = await self._anthropic.messages.create(
            model=model,
            max_tokens=max_tokens,
            system=system or "You are CASPER Prime, a precise software-engineering assistant.",
            messages=[
                {"role": "user", "content": prompt}
            ],
        )
        # Concatenate message content text parts
        try:
            parts = []
            for block in resp.content:
                if hasattr(block, 'text') and block.text:
                    parts.append(block.text)
                elif isinstance(block, dict) and block.get('type') == 'text':
                    parts.append(block.get('text', ''))
            return "\n".join([p for p in parts if p])
        except Exception:
            # Fallback: best-effort string
            return str(resp)


llm_service = LLMService()

