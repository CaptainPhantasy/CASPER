from pathlib import Path

import pytest

from core.harness.skills import default_skill_roots
from core.state.simple_state_manager import SimpleStateManager
from core.terminal.streaming.websocket_integration import StreamingWebSocketHandler


def test_state_manager_defaults_to_checkout_local_state(tmp_path: Path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv("CASPER_STATE_DIR", raising=False)

    manager = SimpleStateManager()

    expected = tmp_path / ".casper" / "transformation" / "state_management"
    assert Path(manager.storage_path) == expected
    assert manager.db_path == expected / "simple_state.db"


def test_default_skill_roots_have_no_machine_specific_volume(tmp_path: Path, monkeypatch):
    monkeypatch.setattr(Path, "home", classmethod(lambda cls: tmp_path))
    roots = default_skill_roots(tmp_path)

    assert all("/Volumes/" not in str(root) for root in roots)


@pytest.mark.asyncio
async def test_streaming_working_directory_uses_live_cwd(tmp_path: Path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    handler = object.__new__(StreamingWebSocketHandler)
    session = type("Session", (), {"pty_session_id": None})()

    assert await handler._get_working_directory(session) == str(tmp_path)
