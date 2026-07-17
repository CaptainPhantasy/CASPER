"""Portable polling file-change detection without external dependencies."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from pathlib import Path


_IGNORED = {".git", ".casper", ".venv", "venv", "node_modules", "__pycache__"}


@dataclass(frozen=True)
class FileState:
    path: str
    size: int
    mtime_ns: int
    sha256: str


@dataclass(frozen=True)
class FileChange:
    path: str
    kind: str
    before: FileState | None
    after: FileState | None


class FileChangeDetector:
    """Compare content-hashed snapshots to detect creates, writes, and deletes."""

    def __init__(self, root: Path | str) -> None:
        self.root = Path(root).expanduser().resolve()
        self._previous: dict[str, FileState] | None = None

    def snapshot(self) -> dict[str, FileState]:
        states: dict[str, FileState] = {}
        for path in self.root.rglob("*"):
            if not path.is_file():
                continue
            relative = path.relative_to(self.root)
            if any(part in _IGNORED for part in relative.parts):
                continue
            try:
                stat = path.stat()
                digest = hashlib.sha256(path.read_bytes()).hexdigest()
            except OSError:
                continue
            key = relative.as_posix()
            states[key] = FileState(key, stat.st_size, stat.st_mtime_ns, digest)
        return states

    @staticmethod
    def diff(
        before: dict[str, FileState],
        after: dict[str, FileState],
    ) -> tuple[FileChange, ...]:
        changes: list[FileChange] = []
        for path in sorted(before.keys() | after.keys()):
            old = before.get(path)
            new = after.get(path)
            if old is None:
                changes.append(FileChange(path, "created", None, new))
            elif new is None:
                changes.append(FileChange(path, "deleted", old, None))
            elif old.sha256 != new.sha256:
                changes.append(FileChange(path, "modified", old, new))
        return tuple(changes)

    def poll(self) -> tuple[FileChange, ...]:
        current = self.snapshot()
        if self._previous is None:
            self._previous = current
            return ()
        changes = self.diff(self._previous, current)
        self._previous = current
        return changes
