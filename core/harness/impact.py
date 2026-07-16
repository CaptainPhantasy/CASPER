"""Change-impact analysis over repository dependencies and tests."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

from .dependencies import DependencyGraph
from .test_selection import TargetedTestSelector


@dataclass(frozen=True)
class ImpactReport:
    changed: tuple[str, ...]
    directly_affected: tuple[str, ...]
    transitively_affected: tuple[str, ...]
    tests: tuple[str, ...]
    risk: str
    reasons: tuple[str, ...]


class ChangeImpactAnalyzer:
    """Combine reverse imports, test selection, and risk rules into one report."""

    _HIGH_RISK_NAMES = {
        "pyproject.toml", "package.json", "requirements.txt", "setup.py",
        "Dockerfile", "docker-compose.yml",
    }

    def __init__(
        self,
        root: Path | str,
        graph: DependencyGraph | None = None,
        selector: TargetedTestSelector | None = None,
    ) -> None:
        self.root = Path(root).expanduser().resolve()
        self.graph = graph or DependencyGraph(self.root)
        self.selector = selector or TargetedTestSelector(self.root)

    def _relative(self, path: Path | str) -> str:
        absolute = (self.root / path).resolve() if not Path(path).is_absolute() else Path(path).resolve()
        try:
            return absolute.relative_to(self.root).as_posix()
        except ValueError as exc:
            raise ValueError(f"path escapes repository root: {path}") from exc

    def analyze(self, changed_paths: Iterable[Path | str]) -> ImpactReport:
        changed = tuple(sorted({self._relative(path) for path in changed_paths}))
        if not self.graph.edges():
            self.graph.build()
        direct = tuple(sorted({dependent for path in changed for dependent in self.graph.dependents(path)}))
        transitive_all = set(self.graph.transitive_dependents(changed))
        transitive = tuple(sorted(transitive_all - set(direct)))
        selection = self.selector.select(changed)
        reasons: list[str] = []
        high_risk = [path for path in changed if Path(path).name in self._HIGH_RISK_NAMES or Path(path).name == "__init__.py"]
        if high_risk:
            risk = "high"
            reasons.append("public API, build, or dependency configuration changed")
        elif transitive or len(direct) >= 3:
            risk = "high"
            reasons.append("change propagates across multiple dependency levels")
        elif direct:
            risk = "medium"
            reasons.append("one or more modules import a changed file")
        elif changed and all(path.startswith(("tests/", "docs/")) for path in changed):
            risk = "low"
            reasons.append("changes are isolated to tests or documentation")
        else:
            risk = "medium"
            reasons.append("implementation change has no known reverse imports")
        if selection.fallback:
            reasons.append("no targeted test mapping; using discovered-test fallback")
        return ImpactReport(changed, direct, transitive, selection.tests, risk, tuple(reasons))
