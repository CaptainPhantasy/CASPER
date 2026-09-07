"""Provider-neutral native tool-call contracts and response normalization."""

from __future__ import annotations

import inspect
import json
from typing import Any, Awaitable, Callable, Mapping, Optional, Protocol, Sequence

from .models import ModelTurn, ToolCall


class HarnessProvider(Protocol):
    async def complete(
        self, messages: Sequence[Mapping[str, Any]], tools: Sequence[Mapping[str, Any]],
    ) -> ModelTurn: ...


class ProviderChain:
    """Sticky failover across configured native tool providers."""

    def __init__(self, providers: Sequence[HarnessProvider]) -> None:
        self.providers = list(providers)
        if not self.providers:
            raise ValueError("provider chain requires at least one provider")
        self.active_index = 0
        self.failures: list[dict[str, str]] = []

    @property
    def active(self) -> HarnessProvider:
        return self.providers[self.active_index]

    async def complete(
        self,
        messages: Sequence[Mapping[str, Any]],
        tools: Sequence[Mapping[str, Any]],
    ) -> ModelTurn:
        errors: list[str] = []
        for index in range(self.active_index, len(self.providers)):
            provider = self.providers[index]
            try:
                turn = await provider.complete(messages, tools)
                self.active_index = index
                return turn
            except Exception as exc:
                failure = {"provider": type(provider).__name__, "error": str(exc)}
                self.failures.append(failure)
                errors.append(f"{failure['provider']}: {failure['error']}")
        raise RuntimeError("All configured tool providers failed: " + " | ".join(errors))


def _value(value: Any, name: str, default: Any = None) -> Any:
    if isinstance(value, Mapping):
        return value.get(name, default)
    return getattr(value, name, default)


def _arguments(raw: Any) -> dict[str, Any]:
    if isinstance(raw, Mapping):
        return dict(raw)
    if not raw:
        return {}
    try:
        value = json.loads(str(raw))
        return value if isinstance(value, dict) else {"value": value}
    except json.JSONDecodeError:
        return {"_invalid_json": str(raw)}


def _tool_call(name: Any, arguments: Any, call_id: Any = "") -> ToolCall:
    identity = str(call_id or "")
    if identity:
        return ToolCall(name=str(name), arguments=_arguments(arguments), id=identity)
    return ToolCall(name=str(name), arguments=_arguments(arguments))


def normalize_openai_response(response: Any) -> ModelTurn:
    choices = _value(response, "choices", []) or []
    choice = choices[0] if choices else {}
    message = _value(choice, "message", {}) or {}
    calls: list[ToolCall] = []
    for item in _value(message, "tool_calls", []) or []:
        function = _value(item, "function", {}) or {}
        calls.append(_tool_call(
            _value(function, "name", ""), _value(function, "arguments", {}), _value(item, "id", ""),
        ))
    usage = _value(response, "usage", {}) or {}
    usage_dict = {
        "input_tokens": int(_value(usage, "prompt_tokens", 0) or 0),
        "output_tokens": int(_value(usage, "completion_tokens", 0) or 0),
    }
    return ModelTurn(
        text=str(_value(message, "content", "") or ""), tool_calls=tuple(calls),
        stop_reason=str(_value(choice, "finish_reason", "stop") or "stop"),
        usage=usage_dict, model=str(_value(response, "model", "") or ""),
    )


def normalize_anthropic_response(response: Any) -> ModelTurn:
    text: list[str] = []
    calls: list[ToolCall] = []
    for block in _value(response, "content", []) or []:
        kind = _value(block, "type", "")
        if kind == "text":
            text.append(str(_value(block, "text", "")))
        elif kind == "tool_use":
            calls.append(_tool_call(
                _value(block, "name", ""), _value(block, "input", {}), _value(block, "id", ""),
            ))
    usage = _value(response, "usage", {}) or {}
    return ModelTurn(
        text="\n".join(part for part in text if part), tool_calls=tuple(calls),
        stop_reason=str(_value(response, "stop_reason", "end_turn") or "end_turn"),
        usage={
            "input_tokens": int(_value(usage, "input_tokens", 0) or 0),
            "output_tokens": int(_value(usage, "output_tokens", 0) or 0),
        },
        model=str(_value(response, "model", "") or ""),
    )


def normalize_gemini_response(response: Any) -> ModelTurn:
    candidates = _value(response, "candidates", []) or []
    candidate = candidates[0] if candidates else {}
    content = _value(candidate, "content", {}) or {}
    text: list[str] = []
    calls: list[ToolCall] = []
    for part in _value(content, "parts", []) or []:
        part_text = _value(part, "text", None)
        if part_text is not None:
            text.append(str(part_text))
        function_call = _value(part, "function_call", None) or _value(part, "functionCall", None)
        if function_call:
            calls.append(_tool_call(
                _value(function_call, "name", ""), _value(function_call, "args", {}),
            ))
    usage = _value(response, "usage_metadata", {}) or _value(response, "usageMetadata", {}) or {}
    return ModelTurn(
        text="\n".join(text), tool_calls=tuple(calls),
        stop_reason=str(_value(candidate, "finish_reason", "stop") or "stop"),
        usage={
            "input_tokens": int(_value(usage, "prompt_token_count", 0) or _value(usage, "promptTokenCount", 0) or 0),
            "output_tokens": int(_value(usage, "candidates_token_count", 0) or _value(usage, "candidatesTokenCount", 0) or 0),
        }, model=str(_value(response, "model_version", "") or ""),
    )


ProviderCallable = Callable[[Sequence[Mapping[str, Any]], Sequence[Mapping[str, Any]]], Awaitable[Any] | Any]


class CallableProvider:
    """Adapter for SDK clients or deterministic test providers."""

    def __init__(self, callback: ProviderCallable, dialect: str = "model_turn") -> None:
        if dialect not in {"model_turn", "openai", "anthropic", "gemini"}:
            raise ValueError("unsupported provider dialect")
        self.callback = callback
        self.dialect = dialect

    async def complete(
        self,
        messages: Sequence[Mapping[str, Any]],
        tools: Sequence[Mapping[str, Any]],
    ) -> ModelTurn:
        value = self.callback(messages, tools)
        if inspect.isawaitable(value):
            value = await value
        if self.dialect == "model_turn":
            if not isinstance(value, ModelTurn):
                raise TypeError("model_turn providers must return ModelTurn")
            return value
        normalizer = {
            "openai": normalize_openai_response,
            "anthropic": normalize_anthropic_response,
            "gemini": normalize_gemini_response,
        }[self.dialect]
        return normalizer(value)


class TextCompletionProvider:
    """Compatibility adapter for CASPER's text-only LLM service.

    This provider can converse but cannot request tools. Native provider adapters
    should be used for autonomous coding runs.
    """

    def __init__(self, service: Any) -> None:
        self.service = service

    async def complete(
        self,
        messages: Sequence[Mapping[str, Any]],
        tools: Sequence[Mapping[str, Any]],
    ) -> ModelTurn:
        transcript = "\n".join(
            f"{item.get('role', 'user')}: {item.get('content', '')}" for item in messages[-20:]
        )
        text = await self.service.complete(
            prompt=transcript,
            system="You are CASPER's coding harness. Answer concisely. This provider path cannot call tools.",
            max_tokens=1600,
        )
        return ModelTurn(text=text or "", stop_reason="stop", model="text-compat")


class OpenAIToolProvider:
    """Native OpenAI-compatible function-calling adapter."""

    def __init__(self, client: Any, model: Optional[str] = None, model_resolver: Optional[Callable[[], Any]] = None) -> None:
        self.client = client
        self.model = model
        self.model_resolver = model_resolver

    async def _model(self) -> str:
        if self.model:
            return self.model
        if not self.model_resolver:
            raise RuntimeError("OpenAI tool provider has no model or resolver")
        value = self.model_resolver()
        if inspect.isawaitable(value):
            value = await value
        if not value:
            raise RuntimeError("OpenAI model resolution returned no model")
        self.model = str(value)
        return self.model

    @staticmethod
    def _messages(messages: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
        converted: list[dict[str, Any]] = []
        for item in messages:
            role = str(item.get("role", "user"))
            if role == "assistant" and item.get("tool_calls"):
                converted.append({
                    "role": "assistant", "content": item.get("content") or None,
                    "tool_calls": [{
                        "id": call["id"], "type": "function",
                        "function": {"name": call["name"], "arguments": json.dumps(call.get("arguments", {}), sort_keys=True)},
                    } for call in item["tool_calls"]],
                })
            elif role == "tool":
                converted.append({
                    "role": "tool", "tool_call_id": item.get("tool_call_id"),
                    "content": str(item.get("content", "")),
                })
            else:
                converted.append({"role": role, "content": str(item.get("content", ""))})
        return converted

    async def complete(
        self,
        messages: Sequence[Mapping[str, Any]],
        tools: Sequence[Mapping[str, Any]],
    ) -> ModelTurn:
        response = await self.client.chat.completions.create(
            model=await self._model(), messages=self._messages(messages),
            tools=[{"type": "function", "function": {
                "name": tool["name"], "description": tool["description"],
                "parameters": tool["input_schema"],
            }} for tool in tools], tool_choice="auto",
        )
        return normalize_openai_response(response)


class AnthropicToolProvider:
    """Native Anthropic tool-use adapter with tool-result round trips."""

    def __init__(self, client: Any, model: Optional[str] = None, model_resolver: Optional[Callable[[], Any]] = None, max_tokens: int = 4096) -> None:
        self.client = client
        self.model = model
        self.model_resolver = model_resolver
        self.max_tokens = max_tokens

    async def _model(self) -> str:
        if self.model:
            return self.model
        if not self.model_resolver:
            raise RuntimeError("Anthropic tool provider has no model or resolver")
        value = self.model_resolver()
        if inspect.isawaitable(value):
            value = await value
        if not value:
            raise RuntimeError("Anthropic model resolution returned no model")
        self.model = str(value)
        return self.model

    @staticmethod
    def _payload(messages: Sequence[Mapping[str, Any]]) -> tuple[str, list[dict[str, Any]]]:
        system_parts: list[str] = []
        converted: list[dict[str, Any]] = []

        def append(role: str, blocks: list[dict[str, Any]]) -> None:
            if converted and converted[-1]["role"] == role:
                converted[-1]["content"].extend(blocks)
            else:
                converted.append({"role": role, "content": blocks})

        for item in messages:
            role = str(item.get("role", "user"))
            if role == "system":
                system_parts.append(str(item.get("content", "")))
            elif role == "assistant":
                blocks: list[dict[str, Any]] = []
                if item.get("content"):
                    blocks.append({"type": "text", "text": str(item["content"])})
                blocks.extend({
                    "type": "tool_use", "id": call["id"], "name": call["name"],
                    "input": call.get("arguments", {}),
                } for call in item.get("tool_calls", []))
                append("assistant", blocks)
            elif role == "tool":
                raw = str(item.get("content", ""))
                try:
                    decoded = json.loads(raw)
                    is_error = decoded.get("status") == "error"
                except (json.JSONDecodeError, AttributeError):
                    is_error = False
                append("user", [{
                    "type": "tool_result", "tool_use_id": item.get("tool_call_id"),
                    "content": raw, "is_error": is_error,
                }])
            else:
                append("user", [{"type": "text", "text": str(item.get("content", ""))}])
        return "\n\n".join(system_parts), converted

    async def complete(
        self,
        messages: Sequence[Mapping[str, Any]],
        tools: Sequence[Mapping[str, Any]],
    ) -> ModelTurn:
        system, converted = self._payload(messages)
        response = await self.client.messages.create(
            model=await self._model(), max_tokens=self.max_tokens, system=system,
            messages=converted, tools=list(tools),
        )
        return normalize_anthropic_response(response)


def create_default_provider(service: Any = None) -> HarnessProvider:
    """Select a configured native tool provider, or explicit chat-only fallback."""
    if service is None:
        from core.services.llm import llm_service
        service = llm_service
    try:
        from core.services.user_config import user_config
        preferred = user_config.get_default_provider()
    except Exception:
        preferred = ""
    candidates = [preferred, "anthropic", "openai"]
    providers: list[HarnessProvider] = []
    for name in dict.fromkeys(candidates):
        if name == "anthropic" and getattr(service, "_anthropic", None) is not None:
            providers.append(AnthropicToolProvider(
                service._anthropic, model_resolver=lambda: service.resolve_model("anthropic", "primary"),
            ))
        if name == "openai" and getattr(service, "_openai", None) is not None:
            providers.append(OpenAIToolProvider(
                service._openai, model_resolver=lambda: service.resolve_model("openai", "primary"),
            ))
    if len(providers) > 1:
        return ProviderChain(providers)
    if providers:
        return providers[0]
    return TextCompletionProvider(service)
