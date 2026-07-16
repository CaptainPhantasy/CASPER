"""Evidence tests for the 20 coding-agent slash command engines."""

from __future__ import annotations

import io
import json
import subprocess
from dataclasses import dataclass
from pathlib import Path

import pytest
from rich.console import Console

from core.terminal.ui.feature_manager import TranscriptEntry
from core.terminal.ui.terminal_ui import TerminalUI


def git(root: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", *args], cwd=root, text=True, capture_output=True, check=False
    )


def project(tmp_path: Path) -> Path:
    git(tmp_path, "init", "-q")
    git(tmp_path, "config", "user.email", "casper-tests@example.invalid")
    git(tmp_path, "config", "user.name", "CASPER Tests")
    (tmp_path / "pyproject.toml").write_text(
        "[project]\nname='fixture'\nversion='0.1.0'\n"
    )
    (tmp_path / "sample.py").write_text("def add(a, b):\n    return a + b\n")
    (tmp_path / "test_sample.py").write_text(
        "from sample import add\n\ndef test_add():\n    assert add(2, 3) == 5\n"
    )
    git(tmp_path, "add", ".")
    git(tmp_path, "commit", "-qm", "fixture")
    return tmp_path


def make_ui(tmp_path: Path) -> TerminalUI:
    return TerminalUI(
        "Coding Commands",
        state_root=tmp_path / ".tui-state",
        project_root=tmp_path,
        console=Console(file=io.StringIO(), force_terminal=False, record=True),
    )


def observation(result) -> dict:
    return json.loads(result.message)


@pytest.mark.asyncio
async def test_init_engine(tmp_path):
    root = project(tmp_path)
    ui = make_ui(root)
    await ui.execute_command("/permissions set accept-edits")
    result = observation(await ui.execute_command("/init"))
    assert result["status"] == "success"
    assert (root / "AGENTS.md").exists()
    assert str(root / "AGENTS.md") in result["artifacts"]


@pytest.mark.asyncio
async def test_status_engine(tmp_path):
    root = project(tmp_path)
    (root / "sample.py").write_text("changed = True\n")
    result = observation(await make_ui(root).execute_command("/status"))
    assert result["status"] == "success"
    assert result["data"]["changes"] == [" M sample.py"]
    assert result["data"]["head"]


@pytest.mark.asyncio
async def test_doctor_engine(tmp_path):
    result = observation(await make_ui(project(tmp_path)).execute_command("/doctor"))
    assert result["status"] == "success"
    assert result["data"]["build_system"]["kind"] == "python"
    assert result["data"]["runtimes"]["git"]["present"] is True


class FakeConfig:
    def __init__(self):
        self.provider = "anthropic"
        self.model = "alpha"

    def get_default_provider(self):
        return self.provider

    def get_default_model(self, fallback=None, provider=None):
        return self.model or fallback

    def set_default_model(self, provider, model):
        self.provider, self.model = provider, model


class FakeModels:
    async def list_available_models(self):
        return {"anthropic": {"primary": "alpha", "worker": "beta"}}

    async def complete(self, **kwargs):
        return "P1 sample.py:1 concrete review finding"


@pytest.mark.asyncio
async def test_model_engine(tmp_path):
    ui = make_ui(project(tmp_path))
    ui.coding_commands.config_adapter = FakeConfig()
    ui.coding_commands.model_service = FakeModels()
    listed = observation(await ui.execute_command("/model list"))
    assert listed["data"]["models"]["anthropic"]["primary"] == "alpha"
    await ui.execute_command("/permissions set accept-edits")
    selected = observation(await ui.execute_command("/model set openai omega"))
    assert selected["data"]["provider"] == "openai"
    assert selected["data"]["model"] == "omega"
    assert ui.coding_commands.config_adapter.model == "omega"


@pytest.mark.asyncio
async def test_permissions_engine(tmp_path):
    ui = make_ui(project(tmp_path))
    result = observation(await ui.execute_command("/permissions set plan"))
    assert result["data"]["mode"] == "plan"
    assert result["data"]["mutations_allowed"] is False
    blocked = observation(await ui.execute_command("/init"))
    assert blocked["status"] in {"success", "warning"}


@pytest.mark.asyncio
async def test_diff_engine(tmp_path):
    root = project(tmp_path)
    (root / "sample.py").write_text("value = 42\n")
    result = observation(await make_ui(root).execute_command("/diff -- sample.py"))
    assert result["status"] == "success"
    assert "+value = 42" in result["data"]["output"]


@pytest.mark.asyncio
async def test_review_engine(tmp_path):
    root = project(tmp_path)
    (root / "sample.py").write_text("value = 42\n")
    ui = make_ui(root)
    ui.coding_commands.model_service = FakeModels()
    result = observation(await ui.execute_command("/review"))
    assert result["status"] == "success"
    assert "concrete review finding" in result["data"]["review"]


class FakeSpec:
    def to_dict(self):
        return {"summary": "frozen", "frozen": True}


class FakeCompiler:
    async def compile(self, request):
        return FakeSpec()


@pytest.mark.asyncio
async def test_plan_engine(tmp_path):
    ui = make_ui(project(tmp_path))
    ui.coding_commands.compiler_factory = FakeCompiler
    result = observation(await ui.execute_command("/plan add validation"))
    assert result["status"] == "success"
    assert result["data"]["spec"]["frozen"] is True
    assert "no code was executed" in result["summary"]


class FakePipelineResult:
    def to_dict(self):
        return {
            "status": "done",
            "human_summary": "verified task",
            "artifacts": ["proof.py"],
        }


class FakePipeline:
    async def run(self, request):
        return FakePipelineResult()


@pytest.mark.asyncio
async def test_task_engine(tmp_path):
    ui = make_ui(project(tmp_path))
    ui.coding_commands.pipeline_factory = lambda root: FakePipeline()
    blocked = observation(await ui.execute_command("/task create proof"))
    assert blocked["status"] == "warning"
    await ui.execute_command("/permissions set accept-edits")
    result = observation(await ui.execute_command("/task create proof"))
    assert result["status"] == "success"
    assert result["artifacts"] == ["proof.py"]


@pytest.mark.asyncio
async def test_test_engine(tmp_path):
    root = project(tmp_path)
    result = observation(await make_ui(root).execute_command("/test test_sample.py"))
    assert result["status"] == "success"
    assert result["data"]["exit_code"] == 0
    assert "1 passed" in result["data"]["output"]


@pytest.mark.asyncio
async def test_lint_engine(tmp_path):
    result = observation(
        await make_ui(project(tmp_path)).execute_command("/lint sample.py")
    )
    assert result["status"] == "success"
    assert result["data"]["exit_code"] == 0


@pytest.mark.asyncio
async def test_build_engine(tmp_path):
    result = observation(await make_ui(project(tmp_path)).execute_command("/build"))
    assert result["status"] == "success"
    assert result["data"]["exit_code"] == 0


@pytest.mark.asyncio
async def test_context_engine(tmp_path):
    result = observation(await make_ui(project(tmp_path)).execute_command("/context"))
    assert result["status"] == "success"
    assert result["data"]["tracked_files"] == 3
    assert result["data"]["git_head"]


@pytest.mark.asyncio
async def test_compact_engine(tmp_path):
    ui = make_ui(project(tmp_path))
    for index in range(15):
        ui.features.transcript.append(
            TranscriptEntry(str(index), "reasoning", "result", f"entry {index}")
        )
    result = observation(await ui.execute_command("/compact"))
    assert result["status"] == "success"
    assert result["data"]["before"] == 15
    assert result["data"]["after"] == 11


@pytest.mark.asyncio
async def test_resume_engine(tmp_path):
    ui = make_ui(project(tmp_path))
    ui.panes["code"].content = "saved content"
    ui.features.save_session("demo", ui.panes)
    ui.panes["code"].content = "changed"
    result = observation(await ui.execute_command("/resume demo"))
    assert result["status"] == "success"
    assert ui.panes["code"].content == "saved content"


@pytest.mark.asyncio
async def test_skills_engine(tmp_path):
    root = project(tmp_path)
    skills = root / ".casper" / "skills"
    skills.mkdir(parents=True)
    (skills / "proof.json").write_text(
        json.dumps(
            {"id": "proof", "name": "Proof Skill", "description": "pytest evidence"}
        )
    )
    result = observation(await make_ui(root).execute_command("/skills pytest"))
    assert result["status"] == "success"
    assert result["data"]["skills"][0]["name"] == "Proof Skill"


@dataclass
class FakeMCP:
    port: int = 8743
    stats: dict = None
    connections: dict = None

    def __post_init__(self):
        self.stats = {"requests_processed": 7}
        self.connections = {"one": object()}


class FakeIntegration:
    def __init__(self):
        self.mcp_server = FakeMCP()
        self.agent_session = {
            "session_id": "agent-1",
            "status": "ready",
            "layers": {"omega": {"agents_count": 1}},
        }


@pytest.mark.asyncio
async def test_mcp_engine(tmp_path):
    ui = make_ui(project(tmp_path))
    ui.bind_integration(FakeIntegration())
    result = observation(await ui.execute_command("/mcp"))
    assert result["status"] == "success"
    assert result["data"]["connections"] == 1
    assert result["data"]["stats"]["requests_processed"] == 7


@pytest.mark.asyncio
async def test_agents_engine(tmp_path):
    ui = make_ui(project(tmp_path))
    ui.bind_integration(FakeIntegration())
    result = observation(await ui.execute_command("/agents"))
    assert result["status"] == "success"
    assert result["data"]["session_id"] == "agent-1"
    assert result["data"]["layers"]["omega"]["agents_count"] == 1


@pytest.mark.asyncio
async def test_rewind_engine(tmp_path):
    root = project(tmp_path)
    created = root / "generated.py"
    created.write_text("generated = True\n")
    from core.pipeline.progress import ChangeLedger

    ledger = ChangeLedger(str(root))
    entry = ledger.record_create("generated.py", "Created generated.py")
    ui = make_ui(root)
    listed = observation(await ui.execute_command("/rewind list"))
    assert listed["data"]["changes"][0]["id"] == entry.id
    await ui.execute_command("/permissions set accept-edits")
    undone = observation(await ui.execute_command(f"/rewind undo {entry.id}"))
    assert undone["status"] == "success"
    assert not created.exists()


@pytest.mark.asyncio
async def test_usage_engine(tmp_path):
    ui = make_ui(project(tmp_path))
    await ui.execute_command("/status")
    result = observation(await ui.execute_command("/usage"))
    assert result["status"] == "success"
    assert result["data"]["commands"]["/status"]["count"] == 1
    assert result["summary"].endswith("not provider billing data.")
