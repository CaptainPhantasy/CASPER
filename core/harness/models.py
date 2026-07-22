"""Typed contracts shared by the canonical CASPER coding harness."""

from __future__ import annotations

import time
import uuid
from dataclasses import asdict, dataclass, field
from enum import Enum
from typing import Any, Awaitable, Callable, Mapping, Optional


class ObservationStatus(str, Enum):
    SUCCESS = "success"
    WARNING = "warning"
    ERROR = "error"


class RunStatus(str, Enum):
    ACTIVE = "active"
    AWAITING_APPROVAL = "awaiting_approval"
    COMPLETE = "complete"
    BLOCKED = "blocked"
    FAILED = "failed"


ToolHandler = Callable[[Mapping[str, Any]], Awaitable["ToolObservation"] | "ToolObservation"]


@dataclass(frozen=True)
class ToolSpec:
    name: str
    description: str
    input_schema: dict[str, Any]
    mutates: bool = False
    risk: str = "safe"
    timeout_seconds: float = 120.0
    capabilities: tuple[str, ...] = ()

    def provider_schema(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "description": self.description,
            "input_schema": self.input_schema,
        }


@dataclass(frozen=True)
class ToolCall:
    name: str
    arguments: dict[str, Any]
    id: str = field(default_factory=lambda: f"call_{uuid.uuid4().hex[:16]}")

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class ToolObservation:
    status: ObservationStatus
    summary: str
    next_actions: list[str] = field(default_factory=list)
    artifacts: list[str] = field(default_factory=list)
    data: dict[str, Any] = field(default_factory=dict)
    root_cause_hint: str = ""
    safe_retry: str = ""
    stop_condition: str = ""
    call_id: str = ""
    elapsed_ms: float = 0.0

    @classmethod
    def success(
        cls, summary: str, *, data: Optional[dict[str, Any]] = None,
        artifacts: Optional[list[str]] = None, next_actions: Optional[list[str]] = None,
    ) -> "ToolObservation":
        return cls(
            ObservationStatus.SUCCESS, summary, next_actions or [], artifacts or [], data or {}
        )

    @classmethod
    def warning(
        cls, summary: str, *, data: Optional[dict[str, Any]] = None,
        next_actions: Optional[list[str]] = None,
    ) -> "ToolObservation":
        return cls(ObservationStatus.WARNING, summary, next_actions or [], [], data or {})

    @classmethod
    def error(
        cls, summary: str, root_cause: str, retry: str, stop: str,
        *, data: Optional[dict[str, Any]] = None,
    ) -> "ToolObservation":
        return cls(
            ObservationStatus.ERROR,
            summary,
            [retry] if retry else [],
            [],
            data or {},
            root_cause,
            retry,
            stop,
        )

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["status"] = self.status.value
        return payload

    def render(self) -> str:
        import json
        return json.dumps(self.to_dict(), indent=2, sort_keys=True, default=str)


@dataclass(frozen=True)
class ModelTurn:
    text: str = ""
    tool_calls: tuple[ToolCall, ...] = ()
    stop_reason: str = "stop"
    usage: dict[str, int] = field(default_factory=dict)
    model: str = ""


@dataclass(frozen=True)
class RunEvent:
    run_id: str
    sequence: int
    type: str
    payload: dict[str, Any]
    created_at: float = field(default_factory=time.time)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class RunState:
    objective: str
    run_id: str = field(default_factory=lambda: f"run_{uuid.uuid4().hex[:16]}")
    status: RunStatus = RunStatus.ACTIVE
    step: int = 0
    messages: list[dict[str, Any]] = field(default_factory=list)
    pending_calls: list[ToolCall] = field(default_factory=list)
    artifacts: list[str] = field(default_factory=list)
    usage: dict[str, int] = field(default_factory=dict)
    final_text: str = ""
    error: str = ""
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["status"] = self.status.value
        payload["pending_calls"] = [call.to_dict() for call in self.pending_calls]
        return payload

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "RunState":
        values = dict(payload)
        values["status"] = RunStatus(values.get("status", RunStatus.ACTIVE.value))
        values["pending_calls"] = [ToolCall(**item) for item in values.get("pending_calls", [])]
        return cls(**values)


@dataclass(frozen=True)
class RunResult:
    run_id: str
    status: RunStatus
    text: str
    artifacts: tuple[str, ...] = ()
    pending_calls: tuple[ToolCall, ...] = ()
    usage: dict[str, int] = field(default_factory=dict)
    steps: int = 0
    error: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "run_id": self.run_id,
            "status": self.status.value,
            "text": self.text,
            "artifacts": list(self.artifacts),
            "pending_calls": [call.to_dict() for call in self.pending_calls],
            "usage": dict(self.usage),
            "steps": self.steps,
            "error": self.error,
        }

    def render(self) -> str:
        import json
        return json.dumps(self.to_dict(), indent=2, sort_keys=True, default=str)
