"""
Feature 3 — Context lifecycle (minimal slices, discard on completion).

The planner holds the *global* plan (the spec + all units + recorded results).
Each worker receives only a minimal WorkerContext: its subtask, the slice of the
spec it must satisfy, and the contents of just the files relevant to it. Workers
never see the whole project.

After a unit completes, its working context is discarded — only the durable
outputs (artifacts created, decisions made) are recorded back into the global
plan. The next unit therefore starts from a clean slate, preventing the context
drift and quality decay that accumulate when one long-lived context handles an
entire project.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import Dict, List, Optional

from core.pipeline.models import FrozenSpec, SpecRequirement, TaskUnit

# Per-file read cap so a worker slice never balloons with huge files.
_MAX_FILE_BYTES = 16_000


@dataclass
class WorkerContext:
    """The complete, minimal context handed to a single worker for one unit."""

    unit: TaskUnit
    spec_summary: str
    requirements: List[SpecRequirement]  # only the unit's slice
    constraints: List[str]
    files: Dict[str, str] = field(default_factory=dict)  # path -> contents (truncated)
    notes: List[str] = field(default_factory=list)  # durable upstream decisions

    def render_prompt(self) -> str:
        """Render the slice as a compact prompt block for the worker."""
        lines = [
            f"# Task: {self.unit.title}",
            self.unit.description.strip(),
            "",
            f"# Goal (from the locked spec): {self.spec_summary}",
            "",
            "# Requirements you must satisfy:",
        ]
        for r in self.requirements:
            lines.append(f"- [{r.id}] {r.text}")
            for c in r.acceptance_criteria:
                lines.append(f"    • acceptance: {c}")
        if self.constraints:
            lines.append("")
            lines.append("# Constraints:")
            lines += [f"- {c}" for c in self.constraints]
        if self.notes:
            lines.append("")
            lines.append("# Relevant prior decisions:")
            lines += [f"- {n}" for n in self.notes]
        if self.files:
            lines.append("")
            lines.append("# Relevant files (may be truncated):")
            for path, content in self.files.items():
                lines.append(f"\n--- {path} ---\n{content}")
        return "\n".join(lines)


@dataclass
class UnitOutcome:
    """Durable record of a finished unit — the ONLY thing that survives back to the plan."""

    unit_id: str
    success: bool
    artifacts: List[str] = field(default_factory=list)
    decisions: List[str] = field(default_factory=list)
    summary: str = ""


@dataclass
class GlobalPlan:
    """Planner-held state. Holds the whole picture so workers don't have to."""

    spec: FrozenSpec
    units: List[TaskUnit] = field(default_factory=list)
    outcomes: Dict[str, UnitOutcome] = field(default_factory=dict)

    def pending_units(self) -> List[TaskUnit]:
        """Units whose dependencies are all satisfied and not yet completed."""
        done = {uid for uid, o in self.outcomes.items() if o.success}
        ready = []
        for u in self.units:
            if u.id in self.outcomes and self.outcomes[u.id].success:
                continue
            if all(dep in done for dep in u.depends_on):
                ready.append(u)
        return ready

    def record(self, outcome: UnitOutcome) -> None:
        self.outcomes[outcome.unit_id] = outcome

    def is_complete(self) -> bool:
        return all(o.success for o in self.outcomes.values()) and len(
            self.outcomes
        ) == len(self.units)


class ContextManager:
    """Builds minimal worker slices and records durable outcomes back to the plan."""

    def __init__(self, project_root: str, max_file_bytes: int = _MAX_FILE_BYTES):
        self.project_root = project_root
        self.max_file_bytes = max_file_bytes

    def build_worker_context(self, plan: GlobalPlan, unit: TaskUnit) -> WorkerContext:
        """Assemble the minimal context for one unit. Reads only `relevant_paths`."""
        # Spec slice: only the requirements this unit is responsible for.
        req_map = {r.id: r for r in plan.spec.requirements}
        slice_reqs = [req_map[rid] for rid in unit.requirement_ids if rid in req_map]
        if not slice_reqs:
            slice_reqs = plan.spec.requirements[:1]  # never send an empty contract

        files = self._read_relevant_files(unit.relevant_paths)

        # Carry forward only durable decisions from completed dependency units.
        notes: List[str] = []
        for dep in unit.depends_on:
            out = plan.outcomes.get(dep)
            if out:
                notes.extend(out.decisions[:3])

        return WorkerContext(
            unit=unit,
            spec_summary=plan.spec.summary,
            requirements=slice_reqs,
            constraints=list(plan.spec.constraints),
            files=files,
            notes=notes,
        )

    def discard(self, context: WorkerContext) -> UnitOutcome:
        """
        Discard a worker's transient context, returning a compact outcome that is
        the only thing recorded back into the global plan. Explicitly drops file
        contents and the rendered prompt so nothing leaks into the next unit.
        """
        context.files.clear()
        context.notes.clear()
        return UnitOutcome(unit_id=context.unit.id, success=False)

    def _read_relevant_files(self, paths: List[str]) -> Dict[str, str]:
        out: Dict[str, str] = {}
        for rel in paths:
            full = (
                os.path.join(self.project_root, rel) if not os.path.isabs(rel) else rel
            )
            try:
                if os.path.isfile(full):
                    with open(full, "r", encoding="utf-8", errors="replace") as f:
                        data = f.read(self.max_file_bytes + 1)
                    if len(data) > self.max_file_bytes:
                        data = data[: self.max_file_bytes] + "\n… (truncated)"
                    out[rel] = data
            except Exception:
                # A missing/unreadable file is not fatal — the worker may create it.
                continue
        return out
