import json
import subprocess

import pytest

from core.harness import (
    HARNESS_COMMANDS, CodeReviewSentinel, HarnessRuntime, ModelTurn,
    ReviewValidationError,
)
from core.terminal.modern_cli import _agentic_prompt


class CapturingProvider:
    def __init__(self, reports):
        self.reports = list(reports)
        self.messages = []

    async def complete(self, messages, tools):
        self.messages.append(messages)
        value = self.reports.pop(0)
        return ModelTurn(text=value if isinstance(value, str) else json.dumps(value))


def clean_report(files=1):
    return {
        "summary": {
            "files_reviewed": files,
            "overall_verdict": "CLEAN",
            "headline": "No threshold-qualified defects were found in the reviewed diff.",
        },
        "findings": [],
        "low_confidence_observations": [],
        "things_i_could_not_verify": ["Runtime behavior was not exercised by this model-only review."],
    }


def project(tmp_path):
    root = tmp_path / "project"
    root.mkdir(exist_ok=True)
    subprocess.run(["git", "init", "-q"], cwd=root, check=True)
    subprocess.run(["git", "config", "user.email", "e2e@example.invalid"], cwd=root, check=True)
    subprocess.run(["git", "config", "user.name", "E2E"], cwd=root, check=True)
    target = root / "app.py"
    target.write_text("value = 1\n", encoding="utf-8")
    subprocess.run(["git", "add", "app.py"], cwd=root, check=True)
    subprocess.run(["git", "commit", "-qm", "base"], cwd=root, check=True)
    return root


def test_command_catalog_is_unique_and_claude_code_aligned():
    names = [item.name for item in HARNESS_COMMANDS]
    assert len(names) == len(set(names)) == 36
    assert {
        "commands", "status", "doctor", "context", "diff", "review", "code-review",
        "security-review", "goal", "plan", "task", "verify", "permissions", "resume",
        "rewind", "skills", "mcp", "agents", "tasks", "hooks", "usage", "setup",
        "config", "export", "pwd", "clear",
        "workdir", "history", "mkdir",
        "new",
    } <= set(names)


@pytest.mark.asyncio
async def test_runtime_commands_are_typed_and_unknown_commands_fail_closed(tmp_path):
    root = project(tmp_path)
    runtime = HarnessRuntime(root, tmp_path / "state", provider=CapturingProvider([]))
    commands = await runtime.handle_control("/commands review")
    status = await runtime.handle_control("/status")
    unknown = await runtime.handle_control("/definitely-not-real")
    assert commands.status.value == "success"
    assert [item["name"] for item in commands.data["commands"]] == [
        "review", "code-review", "security-review"
    ]
    assert status.data["branch"]
    assert unknown.status.value == "error"
    assert unknown.stop_condition


@pytest.mark.asyncio
async def test_goal_command_enforces_evidence_before_completion(tmp_path):
    root = project(tmp_path)
    runtime = HarnessRuntime(root, tmp_path / "state", provider=CapturingProvider([]))
    started = await runtime.handle_control("/goal ship verified commands")
    rejected = await runtime.handle_control("/goal complete")
    await runtime.handle_control("/goal prove pytest exited 0")
    await runtime.handle_control("/goal verify pass command tests passed")
    completed = await runtime.handle_control("/goal complete")
    assert started.data["goal"]["status"] == "active"
    assert rejected.status.value == "error"
    assert completed.data["goal"]["status"] == "complete"


@pytest.mark.asyncio
async def test_review_redacts_diff_and_returns_validated_json(tmp_path):
    root = project(tmp_path)
    (root / "app.py").write_text("api_key=secretvalue123\n", encoding="utf-8")
    provider = CapturingProvider([clean_report()])
    result = await CodeReviewSentinel(root, provider).review(effort="low")
    sent = provider.messages[0][-1]["content"]
    assert result.report["summary"]["overall_verdict"] == "CLEAN"
    assert result.redactions == 1
    assert "secretvalue123" not in sent
    assert "<redacted:credential_assignment>" in sent


@pytest.mark.asyncio
async def test_review_retries_invalid_json_once(tmp_path):
    root = project(tmp_path)
    (root / "app.py").write_text("value = 2\n", encoding="utf-8")
    provider = CapturingProvider(["not json", clean_report()])
    result = await CodeReviewSentinel(root, provider).review()
    assert result.attempts == 2
    assert len(provider.messages) == 2


@pytest.mark.asyncio
async def test_review_hard_gate_rejects_unbundled_high_finding(tmp_path):
    root = project(tmp_path)
    (root / "app.py").write_text("value = 2\n", encoding="utf-8")
    invalid = clean_report()
    invalid["summary"]["overall_verdict"] = "REQUEST_CHANGES"
    invalid["findings"] = [{
        "id": "F1", "lens": "CORRECTNESS", "severity": "HIGH", "confidence": 0.9,
        "file": "app.py", "line_start": 1, "line_end": 1, "title": "Fix the defect",
        "observation": "The changed value violates the contract.",
        "why_it_matters": "Callers receive the wrong value.",
        "remediation": {"approach": "Add a red-to-green assertion.", "tier": "YELLOW"},
    }]
    provider = CapturingProvider([invalid, invalid])
    with pytest.raises(ReviewValidationError, match="remained invalid"):
        await CodeReviewSentinel(root, provider).review()


def test_agentic_commands_compile_to_explicit_runtime_contracts():
    assert _agentic_prompt("/task fix parser") == "fix parser"
    assert "without mutating files" in _agentic_prompt("/plan fix parser")
    assert "direct runtime or test evidence" in _agentic_prompt("/verify parser behavior")
    with pytest.raises(ValueError, match="Usage: /task"):
        _agentic_prompt("/task")
