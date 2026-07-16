"""Bounded dependency-aware task scheduling for harness orchestration."""

from __future__ import annotations

import asyncio
import inspect
from dataclasses import dataclass
from enum import Enum
from typing import Any, Awaitable, Callable

from .cancellation import CancellationError, CancellationToken


class TaskStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    BLOCKED = "blocked"
    CANCELLED = "cancelled"


TaskRunner = Callable[[CancellationToken], Awaitable[Any] | Any]


@dataclass(frozen=True)
class TaskNode:
    name: str
    runner: TaskRunner
    dependencies: tuple[str, ...] = ()


@dataclass(frozen=True)
class TaskResult:
    name: str
    status: TaskStatus
    value: Any = None
    error: str = ""


class TaskDAGScheduler:
    def __init__(self, nodes: tuple[TaskNode, ...], *, max_concurrency: int = 4) -> None:
        self.nodes = {node.name: node for node in nodes}
        if len(self.nodes) != len(nodes) or any(not node.name for node in nodes):
            raise ValueError("task names must be non-empty and unique")
        self.max_concurrency = max(1, max_concurrency)
        self._validate()

    def _validate(self) -> None:
        missing = sorted({dep for node in self.nodes.values() for dep in node.dependencies if dep not in self.nodes})
        if missing:
            raise ValueError(f"unknown task dependencies: {', '.join(missing)}")
        visiting: set[str] = set()
        visited: set[str] = set()

        def visit(name: str) -> None:
            if name in visiting:
                raise ValueError(f"task dependency cycle includes {name}")
            if name in visited:
                return
            visiting.add(name)
            for dependency in self.nodes[name].dependencies:
                visit(dependency)
            visiting.remove(name)
            visited.add(name)

        for name in sorted(self.nodes):
            visit(name)

    @staticmethod
    async def _invoke(node: TaskNode, token: CancellationToken) -> TaskResult:
        try:
            token.raise_if_cancelled()
            value = node.runner(token)
            if inspect.isawaitable(value):
                value = await value
            token.raise_if_cancelled()
            return TaskResult(node.name, TaskStatus.SUCCEEDED, value)
        except (CancellationError, asyncio.CancelledError) as exc:
            return TaskResult(node.name, TaskStatus.CANCELLED, error=str(exc) or "cancelled")
        except Exception as exc:
            return TaskResult(node.name, TaskStatus.FAILED, error=f"{type(exc).__name__}: {exc}")

    async def run(self, token: CancellationToken | None = None) -> dict[str, TaskResult]:
        token = token or CancellationToken()
        results: dict[str, TaskResult] = {}
        active: dict[asyncio.Task[TaskResult], str] = {}
        pending = set(self.nodes)
        while pending or active:
            if token.cancelled:
                for name in sorted(pending):
                    results[name] = TaskResult(name, TaskStatus.CANCELLED, error=token.reason)
                pending.clear()
                for task in active:
                    task.cancel()
            for name in sorted(tuple(pending)):
                dependencies = self.nodes[name].dependencies
                if any(
                    dependency in results and results[dependency].status != TaskStatus.SUCCEEDED
                    for dependency in dependencies
                ):
                    results[name] = TaskResult(name, TaskStatus.BLOCKED, error="dependency did not succeed")
                    pending.remove(name)
            ready = [
                name for name in sorted(pending)
                if all(results.get(dep, TaskResult(dep, TaskStatus.PENDING)).status == TaskStatus.SUCCEEDED
                   for dep in self.nodes[name].dependencies)
            ]
            for name in ready[:max(0, self.max_concurrency - len(active))]:
                pending.remove(name)
                task = asyncio.create_task(self._invoke(self.nodes[name], token.child()))
                active[task] = name
            if not active:
                continue
            done, _ = await asyncio.wait(active, return_when=asyncio.FIRST_COMPLETED)
            for task in done:
                name = active.pop(task)
                try:
                    results[name] = await task
                except asyncio.CancelledError:
                    results[name] = TaskResult(name, TaskStatus.CANCELLED, error=token.reason or "cancelled")
        return {name: results[name] for name in sorted(results)}
