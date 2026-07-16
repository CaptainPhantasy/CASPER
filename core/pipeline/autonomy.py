"""
Feature 7 — Graduated autonomy gates.

Instead of asking a non-developer to approve raw low-level operations ("approve
write to factorial.py?"), the gate classifies each proposed action by risk and:

- auto-approves safe / reversible actions,
- escalates dangerous, irreversible, costly, credential-related, or public-impact
  actions, phrased as intent-with-consequence plus a recommendation
  ("Deploying makes this public — approve?").

The decision respects an autonomy MODE (STRICT / AUTO / YOLO) so the existing
approval service can keep its modes, while the *what to escalate* logic becomes
risk-based and human-legible rather than blanket.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from enum import Enum
from typing import Optional

from core.pipeline.models import AutonomyDecision, RiskLevel


class AutonomyMode(str, Enum):
    STRICT = "STRICT"  # escalate everything except trivially safe reads
    AUTO = "AUTO"  # auto safe/low/moderate; escalate high/critical
    YOLO = "YOLO"  # auto everything except CRITICAL


@dataclass
class ProposedAction:
    """A normalized description of something an agent wants to do."""

    action_type: str  # create | modify | delete | move | command | deploy | network | credential | spend
    path: Optional[str] = None
    command: Optional[str] = None
    detail: str = ""
    estimated_cost_usd: float = 0.0
    reversible: Optional[bool] = None  # None → inferred


# Command patterns that are destructive / irreversible / public-impact.
_DESTRUCTIVE_CMD = re.compile(
    r"\b(rm\s+-rf|rm\s+-r|rmdir|drop\s+(table|database)|truncate|mkfs|dd\s+if=|"
    r"git\s+push|git\s+reset\s+--hard|force-push|--force|kubectl\s+delete|terraform\s+destroy)\b",
    re.IGNORECASE,
)
_DEPLOY_CMD = re.compile(
    r"\b(deploy|publish|release|vercel|netlify|heroku|gh\s+release|npm\s+publish|docker\s+push)\b",
    re.IGNORECASE,
)
_NETWORK_SEND = re.compile(
    r"\b(curl|wget|http(ie)?)\b.*\b(-X\s*(POST|PUT|DELETE)|--data|-d\b)", re.IGNORECASE
)
_READ_ONLY_CMD = re.compile(
    r"^\s*(ls|cat|head|tail|grep|rg|find|pwd|echo|wc|stat|git\s+(status|log|diff|show)|"
    r"npm\s+run\s+(build|lint|test)|pytest|python\s+-m\s+pytest|node\s+--version|tsc(\s|$))",
    re.IGNORECASE,
)


class GraduatedAutonomy:
    """Risk classifier + gate decision maker."""

    def __init__(
        self, mode: AutonomyMode = AutonomyMode.AUTO, spend_threshold_usd: float = 1.0
    ):
        self.mode = mode
        self.spend_threshold_usd = spend_threshold_usd

    def set_mode(self, mode: AutonomyMode) -> None:
        self.mode = mode

    # --- risk classification --------------------------------------------
    def classify_risk(self, action: ProposedAction) -> RiskLevel:
        at = action.action_type.lower()
        cmd = action.command or ""

        if at == "delete":
            return RiskLevel.HIGH  # destructive — matches governance no-delete rule
        if at == "credential":
            return RiskLevel.HIGH
        if at == "deploy":
            return RiskLevel.CRITICAL  # public impact
        if at == "spend":
            return (
                RiskLevel.HIGH
                if action.estimated_cost_usd >= self.spend_threshold_usd
                else RiskLevel.MODERATE
            )
        if at == "network":
            return RiskLevel.HIGH  # external send / data leaving the machine
        if at == "move":
            return RiskLevel.LOW  # reversible
        if at in ("create", "modify"):
            return (
                RiskLevel.SAFE
                if self._is_local_reversible(action)
                else RiskLevel.MODERATE
            )
        if at == "command":
            if _DESTRUCTIVE_CMD.search(cmd):
                return RiskLevel.CRITICAL
            if _DEPLOY_CMD.search(cmd):
                return RiskLevel.CRITICAL
            if _NETWORK_SEND.search(cmd):
                return RiskLevel.HIGH
            if _READ_ONLY_CMD.search(cmd):
                return RiskLevel.SAFE
            return RiskLevel.MODERATE  # unknown command — cautious default
        return RiskLevel.MODERATE

    def _is_local_reversible(self, action: ProposedAction) -> bool:
        if action.reversible is not None:
            return action.reversible
        # Local file create/modify is reversible when under version control / ledger.
        return True

    # --- gate decision ---------------------------------------------------
    def assess(self, action: ProposedAction) -> AutonomyDecision:
        risk = self.classify_risk(action)
        auto = self._auto_approves(risk)
        return AutonomyDecision(
            action=self._action_label(action),
            risk=risk,
            auto_approved=auto,
            consequence=self._consequence(action, risk),
            recommendation=self._recommendation(action, risk),
            rationale=self._rationale(action, risk),
        )

    def _auto_approves(self, risk: RiskLevel) -> bool:
        if self.mode == AutonomyMode.STRICT:
            return risk == RiskLevel.SAFE
        if self.mode == AutonomyMode.AUTO:
            return risk in (RiskLevel.SAFE, RiskLevel.LOW, RiskLevel.MODERATE)
        if self.mode == AutonomyMode.YOLO:
            return risk != RiskLevel.CRITICAL
        return False

    # --- plain-language text --------------------------------------------
    def _action_label(self, action: ProposedAction) -> str:
        if action.command:
            return f"run: {action.command.strip()[:120]}"
        if action.path:
            return f"{action.action_type} {action.path}"
        return action.action_type

    def _consequence(self, action: ProposedAction, risk: RiskLevel) -> str:
        at = action.action_type.lower()
        if at == "delete":
            return f"This permanently removes {action.path or 'a file'}. It's quarantined so it can be restored."
        if at == "deploy":
            return "This makes your project publicly accessible on the internet."
        if at == "spend":
            return (
                f"This uses paid API credits (about ${action.estimated_cost_usd:.2f})."
            )
        if at == "network":
            return "This sends data from your machine to an external service."
        if at == "credential":
            return "This reads or changes a secret/API key."
        if at == "move":
            return f"This relocates {action.path or 'a file'}; it can be moved back."
        if at in ("create", "modify"):
            return f"This {'creates' if at == 'create' else 'updates'} {action.path or 'a file'} in your project; it's tracked so you can undo it."
        if at == "command":
            if risk in (RiskLevel.CRITICAL, RiskLevel.HIGH):
                return "This runs a command that could change things outside this project or can't be easily undone."
            return "This runs a routine command in your project."
        return action.detail or "This performs an action in your project."

    def _recommendation(self, action: ProposedAction, risk: RiskLevel) -> str:
        if risk in (RiskLevel.SAFE, RiskLevel.LOW):
            return "Safe to proceed."
        if risk == RiskLevel.MODERATE:
            return "Usually fine — proceed unless this isn't what you wanted."
        if risk == RiskLevel.HIGH:
            return "Review before approving; this is hard to undo."
        return "Approve only if you intend this to go live / be permanent."

    def _rationale(self, action: ProposedAction, risk: RiskLevel) -> str:
        return f"action_type={action.action_type}, risk={risk.value}, mode={self.mode.value}"
