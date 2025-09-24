import os
from pathlib import Path

import pytest


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
