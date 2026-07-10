"""
Unit tests for the deterministic pipeline pieces (no LLM / network required).
Run: ./.casper-venv/bin/python -m pytest core/pipeline/tests -q
"""

import asyncio
import os
import tempfile

import pytest

from core.pipeline.models import (
    FrozenSpec, SpecRequirement, TaskUnit, TaskKind, ModelClass, RiskLevel,
    ClarifyingQuestion, SpecNotReadyError,
)
from core.pipeline.autonomy import GraduatedAutonomy, AutonomyMode, ProposedAction
from core.pipeline.routing import TaskAwareRouter, BudgetState
from core.pipeline.skills import SkillRegistry, ensure_seed_skills
from core.pipeline.context import ContextManager, GlobalPlan, UnitOutcome
from core.pipeline.progress import ChangeLedger, ProgressTracker
from core.pipeline.models import PipelineStage


# ----------------------------------------------------------------- models
def test_spec_freeze_and_integrity():
    s = FrozenSpec.new("build a thing", "summary")
    s.requirements.append(SpecRequirement(id="r1", text="do x", acceptance_criteria=["x exists"]))
    assert not s.frozen
    s.freeze()
    assert s.frozen and s.verify_integrity()
    # Tampering after freeze is detectable.
    s.requirements.append(SpecRequirement(id="r2", text="sneaky"))
    assert not s.verify_integrity()


def test_spec_cannot_freeze_with_open_required_question():
    s = FrozenSpec.new("intent")
    s.requirements.append(SpecRequirement(id="r1", text="x"))
    s.open_questions.append(ClarifyingQuestion(id="q1", question="?", why="because", required=True))
    with pytest.raises(SpecNotReadyError):
        s.freeze()


# --------------------------------------------------------------- autonomy
def test_autonomy_risk_classification():
    ga = GraduatedAutonomy(AutonomyMode.AUTO)
    assert ga.assess(ProposedAction("delete", path="a.py")).risk == RiskLevel.HIGH
    assert ga.assess(ProposedAction("delete", path="a.py")).auto_approved is False
    assert ga.assess(ProposedAction("create", path="a.py")).risk == RiskLevel.SAFE
    assert ga.assess(ProposedAction("create", path="a.py")).auto_approved is True
    assert ga.assess(ProposedAction("command", command="rm -rf /")).risk == RiskLevel.CRITICAL
    assert ga.assess(ProposedAction("command", command="ls -la")).risk == RiskLevel.SAFE
    assert ga.assess(ProposedAction("deploy", path="site")).risk == RiskLevel.CRITICAL


def test_autonomy_modes():
    crit = ProposedAction("deploy")
    assert GraduatedAutonomy(AutonomyMode.YOLO).assess(crit).auto_approved is False  # CRITICAL never auto
    safe = ProposedAction("create", path="x.py")
    assert GraduatedAutonomy(AutonomyMode.STRICT).assess(safe).auto_approved is True  # SAFE auto even in STRICT
    mod = ProposedAction("command", command="some-unknown-cmd")
    assert GraduatedAutonomy(AutonomyMode.STRICT).assess(mod).auto_approved is False
    assert GraduatedAutonomy(AutonomyMode.AUTO).assess(mod).auto_approved is True


# ---------------------------------------------------------------- routing
def test_router_kind_to_class_and_escalation():
    r = TaskAwareRouter(provider="anthropic", budget=BudgetState())
    arch = TaskUnit.new("design system", "architecture", kind=TaskKind.ARCHITECTURE)
    mech = TaskUnit.new("rename files", "move stuff", kind=TaskKind.MECHANICAL)
    # We avoid network by testing the pure classification + escalation helpers.
    assert r.classify_kind(arch) == TaskKind.ARCHITECTURE
    assert r.classify_kind(mech) == TaskKind.MECHANICAL
    # Escalation ladder promotes cheap → ... on repeated failures.
    assert r._apply_escalation(ModelClass.CHEAP, 0) == ModelClass.CHEAP
    assert r._apply_escalation(ModelClass.CHEAP, 1) == ModelClass.STANDARD
    assert r._apply_escalation(ModelClass.CHEAP, 5) == ModelClass.FRONTIER  # capped


def test_router_budget_downgrade():
    r = TaskAwareRouter(provider="anthropic", budget=BudgetState(limit_tokens=1000, spent_tokens=900))
    assert r._apply_budget(ModelClass.STANDARD) == ModelClass.CHEAP
    assert r._apply_budget(ModelClass.FRONTIER) == ModelClass.FRONTIER  # reasoning never crippled


def test_router_kind_inference_from_text():
    r = TaskAwareRouter()
    u = TaskUnit.new("Rename the helper", "rename foo to bar", kind=None)  # type: ignore[arg-type]
    assert r.classify_kind(u) == TaskKind.MECHANICAL


# ----------------------------------------------------------------- skills
def test_skills_find_and_learn():
    with tempfile.TemporaryDirectory() as d:
        reg = SkillRegistry(d, shared_home=os.path.join(d, "shared"))
        ensure_seed_skills(reg)
        match = reg.best("write a python function with pytest tests")
        assert match is not None and "python" in [t.lower() for t in match.triggers] or match.name
        before = match.confidence
        reg.record_outcome(match.id, success=True)
        reg.reload()
        after = next(s for s in reg.all_skills() if s.id == match.id)
        assert after.confidence >= before and after.success_count == 1


# ---------------------------------------------------------------- context
def test_context_slicing_and_discard():
    with tempfile.TemporaryDirectory() as d:
        # a file the unit declares relevant
        with open(os.path.join(d, "a.py"), "w") as f:
            f.write("print('hi')\n")
        spec = FrozenSpec.new("intent", "summary")
        spec.requirements += [SpecRequirement(id="r1", text="x"), SpecRequirement(id="r2", text="y")]
        spec.freeze()
        unit = TaskUnit.new("u", "do x", requirement_ids=["r1"], relevant_paths=["a.py"])
        plan = GlobalPlan(spec=spec, units=[unit])
        cm = ContextManager(d)
        ctx = cm.build_worker_context(plan, unit)
        # Only the r1 slice, only a.py.
        assert [r.id for r in ctx.requirements] == ["r1"]
        assert "a.py" in ctx.files and "hi" in ctx.files["a.py"]
        # Discard wipes transient content.
        cm.discard(ctx)
        assert ctx.files == {}


def test_plan_dependency_ordering():
    spec = FrozenSpec.new("i", "s")
    spec.requirements.append(SpecRequirement(id="r1", text="x"))
    spec.freeze()
    u1 = TaskUnit.new("first", "", requirement_ids=["r1"])
    u2 = TaskUnit.new("second", "", depends_on=[u1.id])
    plan = GlobalPlan(spec=spec, units=[u1, u2])
    ready = [u.id for u in plan.pending_units()]
    assert u1.id in ready and u2.id not in ready  # u2 blocked on u1
    plan.record(UnitOutcome(unit_id=u1.id, success=True))
    ready2 = [u.id for u in plan.pending_units()]
    assert u2.id in ready2


# ----------------------------------------------------------------- ledger
def test_ledger_record_and_undo_create():
    with tempfile.TemporaryDirectory() as d:
        ledger = ChangeLedger(d)
        path = "made.txt"
        full = os.path.join(d, path)
        with open(full, "w") as f:
            f.write("content")
        entry = ledger.record_create(path, "created")
        assert os.path.exists(full)
        res = ledger.undo(entry.id)
        assert res["status"] == "ok"
        assert not os.path.exists(full)  # create undone → file quarantined away


def test_ledger_modify_undo_from_snapshot():
    with tempfile.TemporaryDirectory() as d:
        ledger = ChangeLedger(d)
        path = "m.txt"
        full = os.path.join(d, path)
        with open(full, "w") as f:
            f.write("original")
        ref = ledger.snapshot_before_modify(path)
        with open(full, "w") as f:
            f.write("changed")
        entry = ledger.record_modify(path, ref, "modified")
        assert ledger.undo(entry.id)["status"] == "ok"
        assert open(full).read() == "original"


# ---------------------------------------------------------------- progress
def test_progress_tracker_emits_labels():
    seen = []
    pt = ProgressTracker("run_1")
    pt.on_update(lambda payload: seen.append(payload))
    pt.set_stage(PipelineStage.PLANNING, "x")
    assert seen and seen[-1]["stage"] == "planning"
    assert seen[-1]["label"]  # human label present
