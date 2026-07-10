"""
Feature 2 — Spec-based adversarial verification.

The verifier's job is to *disprove* completion, not to accept a worker's claim.
"Done" requires proof:

- BUILD: the project still builds (if a build command is configured).
- TEST:  the relevant tests pass (if present/configured).
- RUN:   produced artifacts at least import/parse without error.
- SPEC:  every requirement in the unit's slice is checked against the actual
         artifact content. The spec check is adversarial — the model is asked to
         find reasons the work FAILS and defaults to "not met" when uncertain.

A failing verification gates completion and feeds the self-healing/repair loop;
it never silently passes. Results are summarized in plain language.
"""

from __future__ import annotations

import json
import logging
import os
import re
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional

from core.pipeline.models import (
    CheckKind,
    FrozenSpec,
    SpecRequirement,
    TaskUnit,
    VerificationCheck,
    VerificationResult,
)
from core.services.llm import llm_service

logger = logging.getLogger(__name__)

_MAX_ARTIFACT_BYTES = 12_000

_SPEC_JUDGE_SYSTEM = (
    "You are CASPER's adversarial Verifier. Your job is to find reasons the work "
    "does NOT meet the requirement. Be strict: if the artifact does not clearly "
    "satisfy a requirement and its acceptance criteria, mark it NOT met. Reply with "
    "STRICT JSON only."
)


@dataclass
class VerificationPlan:
    """What to run for this verification (kept explicit so it's testable)."""
    build_cmd: Optional[List[str]] = None
    test_cmd: Optional[List[str]] = None
    run_python_artifacts: bool = True
    cwd: Optional[str] = None
    timeout: int = 120


class Verifier:
    def __init__(self, project_root: str):
        self.project_root = project_root

    async def verify(
        self,
        spec: FrozenSpec,
        unit: TaskUnit,
        artifacts: List[str],
        plan: Optional[VerificationPlan] = None,
    ) -> VerificationResult:
        plan = plan or VerificationPlan(cwd=self.project_root)
        plan.cwd = plan.cwd or self.project_root
        checks: List[VerificationCheck] = []

        # 1) BUILD
        if plan.build_cmd:
            checks.append(self._run_command_check("Build", CheckKind.BUILD, plan.build_cmd, plan))

        # 2) TEST
        if plan.test_cmd:
            checks.append(self._run_command_check("Tests", CheckKind.TEST, plan.test_cmd, plan))

        # 3) RUN — artifacts at least parse/import
        if plan.run_python_artifacts:
            for a in artifacts:
                if a.endswith(".py"):
                    checks.append(self._python_parses(a))

        # 4) SPEC — adversarial per-requirement judgement against artifact content
        req_map = {r.id: r for r in spec.requirements}
        slice_reqs = [req_map[rid] for rid in unit.requirement_ids if rid in req_map] or spec.requirements
        unmet: List[str] = []
        artifact_text = self._read_artifacts(artifacts)
        spec_checks, unmet = await self._judge_spec(slice_reqs, artifact_text)
        checks.extend(spec_checks)

        passed = all(c.passed for c in checks) and not unmet
        return VerificationResult(
            unit_id=unit.id,
            passed=passed,
            checks=checks,
            unmet_requirements=unmet,
            human_summary=self._summarize(passed, checks, unmet),
            attempt=unit.attempts + 1,
        )

    # --- individual checks ----------------------------------------------
    def _run_command_check(self, name: str, kind: CheckKind, cmd: List[str], plan: VerificationPlan) -> VerificationCheck:
        try:
            r = subprocess.run(cmd, cwd=plan.cwd, capture_output=True, text=True, timeout=plan.timeout)
            passed = r.returncode == 0
            tail = (r.stdout or "")[-600:] + (r.stderr or "")[-600:]
            return VerificationCheck(
                name=name, kind=kind, passed=passed, detail=tail.strip(),
                human_summary=(f"{name} passed." if passed else f"{name} failed (exit {r.returncode})."),
            )
        except subprocess.TimeoutExpired:
            return VerificationCheck(name=name, kind=kind, passed=False,
                                     detail="timed out", human_summary=f"{name} timed out.")
        except Exception as e:
            return VerificationCheck(name=name, kind=kind, passed=False,
                                     detail=str(e), human_summary=f"{name} could not run: {e}")

    def _python_parses(self, path: str) -> VerificationCheck:
        full = path if os.path.isabs(path) else os.path.join(self.project_root, path)
        try:
            import py_compile
            py_compile.compile(full, doraise=True)
            return VerificationCheck(name=f"Parse {os.path.basename(path)}", kind=CheckKind.RUN,
                                     passed=True, human_summary=f"{os.path.basename(path)} is valid Python.")
        except Exception as e:
            return VerificationCheck(name=f"Parse {os.path.basename(path)}", kind=CheckKind.RUN,
                                     passed=False, detail=str(e),
                                     human_summary=f"{os.path.basename(path)} has a syntax error.")

    async def _judge_spec(self, requirements: List[SpecRequirement], artifact_text: str):
        checks: List[VerificationCheck] = []
        unmet: List[str] = []

        if not artifact_text.strip():
            for r in requirements:
                checks.append(VerificationCheck(
                    name=f"Spec: {r.id}", kind=CheckKind.SPEC, passed=False,
                    detail="No artifact produced.",
                    human_summary=f"Requirement not met (nothing was produced): {r.text}"))
                unmet.append(r.id)
            return checks, unmet

        prompt = self._build_judge_prompt(requirements, artifact_text)
        verdicts: Dict[str, Dict] = {}
        try:
            raw = await llm_service.complete(prompt=prompt, system=_SPEC_JUDGE_SYSTEM,
                                             tier="frontier", max_tokens=1500)
            verdicts = self._parse_verdicts(raw)
        except Exception as e:
            logger.warning(f"Spec judge call failed: {e}")

        for r in requirements:
            v = verdicts.get(r.id)
            if v is None:
                # No verdict → adversarial default is NOT met.
                checks.append(VerificationCheck(
                    name=f"Spec: {r.id}", kind=CheckKind.SPEC, passed=False,
                    detail="No verdict returned; defaulting to not-met.",
                    human_summary=f"Could not confirm: {r.text}"))
                unmet.append(r.id)
                continue
            met = bool(v.get("met"))
            reason = str(v.get("reason", "")).strip()
            checks.append(VerificationCheck(
                name=f"Spec: {r.id}", kind=CheckKind.SPEC, passed=met, detail=reason,
                human_summary=(f"Met: {r.text}" if met else f"Not met: {r.text} — {reason}")))
            if not met:
                unmet.append(r.id)
        return checks, unmet

    def _build_judge_prompt(self, requirements: List[SpecRequirement], artifact_text: str) -> str:
        reqs = "\n".join(
            f'- id={r.id}: {r.text} (acceptance: {"; ".join(r.acceptance_criteria) or "n/a"})'
            for r in requirements
        )
        return (
            "Given the produced artifact(s) below, judge whether EACH requirement is "
            "satisfied. Look for concrete evidence in the artifact. If evidence is "
            "missing or weak, mark met=false.\n\n"
            f"REQUIREMENTS:\n{reqs}\n\n"
            f"ARTIFACT(S):\n{artifact_text}\n\n"
            'Reply with STRICT JSON: {"verdicts": [{"id": "...", "met": true/false, "reason": "short"}]}'
        )

    def _parse_verdicts(self, raw: str) -> Dict[str, Dict]:
        if not raw:
            return {}
        cleaned = re.sub(r"^```(?:json)?|```$", "", raw.strip()).strip()
        start, end = cleaned.find("{"), cleaned.rfind("}")
        if start == -1 or end == -1:
            return {}
        try:
            data = json.loads(cleaned[start:end + 1])
        except Exception:
            return {}
        out: Dict[str, Dict] = {}
        for v in data.get("verdicts", []):
            if isinstance(v, dict) and v.get("id"):
                out[str(v["id"])] = v
        return out

    def _read_artifacts(self, artifacts: List[str]) -> str:
        chunks = []
        for a in artifacts:
            full = a if os.path.isabs(a) else os.path.join(self.project_root, a)
            try:
                if os.path.isfile(full):
                    data = Path(full).read_text(encoding="utf-8", errors="replace")[:_MAX_ARTIFACT_BYTES]
                    chunks.append(f"--- {a} ---\n{data}")
            except Exception:
                continue
        return "\n\n".join(chunks)

    def _summarize(self, passed: bool, checks: List[VerificationCheck], unmet: List[str]) -> str:
        if passed:
            ran = ", ".join(c.name for c in checks) or "basic checks"
            return f"Verified ✓ — {ran} all passed."
        fails = [c.human_summary for c in checks if not c.passed]
        head = "Not verified ✗ — " + f"{len(fails)} check(s) failed."
        return head + (" " + " ".join(fails[:4]) if fails else "")
