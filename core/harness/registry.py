"""Schema-first registry and deterministic tool execution."""

from __future__ import annotations

import asyncio
import inspect
import time
from dataclasses import dataclass
from typing import Any, Mapping, Optional

from .models import ToolCall, ToolHandler, ToolObservation, ToolSpec


@dataclass(frozen=True)
class RegisteredTool:
    spec: ToolSpec
    handler: ToolHandler


class ToolRegistry:
    def __init__(self) -> None:
        self._tools: dict[str, RegisteredTool] = {}

    def register(self, spec: ToolSpec, handler: ToolHandler) -> None:
        if not spec.name or not spec.name.replace("_", "").isalnum():
            raise ValueError("tool names must contain only letters, numbers, and underscores")
        if spec.name in self._tools:
            raise ValueError(f"tool already registered: {spec.name}")
        self._tools[spec.name] = RegisteredTool(spec, handler)

    def get(self, name: str) -> Optional[RegisteredTool]:
        return self._tools.get(name)

    def specs(self) -> tuple[ToolSpec, ...]:
        return tuple(item.spec for item in self._tools.values())

    def provider_schemas(self) -> list[dict[str, Any]]:
        return [spec.provider_schema() for spec in self.specs()]

    @staticmethod
    def _validate(schema: Mapping[str, Any], values: Mapping[str, Any]) -> Optional[str]:
        if schema.get("type", "object") != "object":
            return "top-level tool input schema must be an object"
        required = schema.get("required", [])
        missing = [name for name in required if name not in values]
        if missing:
            return f"missing required field(s): {', '.join(missing)}"
        if schema.get("additionalProperties") is False:
            allowed = set(schema.get("properties", {}))
            extra = sorted(set(values) - allowed)
            if extra:
                return f"unexpected field(s): {', '.join(extra)}"
        type_map: dict[str, type[Any] | tuple[type[Any], ...]] = {
            "string": str, "integer": int, "number": (int, float),
            "boolean": bool, "array": list, "object": dict,
        }
        for name, rule in schema.get("properties", {}).items():
            if name not in values or "type" not in rule:
                continue
            expected = type_map.get(rule["type"])
            value = values[name]
            if expected and (not isinstance(value, expected) or rule["type"] == "integer" and isinstance(value, bool)):
                return f"field {name!r} must be {rule['type']}"
            if "enum" in rule and value not in rule["enum"]:
                return f"field {name!r} must be one of {rule['enum']}"
        return None

    async def execute(self, call: ToolCall) -> ToolObservation:
        registered = self.get(call.name)
        if not registered:
            return ToolObservation.error(
                f"Unknown tool: {call.name}",
                "The model requested a tool that is not in the active registry.",
                "Refresh the capability list and choose a registered tool.",
                "Stop if the requested capability is not installed.",
                data={"available_tools": [spec.name for spec in self.specs()]},
            )
        validation_error = self._validate(registered.spec.input_schema, call.arguments)
        if validation_error:
            return ToolObservation.error(
                f"Invalid input for {call.name}: {validation_error}",
                "The tool arguments do not match its declared schema.",
                "Correct the arguments using the active tool schema and retry once.",
                "Stop after the same schema error repeats.",
            )
        started = time.perf_counter()
        try:
            value = registered.handler(call.arguments)
            if inspect.isawaitable(value):
                value = await asyncio.wait_for(value, timeout=registered.spec.timeout_seconds)
            if not isinstance(value, ToolObservation):
                raise TypeError("tool handler must return ToolObservation")
            observation = value
        except asyncio.TimeoutError:
            observation = ToolObservation.error(
                f"Tool timed out: {call.name}",
                f"The operation exceeded {registered.spec.timeout_seconds:g} seconds.",
                "Narrow the scope or increase the tool's explicit timeout and retry.",
                "Stop if the same bounded operation times out again.",
            )
        except Exception as exc:
            observation = ToolObservation.error(
                f"Tool failed: {call.name}: {exc}",
                f"The handler raised {type(exc).__name__}.",
                "Correct the reported input or environment and retry once.",
                "Stop after the same root cause repeats.",
            )
        observation.call_id = call.id
        observation.elapsed_ms = round((time.perf_counter() - started) * 1000, 2)
        return observation
