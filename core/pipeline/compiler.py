"""
Feature 1 — Input Compiler.

Turns a messy human request into a FrozenSpec: an explicit, content-sealed
contract. It detects missing details, contradictions, and assumed context;
asks bounded clarifying questions when (and only when) a gap would change the
result; surfaces its assumptions in plain language; and emits an immutable spec.

No execution may begin until a FrozenSpec exists and is frozen. That spec is
what the Verifier (Feature 2) later checks the work against.
"""

from __future__ import annotations

import json
import logging
import re
from typing import Any, Dict, List, Optional

from core.pipeline.models import (
    Assumption,
    ClarificationRequired,
    ClarifyingQuestion,
    FrozenSpec,
    SpecRequirement,
    _new_id,
)
from core.services.llm import llm_service

logger = logging.getLogger(__name__)

_COMPILER_SYSTEM = (
    "You are CASPER's Input Compiler. You convert a non-technical user's request "
    "into a precise, buildable specification. You are rigorous about ambiguity: "
    "you surface hidden assumptions and only ask a question when a wrong guess "
    "would materially change what gets built. Always reply with STRICT JSON only."
)

_COMPILER_INSTRUCTION = """\
Analyze the user request and produce a build specification.

Return ONLY a JSON object with this exact shape (no prose, no markdown fences):
{
  "summary": "one-sentence plain-language summary of what will be built",
  "requirements": [
    {"text": "atomic, verifiable requirement",
     "acceptance_criteria": ["how we'll know it's met"],
     "priority": "must|should|could"}
  ],
  "assumptions": [
    {"statement": "an assumption you made to fill a gap, in plain language",
     "basis": "why it's a reasonable default", "confidence": 0.0}
  ],
  "constraints": ["hard constraints (language, framework, no-network, etc.)"],
  "out_of_scope": ["things explicitly NOT included"],
  "clarifying_questions": [
    {"question": "a bounded question",
     "why": "why answering changes the build",
     "options": ["optional", "choices"],
     "required": true}
  ]
}

Rules:
- Prefer assumptions over questions. Ask a question ONLY when a wrong guess would
  produce the wrong result. Never ask more than 4 questions.
- Make requirements atomic and independently verifiable.
- If the request contradicts itself, add a required clarifying_question about it.

User request:
"""


def _extract_json(text: str) -> Optional[Dict[str, Any]]:
    """Best-effort JSON extraction from an LLM reply (handles code fences/prose)."""
    if not text:
        return None
    cleaned = text.strip()
    cleaned = re.sub(r"^```(?:json)?", "", cleaned).strip()
    cleaned = re.sub(r"```$", "", cleaned).strip()
    try:
        return json.loads(cleaned)
    except Exception:
        pass
    # Fall back to the first balanced { ... } block.
    start = cleaned.find("{")
    end = cleaned.rfind("}")
    if start != -1 and end != -1 and end > start:
        try:
            return json.loads(cleaned[start : end + 1])
        except Exception:
            return None
    return None


class InputCompiler:
    """Compiles user intent into a FrozenSpec, asking for clarification when needed."""

    def __init__(self, max_questions: int = 4):
        self.max_questions = max_questions

    async def compile(
        self,
        intent: str,
        answers: Optional[Dict[str, str]] = None,
        prior_spec: Optional[FrozenSpec] = None,
    ) -> FrozenSpec:
        """
        Build a FrozenSpec from `intent`. If required clarifying questions remain
        unanswered, raise ClarificationRequired (carrying the questions + a draft
        spec). Pass the user's answers back in via `answers` (keyed by question id)
        to resolve them and freeze.

        Always returns a *frozen* spec on success.
        """
        answers = answers or {}

        # If we already drafted a spec and just received answers, fold them in.
        if prior_spec is not None:
            return self._apply_answers_and_freeze(prior_spec, answers)

        raw = await self._invoke_llm(intent)
        data = _extract_json(raw) if raw else None

        if not data:
            # Degraded mode (no/failed LLM): build a minimal honest spec so the
            # pipeline still functions, flagged with an explicit assumption.
            logger.warning(
                "Input compiler could not parse an LLM spec; using degraded single-requirement spec."
            )
            spec = FrozenSpec.new(intent, summary=intent.strip()[:140])
            spec.requirements.append(
                SpecRequirement(
                    id=_new_id("req"),
                    text=intent.strip(),
                    acceptance_criteria=[
                        "Output addresses the request as literally stated."
                    ],
                    priority="must",
                )
            )
            spec.assumptions.append(
                Assumption(
                    statement="No clarification was possible; the request is taken literally.",
                    basis="LLM-based compilation was unavailable.",
                    confidence=0.3,
                )
            )
            return spec.freeze()

        spec = self._build_spec(intent, data)

        # Apply any answers provided up-front, then decide if we must ask.
        if answers:
            self._fold_answers(spec, answers)

        unanswered = [q for q in spec.open_questions if q.required and not q.answer]
        if unanswered:
            raise ClarificationRequired(questions=unanswered, partial_spec=spec)

        return spec.freeze()

    # --- internals -------------------------------------------------------

    async def _invoke_llm(self, intent: str) -> str:
        try:
            return await llm_service.complete(
                prompt=_COMPILER_INSTRUCTION + intent.strip(),
                system=_COMPILER_SYSTEM,
                tier="frontier",  # compiling intent is reasoning-heavy
                max_tokens=2000,
            )
        except Exception as e:
            logger.warning(f"Input compiler LLM call failed: {e}")
            return ""

    def _build_spec(self, intent: str, data: Dict[str, Any]) -> FrozenSpec:
        spec = FrozenSpec.new(
            intent, summary=str(data.get("summary", "")).strip() or intent[:140]
        )

        for r in data.get("requirements", []) or []:
            if not isinstance(r, dict):
                continue
            text = str(r.get("text", "")).strip()
            if not text:
                continue
            spec.requirements.append(
                SpecRequirement(
                    id=_new_id("req"),
                    text=text,
                    acceptance_criteria=[
                        str(c)
                        for c in (r.get("acceptance_criteria") or [])
                        if str(c).strip()
                    ],
                    priority=(
                        str(r.get("priority", "must")).lower()
                        if str(r.get("priority", "must")).lower()
                        in ("must", "should", "could")
                        else "must"
                    ),
                )
            )

        # Guarantee at least one requirement.
        if not spec.requirements:
            spec.requirements.append(
                SpecRequirement(
                    id=_new_id("req"),
                    text=intent.strip(),
                    acceptance_criteria=["Output addresses the request."],
                    priority="must",
                )
            )

        for a in data.get("assumptions", []) or []:
            if not isinstance(a, dict):
                continue
            stmt = str(a.get("statement", "")).strip()
            if not stmt:
                continue
            try:
                conf = float(a.get("confidence", 0.5))
            except Exception:
                conf = 0.5
            spec.assumptions.append(
                Assumption(
                    statement=stmt,
                    basis=str(a.get("basis", "")).strip(),
                    confidence=max(0.0, min(1.0, conf)),
                )
            )

        spec.constraints = [
            str(c).strip() for c in (data.get("constraints") or []) if str(c).strip()
        ]
        spec.out_of_scope = [
            str(c).strip() for c in (data.get("out_of_scope") or []) if str(c).strip()
        ]

        for q in (data.get("clarifying_questions") or [])[: self.max_questions]:
            if not isinstance(q, dict):
                continue
            qtext = str(q.get("question", "")).strip()
            if not qtext:
                continue
            spec.open_questions.append(
                ClarifyingQuestion(
                    id=_new_id("q"),
                    question=qtext,
                    why=str(q.get("why", "")).strip(),
                    options=[
                        str(o) for o in (q.get("options") or []) if str(o).strip()
                    ],
                    required=bool(q.get("required", True)),
                )
            )

        return spec

    def _fold_answers(self, spec: FrozenSpec, answers: Dict[str, str]) -> None:
        for q in spec.open_questions:
            if q.id in answers and answers[q.id]:
                q.answer = str(answers[q.id])

    def _apply_answers_and_freeze(
        self, spec: FrozenSpec, answers: Dict[str, str]
    ) -> FrozenSpec:
        self._fold_answers(spec, answers)
        # Promote answered questions into explicit constraints so the contract
        # captures the user's decisions.
        for q in spec.open_questions:
            if q.answer:
                spec.constraints.append(f"{q.question} → {q.answer}")
        still_open = [q for q in spec.open_questions if q.required and not q.answer]
        if still_open:
            raise ClarificationRequired(questions=still_open, partial_spec=spec)
        return spec.freeze()
