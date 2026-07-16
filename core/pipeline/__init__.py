"""
CASPER Prime execution pipeline.

A trustworthy, non-developer-friendly loop that turns messy intent into a
verified, reversible result. See `pipeline.py` for the orchestrator and each
feature module for the individual stages:

  models    — shared, JSON-serializable data contracts
  compiler  — F1 Input Compiler (intent → frozen spec)
  verifier  — F2 adversarial, spec-based verification
  context   — F3 minimal context slices, discarded on completion
  routing   — F4 task-aware model routing + escalation
  skills    — F5 versioned, retrievable skills registry
  autonomy  — F7 graduated autonomy gates (plain-language)
  healing   — F8 self-healing repair loop
  progress  — F9 legible progress + reversibility ledger
  bootstrap — F6 environment bootstrapping
  pipeline  — orchestrates all of the above
"""

from core.pipeline.models import (
    PipelineStage,
    STAGE_LABELS,
    TaskKind,
    ModelClass,
    RiskLevel,
    FrozenSpec,
    SpecRequirement,
    Assumption,
    ClarifyingQuestion,
    TaskUnit,
    VerificationResult,
    AutonomyDecision,
    ChangeLedgerEntry,
    ClarificationRequired,
)
from core.pipeline.compiler import InputCompiler
from core.pipeline.verifier import Verifier, VerificationPlan
from core.pipeline.context import ContextManager, GlobalPlan, WorkerContext, UnitOutcome
from core.pipeline.routing import TaskAwareRouter, BudgetState, RouteDecision
from core.pipeline.skills import SkillRegistry, Skill, ensure_seed_skills
from core.pipeline.autonomy import GraduatedAutonomy, AutonomyMode, ProposedAction
from core.pipeline.healing import SelfHealingLoop, HealingOutcome
from core.pipeline.progress import ProgressTracker, ChangeLedger
from core.pipeline.bootstrap import EnvironmentBootstrapper, EnvReport
from core.pipeline.pipeline import Pipeline, PipelineResult

__all__ = [
    "Pipeline",
    "PipelineResult",
    "InputCompiler",
    "Verifier",
    "VerificationPlan",
    "ContextManager",
    "GlobalPlan",
    "WorkerContext",
    "UnitOutcome",
    "TaskAwareRouter",
    "BudgetState",
    "RouteDecision",
    "SkillRegistry",
    "Skill",
    "ensure_seed_skills",
    "GraduatedAutonomy",
    "AutonomyMode",
    "ProposedAction",
    "SelfHealingLoop",
    "HealingOutcome",
    "ProgressTracker",
    "ChangeLedger",
    "EnvironmentBootstrapper",
    "EnvReport",
    "PipelineStage",
    "STAGE_LABELS",
    "TaskKind",
    "ModelClass",
    "RiskLevel",
    "FrozenSpec",
    "SpecRequirement",
    "Assumption",
    "ClarifyingQuestion",
    "TaskUnit",
    "VerificationResult",
    "AutonomyDecision",
    "ChangeLedgerEntry",
    "ClarificationRequired",
]
