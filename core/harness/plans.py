"""Dependency-aware, evidence-gated structured plan tracking."""

from __future__ import annotations

import json
import os
from dataclasses import asdict, dataclass, replace
from enum import StrEnum
from pathlib import Path
from typing import Iterable


class PlanStatus(StrEnum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    BLOCKED = "blocked"


@dataclass(frozen=True)
class PlanStep:
    id: str
    title: str
    status: PlanStatus = PlanStatus.PENDING
    depends_on: tuple[str, ...] = ()
    evidence: str | None = None
    verification: bool | None = None
    block_reason: str | None = None


class PlanTracker:
    """Track executable steps while enforcing dependencies and proof."""

    def __init__(self, steps: Iterable[PlanStep], storage_path: Path | str | None = None) -> None:
        materialized = tuple(steps)
        self._steps = {step.id: step for step in materialized}
        if len(self._steps) != len(materialized):
            raise ValueError("plan step ids must be unique")
        self.storage_path = Path(storage_path).expanduser() if storage_path else None
        self._validate()

    @property
    def steps(self) -> tuple[PlanStep, ...]:
        return tuple(self._steps.values())

    def _validate(self) -> None:
        active = [step.id for step in self._steps.values() if step.status == PlanStatus.IN_PROGRESS]
        if len(active) > 1:
            raise ValueError("only one plan step may be in progress")
        for step in self._steps.values():
            missing = set(step.depends_on) - self._steps.keys()
            if missing:
                raise ValueError(f"step {step.id} has missing dependencies: {sorted(missing)}")
        visiting: set[str] = set()
        visited: set[str] = set()

        def visit(step_id: str) -> None:
            if step_id in visiting:
                raise ValueError("plan dependencies contain a cycle")
            if step_id in visited:
                return
            visiting.add(step_id)
            for dependency in self._steps[step_id].depends_on:
                visit(dependency)
            visiting.remove(step_id)
            visited.add(step_id)

        for step_id in self._steps:
            visit(step_id)

    def ready(self) -> tuple[PlanStep, ...]:
        return tuple(step for step in self.steps if step.status == PlanStatus.PENDING and all(
            self._steps[dependency].status == PlanStatus.COMPLETED for dependency in step.depends_on
        ))

    def start(self, step_id: str) -> PlanStep:
        step = self._require(step_id)
        if any(item.status == PlanStatus.IN_PROGRESS for item in self.steps):
            raise ValueError("another plan step is already in progress")
        if step not in self.ready():
            raise ValueError(f"step {step_id} is not ready")
        return self._replace(replace(step, status=PlanStatus.IN_PROGRESS, block_reason=None))

    def complete(self, step_id: str, *, evidence: str, verification_passed: bool) -> PlanStep:
        step = self._require(step_id)
        if step.status != PlanStatus.IN_PROGRESS:
            raise ValueError(f"step {step_id} is not in progress")
        if not evidence.strip() or not verification_passed:
            raise ValueError("completion requires evidence and passing verification")
        return self._replace(replace(
            step, status=PlanStatus.COMPLETED, evidence=evidence.strip(), verification=True,
        ))

    def block(self, step_id: str, reason: str) -> PlanStep:
        step = self._require(step_id)
        if not reason.strip():
            raise ValueError("blocked steps require a reason")
        return self._replace(replace(step, status=PlanStatus.BLOCKED, block_reason=reason.strip()))

    def _require(self, step_id: str) -> PlanStep:
        try:
            return self._steps[step_id]
        except KeyError as exc:
            raise KeyError(f"unknown plan step: {step_id}") from exc

    def _replace(self, step: PlanStep) -> PlanStep:
        self._steps[step.id] = step
        if self.storage_path:
            self.save()
        return step

    def to_dict(self) -> dict[str, object]:
        return {"version": 1, "steps": [
            {**asdict(step), "status": step.status.value, "depends_on": list(step.depends_on)}
            for step in self.steps
        ]}

    def save(self, path: Path | str | None = None) -> Path:
        target = Path(path) if path else self.storage_path
        if target is None:
            raise ValueError("no plan storage path configured")
        target = target.expanduser()
        target.parent.mkdir(parents=True, exist_ok=True)
        temporary = target.with_name(f".{target.name}.{os.getpid()}.tmp")
        temporary.write_text(json.dumps(self.to_dict(), indent=2) + "\n", encoding="utf-8")
        temporary.replace(target)
        return target

    @classmethod
    def load(cls, path: Path | str) -> PlanTracker:
        target = Path(path).expanduser()
        payload = json.loads(target.read_text(encoding="utf-8"))
        if payload.get("version") != 1 or not isinstance(payload.get("steps"), list):
            raise ValueError("unsupported plan document")
        steps = tuple(PlanStep(
            id=item["id"],
            title=item["title"],
            status=PlanStatus(item["status"]),
            depends_on=tuple(item.get("depends_on", ())),
            evidence=item.get("evidence"),
            verification=item.get("verification"),
            block_reason=item.get("block_reason"),
        ) for item in payload["steps"])
        return cls(steps, target)
