import os
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

pytest_plugins = ["tests.conftest_terminal"]


@pytest.fixture
def project_root(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    project_root = tmp_path / "project"
    project_root.mkdir()
    monkeypatch.chdir(project_root)
    monkeypatch.setenv("CASPER_PROJECT_ROOT", str(project_root))
    monkeypatch.setenv("CASPER_OUTPUT_DIR", ".casper/output")
    return project_root


@pytest.fixture(autouse=True)
def _auto_project_root(project_root: Path):
    return project_root


@pytest.fixture(autouse=True)
def _mock_llm_service():
    """Auto-mock the LLM service to prevent real API calls during tests.

    This fixture ensures no test makes real network calls to Anthropic or
    OpenAI. Tests that need to verify LLM behavior can override this by
    patching ``core.services.llm.llm_service`` directly with their own mock.
    """
    mock_response = "[MOCK LLM RESPONSE] Task analyzed successfully."
    with patch("core.services.llm.llm_service") as mock_llm:
        mock_llm.complete = AsyncMock(return_value=mock_response)
        mock_llm.available = MagicMock(return_value=True)
        mock_llm.resolve_model = AsyncMock(return_value="mock-model")
        yield mock_llm
