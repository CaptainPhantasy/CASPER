"""
Feature 9 — Legible progress + reversibility.

Two collaborating pieces:

- ProgressTracker: drives the user-visible state machine
  (Planning → Spec Frozen → Building → Verifying → Repairing → Done) and emits
  plain-language updates through callbacks (the dashboard subscribes to these).

- ChangeLedger: an append-only record of every change the system makes, with the
  information needed to undo reversible ones. Creates are undone by quarantining
  the file (never deleting); modifies are undone from a pre-change snapshot or via
  git; moves are reversed. A non-developer can see exactly what changed and roll
  it back.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import time
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, Dict, List, Optional

from core.pipeline.models import ChangeLedgerEntry, PipelineStage, STAGE_LABELS

ProgressCallback = Callable[[Dict], None]


@dataclass
class ProgressEvent:
    stage: PipelineStage
    label: str
    detail: str
    ts: float = field(default_factory=time.time)

    def to_dict(self) -> Dict:
        return {"stage": self.stage.value, "label": self.label, "detail": self.detail, "ts": self.ts}


class ProgressTracker:
    """Tracks and broadcasts user-visible pipeline stages."""

    def __init__(self, run_id: str):
        self.run_id = run_id
        self.current: Optional[ProgressEvent] = None
        self.history: List[ProgressEvent] = []
        self._callbacks: List[ProgressCallback] = []

    def on_update(self, cb: ProgressCallback) -> None:
        self._callbacks.append(cb)

    def set_stage(self, stage: PipelineStage, detail: str = "") -> ProgressEvent:
        event = ProgressEvent(stage=stage, label=STAGE_LABELS.get(stage, stage.value), detail=detail)
        self.current = event
        self.history.append(event)
        payload = {"run_id": self.run_id, **event.to_dict()}
        for cb in self._callbacks:
            try:
                cb(payload)
            except Exception:
                pass
        return event

    def snapshot(self) -> Dict:
        return {
            "run_id": self.run_id,
            "current": self.current.to_dict() if self.current else None,
            "history": [e.to_dict() for e in self.history],
        }


class ChangeLedger:
    """Append-only, undoable record of filesystem changes."""

    def __init__(self, project_root: str):
        self.project_root = Path(project_root)
        self.dir = self.project_root / ".casper" / "ledger"
        self.backups = self.dir / "backups"
        self.quarantine = self.project_root / ".floyd" / "quarantine"
        self.log_path = self.dir / "ledger.jsonl"
        self.entries: List[ChangeLedgerEntry] = []
        for d in (self.dir, self.backups, self.quarantine):
            try:
                d.mkdir(parents=True, exist_ok=True)
            except Exception:
                pass
        self._load()

    def _load(self) -> None:
        if not self.log_path.exists():
            return
        try:
            for line in self.log_path.read_text().splitlines():
                if line.strip():
                    self.entries.append(ChangeLedgerEntry(**json.loads(line)))
        except Exception:
            pass

    def _append(self, entry: ChangeLedgerEntry) -> ChangeLedgerEntry:
        self.entries.append(entry)
        try:
            with open(self.log_path, "a") as f:
                f.write(json.dumps(entry.to_dict()) + "\n")
        except Exception:
            pass
        return entry

    def _abs(self, path: str) -> str:
        return path if os.path.isabs(path) else str(self.project_root / path)

    def _git_tracked(self, path: str) -> bool:
        try:
            r = subprocess.run(
                ["git", "ls-files", "--error-unmatch", path],
                cwd=str(self.project_root), capture_output=True, timeout=5,
            )
            return r.returncode == 0
        except Exception:
            return False

    # --- recording -------------------------------------------------------
    def snapshot_before_modify(self, path: str) -> Optional[str]:
        """Copy the current file aside before it's modified; returns backup ref."""
        full = self._abs(path)
        if not os.path.isfile(full):
            return None
        ref = f"{uuid.uuid4().hex[:10]}_{os.path.basename(full)}"
        try:
            shutil.copy2(full, self.backups / ref)
            return ref
        except Exception:
            return None

    def record_create(self, path: str, summary: str = "") -> ChangeLedgerEntry:
        return self._append(ChangeLedgerEntry.new(
            "create", path, summary or f"Created {path}", reversible=True))

    def record_modify(self, path: str, backup_ref: Optional[str], summary: str = "") -> ChangeLedgerEntry:
        # Reversible via git or a pre-change snapshot.
        reversible = backup_ref is not None or self._git_tracked(path)
        return self._append(ChangeLedgerEntry.new(
            "modify", path, summary or f"Modified {path}", reversible=reversible, undo_ref=backup_ref))

    def record_move(self, src: str, dst: str, summary: str = "") -> ChangeLedgerEntry:
        return self._append(ChangeLedgerEntry.new(
            "move", dst, summary or f"Moved {src} → {dst}", reversible=True, undo_ref=src))

    def record_delete(self, path: str, quarantine_ref: str, summary: str = "") -> ChangeLedgerEntry:
        # Deletes are implemented as quarantine moves, so they're reversible.
        return self._append(ChangeLedgerEntry.new(
            "delete", path, summary or f"Removed {path} (quarantined)", reversible=True, undo_ref=quarantine_ref))

    # --- undo ------------------------------------------------------------
    def undo(self, entry_id: str) -> Dict[str, str]:
        """Reverse a single change. Returns {status, message}."""
        entry = next((e for e in self.entries if e.id == entry_id), None)
        if not entry:
            return {"status": "error", "message": "Unknown change id."}
        if entry.undone:
            return {"status": "noop", "message": "Already undone."}
        if not entry.reversible:
            return {"status": "error", "message": "This change can't be automatically undone."}

        full = self._abs(entry.path) if entry.path else None
        try:
            if entry.action == "create" and full:
                # Quarantine the created file (non-destructive removal).
                if os.path.exists(full):
                    dest = self.quarantine / f"undo_{os.path.basename(full)}_{uuid.uuid4().hex[:6]}"
                    shutil.move(full, dest)
            elif entry.action == "modify" and full:
                if entry.undo_ref and (self.backups / entry.undo_ref).exists():
                    shutil.copy2(self.backups / entry.undo_ref, full)
                elif self._git_tracked(entry.path):
                    subprocess.run(["git", "checkout", "--", entry.path],
                                   cwd=str(self.project_root), timeout=10)
                else:
                    return {"status": "error", "message": "No snapshot available to restore."}
            elif entry.action == "move" and full and entry.undo_ref:
                shutil.move(full, self._abs(entry.undo_ref))
            elif entry.action == "delete" and entry.undo_ref:
                # Restore from quarantine.
                src = entry.undo_ref if os.path.isabs(entry.undo_ref) else str(self.quarantine / entry.undo_ref)
                if os.path.exists(src) and full:
                    shutil.move(src, full)
                else:
                    return {"status": "error", "message": "Quarantined copy not found."}
            entry.undone = True
            return {"status": "ok", "message": f"Reverted: {entry.summary}"}
        except Exception as e:
            return {"status": "error", "message": f"Undo failed: {e}"}

    def human_log(self) -> List[Dict]:
        """Plain-language change log for non-developers."""
        return [
            {"id": e.id, "what": e.summary, "reversible": e.reversible, "undone": e.undone,
             "when": time.strftime("%H:%M:%S", time.localtime(e.ts))}
            for e in self.entries
        ]
