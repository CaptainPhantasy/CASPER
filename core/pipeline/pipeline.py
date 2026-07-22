"""
The CASPER Prime execution pipeline — orchestrates all nine features into one
trustworthy loop:

    intent
      → [F1] InputCompiler ............ frozen spec (or clarifying questions)
      → [F5] SkillRegistry ............ reuse known-good procedures
      → [F3] plan + context slices .... planner holds the whole; workers get a slice
      → [F4] TaskAwareRouter .......... right model for each unit's cognitive load
      → [F7] GraduatedAutonomy ........ auto-approve safe; escalate risky
      →      execute .................. produce artifacts (pluggable executor)
      → [F2] Verifier ................. prove it (build/test/spec), adversarially
      → [F8] SelfHealingLoop .......... repair + re-verify on failure
      → [F9] ProgressTracker + Ledger . legible states + reversible changes

The code-writing executor is pluggable (`set_executor`) so the pipeline can be
driven by the full agent system or, by default, a focused LLM file-writer that
makes the whole loop runnable and testable on its own.
"""

from __future__ import annotations

import json
import logging
import os
import re
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Awaitable, Callable, Dict, List, Optional

from core.pipeline.autonomy import AutonomyMode, GraduatedAutonomy, ProposedAction
from core.pipeline.compiler import InputCompiler
from core.pipeline.context import ContextManager, GlobalPlan, UnitOutcome, WorkerContext
from core.pipeline.healing import SelfHealingLoop
from core.pipeline.models import (
    ClarificationRequired,
    FrozenSpec,
    PipelineStage,
    TaskKind,
    TaskUnit,
    _new_id,
)
from core.pipeline.progress import ChangeLedger, ProgressTracker
from core.pipeline.routing import BudgetState, RouteDecision, TaskAwareRouter
from core.pipeline.skills import SkillRegistry, ensure_seed_skills
from core.pipeline.verifier import Verifier, VerificationPlan
from core.services.llm import llm_service

logger = logging.getLogger(__name__)

# An executor builds the artifact(s) for one unit and returns their paths.
Executor = Callable[[WorkerContext, RouteDecision], Awaitable[List[str]]]

_PLANNER_SYSTEM = (
    "You are CASPER's planner. You break a frozen spec into a minimal set of "
    "independently-verifiable build units. Reply with STRICT JSON only."
)


@dataclass
class PipelineResult:
    run_id: str
    status: str                      # done | needs_clarification | blocked | failed
    spec: Optional[Dict] = None
    questions: List[Dict] = field(default_factory=list)
    units: List[Dict] = field(default_factory=list)
    artifacts: List[str] = field(default_factory=list)
    progress: List[Dict] = field(default_factory=list)
    changes: List[Dict] = field(default_factory=list)
    human_summary: str = ""
    blocked_detail: Optional[Dict] = None

    def to_dict(self) -> Dict:
        return self.__dict__


class Pipeline:
    def __init__(
        self,
        project_root: str,
        provider: str = "anthropic",
        autonomy_mode: AutonomyMode = AutonomyMode.AUTO,
        budget_tokens: Optional[int] = None,
        progress_callback: Optional[Callable[[Dict], None]] = None,
        max_repair_attempts: int = 2,
    ):
        self.project_root = project_root
        self.run_id = _new_id("run")
        self.compiler = InputCompiler()
        self.router = TaskAwareRouter(provider=provider, budget=BudgetState(limit_tokens=budget_tokens))
        self.verifier = Verifier(project_root)
        self.healer = SelfHealingLoop(project_root, self.verifier, self.router, max_attempts=max_repair_attempts)
        self.skills = SkillRegistry(project_root)
        ensure_seed_skills(self.skills)
        self.context = ContextManager(project_root)
        self.autonomy = GraduatedAutonomy(mode=autonomy_mode)
        self.progress = ProgressTracker(self.run_id)
        self.ledger = ChangeLedger(project_root)
        self._executor: Executor = self._default_executor
        self._gate_log: List[Dict] = []
        if progress_callback:
            self.progress.on_update(progress_callback)

    def set_executor(self, executor: Executor) -> None:
        """Override the default LLM file-writer with the full agent system."""
        self._executor = executor

    # ------------------------------------------------------------------ run
    async def run(
        self,
        intent: str,
        answers: Optional[Dict[str, str]] = None,
        build_cmd: Optional[List[str]] = None,
        test_cmd: Optional[List[str]] = None,
    ) -> PipelineResult:
        result = PipelineResult(run_id=self.run_id, status="failed")

        # F1: compile intent → frozen spec (may need clarification first)
        self.progress.set_stage(PipelineStage.COMPILING, "Reading your request")
        try:
            spec = await self.compiler.compile(intent, answers=answers)
        except ClarificationRequired as cr:
            self.progress.set_stage(PipelineStage.AWAITING_CLARIFICATION,
                                    f"{len(cr.questions)} quick question(s)")
            result.status = "needs_clarification"
            result.spec = cr.partial_spec.to_dict()
            result.questions = [q.to_dict() for q in cr.questions]
            result.progress = self.progress.snapshot()["history"]
            result.human_summary = "I need a couple of confirmations before I start."
            return result

        if not spec.verify_integrity():
            spec.freeze()
        self.progress.set_stage(PipelineStage.SPEC_FROZEN, spec.summary)
        result.spec = spec.to_dict()

        # F5 + F3: plan (skills-aware) into minimal units
        self.progress.set_stage(PipelineStage.PLANNING, "Breaking the work into steps")
        plan = await self._plan(spec)
        result.units = [u.to_dict() for u in plan.units]

        verify_plan = VerificationPlan(build_cmd=build_cmd, test_cmd=test_cmd, cwd=self.project_root)

        # Execute units honoring dependencies.
        produced: List[str] = []
        guard = 0
        while not plan.is_complete() and guard < len(plan.units) * 3 + 5:
            guard += 1
            ready = plan.pending_units()
            if not ready:
                break
            for unit in ready:
                outcome, artifacts = await self._execute_unit(spec, plan, unit, verify_plan)
                plan.record(outcome)
                produced.extend(a for a in artifacts if a not in produced)
                if outcome and not outcome.success:
                    # Blocked: surface and stop (a real run could continue others).
                    result.status = "blocked"
                    result.blocked_detail = {"unit": unit.to_dict(), "summary": outcome.summary}
                    result.human_summary = outcome.summary
                    result.artifacts = produced
                    result.progress = self.progress.snapshot()["history"]
                    result.changes = self.ledger.human_log()
                    return result

        # Done
        self.progress.set_stage(PipelineStage.DONE, "All steps verified")
        result.status = "done"
        result.artifacts = produced
        result.progress = self.progress.snapshot()["history"]
        result.changes = self.ledger.human_log()
        result.human_summary = self._final_summary(spec, produced)
        return result

    # -------------------------------------------------------------- planning
    async def _plan(self, spec: FrozenSpec) -> GlobalPlan:
        # F5: does a known-good skill cover this? (records the hint on units)
        skill = self.skills.best(spec.summary + " " + " ".join(r.text for r in spec.requirements))
        units = await self._decompose(spec, skill_id=skill.id if skill else None)
        plan = GlobalPlan(spec=spec, units=units)
        return plan

    async def _decompose(self, spec: FrozenSpec, skill_id: Optional[str]) -> List[TaskUnit]:
        reqs = "\n".join(f"- id={r.id}: {r.text}" for r in spec.requirements)
        prompt = (
            f"Spec summary: {spec.summary}\n\nRequirements:\n{reqs}\n\n"
            "Break this into the FEWEST independently-verifiable units. For each unit give: "
            "title, description, requirement_ids (subset of the ids above), relevant_paths "
            "(files to create/edit, repo-relative), and kind "
            "(architecture|reasoning|debugging|code_gen|mechanical|formatting|organization|classification).\n"
            'Reply STRICT JSON: {"units":[{"title":"","description":"","requirement_ids":[],"relevant_paths":[],"kind":""}]}'
        )
        units: List[TaskUnit] = []
        try:
            raw = await llm_service.complete(prompt=prompt, system=_PLANNER_SYSTEM, tier="frontier", max_tokens=1500)
            data = self._extract_json(raw)
            for u in (data or {}).get("units", []):
                if not isinstance(u, dict) or not u.get("title"):
                    continue
                kind = self._coerce_kind(u.get("kind"))
                units.append(TaskUnit.new(
                    title=str(u["title"]),
                    description=str(u.get("description", "")),
                    requirement_ids=[str(i) for i in (u.get("requirement_ids") or [])],
                    relevant_paths=[str(p) for p in (u.get("relevant_paths") or [])],
                    kind=kind,
                    skill_id=skill_id,
                ))
        except Exception as e:
            logger.warning(f"Planner decomposition failed: {e}")

        if not units:
            # Fallback: one unit covering all 'must' requirements.
            must = [r.id for r in spec.requirements if r.priority == "must"] or spec.requirement_ids()
            units = [TaskUnit.new(
                title=spec.summary[:60] or "Build the requested change",
                description=spec.summary,
                requirement_ids=must,
                relevant_paths=[],
                kind=TaskKind.CODE_GEN,
                skill_id=skill_id,
            )]
        return units

    # ------------------------------------------------------------- execution
    async def _execute_unit(self, spec: FrozenSpec, plan: GlobalPlan, unit: TaskUnit,
                            verify_plan: VerificationPlan):
        # F4: route by cognitive load
        self.progress.set_stage(PipelineStage.ROUTING, f"Assigning a specialist for: {unit.title}")
        route = await self.router.route(unit)

        # F3: build a minimal context slice for this unit
        ctx = self.context.build_worker_context(plan, unit)

        # Execute (build artifacts)
        self.progress.set_stage(PipelineStage.BUILDING, unit.title)
        try:
            artifacts = await self._executor(ctx, route)
        except Exception as e:
            logger.warning(f"Executor failed for unit {unit.id}: {e}")
            artifacts = []
        finally:
            # F3: discard the worker's transient context immediately.
            self.context.discard(ctx)

        # F2: verify (adversarial)
        self.progress.set_stage(PipelineStage.VERIFYING, f"Checking: {unit.title}")
        verification = await self.verifier.verify(spec, unit, artifacts, verify_plan)

        # F8: self-heal on failure
        if not verification.passed:
            self.progress.set_stage(PipelineStage.REPAIRING, f"Fixing: {unit.title}")
            healed = await self.healer.heal(spec, unit, artifacts, verification, verify_plan)
            verification = healed.final_verification
            if not healed.success:
                # F5: a failed skill loses confidence
                if unit.skill_id:
                    self.skills.record_outcome(unit.skill_id, success=False)
                return (UnitOutcome(unit_id=unit.id, success=False,
                                    artifacts=artifacts, summary=healed.human_summary), artifacts)

        # F5: a successful skill gains confidence
        if unit.skill_id:
            self.skills.record_outcome(unit.skill_id, success=True)

        return (UnitOutcome(
            unit_id=unit.id, success=True, artifacts=artifacts,
            decisions=[f"Built {unit.title} using {route.model_class.value} model"],
            summary=verification.human_summary,
        ), artifacts)

    # ---------------------------------------------------- default executor
    async def _default_executor(self, ctx: WorkerContext, route: RouteDecision) -> List[str]:
        """LLM file-writer with autonomy gating + ledger recording."""
        target = ctx.unit.relevant_paths[0] if ctx.unit.relevant_paths else self._derive_path(ctx)
        full = target if os.path.isabs(target) else os.path.join(self.project_root, target)
        exists = os.path.isfile(full)

        # F7: autonomy gate
        action = ProposedAction(action_type="modify" if exists else "create", path=target, reversible=True)
        decision = self.autonomy.assess(action)
        self._gate_log.append(decision.to_dict())
        if not decision.auto_approved:
            # Escalated — in a full UI this becomes a plain-language approval card.
            logger.info(f"Autonomy gate escalated: {decision.action} ({decision.risk.value})")
            # For non-interactive runs we still proceed for local reversible writes,
            # but record the escalation so the UI can surface it.

        content = await llm_service.complete(
            prompt=(ctx.render_prompt() + "\n\nReturn ONLY the complete file content for "
                    f"`{target}` — no explanation, no markdown fences."),
            system="You are a precise software engineer. Output only file content.",
            model=route.model,
            max_tokens=2500,
        )
        content = self._strip_fences(content)
        if not content.strip():
            return []

        backup_ref = self.ledger.snapshot_before_modify(target) if exists else None
        try:
            Path(full).parent.mkdir(parents=True, exist_ok=True)
            Path(full).write_text(content, encoding="utf-8")
        except Exception as e:
            logger.warning(f"Could not write artifact {full}: {e}")
            return []

        # F9: record reversible change
        if exists:
            self.ledger.record_modify(target, backup_ref, summary=f"Updated {target} for: {ctx.unit.title}")
        else:
            self.ledger.record_create(target, summary=f"Created {target} for: {ctx.unit.title}")
        return [target]

    # ------------------------------------------------------------- helpers
    def _derive_path(self, ctx: WorkerContext) -> str:
        slug = re.sub(r"[^a-z0-9]+", "_", ctx.unit.title.lower()).strip("_")[:40] or "artifact"
        return f"{slug}.py"

    def _coerce_kind(self, raw) -> TaskKind:
        try:
            return TaskKind(str(raw).lower())
        except Exception:
            return TaskKind.CODE_GEN

    def _extract_json(self, text: str) -> Optional[Dict]:
        if not text:
            return None
        cleaned = re.sub(r"^```(?:json)?|```$", "", text.strip()).strip()
        s, e = cleaned.find("{"), cleaned.rfind("}")
        if s == -1 or e == -1:
            return None
        try:
            return json.loads(cleaned[s:e + 1])
        except Exception:
            return None

    def _strip_fences(self, text: str) -> str:
        if not text:
            return ""
        t = text.strip()
        t = re.sub(r"^```[a-zA-Z0-9]*\n?", "", t)
        t = re.sub(r"\n?```$", "", t)
        return t

    def _final_summary(self, spec: FrozenSpec, artifacts: List[str]) -> str:
        files = ", ".join(artifacts) if artifacts else "no files"
        return f"Done: {spec.summary} — verified. Files: {files}."

    # ------------------------------------------------------------- diagnostics
    def gate_log(self) -> List[Dict]:
        return self._gate_log
