"""Git-aware repository indexing, selection, and deterministic compaction."""

from __future__ import annotations

import re
import subprocess
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Iterable


_IGNORED = {".git", ".casper", "node_modules", "venv", ".venv", "__pycache__", "dist", "build"}
_TEXT_SUFFIXES = {".py", ".js", ".jsx", ".ts", ".tsx", ".go", ".rs", ".java", ".md", ".toml", ".json", ".yaml", ".yml"}


@dataclass(frozen=True)
class IndexedFile:
    path: str
    size: int
    symbols: tuple[str, ...] = ()


@dataclass
class ContextPack:
    query: str
    instructions: list[str] = field(default_factory=list)
    files: dict[str, str] = field(default_factory=dict)
    approx_tokens: int = 0
    truncated: bool = False

    def render(self) -> str:
        chunks = [f"Repository context for: {self.query}"]
        if self.instructions:
            chunks.append("Instructions: " + ", ".join(self.instructions))
        for path, content in self.files.items():
            chunks.append(f"--- {path} ---\n{content}")
        return "\n\n".join(chunks)


class RepositoryContext:
    def __init__(self, project_root: Path | str, max_files: int = 5_000) -> None:
        self.root = Path(project_root).expanduser().resolve()
        self.max_files = max_files
        self._index: dict[str, IndexedFile] = {}

    def _tracked_paths(self) -> list[Path]:
        try:
            top = subprocess.run(
                ["git", "rev-parse", "--show-toplevel"], cwd=self.root,
                capture_output=True, text=True, check=False, timeout=5,
            )
            result = subprocess.run(
                ["git", "ls-files", "-co", "--exclude-standard", "-z"], cwd=self.root,
                capture_output=True, check=False, timeout=15,
            )
            if top.returncode == 0 and Path(top.stdout.strip()).resolve() == self.root and result.returncode == 0:
                return [self.root / raw.decode("utf-8", errors="replace") for raw in result.stdout.split(b"\0") if raw]
        except (OSError, subprocess.SubprocessError):
            pass
        return [
            path for path in self.root.rglob("*")
            if path.is_file() and not any(part in _IGNORED for part in path.relative_to(self.root).parts)
        ]

    @staticmethod
    def _symbols(content: str) -> tuple[str, ...]:
        patterns = (
            r"^\s*(?:async\s+)?def\s+([A-Za-z_]\w*)",
            r"^\s*class\s+([A-Za-z_]\w*)",
            r"^\s*(?:export\s+)?(?:async\s+)?function\s+([A-Za-z_$][\w$]*)",
            r"^\s*(?:export\s+)?(?:const|let|var)\s+([A-Za-z_$][\w$]*)\s*=",
        )
        found: list[str] = []
        for pattern in patterns:
            found.extend(re.findall(pattern, content, flags=re.MULTILINE))
        return tuple(dict.fromkeys(found[:100]))

    def refresh(self) -> tuple[IndexedFile, ...]:
        index: dict[str, IndexedFile] = {}
        for path in self._tracked_paths()[: self.max_files]:
            try:
                relative = str(path.resolve().relative_to(self.root))
                size = path.stat().st_size
                symbols: tuple[str, ...] = ()
                if path.suffix.lower() in _TEXT_SUFFIXES and size <= 256_000:
                    symbols = self._symbols(path.read_text(encoding="utf-8", errors="replace"))
                index[relative] = IndexedFile(relative, size, symbols)
            except (OSError, ValueError):
                continue
        self._index = index
        return tuple(index.values())

    def select(self, query: str, limit: int = 8) -> list[IndexedFile]:
        if not self._index:
            self.refresh()
        terms = {term for term in re.findall(r"[a-zA-Z_][\w.-]*", query.casefold()) if len(term) > 1}
        scored: list[tuple[int, IndexedFile]] = []
        for item in self._index.values():
            haystack = (item.path + " " + " ".join(item.symbols)).casefold()
            score = sum(4 if term in item.path.casefold() else 2 if term in haystack else 0 for term in terms)
            if score:
                scored.append((score, item))
        scored.sort(key=lambda pair: (-pair[0], pair[1].size, pair[1].path))
        return [item for _, item in scored[:limit]]

    def pack(self, query: str, token_budget: int = 8_000) -> ContextPack:
        budget_chars = max(1, token_budget) * 4
        pack = ContextPack(query=query)
        used = 0
        for marker in ("AGENTS.md", "FLOYD.md", "CLAUDE.md"):
            path = self.root / marker
            if not path.is_file():
                continue
            content = path.read_text(encoding="utf-8", errors="replace")
            remaining = budget_chars - used
            if remaining <= 0:
                pack.truncated = True
                break
            clipped = content[:remaining]
            pack.instructions.append(marker)
            pack.files[marker] = clipped
            used += len(clipped)
            pack.truncated = pack.truncated or len(clipped) < len(content)
        for item in self.select(query):
            if item.path in pack.files:
                continue
            if Path(item.path).suffix.lower() not in _TEXT_SUFFIXES:
                continue
            content = (self.root / item.path).read_text(encoding="utf-8", errors="replace")
            remaining = budget_chars - used
            if remaining <= 0:
                pack.truncated = True
                break
            clipped = content[:remaining]
            pack.files[item.path] = clipped
            used += len(clipped)
            pack.truncated = pack.truncated or len(clipped) < len(content)
        pack.approx_tokens = (used + 3) // 4
        return pack

    @staticmethod
    def compact(messages: Iterable[dict[str, Any]], keep_recent: int = 12) -> list[dict[str, Any]]:
        items = list(messages)
        if len(items) <= keep_recent:
            return items
        older, recent = items[:-keep_recent], items[-keep_recent:]
        roles = Counter(str(item.get("role", "unknown")) for item in older)
        tools = Counter(
            str(item.get("name")) for item in older if item.get("role") == "tool" and item.get("name")
        )
        evidence: list[str] = []
        for item in older[-8:]:
            content = re.sub(r"\s+", " ", str(item.get("content", ""))).strip()
            if not content:
                continue
            role = str(item.get("role", "unknown"))
            name = f"/{item['name']}" if item.get("name") else ""
            evidence.append(f"{role}{name}: {content[:180]}")
        summary = {
            "role": "system",
            "content": "Compacted prior context: "
            + ", ".join(f"{role}={count}" for role, count in sorted(roles.items()))
            + ("; tools: " + ", ".join(f"{name}={count}" for name, count in sorted(tools.items())) if tools else ""),
            "evidence": evidence,
            "compacted_messages": len(older),
        }
        return [summary, *recent]
