"""Evidence tests for autonomous TUI feature batch 1."""

from __future__ import annotations

import io
import json

import pytest
from rich.console import Console

from core.terminal.ui.terminal_ui import TerminalUI


def make_ui(tmp_path, monkeypatch=None) -> TerminalUI:
    if monkeypatch:
        monkeypatch.setenv("CASPER_TUI_HOME", str(tmp_path))
    return TerminalUI(
        "Feature Test",
        state_root=tmp_path,
        console=Console(file=io.StringIO(), force_terminal=False, record=True),
    )


@pytest.mark.asyncio
async def test_non_blocking_lifecycle(tmp_path):
    ui = make_ui(tmp_path)
    await ui.start_ui()
    assert ui.running is True
    assert ui._runner_task is not None
    assert not ui._runner_task.done()
    await ui.shutdown()
    assert ui.running is False


def test_terminal_capability_detection(tmp_path, monkeypatch):
    monkeypatch.setenv("NO_COLOR", "1")
    ui = make_ui(tmp_path)
    assert ui.features.no_color is True
    assert ui.console.no_color is True
    assert ui.console.width > 0


@pytest.mark.asyncio
async def test_theme_selection(tmp_path):
    ui = make_ui(tmp_path)
    result = await ui.execute_command("/theme light")
    assert result.handled and "light" in result.message
    assert ui.features.settings["theme"] == "light"
    assert ui.features.theme["syntax"] == "friendly"


def test_preferences_persist(tmp_path):
    ui = make_ui(tmp_path)
    ui.features.settings["theme"] = "mono"
    ui.features.save_settings()
    reloaded = make_ui(tmp_path)
    assert reloaded.features.settings["theme"] == "mono"
    assert json.loads(reloaded.features.settings_path.read_text())["theme"] == "mono"


def test_history_persistence(tmp_path):
    ui = make_ui(tmp_path)
    ui.features.record_history("/status")
    ui.features.record_history("/status")
    ui.features.record_history("build the project")
    assert make_ui(tmp_path).features.history() == ["/status", "build the project"]


@pytest.mark.asyncio
async def test_history_search(tmp_path):
    ui = make_ui(tmp_path)
    ui.features.record_history("review security")
    ui.features.record_history("run focused tests")
    result = await ui.execute_command("/history security")
    assert "review security" in result.message
    assert "focused tests" not in result.message


def test_undo_redo(tmp_path):
    ui = make_ui(tmp_path)
    original = ui.panes["code"].content
    ui.features.remember_edit(ui.panes)
    ui.panes["code"].content = "print('changed')"
    assert ui.features.undo(ui.panes, "code") is True
    assert ui.panes["code"].content == original
    assert ui.features.redo(ui.panes, "code") is True
    assert ui.panes["code"].content == "print('changed')"


@pytest.mark.asyncio
async def test_layout_presets(tmp_path):
    ui = make_ui(tmp_path)
    result = await ui.execute_command("/layout focus-code")
    assert "applied" in result.message
    assert ui.panes["code"].visible is True
    assert ui.panes["code"].height == 32
    assert ui.panes["tests"].visible is False


@pytest.mark.asyncio
async def test_pane_controls(tmp_path):
    ui = make_ui(tmp_path)
    await ui.execute_command("/pane tests hide")
    await ui.execute_command("/pane code height 40")
    assert ui.panes["tests"].visible is False
    assert ui.panes["code"].height == 40


@pytest.mark.asyncio
async def test_autosave_recovery(tmp_path):
    ui = make_ui(tmp_path)
    ui.panes["reasoning"].content = "recoverable state"
    ui.features.autosave(ui.panes)
    recovered = make_ui(tmp_path)
    result = await recovered.execute_command("/recover")
    assert "restored" in result.message
    assert recovered.panes["reasoning"].content.startswith("recoverable state")


@pytest.mark.asyncio
async def test_global_search(tmp_path):
    ui = make_ui(tmp_path)
    ui.panes["tests"].content = "line one\nneedle in test output"
    result = await ui.execute_command("/search needle")
    assert "tests:2" in result.message


@pytest.mark.asyncio
async def test_command_palette(tmp_path):
    ui = make_ui(tmp_path)
    result = await ui.execute_command("/commands transcript")
    assert "/export" in result.message
    assert "/layout" not in result.message


@pytest.mark.asyncio
async def test_notifications(tmp_path):
    ui = make_ui(tmp_path)
    result = await ui.execute_command("/notify Build complete")
    assert result.message == "Notification: Build complete"
    assert ui.features.notifications[-1] == "Build complete"


@pytest.mark.asyncio
async def test_named_sessions(tmp_path):
    ui = make_ui(tmp_path)
    ui.panes["code"].content = "version one"
    await ui.execute_command("/session save demo")
    ui.panes["code"].content = "version two"
    result = await ui.execute_command("/session load demo")
    assert result.message == "Session loaded."
    assert ui.panes["code"].content == "version one"
    assert "demo" in ui.features.list_sessions()


@pytest.mark.asyncio
async def test_transcript_export(tmp_path):
    ui = make_ui(tmp_path)
    ui.features.append_transcript("code", "code", "print('proof')")
    result = await ui.execute_command("/export json")
    path = ui.features.exports_dir / result.message.rsplit("/", 1)[-1]
    assert path.exists()
    assert json.loads(path.read_text())[0]["content"] == "print('proof')"


def test_transcript_import(tmp_path):
    ui = make_ui(tmp_path)
    source = tmp_path / "input.json"
    source.write_text(
        json.dumps(
            [
                {
                    "timestamp": "2026-01-01T00:00:00+00:00",
                    "pane": "tests",
                    "kind": "result",
                    "content": "pass",
                }
            ]
        )
    )
    assert ui.features.import_transcript(str(source)) == 1
    assert ui.features.transcript[-1].content == "pass"


@pytest.mark.asyncio
async def test_bookmarks(tmp_path):
    ui = make_ui(tmp_path)
    ui.features.append_transcript("reasoning", "result", "important output")
    await ui.execute_command("/bookmark add proof")
    result = await ui.execute_command("/bookmark show proof")
    assert "important output" in result.message


@pytest.mark.asyncio
async def test_macros(tmp_path):
    ui = make_ui(tmp_path)
    await ui.execute_command("/macro start darkmode")
    await ui.execute_command("/theme dark")
    await ui.execute_command("/macro stop")
    await ui.execute_command("/theme light")
    result = await ui.execute_command("/macro play darkmode")
    assert "dark" in result.message
    assert ui.features.settings["theme"] == "dark"


@pytest.mark.asyncio
async def test_shortcut_customization(tmp_path):
    ui = make_ui(tmp_path)
    result = await ui.execute_command("/shortcut set palette Ctrl+P")
    assert result.handled
    assert ui.features.settings["shortcuts"]["palette"] == "Ctrl+P"
    assert make_ui(tmp_path).features.settings["shortcuts"]["palette"] == "Ctrl+P"


@pytest.mark.asyncio
async def test_accessibility_profiles(tmp_path):
    ui = make_ui(tmp_path)
    await ui.execute_command("/accessibility high-contrast")
    assert ui.features.theme["border"] == "bright_white"
    await ui.execute_command("/accessibility reduced-motion")
    assert ui.features.settings["reduced_motion"] is True
    await ui.execute_command("/accessibility plain")
    assert ui.features.no_color is True
