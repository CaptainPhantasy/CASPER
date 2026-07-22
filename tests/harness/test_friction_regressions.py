import json
import sys
from pathlib import Path

import pytest

from core.harness import HarnessRuntime, ModelTurn, PermissionMode, ToolCall
from core.harness.policy import PolicyDisposition
from core.harness.skills import default_skill_roots
from core.terminal.modern_cli import _normalize_input


class QuietProvider:
    async def complete(self, messages, tools):
        return ModelTurn(text="ok")


def test_runtime_can_use_explicit_absolute_paths_outside_launch_project(tmp_path: Path):
    project = tmp_path / "project"
    external = tmp_path / "shared" / "registry.json"
    project.mkdir(exist_ok=True)
    external.parent.mkdir()
    external.write_text('{"port": 5494}\n', encoding="utf-8")

    runtime = HarnessRuntime(project, tmp_path / "state", provider=QuietProvider())
    result = runtime.workspace.read_file(str(external))

    assert result.status.value == "success"
    assert '"port": 5494' in result.data["content"]


def test_external_access_never_turns_relative_traversal_into_authority(tmp_path: Path):
    project = tmp_path / "project"
    project.mkdir(exist_ok=True)
    runtime = HarnessRuntime(project, tmp_path / "state", provider=QuietProvider())

    with pytest.raises(ValueError, match="escapes the active project root"):
        runtime.workspace.resolve("../outside.txt")


def test_volume_paths_without_leading_slash_are_normalized():
    assert HarnessRuntime.normalize_local_path("Volumes/Storage/JCODE") == "/Volumes/Storage/JCODE"
    assert HarnessRuntime.normalize_local_path("/Volumes/Storage/JCODE") == "/Volumes/Storage/JCODE"


def test_directory_creation_is_typed_and_low_friction_in_accept_edits(tmp_path: Path):
    runtime = HarnessRuntime(
        tmp_path,
        tmp_path / "state",
        provider=QuietProvider(),
        permission_mode=PermissionMode.ACCEPT_EDITS,
    )
    spec = runtime.registry.get("make_directory").spec
    call = ToolCall("make_directory", {"path": str(tmp_path / "JCODE")}, id="mkdir")

    decision = runtime.policy.decide(spec, call)
    result = runtime.workspace.make_directory(str(tmp_path / "JCODE"))

    assert decision.disposition == PolicyDisposition.ALLOW
    assert result.status.value == "success"
    assert (tmp_path / "JCODE").is_dir()


def test_verification_commands_do_not_prompt_but_package_changes_do(tmp_path: Path):
    runtime = HarnessRuntime(tmp_path, tmp_path / "state", provider=QuietProvider())
    spec = runtime.registry.get("run_command").spec

    verify = runtime.policy.decide(spec, ToolCall(
        "run_command", {"argv": ["python3", "-m", "json.tool", "/tmp/example.json"]}, id="verify"
    ))
    install = runtime.policy.decide(spec, ToolCall(
        "run_command", {"argv": ["npm", "install"]}, id="install"
    ))

    assert verify.disposition == PolicyDisposition.ALLOW
    assert install.disposition == PolicyDisposition.REQUIRE_APPROVAL


def test_default_skill_roots_include_shared_libraries(tmp_path: Path, monkeypatch):
    shared = tmp_path / "skills"
    shared.mkdir()
    monkeypatch.setenv("CASPER_SKILLS_HOME", str(shared))

    roots = default_skill_roots(tmp_path)

    assert shared.resolve() in roots
    assert all(path.is_dir() for path in roots)


@pytest.mark.asyncio
async def test_setup_config_export_and_pwd_are_canonical_controls(tmp_path: Path):
    runtime = HarnessRuntime(tmp_path, tmp_path / "state", provider=QuietProvider())

    assert await runtime.handle_control("/setup") is None
    assert (await runtime.handle_control("/config")).status.value == "success"
    assert (await runtime.handle_control("/pwd")).data["path"] == str(tmp_path)
    exported = await runtime.handle_control("/export")
    assert exported.status.value == "success"
    assert Path(exported.artifacts[0]).is_file()


@pytest.mark.asyncio
async def test_control_mutations_are_subject_to_pre_tool_hooks(tmp_path: Path, monkeypatch):
    hook_config = tmp_path / "hooks.json"
    hook_config.write_text(json.dumps({"hooks": {"PreToolUse": [{
        "matcher": "^make_directory$",
        "hooks": [{
            "type": "command",
            "command": [sys.executable, "-c", "import sys; sys.stderr.write('blocked'); sys.exit(2)"],
        }],
    }]}}), encoding="utf-8")
    monkeypatch.setenv("CASPER_HOOKS_FILE", str(hook_config))
    runtime = HarnessRuntime(
        tmp_path,
        tmp_path / "state",
        provider=QuietProvider(),
        permission_mode=PermissionMode.ACCEPT_EDITS,
    )

    result = await runtime.handle_control(f"/mkdir {tmp_path / 'blocked'}")

    assert result.status.value == "error"
    assert "Hook blocked" in result.summary
    assert not (tmp_path / "blocked").exists()


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("help", "/help"),
        ("casper setup", "/setup"),
        ("casper: /config", "/config"),
        ("create a new directory in Volumes/Storage named JCODE", "/mkdir /Volumes/Storage/JCODE"),
        ("create a component", "create a component"),
    ],
)
def test_familiar_terminal_input_stays_out_of_the_llm(raw: str, expected: str):
    assert _normalize_input(raw) == expected
