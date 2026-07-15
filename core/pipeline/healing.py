"""
Feature 8 — Self-healing repair loop.

When verification fails, the system tries to fix itself before bothering the
human:

1. Diagnose: turn the failed checks into a concrete, actionable problem statement.
2. Repair: regenerate/patch the affected artifact(s), escalating to a stronger
   model on each retry (via the task-aware router's escalation ladder).
3. Re-verify: run the Verifier again.

It loops up to `max_attempts`. Only when it still can't pass does it surface to
the user — in plain language, with options ("retry with more detail", "skip this
part", "let me fix it myself") — never a raw stack trace.
"""

from __future__ import annotations

import logging
import os
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Awaitable, Callable, Dict, List, Optional

from core.pipeline.models import (
    FrozenSpec,
    SpecRequirement,
    TaskUnit,
    VerificationResult,
)
from core.pipeline.routing import TaskAwareRouter
from core.pipeline.verifier import Verifier, VerificationPlan
from core.services.llm import llm_service

logger = logging.getLogger(__name__)

# A repair executor applies a fix and returns the (possibly updated) artifact paths.
RepairExecutor = Callable[["RepairRequest"], Awaitable[List[str]]]

_REPAIR_SYSTEM = (
    "You are CASPER's repair engineer. You are given an artifact that failed "
    "verification and the specific reasons. Output the COMPLETE corrected file "
    "content only — no explanation, no markdown fences."
)


@dataclass
class RepairRequest:
    spec: FrozenSpec
    unit: TaskUnit
    artifacts: List[str]
    diagnosis: str
    model: str
    unmet: List[SpecRequirement] = field(default_factory=list)


@dataclass
class HealingOutcome:
    success: bool
    attempts: int
    final_verification: VerificationResult
    repair_notes: List[str] = field(default_factory=list)
    blocked: bool = False
    user_options: List[str] = field(default_factory=list)
    human_summary: str = ""

    def to_dict(self) -> Dict:
        return {
            "success": self.success,
            "attempts": self.attempts,
            "blocked": self.blocked,
            "repair_notes": self.repair_notes,
            "user_options": self.user_options,
            "human_summary": self.human_summary,
            "verification": self.final_verification.to_dict(),
        }


class SelfHealingLoop:
    def __init__(
        self,
        project_root: str,
        verifier: Verifier,
        router: TaskAwareRouter,
        repair_executor: Optional[RepairExecutor] = None,
        max_attempts: int = 2,
    ):
        self.project_root = project_root
        self.verifier = verifier
        self.router = router
        self.repair_executor = repair_executor or self._default_file_repair
        self.max_attempts = max_attempts

    async def heal(
        self,
        spec: FrozenSpec,
        unit: TaskUnit,
        artifacts: List[str],
        verification: VerificationResult,
        plan: Optional[VerificationPlan] = None,
    ) -> HealingOutcome:
        notes: List[str] = []
        current = verification

        for attempt in range(1, self.max_attempts + 1):
            if current.passed:
                break
            diagnosis = self._diagnose(current)
            notes.append(f"Attempt {attempt}: {diagnosis}")

            # Escalate model on each retry: bump the unit's attempt count and re-route.
            unit.attempts += 1
            route = await self.router.route(unit)
            notes.append(
                f"Routing repair to {route.model_class.value} ({route.model})."
            )

            req_map = {r.id: r for r in spec.requirements}
            unmet_reqs = [
                req_map[i] for i in current.unmet_requirements if i in req_map
            ]

            try:
                artifacts = await self.repair_executor(
                    RepairRequest(
                        spec=spec,
                        unit=unit,
                        artifacts=artifacts,
                        diagnosis=diagnosis,
                        model=route.model,
                        unmet=unmet_reqs,
                    )
                )
            except Exception as e:
                notes.append(f"Repair step errored: {e}")
                break

            current = await self.verifier.verify(spec, unit, artifacts, plan)

        if current.passed:
            return HealingOutcome(
                success=True,
                attempts=unit.attempts,
                final_verification=current,
                repair_notes=notes,
                human_summary="Found and fixed the issue automatically; the work now passes verification.",
            )

        # Could not self-heal — surface in plain language with options.
        return HealingOutcome(
            success=False,
            attempts=unit.attempts,
            final_verification=current,
            repair_notes=notes,
            blocked=True,
            user_options=[
                "Give me a bit more detail about what you want and I'll retry.",
                "Skip this part for now and continue with the rest.",
                "Show me the technical details so I (or a developer) can look.",
            ],
            human_summary=(
                "I tried to fix this myself but couldn't get it to pass. "
                + current.human_summary
            ),
        )

    # --- diagnosis -------------------------------------------------------
    def _diagnose(self, verification: VerificationResult) -> str:
        problems = []
        for c in verification.failed_checks:
            line = f"[{c.kind.value}] {c.human_summary}"
            if c.detail:
                line += f" Details: {c.detail[:300]}"
            problems.append(line)
        return " | ".join(problems) or "Verification failed for an unknown reason."

    # --- default repair executor ----------------------------------------
    async def _default_file_repair(self, req: RepairRequest) -> List[str]:
        """Regenerate the first text artifact to satisfy the unmet requirements.
        Pipelines can inject a richer executor (e.g. the full worker agent)."""
        target = next((a for a in req.artifacts if self._is_textual(a)), None)
        if not target:
            return req.artifacts
        full = (
            target if os.path.isabs(target) else os.path.join(self.project_root, target)
        )
        try:
            current = (
                Path(full).read_text(encoding="utf-8", errors="replace")
                if os.path.isfile(full)
                else ""
            )
        except Exception:
            current = ""

        reqs = (
            "\n".join(
                f"- {r.text} (acceptance: {'; '.join(r.acceptance_criteria) or 'n/a'})"
                for r in req.unmet
            )
            or "- Satisfy the original task."
        )
        prompt = (
            f"The file `{target}` failed verification.\n\n"
            f"PROBLEMS:\n{req.diagnosis}\n\n"
            f"REQUIREMENTS THAT MUST NOW BE MET:\n{reqs}\n\n"
            f"CURRENT FILE CONTENT:\n{current}\n\n"
            "Return the COMPLETE corrected file content only."
        )
        fixed = await llm_service.complete(
            prompt=prompt, system=_REPAIR_SYSTEM, model=req.model, max_tokens=2000
        )
        fixed = self._strip_fences(fixed)
        if fixed.strip():
            try:
                Path(full).write_text(fixed, encoding="utf-8")
            except Exception as e:
                logger.warning(f"Could not write repaired file {full}: {e}")
        return req.artifacts

    @staticmethod
    def _is_textual(path: str) -> bool:
        return any(
            path.endswith(ext)
            for ext in (
                ".py",
                ".ts",
                ".tsx",
                ".js",
                ".jsx",
                ".json",
                ".md",
                ".txt",
                ".css",
                ".html",
                ".yaml",
                ".yml",
            )
        )

    @staticmethod
    def _strip_fences(text: str) -> str:
        if not text:
            return ""
        t = text.strip()
        t = re.sub(r"^```[a-zA-Z0-9]*\n?", "", t)
        t = re.sub(r"\n?```$", "", t)
        return t
