import json
import sys
from pathlib import Path

import pytest

from core.harness import (
    AgentProfile, AgentProfileRegistry, ExtensionRegistry, ExtensionSpec,
    HookContext, LifecycleEvent, LifecycleHooks, MCPServerConfig,
    MCPServerRegistry, MCPTransport, PermissionMode, SkillDiscovery,
)


@pytest.mark.asyncio
async def test_lifecycle_hooks_are_ordered_and_report_failures():
    hooks = LifecycleHooks()
    calls = []
    hooks.register("late", LifecycleEvent.RUN_START, lambda context: calls.append("late"), priority=20)
    hooks.register("early", LifecycleEvent.RUN_START, lambda context: calls.append("early"), priority=10)

    def broken(context):
        raise RuntimeError("bad extension")

    hooks.register("broken", LifecycleEvent.RUN_START, broken, priority=30)
    failures = await hooks.emit(HookContext(LifecycleEvent.RUN_START, "run_1"))
    assert calls == ["early", "late"]
    assert failures[0].hook == "broken"
    assert "bad extension" in failures[0].error


def test_namespaced_extension_registry():
    registry = ExtensionRegistry()
    spec = ExtensionSpec("acme", "reviewer", "1.2.0", capabilities=("review",))
    registry.register(spec)
    assert registry.require("acme:reviewer") is spec
    assert registry.list("acme") == (spec,)
    with pytest.raises(ValueError, match="already registered"):
        registry.register(spec)


def test_skill_discovery_reads_metadata_and_first_duplicate_wins(tmp_path: Path):
    first = tmp_path / "one" / "review"
    second = tmp_path / "two" / "review"
    first.mkdir(parents=True, exist_ok=True)
    second.mkdir(parents=True, exist_ok=True)
    (first / "SKILL.md").write_text(
        "---\nname: reviewer\ndescription: Reviews code\nversion: 1\ntags: [code, quality]\n---\n",
        encoding="utf-8",
    )
    (second / "SKILL.md").write_text("---\nname: reviewer\ndescription: Other\n---\n", encoding="utf-8")
    result = SkillDiscovery((tmp_path / "one", tmp_path / "two")).discover()
    assert result.skills[0].description == "Reviews code"
    assert result.skills[0].tags == ("code", "quality")
    assert result.warnings == ()


@pytest.mark.asyncio
async def test_command_hooks_load_match_receive_json_and_block(tmp_path: Path):
    from core.harness import HookContext, LifecycleEvent, LifecycleHooks

    script = tmp_path / "guard.py"
    script.write_text(
        "import json, sys\n"
        "data = json.load(sys.stdin)\n"
        "if data.get('tool_name') == 'patch_file':\n"
        "    print('protected by test hook', file=sys.stderr)\n"
        "    raise SystemExit(2)\n",
        encoding="utf-8",
    )
    config = tmp_path / "hooks.json"
    config.write_text(json.dumps({"hooks": {"PreToolUse": [{
        "matcher": "patch_file", "hooks": [{
            "type": "command", "name": "guard", "command": [sys.executable, str(script)],
            "timeout": 5,
        }],
    }]}}), encoding="utf-8")
    hooks = LifecycleHooks.from_paths((config,), cwd=tmp_path)

    dispatch = await hooks.trigger(HookContext(
        LifecycleEvent.BEFORE_TOOL, "run_1", {"tool_name": "patch_file", "tool_input": {}},
    ), matcher_value="patch_file")

    assert dispatch.blocked is True
    assert "protected by test hook" in dispatch.reason
    assert dispatch.executions[0].exit_code == 2


@pytest.mark.asyncio
async def test_invalid_json_hook_output_is_contained_as_diagnostic(tmp_path: Path):
    from core.harness import HookContext, LifecycleEvent, LifecycleHooks

    script = tmp_path / "invalid.py"
    script.write_text("print('{invalid')\n", encoding="utf-8")
    hooks = LifecycleHooks(cwd=tmp_path)
    hooks.register_command("invalid", LifecycleEvent.SESSION_START, [sys.executable, str(script)])

    dispatch = await hooks.trigger(HookContext(LifecycleEvent.SESSION_START, "session_1"))

    assert dispatch.blocked is False
    assert "invalid JSON" in dispatch.failures[0].error


def test_mcp_registry_validates_transport_and_redacts_environment():
    registry = MCPServerRegistry()
    config = MCPServerConfig(
        "local", MCPTransport.STDIO, command=("python3", "server.py"),
        environment={"SECRET": "value"},
    )
    registry.register(config)
    assert registry.require("local").redacted()["environment_keys"] == ["SECRET"]
    assert "value" not in str(registry.require("local").redacted())
    assert registry.set_enabled("local", False).enabled is False
    with pytest.raises(ValueError, match="require an http"):
        registry.register(MCPServerConfig("remote", MCPTransport.HTTP))


def test_custom_agent_profiles_have_explicit_boundaries():
    registry = AgentProfileRegistry()
    profile = AgentProfile(
        "critic", "Finds defects", "Inspect evidence.", model="test-model",
        allowed_tools=("read_file",), permission_mode=PermissionMode.READ_ONLY, max_steps=8,
    )
    registry.register(profile)
    assert registry.require("critic").max_steps == 8
    assert registry.list() == (profile,)
