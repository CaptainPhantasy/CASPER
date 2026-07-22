#!/usr/bin/env python3
"""One dependency-free end-to-end proof for CASPER's fifty harness engines."""

from __future__ import annotations

import asyncio
import hashlib
import io
import json
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any

from rich.console import Console

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import core.cli  # noqa: E402 - standalone runner bootstraps the repository root
from core.harness import (  # noqa: E402 - see repository-root bootstrap above
    HARNESS_COMMANDS, AgentProfile, AgentProfileRegistry, ArtifactRegistry, BackgroundJobSupervisor,
    BudgetLimits, BudgetUsage, CancellationToken, CircuitBreaker, CommandPalette,
    CommandRisk, CommandRiskAnalyzer, ConfigLayer, ContentCache, DependencyGraph,
    DiagnosticParser, DiffPreview, EvalCase, ExtensionRegistry, ExtensionSpec,
    FileChangeDetector,
    HarnessEvaluator,
    HarnessRuntime,
    HealthCheckResult, HealthDiagnostics, HealthStatus, HookContext, Intent,
    JSONSchemaValidator, LayeredConfiguration, LifecycleEvent, LifecycleHooks,
    MCPServerConfig, MCPServerRegistry, MCPTransport, ModelProfile, ModelRouter,
    ModelTurn,
    NaturalLanguageIntentRouter, OnboardingDoctor, PatchConflictDetector,
    PermissionMode,
    PlanStep, PlanTracker, PromptLibrary, PromptTemplate, RepositorySearch,
    ResourceBudgetEnforcer, RetryPolicy,
    PolicyDisposition,
    PolicyEngine,
    ProviderChain,
    RunState,
    RunStatus,
    SecretRedactor, SessionBranchManager, SessionBundle, SkillDiscovery,
    SlashCommand, SlashCommandRegistry, SymbolIndex, TamperEvidentAuditChain,
    TargetedTestSelector, TaskDAGScheduler, TaskNode, TaskStatus, TelemetryCollector,
    ToolCall,
    WorkspaceTrustLevel, WorkspaceTrustManager, WorktreePlanner,
)
from core.harness.impact import ChangeImpactAnalyzer  # noqa: E402
from core.terminal import modern_cli  # noqa: E402 - see repository-root bootstrap above

class SequenceProvider:
    def __init__(self, turns: list[ModelTurn]) -> None:
        self.turns = list(turns)

    async def complete(self, messages, tools) -> ModelTurn:
        if not self.turns:
            raise RuntimeError("scripted provider exhausted")
        return self.turns.pop(0)


class FailingProvider:
    async def complete(self, messages, tools) -> ModelTurn:
        raise RuntimeError("simulated primary quota exhaustion")


def require(condition: bool, evidence: str) -> str:
    if not condition:
        raise AssertionError(evidence)
    return evidence


async def run() -> int:
    results: list[dict[str, Any]] = []

    async def check(number: int, name: str, operation) -> None:
        try:
            evidence = await operation() if asyncio.iscoroutinefunction(operation) else operation()
            results.append({"number": number, "name": name, "status": "PASS", "evidence": evidence})
            print(f"[PASS] {number:02d} {name}: {evidence}")
        except Exception as exc:
            results.append({"number": number, "name": name, "status": "FAIL", "evidence": str(exc)})
            print(f"[FAIL] {number:02d} {name}: {exc}")

    with tempfile.TemporaryDirectory(prefix="casper-e2e-") as temporary:
        root = Path(temporary)
        project = root / "project"
        project.mkdir()
        (project / "AGENTS.md").write_text("Verify every workspace mutation.\n", encoding="utf-8")
        (project / "app.py").write_text("value = 1\n", encoding="utf-8")

        healthy = SequenceProvider([
            ModelTurn(tool_calls=(ToolCall("read_file", {"path": "app.py"}, id="read-e2e"),)),
            ModelTurn(tool_calls=(ToolCall(
                "patch_file",
                {"path": "app.py", "old_text": "value = 1", "new_text": "value = 2"},
                id="patch-e2e",
            ),)),
            ModelTurn(text="Done before verification."),
            ModelTurn(tool_calls=(ToolCall(
                "run_command",
                {"argv": ["python", "-m", "py_compile", "app.py"]},
                id="verify-e2e",
            ),)),
            ModelTurn(text="Changed value to two and verified the module."),
        ])
        chain = ProviderChain([FailingProvider(), healthy])
        runtime = HarnessRuntime(
            project,
            root / "state",
            chain,
            permission_mode=PermissionMode.BYPASS,
        )
        scenario: dict[str, Any] = {}

        async def canonical_runtime() -> str:
            result = await runtime.run("Inspect app.py, change value to two, and verify it.")
            scenario["result"] = result
            event_types = [event.type for event in runtime.events]
            return require(
                result.status == RunStatus.COMPLETE
                and (project / "app.py").read_text() == "value = 2\n"
                and "verification.required" in event_types
                and event_types[-1] == "run.completed",
                f"run={result.run_id} status={result.status.value} steps={result.steps} recovery=verified",
            )

        await check(1, "canonical bounded runtime", canonical_runtime)

        await check(2, "native provider failover", lambda: require(
            chain.active is healthy and len(chain.failures) == 1,
            f"active={type(chain.active).__name__} failovers={len(chain.failures)}",
        ))

        async def typed_kernel() -> str:
            names = [spec.name for spec in runtime.registry.specs()]
            failure = await runtime.registry.execute(ToolCall("missing_tool", {}))
            payload = failure.to_dict()
            required = {"status", "summary", "next_actions", "artifacts", "root_cause_hint", "safe_retry", "stop_condition"}
            return require(
                len(names) == len(set(names)) and required <= payload.keys() and payload["status"] == "error",
                f"tools={names} error_contract={sorted(required)}",
            )

        await check(3, "typed tool and observation kernel", typed_kernel)

        def policy_gate() -> str:
            registered = runtime.registry.get("patch_file")
            assert registered is not None
            call = ToolCall("patch_file", {"path": "x", "old_text": "a", "new_text": "b"}, id="approval-e2e")
            policy = PolicyEngine(PermissionMode.DEFAULT)
            before = policy.decide(registered.spec, call)
            policy.approve(call.id)
            after = policy.decide(registered.spec, call)
            reused = policy.decide(registered.spec, call)
            return require(
                before.disposition == PolicyDisposition.REQUIRE_APPROVAL
                and after.disposition == PolicyDisposition.ALLOW
                and reused.disposition == PolicyDisposition.REQUIRE_APPROVAL,
                f"before={before.disposition.value} after={after.disposition.value} reused={reused.disposition.value}",
            )

        await check(4, "central permission and approval policy", policy_gate)

        def transactional_workspace() -> str:
            changes = runtime.workspace.changes()
            assert changes
            contained = False
            try:
                runtime.workspace.resolve("../outside.txt")
            except ValueError:
                contained = True
            undone = runtime.workspace.undo(changes[-1].id)
            return require(
                contained
                and undone.status.value == "success"
                and (project / "app.py").read_text() == "value = 1\n",
                f"change={changes[-1].id} undo={undone.status.value} escape=blocked",
            )

        await check(5, "transactional workspace and durable undo", transactional_workspace)

        def repository_context() -> str:
            pack = runtime.context.pack("app value", token_budget=100)
            compacted = runtime.context.compact(
                [{"role": "user", "content": f"evidence-{index}"} for index in range(15)],
                keep_recent=3,
            )
            return require(
                pack.instructions == ["AGENTS.md"]
                and "Verify every workspace mutation" in pack.files["AGENTS.md"]
                and "app.py" in pack.files
                and pack.approx_tokens <= 100
                and compacted[0]["compacted_messages"] == 12
                and compacted[0]["evidence"][-1] == "user: evidence-11",
                f"instructions={pack.instructions} files={list(pack.files)} tokens={pack.approx_tokens} compacted=12",
            )

        await check(6, "repository context and phase compaction", repository_context)

        async def durable_store() -> str:
            result = scenario["result"]
            loaded = runtime.store.load(result.run_id)
            events = runtime.store.events(result.run_id)
            assert loaded is not None
            runtime.store.checkpoint(loaded, "e2e")
            restored = runtime.store.restore_checkpoint(result.run_id, "e2e")
            resume_provider = SequenceProvider([ModelTurn(text="resumed without replay")])
            resume_runtime = HarnessRuntime(project, root / "resume-state", resume_provider)
            interrupted = RunState("resume interrupted active run")
            interrupted.messages = [
                {"role": "user", "content": interrupted.objective},
                {"role": "tool", "name": "patch_file", "content": "already completed"},
            ]
            resume_runtime.store.save(interrupted)
            resumed = await resume_runtime.resume(interrupted.run_id)
            return require(
                restored is not None
                and restored.run_id == result.run_id
                and len(events) >= 10
                and resumed.status == RunStatus.COMPLETE
                and not resume_provider.turns,
                f"run={result.run_id} events={len(events)} checkpoint=e2e resume={resumed.status.value}",
            )

        await check(7, "durable runs events checkpoints and resume state", durable_store)

        async def headless_protocol() -> str:
            original = modern_cli.HarnessRuntime

            class HeadlessRuntime(HarnessRuntime):
                def __init__(self, project_root, **kwargs) -> None:
                    super().__init__(
                        project_root,
                        root / "headless-state",
                        SequenceProvider([ModelTurn(text="headless verified")]),
                        permission_mode=kwargs.get("permission_mode", PermissionMode.READ_ONLY),
                    )

            modern_cli.HarnessRuntime = HeadlessRuntime
            stream = io.StringIO()
            try:
                exit_code = await modern_cli.run_exec(
                    "report status",
                    project_root=project,
                    output=Console(file=stream, force_terminal=False, color_system=None, width=32),
                )
            finally:
                modern_cli.HarnessRuntime = original
            payloads = [json.loads(line) for line in stream.getvalue().splitlines()]
            return require(
                exit_code == 0
                and payloads[-1]["status"] == "complete"
                and all(item["protocol"] == "casper.events/v1" for item in payloads),
                f"exit={exit_code} events={len(payloads)} protocol=casper.events/v1",
            )

        await check(8, "versioned event bus and headless protocol", headless_protocol)

        async def evaluation_engine() -> str:
            counter = 0

            def factory() -> HarnessRuntime:
                nonlocal counter
                counter += 1
                return HarnessRuntime(
                    project,
                    root / f"eval-{counter}",
                    SequenceProvider([ModelTurn(
                        text="benchmark complete",
                        usage={"input_tokens": 10, "output_tokens": 5},
                    )]),
                )

            report = await HarnessEvaluator(factory).run([
                EvalCase("lean-e2e", "benchmark", verifier=lambda result, events: bool(events)),
            ])
            metrics = report.to_dict()
            return require(
                metrics["completion_rate"] == 1.0
                and metrics["pass_at_1"] == 1.0
                and metrics["pass_at_3"] == 1.0,
                f"completion={metrics['completion_rate']} pass@1={metrics['pass_at_1']} pass@3={metrics['pass_at_3']}",
            )

        await check(9, "evidence telemetry and ROI evaluation", evaluation_engine)

        def terminal_client() -> str:
            stream = io.StringIO()
            console = Console(file=stream, force_terminal=False, color_system=None, width=160)
            modern_cli.render_help(console, runtime)
            modern_cli.render_tools(console, runtime)
            rendered = stream.getvalue()
            launcher = subprocess.run(
                [str(ROOT / "casper"), "--help"],
                cwd=project,
                text=True,
                capture_output=True,
                check=False,
            )
            catalog = subprocess.run(
                [str(ROOT / "casper"), "--features"],
                cwd=project,
                text=True,
                capture_output=True,
                check=False,
            )
            old_console = core.cli.console
            banner = io.StringIO()
            core.cli.console = Console(file=banner, force_terminal=False, color_system=None, width=200)
            try:
                core.cli.print_modern_banner()
            finally:
                core.cli.console = old_console
            digest = hashlib.sha256(banner.getvalue().encode()).hexdigest()
            tool_names = [spec.name for spec in runtime.registry.specs()]
            return require(
                launcher.returncode == 0
                and catalog.returncode == 0
                and "50 total" in catalog.stdout
                and "Typed AI Coding Harness" in launcher.stdout
                and all(name in rendered for name in tool_names)
                and digest == "b9995c987598cff903fd32a2c3bc8d18a1569bb2a8fd14187df5cec7e91a70b8",
                f"launcher={launcher.returncode} catalog=50 tools={len(tool_names)} banner_sha256={digest}",
            )

        await check(10, "modern terminal client and preserved identity", terminal_client)

        async def lifecycle_hooks() -> str:
            order: list[str] = []
            hooks = LifecycleHooks()
            hooks.register("late", LifecycleEvent.RUN_START, lambda _: order.append("late"), priority=20)
            hooks.register("early", LifecycleEvent.RUN_START, lambda _: order.append("early"), priority=10)
            failures = await hooks.emit(HookContext(LifecycleEvent.RUN_START, "e2e"))
            return require(order == ["early", "late"] and not failures, f"order={order}")

        await check(11, "ordered lifecycle hook engine", lifecycle_hooks)

        def extension_registry() -> str:
            registry = ExtensionRegistry()
            registry.register(ExtensionSpec("casper", "reviewer", "1", capabilities=("review",)))
            item = registry.require("casper:reviewer")
            return require(item.capabilities == ("review",), f"extension={item.qualified_name}")

        await check(12, "namespaced extension registry", extension_registry)

        def skill_discovery() -> str:
            skill = root / "skills" / "reviewer"
            skill.mkdir(parents=True)
            (skill / "SKILL.md").write_text(
                "---\nname: reviewer\ndescription: Reviews code\ntags: [code, quality]\n---\n",
                encoding="utf-8",
            )
            result = SkillDiscovery((root / "skills",)).discover()
            return require(result.skills[0].name == "reviewer", f"skills={[item.name for item in result.skills]}")

        await check(13, "progressive skill discovery", skill_discovery)

        def mcp_registry() -> str:
            registry = MCPServerRegistry()
            registry.register(MCPServerConfig("local", MCPTransport.STDIO, command=("python", "server.py")))
            item = registry.set_enabled("local", False)
            return require(not item.enabled and item.transport == MCPTransport.STDIO, "local=disabled transport=stdio")

        await check(14, "validated MCP server registry", mcp_registry)

        def agent_profiles() -> str:
            registry = AgentProfileRegistry()
            profile = AgentProfile(
                "critic", "Find defects", "Inspect evidence", allowed_tools=("read_file",),
                permission_mode=PermissionMode.READ_ONLY, max_steps=4,
            )
            registry.register(profile)
            return require(registry.require("critic").max_steps == 4, "critic max_steps=4 read_only")

        await check(15, "bounded custom agent profiles", agent_profiles)

        async def dag_scheduler() -> str:
            calls: list[str] = []
            scheduler = TaskDAGScheduler((
                TaskNode("inspect", lambda _: calls.append("inspect")),
                TaskNode("verify", lambda _: calls.append("verify"), ("inspect",)),
            ), max_concurrency=2)
            task_results = await scheduler.run()
            return require(
                calls == ["inspect", "verify"]
                and all(item.status == TaskStatus.SUCCEEDED for item in task_results.values()),
                f"order={calls}",
            )

        await check(16, "bounded dependency-aware agent DAG", dag_scheduler)

        def cancellation() -> str:
            parent = CancellationToken()
            child = parent.child()
            first = parent.cancel("operator")
            return require(first and child.cancelled and child.reason == "operator", "propagated=operator")

        await check(17, "cooperative cancellation propagation", cancellation)

        async def background_jobs() -> str:
            supervisor = BackgroundJobSupervisor(max_active=1)
            record = supervisor.submit("e2e", lambda _: 42)
            completed = await supervisor.wait(record.job_id)
            return require(completed.result == 42, f"job={record.job_id} status={completed.status.value}")

        await check(18, "background job supervisor", background_jobs)

        async def health_diagnostics() -> str:
            diagnostics = HealthDiagnostics()
            diagnostics.register("store", lambda: HealthCheckResult("store", HealthStatus.HEALTHY, "ok"))
            report = await diagnostics.run(timeout_seconds=0.1)
            return require(report.healthy, f"status={report.status.value} checks={len(report.checks)}")

        await check(19, "bounded health diagnostics", health_diagnostics)

        def worktree_planning() -> str:
            repository = root / "worktree-repo"
            repository.mkdir()
            planner = WorktreePlanner(repository, root / "worktree-state")
            plan = planner.plan("Fix parser race")
            lease = planner.acquire(plan, "e2e", ttl_seconds=60)
            released = planner.release(lease)
            return require(released and plan.branch.startswith("casper/"), f"branch={plan.branch} lease=released")

        await check(20, "isolated worktree planning and leases", worktree_planning)

        intelligence = root / "intelligence"
        (intelligence / "pkg").mkdir(parents=True)
        (intelligence / "tests").mkdir()
        (intelligence / "pkg" / "core.py").write_text("class Service:\n    def run(self): return 1\n")
        (intelligence / "pkg" / "api.py").write_text("from pkg import core\n")
        (intelligence / "tests" / "test_core.py").write_text("from pkg.core import Service\n")

        def symbol_index() -> str:
            index = SymbolIndex(intelligence)
            index.refresh([intelligence / "pkg" / "core.py"])
            matches = index.find("run", exact=True)
            return require(matches[0].qualified_name == "Service.run", f"symbol={matches[0].qualified_name}")

        await check(21, "multi-language symbol index", symbol_index)

        graph = DependencyGraph(intelligence)
        graph.build()
        await check(22, "import and reverse-dependency graph", lambda: require(
            graph.dependencies("pkg/api.py") == ("pkg/core.py",),
            f"dependencies={graph.dependencies('pkg/api.py')}",
        ))

        await check(23, "ranked repository search", lambda: require(
            RepositorySearch(intelligence).search("class Service")[0].path == "pkg/core.py",
            "top=pkg/core.py",
        ))

        await check(24, "compiler diagnostic normalization", lambda: require(
            [item.source for item in DiagnosticParser.parse("a.py:1:2: E501 long\na.ts(2,3): error TS1: bad")]
            == ["ruff", "typescript"],
            "sources=ruff,typescript",
        ))

        await check(25, "targeted test selection", lambda: require(
            TargetedTestSelector(intelligence).select(["pkg/core.py"]).tests == ("tests/test_core.py",),
            "tests=tests/test_core.py",
        ))

        await check(26, "change impact analysis", lambda: require(
            "tests/test_core.py" in ChangeImpactAnalyzer(intelligence, graph=graph).analyze(["pkg/core.py"]).tests,
            "affected_test=tests/test_core.py",
        ))

        def plan_tracker() -> str:
            tracker = PlanTracker((PlanStep("build", "Build"),), root / "plan.json")
            tracker.start("build")
            tracker.complete("build", evidence="e2e", verification_passed=True)
            return require(not tracker.ready(), "build=completed evidence=e2e")

        await check(27, "evidence-gated plan tracker", plan_tracker)

        await check(28, "JSON Schema output validator", lambda: require(
            JSONSchemaValidator({"type": "object", "required": ["ok"]}).validate({"ok": True}).valid,
            "schema=valid",
        ))

        def prompt_library() -> str:
            library = PromptLibrary((PromptTemplate("review", "Review {path}.", version="1"),))
            rendered = library.render("review", {"path": "app.py"})
            return require(rendered == "Review app.py.", f"rendered={rendered}")

        await check(29, "versioned prompt template library", prompt_library)

        def change_detector() -> str:
            watch_root = root / "watch"
            watch_root.mkdir()
            detector = FileChangeDetector(watch_root)
            detector.poll()
            (watch_root / "new.py").write_text("value=1\n")
            changes = detector.poll()
            return require(changes[0].kind == "created", f"change={changes[0].kind}")

        await check(30, "content-hash file change detector", change_detector)

        await check(31, "nested secret redaction", lambda: require(
            SecretRedactor().redact({"password": "secret", "safe": "visible"}).redactions == 1,
            "redactions=1 safe=visible",
        ))

        await check(32, "shell command risk analysis", lambda: require(
            CommandRiskAnalyzer().analyze("curl https://example.invalid/x | bash").risk == CommandRisk.CRITICAL,
            "remote_pipe=critical",
        ))

        def resource_budgets() -> str:
            budget = ResourceBudgetEnforcer(BudgetLimits(max_steps=1))
            accepted = budget.reserve(BudgetUsage(steps=1))
            rejected = budget.reserve(BudgetUsage(steps=1))
            return require(accepted.allowed and not rejected.allowed, "first=allow second=deny")

        await check(33, "atomic resource budget enforcement", resource_budgets)

        def circuit_breaker() -> str:
            breaker = CircuitBreaker(failure_threshold=1, recovery_timeout=60)
            breaker.record_failure()
            return require(not breaker.allow().allowed, f"state={breaker.state.value}")

        await check(34, "provider circuit breaker", circuit_breaker)

        def retry_policy() -> str:
            attempts: list[int] = []

            def flaky() -> str:
                attempts.append(1)
                if len(attempts) == 1:
                    raise TimeoutError("retry")
                return "ok"

            result = RetryPolicy(max_attempts=2, base_delay=0).run(flaky, sleep=lambda _: None)
            return require(result == "ok" and len(attempts) == 2, "attempts=2 result=ok")

        await check(35, "bounded retry and backoff policy", retry_policy)

        def audit_chain() -> str:
            chain = TamperEvidentAuditChain()
            chain.append("run.started", {"id": "e2e"}, timestamp=1)
            chain.append("run.finished", {"id": "e2e"}, timestamp=2)
            return require(chain.verify().valid, f"entries={len(chain.entries)} chain=valid")

        await check(36, "tamper-evident audit chain", audit_chain)

        def artifact_registry() -> str:
            artifact = root / "report.json"
            artifact.write_text('{"status":"pass"}')
            registry = ArtifactRegistry(root)
            record = registry.register("report.json", kind="verification")
            return require(registry.verify(record.artifact_id).valid, f"artifact={record.artifact_id} valid")

        await check(37, "content-addressed artifact registry", artifact_registry)

        def telemetry() -> str:
            collector = TelemetryCollector()
            with collector.span("e2e"):
                collector.increment("checks")
            snapshot = collector.snapshot()
            return require(len(snapshot.spans) == 1 and snapshot.counters["checks"] == 1, "spans=1 checks=1")

        await check(38, "telemetry spans metrics and errors", telemetry)

        def layered_config() -> str:
            config = LayeredConfiguration((
                ConfigLayer("defaults", {"model": {"name": "small"}}),
                ConfigLayer("cli", {"model": {"name": "strong"}}),
            ))
            return require(config.get("model.name") == "strong", "model.name=strong source=cli")

        await check(39, "layered configuration provenance", layered_config)

        def workspace_trust() -> str:
            manager = WorkspaceTrustManager(root / "trust.json")
            decision = manager.set_trust(project, WorkspaceTrustLevel.TRUSTED)
            return require(decision.profile.allow_network, f"trust={decision.profile.level.value}")

        await check(40, "persistent workspace trust profiles", workspace_trust)

        async def slash_commands() -> str:
            registry = SlashCommandRegistry()
            registry.register(SlashCommand("goal", "Set goal", lambda value: value, ("g",)))
            projected = await runtime.handle_control("/commands review")
            names = {item.name for item in HARNESS_COMMANDS}
            aligned = {"review", "code-review", "security-review", "plan", "verify", "tasks"} <= names
            return require(
                registry.execute("/g ship") == "ship"
                and projected is not None and projected.status.value == "success"
                and aligned,
                f"commands={len(names)} review_projection={projected.status.value if projected else 'missing'}",
            )

        await check(41, "discoverable slash command registry", slash_commands)

        intents = NaturalLanguageIntentRouter((
            Intent("test", ("test", "verify")), Intent("edit", ("change", "file")),
        ))
        await check(42, "natural-language intent routing", lambda: require(
            intents.route("please change this file")[0] == "edit", "intent=edit",
        ))

        await check(43, "fuzzy command palette", lambda: require(
            CommandPalette.search("rn tst", ("run tests", "resume"))[0] == "run tests",
            "top=run tests",
        ))

        def session_branches() -> str:
            branches = SessionBranchManager(({"role": "user", "content": "hello"},))
            fork = branches.fork("main", "experiment")
            fork.messages.append({"role": "assistant", "content": "new"})
            return require(len(branches.branches["main"].messages) == 1, "fork=isolated")

        await check(44, "isolated session branching", session_branches)

        await check(45, "unified diff preview and statistics", lambda: require(
            (preview := DiffPreview.render("x=1\n", "x=2\n", path="x.py")).additions == 1
            and preview.deletions == 1,
            "additions=1 deletions=1",
        ))

        def conflict_detection() -> str:
            target = root / "conflict.py"
            target.write_text("before")
            detector = PatchConflictDetector()
            fingerprint = detector.fingerprint(target.read_bytes())
            target.write_text("after")
            return require(not detector.unchanged(target, fingerprint), "concurrent_change=detected")

        await check(46, "optimistic patch conflict detection", conflict_detection)

        await check(47, "capability and cost-aware model routing", lambda: require(
            ModelRouter((
                ModelProfile("cheap", frozenset({"code"}), 8_000, 1),
                ModelProfile("strong", frozenset({"code", "vision"}), 100_000, 5),
            )).select({"vision"}).name == "strong",
            "selected=strong capability=vision",
        ))

        def content_cache() -> str:
            cache = ContentCache(capacity=1)
            key = cache.key("context", "stable")
            cache.put(key, 42)
            return require(cache.get(key) == 42, f"key={key[:20]} hit=true")

        await check(48, "bounded content-addressed cache", content_cache)

        def session_bundle() -> str:
            bundle = SessionBundle(1, "ship", ({"role": "user", "content": "go"},), {"model": "x"})
            restored = SessionBundle.loads(bundle.dumps())
            return require(restored == bundle, "version=1 round_trip=true")

        await check(49, "portable session export and import", session_bundle)

        def onboarding_doctor() -> str:
            checks = OnboardingDoctor().inspect(project, executables=("git",))
            return require(all(item.passed for item in checks), f"checks={len(checks)} all_passed=true")

        await check(50, "actionable onboarding doctor", onboarding_doctor)

    passed = sum(item["status"] == "PASS" for item in results)
    summary = {
        "status": "PASS" if passed == 50 else "FAIL",
        "passed": passed,
        "total": 50,
        "features": results,
    }
    print("E2E_SUMMARY=" + json.dumps(summary, sort_keys=True))
    return 0 if passed == 50 else 1


if __name__ == "__main__":
    raise SystemExit(asyncio.run(run()))
