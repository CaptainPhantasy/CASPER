import asyncio
from pathlib import Path

import pytest

from core.harness import (
    BackgroundJobSupervisor, CancellationError, CancellationToken,
    HealthCheckResult, HealthDiagnostics, HealthStatus, JobStatus,
    TaskDAGScheduler, TaskNode, TaskStatus, WorktreePlanner,
)


def test_cancellation_token_propagates_once():
    parent = CancellationToken()
    child = parent.child()
    assert parent.cancel("operator stopped") is True
    assert parent.cancel("again") is False
    assert child.cancelled and child.reason == "operator stopped"
    with pytest.raises(CancellationError, match="operator stopped"):
        child.raise_if_cancelled()


@pytest.mark.asyncio
async def test_dag_scheduler_orders_dependencies_and_blocks_failures():
    calls = []

    async def first(token):
        calls.append("first")
        return 1

    async def second(token):
        calls.append("second")
        raise ValueError("broken")

    scheduler = TaskDAGScheduler((
        TaskNode("first", first),
        TaskNode("second", second, ("first",)),
        TaskNode("third", lambda token: calls.append("third"), ("second",)),
    ), max_concurrency=2)
    results = await scheduler.run()
    assert calls == ["first", "second"]
    assert results["first"].status == TaskStatus.SUCCEEDED
    assert results["second"].status == TaskStatus.FAILED
    assert results["third"].status == TaskStatus.BLOCKED
    with pytest.raises(ValueError, match="cycle"):
        TaskDAGScheduler((TaskNode("a", first, ("b",)), TaskNode("b", first, ("a",))))


@pytest.mark.asyncio
async def test_background_job_supervisor_tracks_success_and_cancellation():
    supervisor = BackgroundJobSupervisor(max_active=2)
    success = supervisor.submit("success", lambda token: 42)
    finished = await supervisor.wait(success.job_id)
    assert finished.status == JobStatus.SUCCEEDED and finished.result == 42

    started = asyncio.Event()

    async def long_running(token):
        started.set()
        await asyncio.sleep(30)

    active = supervisor.submit("long", long_running)
    await started.wait()
    assert supervisor.cancel(active.job_id, "test stop") is True
    cancelled = await supervisor.wait(active.job_id)
    assert cancelled.status == JobStatus.CANCELLED
    assert "test stop" in cancelled.error


@pytest.mark.asyncio
async def test_health_diagnostics_aggregate_and_bound_failures():
    diagnostics = HealthDiagnostics()
    diagnostics.register("store", lambda: HealthCheckResult("store", HealthStatus.HEALTHY, "ok"))

    async def degraded():
        return HealthCheckResult("provider", HealthStatus.DEGRADED, "fallback")

    diagnostics.register("provider", degraded)
    diagnostics.register("broken", lambda: 1 / 0)
    report = await diagnostics.run(timeout_seconds=0.1)
    assert report.status == HealthStatus.UNHEALTHY
    assert [check.name for check in report.checks] == ["broken", "provider", "store"]
    assert "ZeroDivisionError" in report.checks[0].summary


def test_worktree_planning_and_exclusive_lease(tmp_path: Path):
    repository = tmp_path / "repo"
    state = tmp_path / "state"
    repository.mkdir(exist_ok=True)
    planner = WorktreePlanner(repository, state)
    plan = planner.plan("Fix parser race")
    assert plan.branch.startswith("casper/fix-parser-race-")
    assert plan.path.parent.name == ".casper-worktrees"
    lease = planner.acquire(plan, "agent-1", ttl_seconds=60)
    with pytest.raises(RuntimeError, match="already leased"):
        planner.acquire(plan, "agent-2", ttl_seconds=60)
    assert planner.release(lease) is True
    assert planner.release(lease) is False
