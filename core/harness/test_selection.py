"""Select the smallest useful test set for a group of changed files."""

from __future__ import annotations

import ast
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable


@dataclass(frozen=True)
class TestSelection:
    tests: tuple[str, ...]
    reasons: dict[str, tuple[str, ...]]
    fallback: bool


class TargetedTestSelector:
    """Map source changes to tests by name, location, and import references."""

    def __init__(self, root: Path | str) -> None:
        self.root = Path(root).expanduser().resolve()

    def _relative(self, path: Path | str) -> str:
        absolute = (self.root / path).resolve() if not Path(path).is_absolute() else Path(path).resolve()
        try:
            return absolute.relative_to(self.root).as_posix()
        except ValueError as exc:
            raise ValueError(f"path escapes repository root: {path}") from exc

    def _test_files(self) -> tuple[Path, ...]:
        return tuple(sorted(
            path for path in self.root.rglob("*.py")
            if (path.name.startswith("test_") or path.name.endswith("_test.py"))
            and not any(part in {".git", ".venv", "venv", "__pycache__"} for part in path.parts)
        ))

    @staticmethod
    def _imports(path: Path) -> set[str]:
        try:
            tree = ast.parse(path.read_text(encoding="utf-8", errors="replace"))
        except (OSError, SyntaxError):
            return set()
        modules: set[str] = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                modules.update(alias.name for alias in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module:
                modules.add(node.module)
        return modules

    def select(self, changed_paths: Iterable[Path | str], *, max_tests: int = 50) -> TestSelection:
        changed = tuple(sorted({self._relative(path) for path in changed_paths}))
        tests = self._test_files()
        reasons: dict[str, set[str]] = {}
        changed_modules = {
            path.removesuffix("/__init__.py").removesuffix(".py").replace("/", ".")
            for path in changed if path.endswith(".py")
        }
        for test_path in tests:
            relative = test_path.relative_to(self.root).as_posix()
            found: set[str] = set()
            if relative in changed:
                found.add("test file changed")
            stem = test_path.stem.removeprefix("test_").removesuffix("_test")
            for changed_path in changed:
                changed_stem = Path(changed_path).stem
                if changed_stem == stem and changed_path != relative:
                    found.add(f"name matches {changed_path}")
            imports = self._imports(test_path)
            for module in changed_modules:
                if any(imported == module or imported.startswith(module + ".") or module.startswith(imported + ".") for imported in imports):
                    found.add(f"imports {module}")
            if found:
                reasons[relative] = found
        fallback = not reasons
        if fallback:
            for test_path in tests[:max_tests]:
                reasons[test_path.relative_to(self.root).as_posix()] = {"fallback test discovery"}
        ordered = tuple(sorted(reasons)[:max_tests])
        return TestSelection(
            tests=ordered,
            reasons={path: tuple(sorted(reasons[path])) for path in ordered},
            fallback=fallback,
        )
