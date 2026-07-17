"""Deterministic, evidence-gated goal state for the CASPER shell."""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional
from uuid import uuid4


class GoalError(ValueError):
    """Raised when a requested goal transition violates the state contract."""


class GoalEngine:
    """Persist one active goal per project and enforce proof before completion."""

    def __init__(self, storage_path: Optional[Path] = None, project_root: Optional[Path] = None):
        root = (project_root or Path.cwd()).resolve()
        project_key = hashlib.sha256(str(root).encode("utf-8")).hexdigest()[:16]
        self.storage_path = storage_path or Path.home() / ".casper" / "goals" / f"{project_key}.json"
        self.project_root = root

    @staticmethod
    def _now() -> str:
        return datetime.now(timezone.utc).isoformat()

    def load(self) -> Optional[Dict[str, Any]]:
        if not self.storage_path.exists():
            return None
        with self.storage_path.open(encoding="utf-8") as handle:
            return json.load(handle)

    def _store(self, goal: Dict[str, Any]) -> Dict[str, Any]:
        self.storage_path.parent.mkdir(parents=True, exist_ok=True)
        temporary = self.storage_path.with_suffix(".tmp")
        with temporary.open("w", encoding="utf-8") as handle:
            json.dump(goal, handle, indent=2, sort_keys=True)
            handle.write("\n")
        temporary.replace(self.storage_path)
        return goal

    def start(self, objective: str) -> Dict[str, Any]:
        objective = objective.strip()
        if not objective:
            raise GoalError("A goal objective is required.")

        current = self.load()
        if current and current.get("status") == "active":
            raise GoalError("An active goal already exists. Complete, block, or clear it first.")

        now = self._now()
        return self._store({
            "id": str(uuid4()),
            "objective": objective,
            "project_root": str(self.project_root),
            "status": "active",
            "created_at": now,
            "updated_at": now,
            "evidence": [],
            "verification": None,
            "blocker": None,
        })

    def add_evidence(self, evidence: str) -> Dict[str, Any]:
        goal = self._require_active()
        evidence = evidence.strip()
        if not evidence:
            raise GoalError("Direct evidence is required.")
        goal["evidence"].append({"text": evidence, "recorded_at": self._now()})
        goal["updated_at"] = self._now()
        return self._store(goal)

    def verify(self, passed: bool, result: str) -> Dict[str, Any]:
        goal = self._require_active()
        result = result.strip()
        if not result:
            raise GoalError("A concrete verification result is required.")
        goal["verification"] = {
            "status": "PASS" if passed else "FAIL",
            "result": result,
            "verified_at": self._now(),
        }
        goal["updated_at"] = self._now()
        return self._store(goal)

    def complete(self) -> Dict[str, Any]:
        goal = self._require_active()
        if not goal.get("evidence"):
            raise GoalError("Completion requires at least one direct-evidence record.")
        verification = goal.get("verification") or {}
        if verification.get("status") != "PASS":
            raise GoalError("Completion requires a PASS verification result.")
        goal["status"] = "complete"
        goal["updated_at"] = self._now()
        return self._store(goal)

    def block(self, reason: str) -> Dict[str, Any]:
        goal = self._require_active()
        reason = reason.strip()
        if not reason:
            raise GoalError("A concrete blocker is required.")
        goal["status"] = "blocked"
        goal["blocker"] = reason
        goal["updated_at"] = self._now()
        return self._store(goal)

    def clear(self) -> None:
        self.storage_path.unlink(missing_ok=True)

    def _require_active(self) -> Dict[str, Any]:
        goal = self.load()
        if not goal:
            raise GoalError("No goal exists. Start one with /goal <objective>.")
        if goal.get("status") != "active":
            raise GoalError(f"Goal is {goal.get('status')}; only active goals can be changed.")
        return goal
