import pytest

from core.services.goal_engine import GoalEngine, GoalError


def test_goal_completion_requires_evidence_and_passing_verification(tmp_path):
    engine = GoalEngine(storage_path=tmp_path / "goal.json", project_root=tmp_path)
    goal = engine.start("Ship a verified change")
    assert goal["status"] == "active"

    with pytest.raises(GoalError, match="direct-evidence"):
        engine.complete()

    engine.add_evidence("pytest tests/test_goal_engine.py exited 0")
    with pytest.raises(GoalError, match="PASS"):
        engine.complete()

    engine.verify(True, "1 test passed")
    completed = engine.complete()
    assert completed["status"] == "complete"
    assert completed["verification"]["status"] == "PASS"


def test_goal_refuses_to_replace_an_active_goal(tmp_path):
    engine = GoalEngine(storage_path=tmp_path / "goal.json", project_root=tmp_path)
    engine.start("First goal")
    with pytest.raises(GoalError, match="active goal"):
        engine.start("Second goal")


def test_goal_block_and_clear_are_persisted(tmp_path):
    engine = GoalEngine(storage_path=tmp_path / "goal.json", project_root=tmp_path)
    engine.start("Blocked goal")
    assert engine.block("Missing user credential")["status"] == "blocked"
    engine.clear()
    assert engine.load() is None
