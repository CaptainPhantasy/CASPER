import pytest

from core.harness import (
    EvalCase, HarnessEvaluator, HarnessRuntime, ModelTurn,
    PermissionMode, ProviderChain, RunState, RunStatus, ToolCall, normalize_anthropic_response,
    normalize_gemini_response, normalize_openai_response,
)


def test_provider_response_normalizers():
    openai = normalize_openai_response({
        "model": "gpt-test", "choices": [{"finish_reason": "tool_calls", "message": {
            "content": "", "tool_calls": [{"id": "c1", "function": {"name": "read_file", "arguments": '{"path":"a.py"}'}}],
        }}], "usage": {"prompt_tokens": 3, "completion_tokens": 4},
    })
    anthropic = normalize_anthropic_response({
        "content": [{"type": "text", "text": "checking"}, {"type": "tool_use", "id": "c2", "name": "read_file", "input": {"path": "b.py"}}],
        "usage": {"input_tokens": 5, "output_tokens": 6},
    })
    gemini = normalize_gemini_response({
        "candidates": [{"content": {"parts": [{"functionCall": {"name": "read_file", "args": {"path": "c.py"}}}]}}],
        "usageMetadata": {"promptTokenCount": 7, "candidatesTokenCount": 8},
    })
    assert openai.tool_calls[0].arguments["path"] == "a.py"
    assert anthropic.text == "checking"
    assert gemini.tool_calls[0].name == "read_file"
    assert openai.usage["output_tokens"] == 4


class SequenceProvider:
    def __init__(self, turns):
        self.turns = list(turns)
        self.seen_tools = None

    async def complete(self, messages, tools):
        self.seen_tools = tools
        return self.turns.pop(0)


@pytest.mark.asyncio
async def test_provider_chain_fails_over_and_sticks_to_healthy_provider():
    class Failing:
        async def complete(self, messages, tools):
            raise RuntimeError("quota exhausted")

    healthy = SequenceProvider([ModelTurn(text="first"), ModelTurn(text="second")])
    chain = ProviderChain([Failing(), healthy])
    assert (await chain.complete([], [])).text == "first"
    assert (await chain.complete([], [])).text == "second"
    assert chain.active is healthy
    assert chain.failures[0]["provider"] == "Failing"


@pytest.mark.asyncio
async def test_runtime_executes_native_tool_loop_and_persists_events(tmp_path):
    project = tmp_path / "project"
    project.mkdir(exist_ok=True)
    (project / "app.py").write_text("answer = 42\n")
    provider = SequenceProvider([
        ModelTurn(tool_calls=(ToolCall("read_file", {"path": "app.py"}, id="read1"),), stop_reason="tool_use", usage={"input_tokens": 2}),
        ModelTurn(text="Verified answer is 42.", usage={"output_tokens": 3}),
    ])
    runtime = HarnessRuntime(project, tmp_path / "state", provider)
    result = await runtime.run("What is the answer in app.py?")
    assert result.status == RunStatus.COMPLETE
    assert result.text == "Verified answer is 42."
    assert any(event.type == "tool.completed" for event in runtime.events)
    assert runtime.store.load(result.run_id).status == RunStatus.COMPLETE
    assert any(schema["name"] == "read_file" for schema in provider.seen_tools)


@pytest.mark.asyncio
async def test_runtime_pauses_for_patch_approval_and_resumes(tmp_path):
    project = tmp_path / "project"
    project.mkdir(exist_ok=True)
    (project / "app.py").write_text("value = 1\n")
    call = ToolCall("patch_file", {"path": "app.py", "old_text": "value = 1", "new_text": "value = 2"}, id="patch1")
    verify = ToolCall(
        "run_command",
        {"argv": ["python", "-m", "py_compile", "app.py"]},
        id="verify1",
    )
    provider = SequenceProvider([
        ModelTurn(tool_calls=(call,), stop_reason="tool_use"),
        ModelTurn(tool_calls=(verify,), stop_reason="tool_use"),
        ModelTurn(text="Patch applied and verified."),
    ])
    runtime = HarnessRuntime(project, tmp_path / "state", provider)
    paused = await runtime.run("Set value to two")
    assert paused.status == RunStatus.AWAITING_APPROVAL
    assert (project / "app.py").read_text() == "value = 1\n"
    completed = await runtime.resume(paused.run_id, ["patch1"])
    assert completed.status == RunStatus.COMPLETE
    assert (project / "app.py").read_text() == "value = 2\n"
    assert any(event.type == "approval.required" for event in runtime.events)


@pytest.mark.asyncio
async def test_runtime_blocks_unverified_mutation(tmp_path):
    (tmp_path / "app.py").write_text("value = 1\n")
    call = ToolCall(
        "patch_file",
        {"path": "app.py", "old_text": "value = 1", "new_text": "value = 2"},
        id="patch-unverified",
    )
    provider = SequenceProvider([
        ModelTurn(tool_calls=(call,), stop_reason="tool_use"),
        ModelTurn(text="Looks done."),
        ModelTurn(text="Still done without evidence."),
    ])
    runtime = HarnessRuntime(
        tmp_path,
        tmp_path / "state-unverified",
        provider,
        permission_mode=PermissionMode.ACCEPT_EDITS,
    )
    result = await runtime.run("change it")
    assert result.status == RunStatus.BLOCKED
    assert "no successful verification" in result.error
    assert any(event.type == "verification.required" for event in runtime.events)


@pytest.mark.asyncio
async def test_runtime_recovers_by_requesting_verification(tmp_path):
    (tmp_path / "app.py").write_text("value = 1\n")
    patch = ToolCall(
        "patch_file",
        {"path": "app.py", "old_text": "value = 1", "new_text": "value = 2"},
        id="patch-recovery",
    )
    verify = ToolCall(
        "run_command",
        {"argv": ["python", "-m", "py_compile", "app.py"]},
        id="verify-recovery",
    )
    provider = SequenceProvider([
        ModelTurn(tool_calls=(patch,), stop_reason="tool_use"),
        ModelTurn(text="Done before checking."),
        ModelTurn(tool_calls=(verify,), stop_reason="tool_use"),
        ModelTurn(text="Now verified."),
    ])
    runtime = HarnessRuntime(
        tmp_path,
        tmp_path / "state-recovery",
        provider,
        permission_mode=PermissionMode.BYPASS,
    )
    result = await runtime.run("change and verify")
    assert result.status == RunStatus.COMPLETE
    assert result.text == "Now verified."
    assert sum(event.type == "verification.required" for event in runtime.events) == 1


@pytest.mark.asyncio
async def test_runtime_pre_tool_hook_blocks_operation_and_records_event(tmp_path):
    import json
    import sys

    hook_script = tmp_path / "block.py"
    hook_script.write_text("import sys\nprint('blocked by policy', file=sys.stderr)\nraise SystemExit(2)\n")
    hook_dir = tmp_path / ".casper"
    hook_dir.mkdir()
    (hook_dir / "hooks.json").write_text(json.dumps({"hooks": {"PreToolUse": [{
        "matcher": "make_directory", "hooks": [{
            "type": "command", "command": [sys.executable, str(hook_script)],
        }],
    }]}}))
    provider = SequenceProvider([
        ModelTurn(tool_calls=(ToolCall("make_directory", {"path": "blocked"}, id="mkdir-blocked"),)),
        ModelTurn(text="The hook blocked the operation."),
    ])
    runtime = HarnessRuntime(
        tmp_path, tmp_path / "state-hook", provider,
        permission_mode=PermissionMode.ACCEPT_EDITS,
    )

    result = await runtime.run("create blocked directory")

    assert result.status == RunStatus.COMPLETE
    assert not (tmp_path / "blocked").exists()
    assert any(event.type == "hook.blocked" for event in runtime.events)


@pytest.mark.asyncio
async def test_runtime_preserves_follow_up_context_and_new_clears_it(tmp_path):
    class ConversationProvider:
        def __init__(self):
            self.messages = []

        async def complete(self, messages, tools):
            self.messages.append(list(messages))
            return ModelTurn(text="first answer" if len(self.messages) == 1 else "follow-up answer")

    provider = ConversationProvider()
    runtime = HarnessRuntime(tmp_path, tmp_path / "state-conversation", provider)

    await runtime.run("My claim is that the file is accessible.")
    await runtime.run("Prove that claim.")

    second = provider.messages[1]
    assert any(item["role"] == "assistant" and item["content"] == "first answer" for item in second)
    assert (await runtime.handle_control("/new")).status.value == "success"
    assert runtime.conversation == []


@pytest.mark.asyncio
async def test_explicit_file_mentions_are_injected_and_recorded(tmp_path):
    target = tmp_path / "facts.txt"
    target.write_text("DIRECT_EVIDENCE=visible\n", encoding="utf-8")
    provider = SequenceProvider([ModelTurn(text="I used the mentioned file.")])
    runtime = HarnessRuntime(tmp_path, tmp_path / "state-mentions", provider)

    result = await runtime.run("Inspect @facts.txt")

    assert result.status == RunStatus.COMPLETE
    state = runtime.store.load(result.run_id)
    assert any("DIRECT_EVIDENCE=visible" in item.get("content", "") for item in state.messages)
    assert any(event.type == "context.mentioned_files" for event in runtime.events)


@pytest.mark.asyncio
async def test_runtime_controls(tmp_path):
    runtime = HarnessRuntime(tmp_path, tmp_path / "state", SequenceProvider([ModelTurn(text="ok")]))
    permission = await runtime.handle_control("/permissions set accept_edits")
    changes = await runtime.handle_control("/changes")
    assert permission.data["mode"] == PermissionMode.ACCEPT_EDITS.value
    assert changes.data["changes"] == []
    assert await runtime.handle_control("ordinary text") is None


@pytest.mark.asyncio
async def test_runtime_resumes_active_state_without_replaying_tools(tmp_path):
    provider = SequenceProvider([ModelTurn(text="Recovered without replay.")])
    runtime = HarnessRuntime(tmp_path, tmp_path / "state-active", provider)
    state = RunState("recover interrupted run")
    state.messages = [
        {"role": "user", "content": state.objective},
        {"role": "tool", "name": "patch_file", "content": "already completed"},
    ]
    runtime.store.save(state)
    resumed = await runtime.resume(state.run_id)
    assert resumed.status == RunStatus.COMPLETE
    assert resumed.text == "Recovered without replay."
    assert provider.seen_tools is not None
    assert any(event.type == "run.resumed" for event in runtime.events)


@pytest.mark.asyncio
async def test_evaluator_reports_pass_at_one_tokens_and_cost(tmp_path):
    counter = {"value": 0}
    def factory():
        counter["value"] += 1
        provider = SequenceProvider([ModelTurn(text="done", usage={"input_tokens": 100, "output_tokens": 50})])
        return HarnessRuntime(tmp_path, tmp_path / f"state-{counter['value']}", provider)
    evaluator = HarnessEvaluator(factory, input_cost_per_million=1.0, output_cost_per_million=2.0)
    report = await evaluator.run([EvalCase("simple", "answer", verifier=lambda result, events: result.text == "done")])
    data = report.to_dict()
    assert data["completion_rate"] == 1.0
    assert data["pass_at_1"] == 1.0
    assert data["attempts"][0]["estimated_cost_usd"] == 0.0002
