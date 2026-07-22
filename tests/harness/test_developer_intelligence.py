from pathlib import Path

import pytest

from core.harness.dependencies import DependencyGraph
from core.harness.diagnostics import DiagnosticParser
from core.harness.impact import ChangeImpactAnalyzer
from core.harness.plans import PlanStatus, PlanStep, PlanTracker
from core.harness.prompts import PromptLibrary, PromptTemplate
from core.harness.schema import JSONSchemaValidator
from core.harness.search import RepositorySearch
from core.harness.symbols import SymbolIndex
from core.harness.test_selection import TargetedTestSelector
from core.harness.watcher import FileChangeDetector


def write(root: Path, relative: str, content: str) -> Path:
    path = root / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    return path


def test_symbol_index_tracks_qualified_python_and_javascript_symbols(tmp_path: Path) -> None:
    source = write(tmp_path, "pkg/service.py", "class Service:\n    async def run(self):\n        pass\n")
    script = write(tmp_path, "web/app.ts", "export function boot() {}\n")
    index = SymbolIndex(tmp_path)
    index.refresh([source, script])
    assert [(item.qualified_name, item.kind) for item in index.find("run", exact=True)] == [
        ("Service.run", "async_method")
    ]
    assert index.find("boot")[0].path == "web/app.ts"


def test_dependency_graph_resolves_relative_imports_and_transitive_dependents(tmp_path: Path) -> None:
    write(tmp_path, "pkg/__init__.py", "")
    write(tmp_path, "pkg/base.py", "VALUE = 1\n")
    write(tmp_path, "pkg/mid.py", "from . import base\n")
    write(tmp_path, "app.py", "from pkg import mid\n")
    graph = DependencyGraph(tmp_path)
    graph.build()
    assert graph.dependencies("pkg/mid.py") == ("pkg/base.py",)
    assert graph.transitive_dependents("pkg/base.py") == ("app.py", "pkg/mid.py")


def test_repository_search_ranks_phrase_and_path_matches(tmp_path: Path) -> None:
    write(tmp_path, "auth/token_service.py", "def rotate_token():\n    return 'rotate token'\n")
    write(tmp_path, "misc.py", "# token only\n")
    hits = RepositorySearch(tmp_path).search("rotate token")
    assert hits[0].path == "auth/token_service.py"
    assert "exact phrase" in hits[0].reasons


def test_diagnostic_parser_normalizes_ruff_mypy_and_typescript() -> None:
    parsed = DiagnosticParser.parse(
        "src/a.py:4:2: E501 line too long\n"
        "src/b.py:8: error: bad assignment [assignment]\n"
        "web/a.ts(9,3): error TS2322: wrong type"
    )
    assert [(item.source, item.code, item.line) for item in parsed] == [
        ("ruff", "E501", 4), ("mypy", "assignment", 8), ("typescript", "TS2322", 9)
    ]


def test_targeted_test_selector_uses_name_and_import_evidence(tmp_path: Path) -> None:
    write(tmp_path, "pkg/service.py", "def run(): pass\n")
    write(tmp_path, "tests/test_service.py", "from pkg.service import run\n\ndef test_run(): run()\n")
    write(tmp_path, "tests/test_other.py", "def test_other(): pass\n")
    result = TargetedTestSelector(tmp_path).select(["pkg/service.py"])
    assert result.tests == ("tests/test_service.py",)
    assert not result.fallback
    assert any(reason.startswith("imports") for reason in result.reasons["tests/test_service.py"])


def test_change_impact_combines_reverse_dependencies_tests_and_risk(tmp_path: Path) -> None:
    write(tmp_path, "pkg/core.py", "VALUE = 1\n")
    write(tmp_path, "pkg/api.py", "from pkg import core\n")
    write(tmp_path, "tests/test_core.py", "from pkg.core import VALUE\n")
    graph = DependencyGraph(tmp_path)
    graph.build()
    report = ChangeImpactAnalyzer(tmp_path, graph=graph).analyze(["pkg/core.py"])
    assert report.directly_affected == ("pkg/api.py", "tests/test_core.py")
    assert report.tests == ("tests/test_core.py",)
    assert report.risk == "medium"


def test_plan_tracker_enforces_dependencies_proof_and_persists(tmp_path: Path) -> None:
    path = tmp_path / "plan.json"
    tracker = PlanTracker((PlanStep("build", "Build"), PlanStep("test", "Test", depends_on=("build",))), path)
    with pytest.raises(ValueError, match="not ready"):
        tracker.start("test")
    tracker.start("build")
    with pytest.raises(ValueError, match="requires evidence"):
        tracker.complete("build", evidence="", verification_passed=True)
    tracker.complete("build", evidence="pytest: 1 passed", verification_passed=True)
    assert PlanTracker.load(path).steps[0].status == PlanStatus.COMPLETED
    assert tracker.ready()[0].id == "test"


def test_json_schema_validator_reports_nested_contract_violations() -> None:
    validator = JSONSchemaValidator({
        "type": "object", "required": ["items"], "additionalProperties": False,
        "properties": {"items": {"type": "array", "items": {"type": "integer", "minimum": 1}}},
    })
    assert validator.validate({"items": [1, 2]}).valid
    result = validator.validate({"items": [0, True], "extra": 1})
    assert {issue.keyword for issue in result.issues} == {"minimum", "type", "additionalProperties"}
    assert not validator.validate_json("{").valid


def test_prompt_library_versions_validates_and_renders() -> None:
    library = PromptLibrary((PromptTemplate("review", "Review {path} for {goal}.", version="2"),))
    assert library.render("review", {"path": "app.py", "goal": "safety"}) == "Review app.py for safety."
    assert len(library.get("review").checksum) == 64
    with pytest.raises(ValueError, match="missing"):
        library.render("review", {"path": "app.py"})


def test_file_change_detector_finds_create_modify_delete_by_content(tmp_path: Path) -> None:
    detector = FileChangeDetector(tmp_path)
    assert detector.poll() == ()
    path = write(tmp_path, "app.py", "one")
    assert [(item.path, item.kind) for item in detector.poll()] == [("app.py", "created")]
    path.write_text("two", encoding="utf-8")
    assert detector.poll()[0].kind == "modified"
    path.unlink()
    assert detector.poll()[0].kind == "deleted"
