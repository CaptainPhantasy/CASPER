"""Repository import and reverse-dependency graph."""

from __future__ import annotations

import ast
from collections import defaultdict, deque
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable


@dataclass(frozen=True, order=True)
class DependencyEdge:
    source: str
    target: str
    kind: str
    imported_name: str


class DependencyGraph:
    """Resolve Python imports to repository files and expose impact traversal."""

    def __init__(self, root: Path | str) -> None:
        self.root = Path(root).expanduser().resolve()
        self._edges: set[DependencyEdge] = set()
        self.external_imports: dict[str, tuple[str, ...]] = {}

    def _relative(self, path: Path | str) -> tuple[Path, str]:
        absolute = (self.root / path).resolve() if not Path(path).is_absolute() else Path(path).resolve()
        try:
            relative = absolute.relative_to(self.root).as_posix()
        except ValueError as exc:
            raise ValueError(f"path escapes repository root: {path}") from exc
        return absolute, relative

    def _resolve_module(self, source: Path, module: str, level: int) -> str | None:
        if level:
            base = source.parent
            for _ in range(level - 1):
                base = base.parent
            candidate_base = base.joinpath(*module.split(".")) if module else base
        else:
            candidate_base = self.root.joinpath(*module.split("."))
        candidates = (candidate_base.with_suffix(".py"), candidate_base / "__init__.py")
        for candidate in candidates:
            if candidate.is_file():
                return candidate.resolve().relative_to(self.root).as_posix()
        return None

    def analyze_file(self, path: Path | str) -> tuple[DependencyEdge, ...]:
        absolute, relative = self._relative(path)
        self._edges = {edge for edge in self._edges if edge.source != relative}
        try:
            tree = ast.parse(absolute.read_text(encoding="utf-8", errors="replace"))
        except (OSError, SyntaxError):
            self.external_imports[relative] = ()
            return ()
        edges: list[DependencyEdge] = []
        external: set[str] = set()
        for node in ast.walk(tree):
            imports: list[tuple[str, int, str]] = []
            if isinstance(node, ast.Import):
                imports = [(alias.name, 0, alias.name) for alias in node.names]
            elif isinstance(node, ast.ImportFrom):
                module = node.module or ""
                imports = [(module, node.level, alias.name) for alias in node.names]
            for module, level, imported_name in imports:
                target = None
                if isinstance(node, ast.ImportFrom) and imported_name != "*":
                    target = self._resolve_module(
                        absolute, f"{module}.{imported_name}".strip("."), level,
                    )
                if target is None:
                    target = self._resolve_module(absolute, module, level)
                if target:
                    edges.append(DependencyEdge(relative, target, "import", imported_name))
                else:
                    external.add(("." * level) + module)
        self._edges.update(edges)
        self.external_imports[relative] = tuple(sorted(external))
        return tuple(sorted(edges))

    def build(self, paths: Iterable[Path | str] | None = None) -> tuple[DependencyEdge, ...]:
        self._edges.clear()
        candidates = paths or (
            path for path in self.root.rglob("*.py")
            if not any(part in {".git", ".casper", ".venv", "venv", "__pycache__"} for part in path.parts)
        )
        for path in candidates:
            self.analyze_file(path)
        return self.edges()

    def edges(self) -> tuple[DependencyEdge, ...]:
        return tuple(sorted(self._edges))

    def dependencies(self, path: Path | str) -> tuple[str, ...]:
        _, relative = self._relative(path)
        return tuple(sorted({edge.target for edge in self._edges if edge.source == relative}))

    def dependents(self, path: Path | str) -> tuple[str, ...]:
        _, relative = self._relative(path)
        return tuple(sorted({edge.source for edge in self._edges if edge.target == relative}))

    def transitive_dependents(self, paths: Path | str | Iterable[Path | str]) -> tuple[str, ...]:
        items = [paths] if isinstance(paths, (str, Path)) else list(paths)
        queue = deque(self._relative(path)[1] for path in items)
        visited = set(queue)
        reverse: dict[str, set[str]] = defaultdict(set)
        for edge in self._edges:
            reverse[edge.target].add(edge.source)
        affected: set[str] = set()
        while queue:
            current = queue.popleft()
            for dependent in reverse[current]:
                if dependent not in visited:
                    visited.add(dependent)
                    affected.add(dependent)
                    queue.append(dependent)
        return tuple(sorted(affected))
