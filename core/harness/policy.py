"""One permission and approval gate for every harness tool call."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from .models import ToolCall, ToolSpec


class PermissionMode(str, Enum):
    READ_ONLY = "read_only"
    DEFAULT = "default"
    ACCEPT_EDITS = "accept_edits"
    BYPASS = "bypass"


class PolicyDisposition(str, Enum):
    ALLOW = "allow"
    REQUIRE_APPROVAL = "require_approval"
    DENY = "deny"


@dataclass(frozen=True)
class PolicyDecision:
    disposition: PolicyDisposition
    reason: str
    consequence: str
    recommendation: str

    @property
    def allowed(self) -> bool:
        return self.disposition == PolicyDisposition.ALLOW


class PolicyEngine:
    """Deterministic risk gate; approvals are scoped to one tool call id."""

    _RISK_ORDER = {"safe": 0, "low": 1, "moderate": 2, "high": 3, "critical": 4}

    def __init__(self, mode: PermissionMode = PermissionMode.DEFAULT) -> None:
        self.mode = mode
        self._approvals: set[str] = set()

    def set_mode(self, mode: PermissionMode | str) -> None:
        self.mode = PermissionMode(mode)

    def approve(self, call_id: str) -> None:
        if not call_id:
            raise ValueError("an approval requires a tool call id")
        self._approvals.add(call_id)

    def revoke(self, call_id: str) -> None:
        self._approvals.discard(call_id)

    def decide(self, spec: ToolSpec, call: ToolCall) -> PolicyDecision:
        risk = spec.risk if spec.risk in self._RISK_ORDER else "moderate"
        if call.id in self._approvals:
            self._approvals.remove(call.id)
            return self._decision(PolicyDisposition.ALLOW, spec, "The operator approved this exact tool call.")
        if self.mode == PermissionMode.READ_ONLY and spec.mutates:
            return self._decision(PolicyDisposition.DENY, spec, "Read-only mode prohibits mutations.")
        if risk == "critical":
            return self._decision(
                PolicyDisposition.REQUIRE_APPROVAL, spec,
                "Critical actions always require explicit approval, including in bypass mode.",
            )
        if self.mode == PermissionMode.BYPASS:
            return self._decision(PolicyDisposition.ALLOW, spec, "Bypass mode allows non-critical actions.")
        if not spec.mutates and risk in {"safe", "low"}:
            return self._decision(PolicyDisposition.ALLOW, spec, "This is a bounded read-only action.")
        if self.mode == PermissionMode.ACCEPT_EDITS and risk in {"safe", "low", "moderate"}:
            return self._decision(PolicyDisposition.ALLOW, spec, "Accept-edits mode allows local reversible changes.")
        return self._decision(
            PolicyDisposition.REQUIRE_APPROVAL, spec,
            "The action mutates state, accesses an external capability, or has elevated risk.",
        )

    @staticmethod
    def _decision(disposition: PolicyDisposition, spec: ToolSpec, reason: str) -> PolicyDecision:
        capabilities = ", ".join(spec.capabilities) or "local project resources"
        consequence = (
            f"{spec.name} can change {capabilities}." if spec.mutates
            else f"{spec.name} can read {capabilities}."
        )
        recommendation = {
            PolicyDisposition.ALLOW: "Proceed with the bounded call.",
            PolicyDisposition.REQUIRE_APPROVAL: "Review the exact arguments before approving.",
            PolicyDisposition.DENY: "Change permission mode only if this mutation is intended.",
        }[disposition]
        return PolicyDecision(disposition, reason, consequence, recommendation)
