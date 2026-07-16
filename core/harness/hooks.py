"""Configurable, observable lifecycle hooks for the canonical CASPER runtime."""

from __future__ import annotations

import asyncio
import inspect
import json
import os
import re
import shlex
import time
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Awaitable, Callable, Optional


class LifecycleEvent(str, Enum):
    SESSION_START = "session_start"
    SESSION_END = "session_end"
    USER_PROMPT_SUBMIT = "user_prompt_submit"
    RUN_START = "run_start"
    BEFORE_MODEL = "before_model"
    AFTER_MODEL = "after_model"
    BEFORE_TOOL = "before_tool"
    AFTER_TOOL = "after_tool"
    TOOL_ERROR = "tool_error"
    RUN_FINISH = "run_finish"
    RUN_ERROR = "run_error"


_EVENT_ALIASES = {
    "SessionStart": LifecycleEvent.SESSION_START,
    "SessionEnd": LifecycleEvent.SESSION_END,
    "UserPromptSubmit": LifecycleEvent.USER_PROMPT_SUBMIT,
    "RunStart": LifecycleEvent.RUN_START,
    "BeforeModel": LifecycleEvent.BEFORE_MODEL,
    "AfterModel": LifecycleEvent.AFTER_MODEL,
    "PreToolUse": LifecycleEvent.BEFORE_TOOL,
    "PostToolUse": LifecycleEvent.AFTER_TOOL,
    "PostToolUseFailure": LifecycleEvent.TOOL_ERROR,
    "Stop": LifecycleEvent.RUN_FINISH,
    "StopFailure": LifecycleEvent.RUN_ERROR,
}


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
    handler: Optional[HookHandler] = None
    priority: int = 100
    matcher: str = ""
    command: tuple[str, ...] = ()
    timeout_seconds: float = 10.0
    source: str = "session"


@dataclass(frozen=True)
class HookFailure:
    hook: str
    error: str


@dataclass(frozen=True)
class HookExecution:
    hook: str
    event: str
    action: str
    duration_ms: float
    exit_code: Optional[int] = None
    stdout: str = ""
    stderr: str = ""
    additional_context: str = ""


@dataclass(frozen=True)
class HookDispatch:
    executions: tuple[HookExecution, ...] = ()
    failures: tuple[HookFailure, ...] = ()
    blocked: bool = False
    reason: str = ""
    additional_context: str = ""


def default_hook_paths(project_root: Path | str) -> tuple[Path, ...]:
    project = Path(project_root).expanduser().resolve()
    configured = os.environ.get("CASPER_HOOKS_FILE", "")
    candidates = [
        Path.home() / ".casper" / "hooks.json",
        project / ".casper" / "hooks.json",
        project / ".casper" / "config" / "hooks.json",
        project / ".casper" / "hooks.local.json",
    ]
    if configured:
        candidates.insert(0, Path(configured).expanduser())
    result: list[Path] = []
    seen: set[Path] = set()
    for path in candidates:
        resolved = path.resolve()
        if resolved.is_file() and resolved not in seen:
            result.append(resolved)
            seen.add(resolved)
    return tuple(result)


class LifecycleHooks:
    """Run Python or argv-based hooks with matching, timeouts, and fail-open diagnostics."""

    def __init__(self, *, cwd: Optional[Path | str] = None) -> None:
        self.cwd = Path(cwd).expanduser().resolve() if cwd else None
        self._hooks: dict[str, HookRegistration] = {}
        self.history: list[HookExecution] = []
        self.warnings: list[str] = []

    @classmethod
    def from_paths(
        cls, paths: tuple[Path | str, ...], *, cwd: Optional[Path | str] = None,
    ) -> "LifecycleHooks":
        hooks = cls(cwd=cwd)
        for path in paths:
            hooks.load(path)
        return hooks

    def register(
        self, name: str, event: LifecycleEvent, handler: HookHandler, *, priority: int = 100,
        matcher: str = "", source: str = "session",
    ) -> None:
        self._register(HookRegistration(
            name, event, handler, priority, matcher=matcher, source=source,
        ))

    def register_command(
        self, name: str, event: LifecycleEvent, command: str | list[str] | tuple[str, ...], *,
        priority: int = 100, matcher: str = "", timeout_seconds: float = 30.0,
        source: str = "session",
    ) -> None:
        argv = tuple(shlex.split(command)) if isinstance(command, str) else tuple(str(item) for item in command)
        if not argv:
            raise ValueError("hook command must contain an executable")
        if timeout_seconds <= 0 or timeout_seconds > 600:
            raise ValueError("hook timeout must be between 0 and 600 seconds")
        if matcher:
            re.compile(matcher)
        self._register(HookRegistration(
            name, event, None, priority, matcher, argv, timeout_seconds, source,
        ))

    def _register(self, registration: HookRegistration) -> None:
        if not registration.name or registration.name in self._hooks:
            raise ValueError(f"hook name must be non-empty and unique: {registration.name!r}")
        self._hooks[registration.name] = registration

    def load(self, path: Path | str) -> None:
        source = Path(path).expanduser().resolve()
        try:
            payload = json.loads(source.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            self.warnings.append(f"cannot load hook config {source}: {type(exc).__name__}: {exc}")
            return
        groups = payload.get("hooks", {}) if isinstance(payload, dict) else {}
        if not isinstance(groups, dict):
            self.warnings.append(f"hook config must contain an object at hooks: {source}")
            return
        for raw_event, matcher_groups in groups.items():
            event = _EVENT_ALIASES.get(str(raw_event))
            if event is None:
                try:
                    event = LifecycleEvent(str(raw_event))
                except ValueError:
                    self.warnings.append(f"unknown hook event {raw_event!r} in {source}")
                    continue
            if not isinstance(matcher_groups, list):
                self.warnings.append(f"hook event {raw_event} must be a list in {source}")
                continue
            for group_index, group in enumerate(matcher_groups):
                if not isinstance(group, dict):
                    continue
                matcher = str(group.get("matcher", ""))
                handlers = group.get("hooks", [])
                if not isinstance(handlers, list):
                    continue
                for hook_index, handler in enumerate(handlers):
                    if not isinstance(handler, dict) or handler.get("type", "command") != "command":
                        self.warnings.append(
                            f"unsupported hook handler at {source}:{raw_event}[{group_index}][{hook_index}]"
                        )
                        continue
                    name = str(handler.get("name") or f"{source.name}:{raw_event}:{group_index}:{hook_index}")
                    try:
                        self.register_command(
                            name, event, handler.get("command", ""), matcher=matcher,
                            timeout_seconds=float(handler.get("timeout", 30)),
                            priority=int(handler.get("priority", 100)), source=str(source),
                        )
                    except (TypeError, ValueError, re.error) as exc:
                        self.warnings.append(f"invalid hook {name} in {source}: {exc}")

    def unregister(self, name: str) -> bool:
        return self._hooks.pop(name, None) is not None

    def registrations(self, event: LifecycleEvent | None = None) -> tuple[HookRegistration, ...]:
        values = (item for item in self._hooks.values() if event is None or item.event == event)
        return tuple(sorted(values, key=lambda item: (item.priority, item.name)))

    @staticmethod
    def _matches(pattern: str, value: str) -> bool:
        return not pattern or bool(re.search(pattern, value))

    async def trigger(
        self, context: HookContext, *, matcher_value: str = "", fail_fast: bool = False,
    ) -> HookDispatch:
        executions: list[HookExecution] = []
        failures: list[HookFailure] = []
        blocked = False
        reason = ""
        contexts: list[str] = []
        for hook in self.registrations(context.event):
            if not self._matches(hook.matcher, matcher_value):
                continue
            try:
                execution = await self._run_one(hook, context)
                executions.append(execution)
                self.history.append(execution)
                self.history = self.history[-200:]
                if execution.additional_context:
                    contexts.append(execution.additional_context)
                if execution.action == "block":
                    blocked = True
                    reason = reason or execution.stderr or execution.stdout or f"Blocked by hook {hook.name}."
            except asyncio.CancelledError:
                raise
            except Exception as exc:
                failure = HookFailure(hook.name, f"{type(exc).__name__}: {exc}")
                failures.append(failure)
                if fail_fast:
                    raise
        return HookDispatch(
            tuple(executions), tuple(failures), blocked, reason, "\n".join(contexts),
        )

    async def emit(
        self, context: HookContext, *, timeout_seconds: float = 10.0,
        fail_fast: bool = False,
    ) -> tuple[HookFailure, ...]:
        """Backward-compatible callable-hook API."""
        dispatch = await self.trigger(context, fail_fast=fail_fast)
        return dispatch.failures

    async def _run_one(self, hook: HookRegistration, context: HookContext) -> HookExecution:
        started = time.monotonic()
        if hook.handler is not None:
            value = hook.handler(context)
            if inspect.isawaitable(value):
                await asyncio.wait_for(value, timeout=hook.timeout_seconds)
            return HookExecution(
                hook.name, context.event.value, "allow", (time.monotonic() - started) * 1000,
            )
        process = await asyncio.create_subprocess_exec(
            *hook.command,
            cwd=str(self.cwd) if self.cwd else None,
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        raw_input = json.dumps({
            "hook_event_name": context.event.value,
            "session_id": context.run_id,
            "cwd": str(self.cwd or Path.cwd()),
            **context.payload,
        }, sort_keys=True).encode("utf-8")
        try:
            stdout_bytes, stderr_bytes = await asyncio.wait_for(
                process.communicate(input=raw_input), timeout=hook.timeout_seconds,
            )
        except asyncio.TimeoutError:
            process.kill()
            await process.wait()
            raise TimeoutError(f"hook timed out after {hook.timeout_seconds:g}s")
        except asyncio.CancelledError:
            process.kill()
            await process.wait()
            raise
        stdout = stdout_bytes.decode("utf-8", errors="replace")[-8_000:].strip()
        stderr = stderr_bytes.decode("utf-8", errors="replace")[-8_000:].strip()
        exit_code = int(process.returncode or 0)
        action = "block" if exit_code == 2 else "allow"
        additional_context = ""
        if exit_code == 0 and stdout:
            try:
                decoded = json.loads(stdout)
            except json.JSONDecodeError as exc:
                if stdout.lstrip().startswith(("{", "[")):
                    raise ValueError(f"hook returned invalid JSON output: {exc.msg}") from exc
                if context.event in {LifecycleEvent.SESSION_START, LifecycleEvent.USER_PROMPT_SUBMIT}:
                    additional_context = stdout
            else:
                if isinstance(decoded, dict):
                    specific = decoded.get("hookSpecificOutput", {})
                    if not isinstance(specific, dict):
                        specific = {}
                    decision = str(
                        specific.get("permissionDecision", decoded.get("decision", ""))
                    ).casefold()
                    if decision in {"deny", "block"}:
                        action = "block"
                    additional_context = str(
                        specific.get("additionalContext", decoded.get("additionalContext", ""))
                    )
                    if not stderr:
                        stderr = str(
                            specific.get("permissionDecisionReason", decoded.get("reason", ""))
                        )
        if exit_code not in {0, 2}:
            raise RuntimeError(f"hook exited {exit_code}: {stderr or stdout or 'no output'}")
        return HookExecution(
            hook.name, context.event.value, action, (time.monotonic() - started) * 1000,
            exit_code, stdout, stderr, additional_context,
        )
