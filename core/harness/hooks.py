"""Ordered lifecycle hooks for extending runs without coupling the runtime."""

from __future__ import annotations

import asyncio
import inspect
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Awaitable, Callable


class LifecycleEvent(str, Enum):
    RUN_START = "run_start"
    BEFORE_MODEL = "before_model"
    AFTER_MODEL = "after_model"
    BEFORE_TOOL = "before_tool"
    AFTER_TOOL = "after_tool"
    RUN_FINISH = "run_finish"
    RUN_ERROR = "run_error"


@dataclass
class HookContext:
    event: LifecycleEvent
    run_id: str
    payload: dict[str, Any] = field(default_factory=dict)


HookHandler = Callable[[HookContext], Awaitable[None] | None]


@dataclass(frozen=True)
class HookRegistration:
    name: str
    event: LifecycleEvent
    handler: HookHandler
    priority: int = 100


@dataclass(frozen=True)
class HookFailure:
    hook: str
    error: str


class LifecycleHooks:
    """Deterministic hook runner; failures are reported, not hidden."""

    def __init__(self) -> None:
        self._hooks: dict[str, HookRegistration] = {}

    def register(
        self, name: str, event: LifecycleEvent, handler: HookHandler, *, priority: int = 100,
    ) -> None:
        if not name or name in self._hooks:
            raise ValueError(f"hook name must be non-empty and unique: {name!r}")
        self._hooks[name] = HookRegistration(name, event, handler, priority)

    def unregister(self, name: str) -> bool:
        return self._hooks.pop(name, None) is not None

    def registrations(self, event: LifecycleEvent | None = None) -> tuple[HookRegistration, ...]:
        values = (item for item in self._hooks.values() if event is None or item.event == event)
        return tuple(sorted(values, key=lambda item: (item.priority, item.name)))

    async def emit(
        self, context: HookContext, *, timeout_seconds: float = 10.0,
        fail_fast: bool = False,
    ) -> tuple[HookFailure, ...]:
        failures: list[HookFailure] = []
        for hook in self.registrations(context.event):
            try:
                result = hook.handler(context)
                if inspect.isawaitable(result):
                    await asyncio.wait_for(result, timeout=max(0.01, timeout_seconds))
            except Exception as exc:
                failures.append(HookFailure(hook.name, f"{type(exc).__name__}: {exc}"))
                if fail_fast:
                    raise
        return tuple(failures)
