"""
Feature 4 — Task-aware model routing.

Routes work to a model *class* based on the cognitive load of the task, not the
agent's role. Reasoning/architecture/debugging/repair go to the frontier model;
mechanical/formatting/organization go to the cheap model; routing/classification
goes to the tiny model. Two extra behaviors make it adaptive:

- Escalation: if a unit fails verification, the next attempt is promoted to a
  stronger class (cheap → standard → frontier). The verifier's pass/fail is the
  feedback signal.
- Budget awareness: a soft token budget can downgrade non-critical work to a
  cheaper class once most of the budget is spent (frontier reasoning is never
  downgraded below `standard`).

Concrete model ids are resolved at runtime by `LLMService` (no hardcoding).
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Dict, Optional

from core.pipeline.models import TaskKind, ModelClass, TaskUnit
from core.services.llm import llm_service

logger = logging.getLogger(__name__)


# Base mapping: task cognitive load → model class.
_KIND_TO_CLASS: Dict[TaskKind, ModelClass] = {
    TaskKind.ARCHITECTURE: ModelClass.FRONTIER,
    TaskKind.REASONING: ModelClass.FRONTIER,
    TaskKind.DEBUGGING: ModelClass.FRONTIER,
    TaskKind.REPAIR: ModelClass.FRONTIER,
    TaskKind.CODE_GEN: ModelClass.STANDARD,
    TaskKind.MECHANICAL: ModelClass.CHEAP,
    TaskKind.FORMATTING: ModelClass.CHEAP,
    TaskKind.ORGANIZATION: ModelClass.CHEAP,
    TaskKind.CLASSIFICATION: ModelClass.TINY,
}

# Escalation ladder (weakest → strongest).
_LADDER = [ModelClass.TINY, ModelClass.CHEAP, ModelClass.STANDARD, ModelClass.FRONTIER]


@dataclass
class RouteDecision:
    task_kind: TaskKind
    model_class: ModelClass
    provider: str
    model: str
    tier: str  # the tier string passed to LLMService
    escalated_from: Optional[ModelClass] = None
    downgraded_from: Optional[ModelClass] = None
    rationale: str = ""

    def to_dict(self) -> Dict:
        d = {
            "task_kind": self.task_kind.value,
            "model_class": self.model_class.value,
            "provider": self.provider,
            "model": self.model,
            "tier": self.tier,
            "rationale": self.rationale,
        }
        if self.escalated_from:
            d["escalated_from"] = self.escalated_from.value
        if self.downgraded_from:
            d["downgraded_from"] = self.downgraded_from.value
        return d


@dataclass
class BudgetState:
    """Soft token budget. `limit_tokens=None` means unlimited."""

    limit_tokens: Optional[int] = None
    spent_tokens: int = 0

    def fraction_spent(self) -> float:
        if not self.limit_tokens:
            return 0.0
        return min(1.0, self.spent_tokens / max(1, self.limit_tokens))

    def record(self, tokens: int) -> None:
        self.spent_tokens += max(0, int(tokens or 0))


class TaskAwareRouter:
    """Resolves the model class + concrete model for a unit of work."""

    def __init__(
        self, provider: str = "anthropic", budget: Optional[BudgetState] = None
    ):
        self.provider = provider
        self.budget = budget or BudgetState()

    @staticmethod
    def classify_kind(unit: TaskUnit) -> TaskKind:
        """If a unit doesn't declare a kind, infer it from keywords. (A tiny LLM
        could do this; keyword heuristics keep it free and deterministic.)"""
        if unit.kind:
            return unit.kind
        text = f"{unit.title} {unit.description}".lower()
        if any(k in text for k in ("architect", "design", "trade-off", "approach")):
            return TaskKind.ARCHITECTURE
        if any(k in text for k in ("debug", "diagnose", "why is", "failing", "error")):
            return TaskKind.DEBUGGING
        if any(k in text for k in ("rename", "move", "delete", "relocate")):
            return TaskKind.MECHANICAL
        if any(k in text for k in ("format", "lint", "style", "prettier")):
            return TaskKind.FORMATTING
        if any(k in text for k in ("organize", "cleanup", "tidy", "restructure")):
            return TaskKind.ORGANIZATION
        return TaskKind.CODE_GEN

    def _apply_escalation(self, base: ModelClass, attempts: int) -> ModelClass:
        """Promote one rung per prior failed attempt, capped at frontier."""
        if attempts <= 0:
            return base
        idx = min(_LADDER.index(base) + attempts, len(_LADDER) - 1)
        return _LADDER[idx]

    def _apply_budget(self, cls: ModelClass) -> ModelClass:
        """Downgrade non-critical classes when the budget is mostly spent.
        Frontier reasoning is never downgraded below STANDARD."""
        if self.budget.fraction_spent() < 0.8:
            return cls
        if cls == ModelClass.STANDARD:
            return ModelClass.CHEAP
        if cls == ModelClass.CHEAP:
            return ModelClass.TINY
        # FRONTIER stays FRONTIER (don't cripple hard reasoning); TINY stays TINY.
        return cls

    async def route(self, unit: TaskUnit) -> RouteDecision:
        kind = self.classify_kind(unit)
        base_class = _KIND_TO_CLASS.get(kind, ModelClass.STANDARD)

        escalated = self._apply_escalation(base_class, unit.attempts)
        final = self._apply_budget(escalated)

        tier = final.value  # LLMService understands frontier/standard/cheap/tiny
        model = await llm_service.resolve_model(self.provider, tier) or tier

        rationale_bits = [f"{kind.value} → {base_class.value}"]
        if escalated != base_class:
            rationale_bits.append(
                f"escalated to {escalated.value} after {unit.attempts} failed attempt(s)"
            )
        if final != escalated:
            rationale_bits.append(
                f"downgraded to {final.value} (budget {int(self.budget.fraction_spent()*100)}% spent)"
            )

        return RouteDecision(
            task_kind=kind,
            model_class=final,
            provider=self.provider,
            model=model,
            tier=tier,
            escalated_from=base_class if escalated != base_class else None,
            downgraded_from=escalated if final != escalated else None,
            rationale="; ".join(rationale_bits),
        )
