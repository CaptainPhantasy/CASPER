"""Language-aware source symbol indexing."""

from __future__ import annotations

import ast
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable


@dataclass(frozen=True, order=True)
class SymbolRecord:
    path: str
    line: int
    column: int
    name: str
    qualified_name: str
    kind: str
    end_line: int


class SymbolIndex:
    """Build a deterministic, incrementally refreshable source-symbol index."""

    _JS_SYMBOL = re.compile(
        r"^\s*(?:export\s+)?(?:(?:async\s+)?function|class|const|let|var)\s+"
        r"(?P<name>[A-Za-z_$][\w$]*)",
        re.MULTILINE,
    )

    def __init__(self, root: Path | str) -> None:
        self.root = Path(root).expanduser().resolve()
        self._by_path: dict[str, tuple[SymbolRecord, ...]] = {}

    def _relative(self, path: Path | str) -> tuple[Path, str]:
        resolved = (self.root / path).resolve() if not Path(path).is_absolute() else Path(path).resolve()
        try:
            relative = resolved.relative_to(self.root).as_posix()
        except ValueError as exc:
            raise ValueError(f"path escapes repository root: {path}") from exc
        return resolved, relative

    def index_file(self, path: Path | str) -> tuple[SymbolRecord, ...]:
        absolute, relative = self._relative(path)
        content = absolute.read_text(encoding="utf-8", errors="replace")
        records = self._python_symbols(relative, content) if absolute.suffix == ".py" else self._js_symbols(relative, content)
        self._by_path[relative] = records
        return records

    @staticmethod
    def _python_symbols(path: str, content: str) -> tuple[SymbolRecord, ...]:
        try:
            tree = ast.parse(content)
        except SyntaxError:
            return ()
        records: list[SymbolRecord] = []

        class Visitor(ast.NodeVisitor):
            def __init__(self) -> None:
                self.parents: list[str] = []

            def _record(self, node: ast.AST, name: str, kind: str) -> None:
                qualified = ".".join((*self.parents, name))
                records.append(SymbolRecord(
                    path=path,
                    line=int(getattr(node, "lineno", 1)),
                    column=int(getattr(node, "col_offset", 0)) + 1,
                    name=name,
                    qualified_name=qualified,
                    kind=kind,
                    end_line=int(getattr(node, "end_lineno", getattr(node, "lineno", 1))),
                ))

            def visit_ClassDef(self, node: ast.ClassDef) -> None:
                self._record(node, node.name, "class")
                self.parents.append(node.name)
                self.generic_visit(node)
                self.parents.pop()

            def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
                self._record(node, node.name, "method" if self.parents else "function")
                self.parents.append(node.name)
                self.generic_visit(node)
                self.parents.pop()

            def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:
                self._record(node, node.name, "async_method" if self.parents else "async_function")
                self.parents.append(node.name)
                self.generic_visit(node)
                self.parents.pop()

        Visitor().visit(tree)
        return tuple(sorted(records))

    @classmethod
    def _js_symbols(cls, path: str, content: str) -> tuple[SymbolRecord, ...]:
        records: list[SymbolRecord] = []
        for match in cls._JS_SYMBOL.finditer(content):
            name = match.group("name")
            line = content.count("\n", 0, match.start()) + 1
            declaration = match.group(0)
            if "class" in declaration:
                kind = "class"
            elif "function" in declaration:
                kind = "function"
            else:
                kind = "variable"
            records.append(SymbolRecord(path, line, match.start() - content.rfind("\n", 0, match.start()), name, name, kind, line))
        return tuple(sorted(records))

    def refresh(self, paths: Iterable[Path | str] | None = None) -> tuple[SymbolRecord, ...]:
        candidates = paths or (
            path for path in self.root.rglob("*")
            if path.is_file() and path.suffix.lower() in {".py", ".js", ".jsx", ".ts", ".tsx"}
            and not any(part in {".git", ".casper", "node_modules", "__pycache__", ".venv"} for part in path.parts)
        )
        seen: set[str] = set()
        for candidate in candidates:
            absolute, relative = self._relative(candidate)
            seen.add(relative)
            if absolute.is_file():
                self.index_file(absolute)
            else:
                self._by_path.pop(relative, None)
        if paths is None:
            for stale in self._by_path.keys() - seen:
                del self._by_path[stale]
        return self.all_symbols()

    def all_symbols(self) -> tuple[SymbolRecord, ...]:
        return tuple(sorted(record for records in self._by_path.values() for record in records))

    def symbols_for(self, path: Path | str) -> tuple[SymbolRecord, ...]:
        _, relative = self._relative(path)
        return self._by_path.get(relative, ())

    def find(self, query: str, *, exact: bool = False) -> tuple[SymbolRecord, ...]:
        needle = query.casefold()
        return tuple(record for record in self.all_symbols() if (
            (record.name.casefold() == needle or record.qualified_name.casefold() == needle)
            if exact
            else (needle in record.name.casefold() or needle in record.qualified_name.casefold())
        ))
