"""
Shared data models for the CASPER Prime execution pipeline.

The pipeline turns a messy human request into a verified, reversible result
through a sequence of stages:

    INTAKE → COMPILING → (AWAITING_CLARIFICATION) → SPEC_FROZEN → PLANNING
           → ROUTING → BUILDING → VERIFYING → (REPAIRING) → DONE
                                                          ↘ BLOCKED / FAILED

Every model here is plain-data (dataclass) and JSON-serializable so it can be
streamed to the dashboard, persisted to the change ledger, and replayed.

Design rules:
- The FrozenSpec is the contract. Once frozen it is content-hash sealed; any
  downstream stage validates against it and the hash detects tampering.
- Nothing in this module performs I/O or calls an LLM. Stages do that; models
  only describe state. This keeps the contract testable in isolation.
"""

from __future__ import annotations

import hashlib
import json
import time
import uuid
from dataclasses import dataclass, field, asdict
from enum import Enum
from typing import Any, Dict, List, Optional

# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------


class PipelineStage(str, Enum):
    """User-visible pipeline stages (Feature 9 — legible progress)."""

    INTAKE = "intake"
    COMPILING = "compiling"
    AWAITING_CLARIFICATION = "awaiting_clarification"
    SPEC_FROZEN = "spec_frozen"
    PLANNING = "planning"
    ROUTING = "routing"
    BUILDING = "building"
    VERIFYING = "verifying"
    REPAIRING = "repairing"
    DONE = "done"
    BLOCKED = "blocked"
    FAILED = "failed"


# Human-friendly labels for each stage, shown to non-developers.
STAGE_LABELS: Dict[str, str] = {
    PipelineStage.INTAKE: "Understanding your request",
    PipelineStage.COMPILING: "Turning it into a clear plan",
    PipelineStage.AWAITING_CLARIFICATION: "I need a quick confirmation",
    PipelineStage.SPEC_FROZEN: "Plan locked in",
    PipelineStage.PLANNING: "Breaking the work into steps",
    PipelineStage.ROUTING: "Assigning the right specialist",
    PipelineStage.BUILDING: "Building",
    PipelineStage.VERIFYING: "Checking the work actually works",
    PipelineStage.REPAIRING: "Fixing an issue I found",
    PipelineStage.DONE: "Done",
    PipelineStage.BLOCKED: "I need your help to continue",
    PipelineStage.FAILED: "I couldn't finish this",
}


class TaskKind(str, Enum):
    """Cognitive load classification used by the task-aware router (Feature 4)."""

    ARCHITECTURE = "architecture"  # system design, hard tradeoffs
    REASONING = "reasoning"  # multi-step problem solving
    DEBUGGING = "debugging"  # diagnose a failure
    REPAIR = "repair"  # fix after a failed verification
    CODE_GEN = "code_gen"  # write new feature code
    MECHANICAL = "mechanical"  # rename/move/delete, simple edits
    FORMATTING = "formatting"  # lint/format/style
    ORGANIZATION = "organization"  # repo cleanup, file shuffling
    CLASSIFICATION = "classification"  # routing/labeling decisions


class ModelClass(str, Enum):
    """Abstract model tiers; resolved to concrete model ids at runtime."""

    FRONTIER = "frontier"  # most capable (architecture, debugging, repair)
    STANDARD = "standard"  # balanced default (most code generation)
    CHEAP = "cheap"  # fast/cheap (mechanical, formatting, organization)
    TINY = "tiny"  # smallest (classification/routing)


class RiskLevel(str, Enum):
    """Risk tiers for graduated autonomy (Feature 7)."""

    SAFE = "safe"  # reversible, local, no cost — auto-approve
    LOW = "low"  # reversible, minor — auto-approve
    MODERATE = "moderate"  # reversible but notable — auto with note
    HIGH = "high"  # irreversible / costly / credential — escalate
    CRITICAL = "critical"  # public impact / destructive — always escalate


class CheckKind(str, Enum):
    BUILD = "build"
    TEST = "test"
    RUN = "run"
    SPEC = "spec"
    LINT = "lint"


def _now() -> float:
    return time.time()


def _new_id(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid4().hex[:12]}"


# ---------------------------------------------------------------------------
# Input compiler artifacts (Feature 1)
# ---------------------------------------------------------------------------


@dataclass
class ClarifyingQuestion:
    """A single bounded question the compiler needs answered before freezing."""

    id: str
    question: str
    why: str  # why this matters, in plain language
    options: List[str] = field(default_factory=list)  # optional multiple-choice
    required: bool = True
    answer: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class Assumption:
    """An assumption the compiler made to fill a gap, surfaced for confirmation."""

    statement: str  # "I'm assuming React with no authentication"
    basis: str  # why the assumption is reasonable
    confidence: float = 0.5  # 0..1
    confirmed: Optional[bool] = None

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class SpecRequirement:
    """One atomic, independently-verifiable requirement."""

    id: str
    text: str
    acceptance_criteria: List[str] = field(default_factory=list)
    priority: str = "must"  # must | should | could

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class FrozenSpec:
    """
    The immutable contract produced by the Input Compiler. Once frozen it is
    sealed with a content hash; downstream stages verify against `requirements`
    and `content_hash`.
    """

    spec_id: str
    source_intent: str
    summary: str
    requirements: List[SpecRequirement] = field(default_factory=list)
    assumptions: List[Assumption] = field(default_factory=list)
    constraints: List[str] = field(default_factory=list)
    out_of_scope: List[str] = field(default_factory=list)
    open_questions: List[ClarifyingQuestion] = field(default_factory=list)
    created_at: float = field(default_factory=_now)
    frozen: bool = False
    content_hash: Optional[str] = None

    # --- lifecycle -------------------------------------------------------
    def _canonical_payload(self) -> str:
        """Stable, order-independent serialization used for hashing."""
        payload = {
            "source_intent": self.source_intent,
            "summary": self.summary,
            "requirements": sorted(
                (
                    [r.id, r.text, sorted(r.acceptance_criteria), r.priority]
                    for r in self.requirements
                ),
                key=lambda x: x[0],
            ),
            "constraints": sorted(self.constraints),
            "out_of_scope": sorted(self.out_of_scope),
        }
        return json.dumps(payload, sort_keys=True, ensure_ascii=False)

    def compute_hash(self) -> str:
        return hashlib.sha256(self._canonical_payload().encode("utf-8")).hexdigest()

    def freeze(self) -> "FrozenSpec":
        """Seal the spec. Idempotent; raises if there are required open questions."""
        unresolved = [q for q in self.open_questions if q.required and not q.answer]
        if unresolved:
            raise SpecNotReadyError(
                f"Cannot freeze spec with {len(unresolved)} unanswered required question(s)."
            )
        self.content_hash = self.compute_hash()
        self.frozen = True
        return self

    def verify_integrity(self) -> bool:
        """True if the spec has not been mutated since freezing."""
        return bool(self.frozen and self.content_hash == self.compute_hash())

    def requirement_ids(self) -> List[str]:
        return [r.id for r in self.requirements]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "spec_id": self.spec_id,
            "source_intent": self.source_intent,
            "summary": self.summary,
            "requirements": [r.to_dict() for r in self.requirements],
            "assumptions": [a.to_dict() for a in self.assumptions],
            "constraints": self.constraints,
            "out_of_scope": self.out_of_scope,
            "open_questions": [q.to_dict() for q in self.open_questions],
            "created_at": self.created_at,
            "frozen": self.frozen,
            "content_hash": self.content_hash,
        }

    @staticmethod
    def new(source_intent: str, summary: str = "") -> "FrozenSpec":
        return FrozenSpec(
            spec_id=_new_id("spec"), source_intent=source_intent, summary=summary
        )


# ---------------------------------------------------------------------------
# Planning / execution units (Feature 3)
# ---------------------------------------------------------------------------


@dataclass
class TaskUnit:
    """
    One independently-verifiable unit of work. Carries ONLY the context a worker
    needs (subtask + relevant paths + the spec slice it satisfies) so workers
    are never polluted with full project knowledge.
    """

    id: str
    title: str
    description: str
    requirement_ids: List[str] = field(default_factory=list)
    relevant_paths: List[str] = field(default_factory=list)
    depends_on: List[str] = field(default_factory=list)
    kind: TaskKind = TaskKind.CODE_GEN
    skill_id: Optional[str] = None
    attempts: int = 0

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        d["kind"] = self.kind.value
        return d

    @staticmethod
    def new(title: str, description: str, **kw: Any) -> "TaskUnit":
        return TaskUnit(id=_new_id("unit"), title=title, description=description, **kw)


# ---------------------------------------------------------------------------
# Verification (Feature 2)
# ---------------------------------------------------------------------------


@dataclass
class VerificationCheck:
    name: str
    kind: CheckKind
    passed: bool
    detail: str = ""  # raw/technical detail (logs, errors)
    human_summary: str = ""  # plain-language summary

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        d["kind"] = self.kind.value
        return d


@dataclass
class VerificationResult:
    unit_id: str
    passed: bool
    checks: List[VerificationCheck] = field(default_factory=list)
    unmet_requirements: List[str] = field(default_factory=list)
    human_summary: str = ""
    attempt: int = 1

    @property
    def failed_checks(self) -> List[VerificationCheck]:
        return [c for c in self.checks if not c.passed]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "unit_id": self.unit_id,
            "passed": self.passed,
            "checks": [c.to_dict() for c in self.checks],
            "unmet_requirements": self.unmet_requirements,
            "human_summary": self.human_summary,
            "attempt": self.attempt,
        }


# ---------------------------------------------------------------------------
# Graduated autonomy (Feature 7)
# ---------------------------------------------------------------------------


@dataclass
class AutonomyDecision:
    action: str
    risk: RiskLevel
    auto_approved: bool
    consequence: str  # plain-language "what this will do"
    recommendation: str = ""  # plain-language suggestion
    rationale: str = ""  # why this risk level

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        d["risk"] = self.risk.value
        return d


# ---------------------------------------------------------------------------
# Reversibility ledger (Feature 9)
# ---------------------------------------------------------------------------


@dataclass
class ChangeLedgerEntry:
    id: str
    action: str  # create | modify | delete | move | command
    path: Optional[str]
    summary: str
    reversible: bool
    undo_ref: Optional[str] = None  # e.g. quarantine path or git ref/backup
    ts: float = field(default_factory=_now)
    undone: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @staticmethod
    def new(
        action: str,
        path: Optional[str],
        summary: str,
        reversible: bool,
        undo_ref: Optional[str] = None,
    ) -> "ChangeLedgerEntry":
        return ChangeLedgerEntry(
            id=_new_id("chg"),
            action=action,
            path=path,
            summary=summary,
            reversible=reversible,
            undo_ref=undo_ref,
        )


# ---------------------------------------------------------------------------
# Errors
# ---------------------------------------------------------------------------


class PipelineError(Exception):
    """Base class for pipeline errors."""


class SpecNotReadyError(PipelineError):
    """Raised when freezing a spec that still has unanswered required questions."""


class ClarificationRequired(PipelineError):
    """Raised by the compiler when it must ask the user before continuing."""

    def __init__(self, questions: List[ClarifyingQuestion], partial_spec: FrozenSpec):
        self.questions = questions
        self.partial_spec = partial_spec
        super().__init__(
            f"{len(questions)} clarifying question(s) required before execution."
        )
