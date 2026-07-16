"""Static contracts that keep the harness CI runnable and fail-closed."""

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
WORKFLOW = ROOT / ".github" / "workflows" / "terminal-testing.yml"
PYTEST_INI = ROOT / "pytest.ini"


def workflow_text() -> str:
    return WORKFLOW.read_text(encoding="utf-8")


def test_ci_uses_declared_poetry_group_and_exact_test_paths():
    text = workflow_text()

    assert "poetry install --with dev\n" in text
    assert "--with dev,test" not in text
    assert "--with dev,lint" not in text
    assert '-m "unit and not slow"' not in text
    assert '-m "security"' not in text
    assert 'tests/test_terminal_performance.py' not in text
    assert "tests/test_modern_cli.py" in text
    assert "tests/test_terminal_branding.py" in text
    assert "find tests/harness -type f -name 'test_*.py'" in text


def test_ci_covers_first_class_harness_and_launcher_paths():
    text = workflow_text()

    required_paths = {
        '"core/harness/**"',
        '"core/pipeline/**"',
        '"core/services/goal_engine.py"',
        '"core/terminal/**"',
        '"core/cli.py"',
        '"casper"',
        '"casper_terminal_complete.py"',
        '"scripts/e2e_harness_50.py"',
    }
    missing = sorted(path for path in required_paths if path not in text)
    assert not missing, f"workflow trigger is missing: {missing}"
    assert "poetry run python scripts/e2e_harness_50.py" in text


def test_ci_uses_native_dashboard_runners_and_headless_playwright():
    text = workflow_text()

    assert "npm run test:unit" in text
    assert "npm test --" in text
    assert "--project=chromium" in text
    assert '--grep="should test responsive elements"' in text
    assert 'CI: "true"' in text
    assert "--testPathPattern" not in text
    assert "--coverageThreshold" not in text
    assert "headless=False" not in text


def test_ci_fails_closed_instead_of_accepting_partial_success():
    text = workflow_text()

    assert "success_rate" not in text
    assert "< 90" not in text
    assert 'details.get("result") != "success"' in text
    assert "continue-on-error: true" not in text


def test_pytest_markers_are_registered_and_strict():
    text = PYTEST_INI.read_text(encoding="utf-8")

    assert "--strict-markers" in text
    for marker in ("unit", "integration", "security", "performance", "stress", "slow"):
        assert f"    {marker}:" in text
