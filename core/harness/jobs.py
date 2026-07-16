"""In-process background job supervisor with explicit state transitions."""

from __future__ import annotations

import asyncio
import inspect
import time
import uuid
from dataclasses import dataclass, replace
from enum import Enum
from typing import Any, Awaitable, Callable

from .cancellation import CancellationError, CancellationToken


class JobStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    CANCELLED = "cancelled"


JobRunner = Callable[[CancellationToken], Awaitable[Any] | Any]


@dataclass(frozen=True)
class JobRecord:
    job_id: str
    name: str
    status: JobStatus
    created_at: float
    started_at: float = 0.0
    finished_at: float = 0.0
    result: Any = None
    error: str = ""


class BackgroundJobSupervisor:
    def __init__(self, *, max_active: int = 4, history_limit: int = 100) -> None:
        self.max_active = max(1, max_active)
        self.history_limit = max(1, history_limit)
        self._records: dict[str, JobRecord] = {}
        self._tasks: dict[str, asyncio.Task[None]] = {}
        self._tokens: dict[str, CancellationToken] = {}

    def _active_count(self) -> int:
        return sum(record.status in {JobStatus.PENDING, JobStatus.RUNNING} for record in self._records.values())

    def submit(self, name: str, runner: JobRunner) -> JobRecord:
        if not name.strip():
            raise ValueError("job name is required")
        if self._active_count() >= self.max_active:
            raise RuntimeError(f"active job limit reached: {self.max_active}")
        job_id = f"job_{uuid.uuid4().hex[:16]}"
        record = JobRecord(job_id, name, JobStatus.PENDING, time.time())
        token = CancellationToken()
        self._records[job_id] = record
        self._tokens[job_id] = token
        self._tasks[job_id] = asyncio.create_task(self._execute(job_id, runner, token))
        self._trim()
        return record

    async def _execute(self, job_id: str, runner: JobRunner, token: CancellationToken) -> None:
        record = replace(self._records[job_id], status=JobStatus.RUNNING, started_at=time.time())
        self._records[job_id] = record
        try:
            token.raise_if_cancelled()
            result = runner(token)
            if inspect.isawaitable(result):
                result = await result
            token.raise_if_cancelled()
            record = replace(record, status=JobStatus.SUCCEEDED, result=result, finished_at=time.time())
        except (CancellationError, asyncio.CancelledError) as exc:
            record = replace(
                record, status=JobStatus.CANCELLED, error=str(exc) or token.reason or "cancelled",
                finished_at=time.time(),
            )
        except Exception as exc:
            record = replace(
                record, status=JobStatus.FAILED, error=f"{type(exc).__name__}: {exc}",
                finished_at=time.time(),
            )
        self._records[job_id] = record

    def get(self, job_id: str) -> JobRecord | None:
        return self._records.get(job_id)

    def list(self) -> tuple[JobRecord, ...]:
        return tuple(sorted(self._records.values(), key=lambda item: item.created_at, reverse=True))

    def cancel(self, job_id: str, reason: str = "cancelled by operator") -> bool:
        token = self._tokens.get(job_id)
        if token is None or self._records[job_id].status not in {JobStatus.PENDING, JobStatus.RUNNING}:
            return False
        token.cancel(reason)
        task = self._tasks.get(job_id)
        if task is not None:
            task.cancel()
        return True

    async def wait(self, job_id: str) -> JobRecord:
        task = self._tasks.get(job_id)
        if task is None:
            raise KeyError(f"unknown job: {job_id}")
        await asyncio.gather(task, return_exceptions=True)
        return self._records[job_id]

    async def shutdown(self, reason: str = "supervisor shutdown") -> None:
        for job_id in tuple(self._tasks):
            self.cancel(job_id, reason)
        await asyncio.gather(*self._tasks.values(), return_exceptions=True)

    def _trim(self) -> None:
        completed = [
            record for record in sorted(self._records.values(), key=lambda item: item.created_at)
            if record.status not in {JobStatus.PENDING, JobStatus.RUNNING}
        ]
        for record in completed[:-self.history_limit]:
            self._records.pop(record.job_id, None)
            self._tasks.pop(record.job_id, None)
            self._tokens.pop(record.job_id, None)
