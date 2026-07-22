"""Safe planning and ownership leases for isolated Git worktrees."""

from __future__ import annotations

import hashlib
import json
import os
import re
import time
import uuid
from dataclasses import asdict, dataclass
from pathlib import Path


@dataclass(frozen=True)
class WorktreePlan:
    repository: Path
    path: Path
    branch: str
    base_ref: str
    task_name: str


@dataclass(frozen=True)
class WorktreeLease:
    lease_id: str
    plan: WorktreePlan
    owner: str
    created_at: float
    expires_at: float
    lease_file: Path

    @property
    def expired(self) -> bool:
        return time.time() >= self.expires_at


class WorktreePlanner:
    """Plan isolated paths and lease them; Git creation remains an explicit caller action."""

    def __init__(self, repository: Path | str, state_root: Path | str) -> None:
        self.repository = Path(repository).expanduser().resolve()
        self.state_root = Path(state_root).expanduser().resolve()
        self.lease_root = self.state_root / "worktree-leases"
        self.lease_root.mkdir(parents=True, exist_ok=True)

    @staticmethod
    def _slug(value: str) -> str:
        slug = re.sub(r"[^a-zA-Z0-9]+", "-", value).strip("-").lower()
        return slug[:48] or "task"

    def plan(
        self, task_name: str, *, base_ref: str = "HEAD", worktree_root: Path | str | None = None,
    ) -> WorktreePlan:
        if not task_name.strip() or not base_ref.strip():
            raise ValueError("task_name and base_ref are required")
        slug = self._slug(task_name)
        digest = hashlib.sha256(f"{self.repository}:{task_name}".encode()).hexdigest()[:8]
        root = Path(worktree_root).expanduser().resolve() if worktree_root else self.repository.parent / ".casper-worktrees"
        return WorktreePlan(
            self.repository, root / f"{slug}-{digest}", f"casper/{slug}-{digest}", base_ref, task_name,
        )

    def acquire(self, plan: WorktreePlan, owner: str, *, ttl_seconds: float = 3_600) -> WorktreeLease:
        if plan.repository != self.repository:
            raise ValueError("worktree plan belongs to another repository")
        if not owner.strip() or ttl_seconds <= 0:
            raise ValueError("owner and positive ttl_seconds are required")
        key = hashlib.sha256(str(plan.path).encode()).hexdigest()[:24]
        lease_file = self.lease_root / f"{key}.json"
        if lease_file.exists():
            try:
                existing = json.loads(lease_file.read_text(encoding="utf-8"))
                if float(existing.get("expires_at", 0)) <= time.time():
                    lease_file.unlink()
            except (OSError, ValueError, json.JSONDecodeError):
                raise RuntimeError(f"invalid existing lease: {lease_file}") from None
        lease = WorktreeLease(
            f"lease_{uuid.uuid4().hex[:16]}", plan, owner, time.time(),
            time.time() + ttl_seconds, lease_file,
        )
        payload = {
            "lease_id": lease.lease_id, "owner": owner, "created_at": lease.created_at,
            "expires_at": lease.expires_at, "plan": {
                **asdict(plan), "repository": str(plan.repository), "path": str(plan.path),
            },
        }
        try:
            descriptor = os.open(lease_file, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        except FileExistsError:
            raise RuntimeError(f"worktree path is already leased: {plan.path}") from None
        with os.fdopen(descriptor, "w", encoding="utf-8") as stream:
            json.dump(payload, stream, sort_keys=True)
            stream.flush()
            os.fsync(stream.fileno())
        return lease

    def release(self, lease: WorktreeLease) -> bool:
        try:
            payload = json.loads(lease.lease_file.read_text(encoding="utf-8"))
        except FileNotFoundError:
            return False
        if payload.get("lease_id") != lease.lease_id:
            raise RuntimeError("lease ownership changed; refusing release")
        lease.lease_file.unlink()
        return True
