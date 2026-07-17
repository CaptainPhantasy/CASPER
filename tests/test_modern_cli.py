"""Protocol and identity tests for the modern CASPER terminal client."""

from __future__ import annotations

import io
import json

import pytest
from rich.console import Console

from core.harness import ModelTurn
from core.harness.providers import CallableProvider
from core.terminal import modern_cli


@pytest.mark.asyncio
async def test_headless_protocol_is_jsonl_without_banner(tmp_path, monkeypatch) -> None:
    provider = CallableProvider(lambda messages, tools: ModelTurn(text="verified response"))

    class Runtime(modern_cli.HarnessRuntime):
        def __init__(self, project_root, **kwargs):
            super().__init__(project_root, state_root=tmp_path / "state", provider=provider, **kwargs)

    monkeypatch.setattr(modern_cli, "HarnessRuntime", Runtime)
    stream = io.StringIO()
    exit_code = await modern_cli.run_exec(
        "inspect the repository",
        project_root=tmp_path,
        output=Console(file=stream, force_terminal=False, color_system=None, width=40),
    )

    lines = stream.getvalue().splitlines()
    payloads = [json.loads(line) for line in lines]
    assert exit_code == 0
    assert payloads[0]["type"] == "run.started"
    assert payloads[-1]["type"] == "result"
    assert payloads[-1]["status"] == "complete"
    assert all(item["protocol"] == "casper.events/v1" for item in payloads)
    assert "\\\\\\" not in stream.getvalue()


@pytest.mark.asyncio
async def test_headless_slash_command_uses_control_dispatcher(tmp_path, monkeypatch) -> None:
    provider_called = False

    def provider(messages, tools):
        nonlocal provider_called
        provider_called = True
        return ModelTurn(text="incorrect model claim")

    class Runtime(modern_cli.HarnessRuntime):
        def __init__(self, project_root, **kwargs):
            super().__init__(
                project_root,
                state_root=tmp_path / "state",
                provider=CallableProvider(provider),
                **kwargs,
            )

    monkeypatch.setattr(modern_cli, "HarnessRuntime", Runtime)
    target = tmp_path / "created-by-control"
    stream = io.StringIO()

    exit_code = await modern_cli.run_exec(
        f"/mkdir {target}",
        project_root=tmp_path,
        permission_mode="accept_edits",
        output=Console(file=stream, force_terminal=False, color_system=None, width=160),
    )

    payloads = [json.loads(line) for line in stream.getvalue().splitlines()]
    assert exit_code == 0
    assert target.is_dir()
    assert provider_called is False
    assert payloads[0]["type"] == "control.completed"
    assert payloads[0]["observation"]["data"]["verified_is_directory"] is True


def test_help_and_tools_are_registry_projections(tmp_path) -> None:
    provider = CallableProvider(lambda messages, tools: ModelTurn(text="ok"))
    runtime = modern_cli.HarnessRuntime(tmp_path, state_root=tmp_path / "state", provider=provider)
    stream = io.StringIO()
    console = Console(file=stream, force_terminal=False, color_system=None, width=160)
    modern_cli.render_help(console, runtime)
    modern_cli.render_tools(console, runtime)
    modern_cli.render_features(console)
    rendered = stream.getvalue()
    assert f"{len(runtime.registry.specs())} typed tools" in rendered
    assert "/code-review [low|medium|high] [PATH]" in rendered
    for spec in runtime.registry.specs():
        assert spec.name in rendered
    assert "Verified harness engines (50)" in rendered
    assert "Interaction and portability" in rendered
