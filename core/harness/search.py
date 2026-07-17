"""Deterministic ranked repository text search."""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable


_IGNORED = {".git", ".casper", "node_modules", ".venv", "venv", "__pycache__", "dist", "build"}


@dataclass(frozen=True)
class SearchHit:
    path: str
    line: int
    column: int
    snippet: str
    score: float
    reasons: tuple[str, ...]


class RepositorySearch:
    """Rank lexical matches using phrase, identifier, path, and token signals."""

    def __init__(self, root: Path | str, *, max_file_bytes: int = 1_000_000) -> None:
        self.root = Path(root).expanduser().resolve()
        self.max_file_bytes = max_file_bytes

    def _files(self, paths: Iterable[Path | str] | None) -> Iterable[Path]:
        candidates = paths if paths is not None else self.root.rglob("*")
        for candidate in candidates:
            path = (self.root / candidate).resolve() if not Path(candidate).is_absolute() else Path(candidate).resolve()
            try:
                relative = path.relative_to(self.root)
            except ValueError as exc:
                raise ValueError(f"path escapes repository root: {candidate}") from exc
            if path.is_file() and not any(part in _IGNORED for part in relative.parts):
                try:
                    if path.stat().st_size <= self.max_file_bytes:
                        yield path
                except OSError:
                    continue

    def search(
        self,
        query: str,
        *,
        paths: Iterable[Path | str] | None = None,
        limit: int = 20,
    ) -> tuple[SearchHit, ...]:
        phrase = query.strip().casefold()
        if not phrase or limit <= 0:
            return ()
        tokens = tuple(dict.fromkeys(re.findall(r"[A-Za-z_][\w.-]*", phrase)))
        hits: list[SearchHit] = []
        for path in self._files(paths):
            relative = path.relative_to(self.root).as_posix()
            try:
                lines = path.read_text(encoding="utf-8", errors="strict").splitlines()
            except (OSError, UnicodeError):
                continue
            path_folded = relative.casefold()
            for number, line in enumerate(lines, start=1):
                folded = line.casefold()
                matched = [token for token in tokens if token in folded]
                if phrase not in folded and len(matched) != len(tokens):
                    continue
                score = 0.0
                reasons: list[str] = []
                if phrase in folded:
                    score += 12.0
                    reasons.append("exact phrase")
                if tokens and all(re.search(rf"\b{re.escape(token)}\b", folded) for token in tokens):
                    score += 5.0
                    reasons.append("whole identifiers")
                if any(token in path_folded for token in tokens):
                    score += 4.0
                    reasons.append("path match")
                score += min(len(matched), 4)
                column = folded.find(phrase)
                if column < 0 and matched:
                    column = min(folded.find(token) for token in matched)
                hits.append(SearchHit(relative, number, column + 1, line.strip()[:300], score, tuple(reasons)))
        hits.sort(key=lambda hit: (-hit.score, hit.path, hit.line, hit.column))
        return tuple(hits[:limit])
