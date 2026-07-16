import pytest

from core.harness import RepositoryContext, RunEvent, RunState, RunStore, WorkspaceEngine


def test_transactional_patch_and_durable_undo(tmp_path):
    project = tmp_path / "project"
    state = tmp_path / "state"
    project.mkdir(exist_ok=True)
    target = project / "app.py"
    target.write_text("value = 1\n", encoding="utf-8")
    workspace = WorkspaceEngine(project, state)
    result = workspace.patch_file("app.py", "value = 1", "value = 2")
    change_id = result.data["change_id"]
    assert target.read_text() == "value = 2\n"
    assert "-value = 1" in result.data["diff"]
    restored = WorkspaceEngine(project, state).undo(change_id)
    assert restored.status.value == "success"
    assert target.read_text() == "value = 1\n"
    assert WorkspaceEngine(project, state).changes()[0].undone is True


def test_patch_precondition_and_root_containment(tmp_path):
    project = tmp_path / "project"
    project.mkdir(exist_ok=True)
    (project / "x.txt").write_text("x")
    workspace = WorkspaceEngine(project, tmp_path / "state")
    assert workspace.patch_file("x.txt", "x", "y", "wrong").status.value == "error"
    with pytest.raises(ValueError):
        workspace.read_file("../outside.txt")


@pytest.mark.asyncio
async def test_command_profile_blocks_shell_and_allows_python(tmp_path):
    project = tmp_path / "project"
    project.mkdir(exist_ok=True)
    workspace = WorkspaceEngine(project, tmp_path / "state")
    denied = await workspace.run_command(["bash", "-c", "echo no"])
    allowed = await workspace.run_command(["python3", "-c", "print('yes')"])
    assert denied.status.value == "error"
    assert allowed.data["exit_code"] == 0
    assert allowed.data["execution_profile"] == "project-verification-v1"


def test_run_store_round_trip_events_and_checkpoint(tmp_path):
    store = RunStore(tmp_path / "state")
    state = RunState("Build it")
    store.save(state)
    store.append_event(RunEvent(state.run_id, 1, "run.started", {"ok": True}))
    store.checkpoint(state, "before-edit")
    assert store.load(state.run_id).objective == "Build it"
    assert store.events(state.run_id)[0].payload == {"ok": True}
    assert store.restore_checkpoint(state.run_id, "before-edit").run_id == state.run_id


def test_repository_context_indexes_symbols_and_compacts(tmp_path):
    (tmp_path / "alpha.py").write_text("def calculate_total():\n    return 1\n")
    (tmp_path / "README.md").write_text("alpha project")
    context = RepositoryContext(tmp_path)
    context.refresh()
    selected = context.select("calculate total")
    assert selected[0].path == "alpha.py"
    pack = context.pack("calculate total", token_budget=100)
    assert "alpha.py" in pack.files
    compacted = context.compact([{"role": "user", "content": str(i)} for i in range(20)], keep_recent=3)
    assert compacted[0]["compacted_messages"] == 17
    assert compacted[0]["evidence"][-1] == "user: 16"
    assert len(compacted) == 4


def test_repository_context_includes_instruction_contents_first(tmp_path):
    (tmp_path / "AGENTS.md").write_text("Never report success without evidence.\n")
    (tmp_path / "app.py").write_text("def evidence():\n    return True\n")
    context = RepositoryContext(tmp_path)
    pack = context.pack("evidence", token_budget=100)
    assert pack.instructions == ["AGENTS.md"]
    assert pack.files["AGENTS.md"].startswith("Never report success")
    assert pack.render().index("AGENTS.md") < pack.render().index("app.py")
