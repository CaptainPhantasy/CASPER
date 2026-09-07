"""Bounded health checks for harness dependencies and extension points."""

from __future__ import annotations

import asyncio
import inspect
import time
from dataclasses import dataclass
from enum import Enum
from typing import Awaitable, Callable


class HealthStatus(str, Enum):
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"


@dataclass(frozen=True)
class HealthCheckResult:
    name: str
    status: HealthStatus
    summary: str
    elapsed_ms: float = 0.0


@dataclass(frozen=True)
class HealthReport:
    status: HealthStatus
    checks: tuple[HealthCheckResult, ...]

    @property
    def healthy(self) -> bool:
        return self.status == HealthStatus.HEALTHY


HealthCheck = Callable[[], Awaitable[HealthCheckResult] | HealthCheckResult]


class HealthDiagnostics:
    def __init__(self) -> None:
        self._checks: dict[str, HealthCheck] = {}

    def register(self, name: str, check: HealthCheck) -> None:
        if not name or name in self._checks:
            raise ValueError(f"health check name must be non-empty and unique: {name!r}")
        self._checks[name] = check

    async def _run_one(self, name: str, check: HealthCheck, timeout: float) -> HealthCheckResult:
        started = time.perf_counter()
        try:
            value = check()
            if inspect.isawaitable(value):
                value = await asyncio.wait_for(value, timeout=timeout)
            if not isinstance(value, HealthCheckResult):
                raise TypeError("health check must return HealthCheckResult")
            result = value
        except asyncio.TimeoutError:
            result = HealthCheckResult(name, HealthStatus.UNHEALTHY, f"timed out after {timeout:g}s")
        except Exception as exc:
            result = HealthCheckResult(name, HealthStatus.UNHEALTHY, f"{type(exc).__name__}: {exc}")
        return HealthCheckResult(
            name, result.status, result.summary,
            round((time.perf_counter() - started) * 1_000, 2),
        )

    async def run(self, *, timeout_seconds: float = 5.0) -> HealthReport:
        timeout = max(0.01, timeout_seconds)
        results = await asyncio.gather(*(
            self._run_one(name, self._checks[name], timeout) for name in sorted(self._checks)
        ))
        statuses = {item.status for item in results}
        if HealthStatus.UNHEALTHY in statuses:
            overall = HealthStatus.UNHEALTHY
        elif HealthStatus.DEGRADED in statuses:
            overall = HealthStatus.DEGRADED
        else:
            overall = HealthStatus.HEALTHY
        return HealthReport(overall, tuple(results))
