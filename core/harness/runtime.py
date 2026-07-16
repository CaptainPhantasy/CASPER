"""Canonical bounded tool-calling runtime for the CASPER coding harness."""

from __future__ import annotations

import hashlib
import json
import os
import shlex
import subprocess
from pathlib import Path
from typing import Any, Iterable, Mapping, Optional

from core.services.goal_engine import GoalEngine, GoalError

from .agents import AgentProfileRegistry
from .commands import command_index, command_palette
from .context import RepositoryContext
from .hooks import LifecycleHooks
from .interaction import OnboardingDoctor
from .jobs import BackgroundJobSupervisor
from .mcp import MCPServerRegistry
from .models import (
    ModelTurn, ObservationStatus, RunEvent, RunResult, RunState, RunStatus,
    ToolCall, ToolObservation, ToolSpec,
)
from .policy import PermissionMode, PolicyDisposition, PolicyEngine
from .providers import HarnessProvider, ProviderChain, TextCompletionProvider, create_default_provider
from .review import CodeReviewSentinel, ReviewValidationError
from .registry import ToolRegistry
from .safety import SecretRedactor
from .skills import SkillDiscovery
from .store import RunStore
from .workspace import WorkspaceEngine


_SYSTEM = """You are CASPER, a coding harness operating on one local repository.
Use the supplied typed tools to inspect evidence before making claims. Prefer exact,
small patches. After every mutation run the narrowest useful verification. Never
invent tool results. If a tool returns an error, follow its safe retry and stop
condition. Finish with a concise account of the verified outcome."""


class HarnessRuntime:
    """One provider loop, registry, policy gate, store, and event stream."""

    def __init__(
        self,
        project_root: Path | str,
        state_root: Optional[Path | str] = None,
        provider: Optional[HarnessProvider] = None,
        *,
        permission_mode: PermissionMode | str = PermissionMode.DEFAULT,
        max_steps: int = 24,
    ) -> None:
        self.project_root = Path(project_root).expanduser().resolve()
        if state_root is None:
            state_home = Path(os.environ.get("XDG_STATE_HOME", Path.home() / ".local" / "state"))
            project_key = hashlib.sha256(str(self.project_root).encode("utf-8")).hexdigest()[:16]
            state_root = state_home / "casper" / "harness" / project_key
        self.state_root = Path(state_root).expanduser().resolve()
        self.store = RunStore(self.state_root)
        self.workspace = WorkspaceEngine(self.project_root, self.state_root / "workspace")
        self.context = RepositoryContext(self.project_root)
        self.policy = PolicyEngine(PermissionMode(permission_mode))
        self.registry = ToolRegistry()
        self.workspace.register_tools(self.registry)
        self._register_context_tools()
        if provider is None:
            provider = create_default_provider()
        self.provider = provider
        self.reviewer = CodeReviewSentinel(self.project_root, provider)
        self.redactor = SecretRedactor()
        self.goal = GoalEngine(storage_path=self.state_root / "goal.json", project_root=self.project_root)
        self.hooks = LifecycleHooks()
        self.mcp = MCPServerRegistry()
        self.agents = AgentProfileRegistry()
        self.jobs = BackgroundJobSupervisor()
        self.commands = command_index()
        self.degraded_mode = isinstance(provider, TextCompletionProvider) or (
            isinstance(provider, ProviderChain)
            and all(isinstance(item, TextCompletionProvider) for item in provider.providers)
        )
        self.max_steps = max(1, max_steps)
        self.events: list[RunEvent] = []
        self._event_sequence = 0

    def _register_context_tools(self) -> None:
        self.registry.register(ToolSpec(
            "search_repository",
            "Find relevant tracked files and top-level symbols for a coding query.",
            {"type": "object", "properties": {
                "query": {"type": "string"}, "limit": {"type": "integer"},
            }, "required": ["query"], "additionalProperties": False},
        ), self._search_repository)

    def _search_repository(self, args: Mapping[str, Any]) -> ToolObservation:
        matches = self.context.select(str(args["query"]), max(1, min(int(args.get("limit", 8)), 25)))
        return ToolObservation.success(
            f"Found {len(matches)} relevant repository file(s).",
            data={"matches": [
                {"path": item.path, "size": item.size, "symbols": list(item.symbols)} for item in matches
            ]}, artifacts=[str(self.project_root / item.path) for item in matches],
            next_actions=["Read only the files needed for the current decision."],
        )

    def _emit(self, run_id: str, event_type: str, payload: dict[str, Any]) -> RunEvent:
        self._event_sequence += 1
        event = RunEvent(run_id, self._event_sequence, event_type, payload)
        self.events.append(event)
        self.store.append_event(event)
        return event

    @staticmethod
    def _result(state: RunState) -> RunResult:
        return RunResult(
            state.run_id, state.status, state.final_text, tuple(state.artifacts),
            tuple(state.pending_calls), dict(state.usage), state.step, state.error,
        )

    async def run(self, prompt: str) -> RunResult:
        prompt = prompt.strip()
        if not prompt:
            raise ValueError("a non-empty coding prompt is required")
        state = RunState(objective=prompt)
        pack = self.context.pack(prompt, token_budget=4_000)
        state.messages = [
            {"role": "system", "content": _SYSTEM},
            {"role": "system", "content": pack.render()},
            {"role": "user", "content": prompt},
        ]
        self.events = []
        self._event_sequence = 0
        self.store.save(state)
        self._emit(state.run_id, "run.started", {
            "objective": prompt, "project_root": str(self.project_root),
            "context_files": list(pack.files), "context_tokens": pack.approx_tokens,
        })
        self._emit(state.run_id, "runtime.mode", {
            "mode": "chat_only_degraded" if self.degraded_mode else "native_tool_calling",
            "provider": type(self.provider).__name__,
            "tool_execution_available": not self.degraded_mode,
        })
        return await self._advance(state)

    async def resume(self, run_id: str, approved_call_ids: Iterable[str] = ()) -> RunResult:
        state = self.store.load(run_id)
        if not state:
            raise ValueError(f"unknown run: {run_id}")
        if state.status not in {RunStatus.ACTIVE, RunStatus.AWAITING_APPROVAL}:
            raise ValueError(f"run is {state.status.value} and cannot be resumed")
        self.events = self.store.events(run_id)
        self._event_sequence = self.events[-1].sequence if self.events else 0
        if state.status == RunStatus.ACTIVE:
            if tuple(approved_call_ids):
                raise ValueError("an active run has no pending calls to approve")
            self._emit(run_id, "run.resumed", {"from_status": RunStatus.ACTIVE.value})
            return await self._advance(state)
        for call_id in approved_call_ids:
            self.policy.approve(call_id)
        state.status = RunStatus.ACTIVE
        pending = list(state.pending_calls)
        state.pending_calls = []
        self.store.save(state)
        if pending:
            paused = await self._execute_calls(state, pending)
            if paused:
                return self._result(state)
        return await self._advance(state)

    async def _advance(self, state: RunState) -> RunResult:
        while state.step < self.max_steps:
            state.step += 1
            self._emit(state.run_id, "model.started", {"step": state.step})
            try:
                turn = await self.provider.complete(state.messages, self.registry.provider_schemas())
            except Exception as exc:
                state.status = RunStatus.FAILED
                state.error = f"Provider failed: {exc}"
                self._emit(state.run_id, "run.failed", {"error": state.error, "error_type": type(exc).__name__})
                self.store.save(state)
                return self._result(state)
            self._record_turn(state, turn)
            if turn.tool_calls:
                paused = await self._execute_calls(state, list(turn.tool_calls))
                if paused:
                    return self._result(state)
                continue
            if not turn.text.strip():
                state.status = RunStatus.FAILED
                state.error = "Provider returned neither text nor tool calls."
                self._emit(state.run_id, "run.failed", {"error": state.error})
            elif self._mutation_needs_verification():
                reason = (
                    "A workspace mutation has no successful verification after it; "
                    "CASPER will not report completion."
                )
                self._emit(state.run_id, "verification.required", {
                    "reason": reason,
                    "safe_retry": "Run the narrowest relevant check through run_command, then continue.",
                    "stop_condition": "Stop if verification cannot run without new authority or external state.",
                })
                attempts = sum(event.type == "verification.required" for event in self.events)
                if attempts < 2:
                    state.messages.append({
                        "role": "system",
                        "content": reason + " Call run_command with the narrowest relevant check now.",
                    })
                    self.store.save(state)
                    continue
                state.status = RunStatus.BLOCKED
                state.error = reason
                self._emit(state.run_id, "run.blocked", {"reason": reason})
            else:
                state.status = RunStatus.COMPLETE
                state.final_text = turn.text
                self._emit(state.run_id, "run.completed", {
                    "text": turn.text, "artifacts": state.artifacts, "usage": state.usage,
                })
            self.store.save(state)
            return self._result(state)
        state.status = RunStatus.BLOCKED
        state.error = f"Stopped after the bounded maximum of {self.max_steps} model steps."
        self._emit(state.run_id, "run.blocked", {"reason": state.error})
        self.store.save(state)
        return self._result(state)

    def _mutation_needs_verification(self) -> bool:
        """Return true when the last successful patch is newer than verification."""
        last_mutation = 0
        last_verification = 0
        for event in self.events:
            if event.type != "tool.completed":
                continue
            call = event.payload.get("call", {})
            observation = event.payload.get("observation", {})
            if observation.get("status") != ObservationStatus.SUCCESS.value:
                continue
            if call.get("name") == "patch_file":
                last_mutation = event.sequence
            elif call.get("name") == "run_command":
                last_verification = event.sequence
        return last_mutation > last_verification

    def _record_turn(self, state: RunState, turn: ModelTurn) -> None:
        state.messages.append({
            "role": "assistant", "content": turn.text,
            "tool_calls": [call.to_dict() for call in turn.tool_calls],
        })
        for key, value in turn.usage.items():
            state.usage[key] = int(state.usage.get(key, 0)) + int(value)
        self._emit(state.run_id, "model.completed", {
            "step": state.step, "text": turn.text,
            "tool_calls": [call.to_dict() for call in turn.tool_calls],
            "stop_reason": turn.stop_reason, "usage": turn.usage, "model": turn.model,
        })

    async def _execute_calls(self, state: RunState, calls: list[ToolCall]) -> bool:
        for position, call in enumerate(calls):
            registered = self.registry.get(call.name)
            if not registered:
                observation = await self.registry.execute(call)
            else:
                decision = self.policy.decide(registered.spec, call)
                self._emit(state.run_id, "policy.decided", {
                    "call": call.to_dict(), "disposition": decision.disposition.value,
                    "reason": decision.reason, "consequence": decision.consequence,
                    "recommendation": decision.recommendation,
                })
                if decision.disposition == PolicyDisposition.REQUIRE_APPROVAL:
                    state.status = RunStatus.AWAITING_APPROVAL
                    state.pending_calls = calls[position:]
                    self._emit(state.run_id, "approval.required", {
                        "call": call.to_dict(), "reason": decision.reason,
                        "consequence": decision.consequence, "recommendation": decision.recommendation,
                    })
                    self.store.save(state)
                    return True
                if decision.disposition == PolicyDisposition.DENY:
                    observation = ToolObservation.error(
                        f"Policy denied {call.name}.", decision.reason,
                        decision.recommendation, "Stop unless the operator intentionally changes permission mode.",
                    )
                else:
                    observation = await self.registry.execute(call)
            self._record_observation(state, call, observation)
        self.store.save(state)
        return False

    def _record_observation(self, state: RunState, call: ToolCall, observation: ToolObservation) -> None:
        sanitized = self.redactor.redact(observation.to_dict())
        payload = sanitized.value
        state.messages.append({
            "role": "tool", "tool_call_id": call.id, "name": call.name,
            "content": json.dumps(payload, indent=2, sort_keys=True, default=str),
        })
        for artifact in observation.artifacts:
            if artifact not in state.artifacts:
                state.artifacts.append(artifact)
        # Persist the observation before another model turn can be requested.
        # A resumed ACTIVE run will therefore not repeat the completed side effect.
        self.store.save(state)
        self._emit(state.run_id, "tool.completed", {
            "call": call.to_dict(), "observation": payload,
            "redactions": sanitized.redactions,
        })

    async def handle_control(self, command_line: str) -> Optional[ToolObservation]:
        """Deterministic slash controls for host TUI integration."""
        try:
            parts = shlex.split(command_line.strip())
        except ValueError as exc:
            return ToolObservation.error(
                f"Could not parse command: {exc}", "The quoting or escaping is incomplete.",
                "Close each quote and retry the same command.",
                "Stop if the intended argument cannot be represented safely.",
            )
        if not parts or not parts[0].startswith("/"):
            return None
        name, args = parts[0][1:].casefold(), parts[1:]
        spec = self.commands.get(name)
        if spec is None:
            suggestions = [item.usage for item in command_palette(name)[:8]]
            return ToolObservation.error(
                f"Unknown command: /{name}", "The command is not in the canonical harness registry.",
                "Run /commands to inspect supported commands.",
                "Stop before assuming a command exists because another harness provides it.",
                data={"suggestions": suggestions},
            )
        command = spec.name

        # These commands are executed by the terminal renderer or transformed into
        # bounded agent prompts after deterministic parsing.
        if command in {"quit", "features", "tools", "plan", "task", "verify"}:
            return None
        if command in {"help", "commands"}:
            query = " ".join(args)
            command_matches = command_palette(query)
            return ToolObservation.success(
                f"Found {len(command_matches)} matching command(s).",
                data={"commands": [vars(item) for item in command_matches]},
            )
        if command == "runs":
            return ToolObservation.success("Collected durable harness runs.", data={"runs": self.store.list_runs()})
        if command == "resume":
            if len(args) > 1:
                return self._control_usage(spec.usage)
            if not args:
                return ToolObservation.success(
                    "Collected durable harness runs.", data={"runs": self.store.list_runs()}
                )
            state = self.store.load(args[0])
            if state is None:
                return ToolObservation.error(
                    f"Unknown run: {args[0]}", "No durable run has that identifier.",
                    "Run /runs and retry with an exact run ID.", "Stop if the run store was removed.",
                )
            if state.status == RunStatus.ACTIVE:
                result = await self.resume(state.run_id)
                return ToolObservation.success(
                    f"Resumed run {state.run_id}; status is {result.status.value}.",
                    data={"run": result.to_dict()}, artifacts=list(result.artifacts),
                )
            return ToolObservation.success(
                f"Run {state.run_id} is {state.status.value}.", data={"run": state.to_dict()}
            )
        if command == "permissions":
            if len(args) == 2 and args[0] == "set":
                try:
                    self.policy.set_mode(args[1].replace("-", "_"))
                except ValueError:
                    return self._control_usage(spec.usage)
            elif args:
                return self._control_usage(spec.usage)
            return ToolObservation.success("Permission mode collected.", data={"mode": self.policy.mode.value})
        if command == "rewind":
            if not args or args == ["list"]:
                return ToolObservation.success(
                    "Collected transactional workspace changes.",
                    data={"changes": [vars(item) for item in self.workspace.changes()]},
                )
            if len(args) == 2 and args[0] == "undo":
                if self.policy.mode not in {PermissionMode.ACCEPT_EDITS, PermissionMode.BYPASS}:
                    return ToolObservation.warning(
                        f"Rewind did not mutate the project in {self.policy.mode.value} mode.",
                        data={"permission_mode": self.policy.mode.value},
                        next_actions=["Run /permissions set accept_edits, inspect the change ID, then retry."],
                    )
                return self.workspace.undo(args[1])
            return self._control_usage(spec.usage)
        if command == "status":
            if args:
                return self._control_usage(spec.usage)
            status = self._git(["status", "--short"])
            branch = self._git(["branch", "--show-current"])
            return ToolObservation.success(
                "Collected live harness and repository status.", data={
                    "project_root": str(self.project_root),
                    "branch": branch.stdout.strip() or "detached",
                    "changes": status.stdout.splitlines() if status.returncode == 0 else [],
                    "provider": type(self.provider).__name__,
                    "execution_mode": "chat_only_degraded" if self.degraded_mode else "native_tool_calling",
                    "permission_mode": self.policy.mode.value,
                    "tools": len(self.registry.specs()),
                },
            )
        if command == "doctor":
            if args:
                return self._control_usage(spec.usage)
            checks = OnboardingDoctor().inspect(self.project_root, executables=("git", "python3"))
            failed = [item for item in checks if not item.passed]
            factory = ToolObservation.warning if failed else ToolObservation.success
            return factory(
                "Harness diagnostics found blockers." if failed else "Harness diagnostics passed.",
                data={"checks": [vars(item) for item in checks]},
                next_actions=["Correct failed checks and rerun /doctor."] if failed else [],
            )
        if command == "context":
            query = " ".join(args) or "current coding task"
            pack = self.context.pack(query, token_budget=4_000)
            return ToolObservation.success(
                "Collected bounded repository context.", data={
                    "query": query, "instructions": pack.instructions,
                    "files": list(pack.files), "approx_tokens": pack.approx_tokens,
                    "truncated": pack.truncated,
                }, artifacts=[str(self.project_root / path) for path in pack.files],
            )
        if command == "diff":
            return self._control_diff(args, spec.usage)
        if command in {"review", "code-review", "security-review"}:
            return await self._control_review(command, args, spec.usage)
        if command == "goal":
            return self._control_goal(args)
        if command == "model":
            if args:
                return self._control_usage(spec.usage)
            active = self.provider.active if isinstance(self.provider, ProviderChain) else self.provider
            return ToolObservation.success(
                "Collected active model provider.", data={
                    "provider": type(active).__name__,
                    "model": getattr(active, "model", None) or "resolved on first request",
                    "degraded": self.degraded_mode,
                },
            )
        if command == "skills":
            roots = [self.project_root / ".casper" / "skills", self.project_root / ".claude" / "skills"]
            shared = os.environ.get("CASPER_SKILLS_HOME")
            if shared:
                roots.append(Path(shared))
            discovered = SkillDiscovery(tuple(roots)).discover()
            query = " ".join(args).casefold()
            skills = [item for item in discovered.skills if not query or query in (
                item.name + " " + item.description + " " + " ".join(item.tags)
            ).casefold()]
            return ToolObservation.success(
                f"Found {len(skills)} matching skill(s).", data={
                    "skills": [{**vars(item), "path": str(item.path)} for item in skills],
                    "warnings": list(discovered.warnings),
                }, artifacts=[str(item.path) for item in skills],
            )
        if command == "mcp":
            if args:
                return self._control_usage(spec.usage)
            return ToolObservation.success(
                "Collected MCP server definitions.",
                data={"servers": [item.redacted() for item in self.mcp.list()]},
            )
        if command == "agents":
            if args:
                return self._control_usage(spec.usage)
            return ToolObservation.success(
                "Collected agent profiles.", data={
                    "agents": [{**vars(item), "permission_mode": item.permission_mode.value} for item in self.agents.list()]
                },
            )
        if command == "tasks":
            if args:
                return self._control_usage(spec.usage)
            return ToolObservation.success(
                "Collected supervised background jobs.", data={"tasks": [vars(item) for item in self.jobs.list()]},
            )
        if command == "hooks":
            if args:
                return self._control_usage(spec.usage)
            return ToolObservation.success(
                "Collected lifecycle hook registrations.", data={
                    "hooks": [{
                        "name": item.name, "event": item.event.value, "priority": item.priority,
                    } for item in self.hooks.registrations()]
                },
            )
        if command == "usage":
            if args:
                return self._control_usage(spec.usage)
            runs = self.store.list_runs(limit=500)
            totals: dict[str, int] = {}
            for item in runs:
                state = self.store.load(item["run_id"])
                if state is None:
                    continue
                for key, value in state.usage.items():
                    totals[key] = totals.get(key, 0) + int(value)
            return ToolObservation.success(
                "Collected measured local run usage; this is not provider billing data.",
                data={"runs": len(runs), "usage": totals},
            )
        return ToolObservation.error(
            f"Command is registered but has no runtime handler: /{command}",
            "The command catalog and dispatcher are out of sync.",
            "Run /doctor and report this command-dispatch defect.",
            "Stop instead of treating an unexecuted command as successful.",
        )

    @staticmethod
    def _control_usage(usage: str) -> ToolObservation:
        return ToolObservation.error(
            f"Usage: {usage}", "The command arguments are invalid.",
            f"Retry using {usage}.", "Stop if the requested operation is outside this command's scope.",
        )

    def _git(self, args: list[str]) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            ["git", *args], cwd=self.project_root, text=True, capture_output=True,
            check=False, timeout=20,
        )

    def _control_diff(self, args: list[str], usage: str) -> ToolObservation:
        git_args = ["diff"]
        remaining = list(args)
        path = ""
        while remaining:
            value = remaining.pop(0)
            if value in {"--stat", "--cached"}:
                git_args.append(value)
            elif value == "--" and remaining:
                path = remaining.pop(0)
                if remaining:
                    return self._control_usage(usage)
            else:
                return self._control_usage(usage)
        if path:
            try:
                resolved = self.workspace.resolve(path)
            except ValueError as exc:
                return ToolObservation.error(
                    "Diff path escapes the project.", str(exc), "Use a repo-relative path.",
                    "Stop if external filesystem access is required.",
                )
            git_args.extend(["--", resolved.relative_to(self.project_root).as_posix()])
        result = self._git(git_args)
        if result.returncode != 0:
            return ToolObservation.error(
                "Git diff failed.", result.stderr.strip() or "Git rejected the arguments.",
                "Run /status and retry with a project-contained path.",
                "Stop if this is not the intended Git repository.",
            )
        output = result.stdout[-32_000:]
        return ToolObservation.success(
            "Git diff collected." if output else "Git diff is empty.",
            data={"output": output, "truncated": len(result.stdout) > 32_000},
        )

    async def _control_review(self, command: str, args: list[str], usage: str) -> ToolObservation:
        effort = "medium"
        target = ""
        remaining = list(args)
        if command == "code-review" and remaining and remaining[0] in {"low", "medium", "high"}:
            effort = remaining.pop(0)
        elif command == "review":
            effort = "low"
        if len(remaining) > 1:
            return self._control_usage(usage)
        if remaining:
            target = remaining[0]
        mode = {"review": "fast", "code-review": "full", "security-review": "security"}[command]
        try:
            execution = await self.reviewer.review(target=target, effort=effort, mode=mode)
        except (ValueError, RuntimeError, ReviewValidationError) as exc:
            return ToolObservation.error(
                f"{command} failed: {exc}", f"The review engine rejected its input or model output ({type(exc).__name__}).",
                f"Correct the target or provider response and retry {usage}.",
                "Stop after the same provider or validation failure repeats.",
            )
        return ToolObservation.success(
            execution.report["summary"]["headline"], data={
                "report": execution.report, "attempts": execution.attempts,
                "truncated": execution.truncated, "redactions": execution.redactions,
            }, artifacts=[str(self.project_root / path) for path in execution.files],
        )

    def _control_goal(self, args: list[str]) -> ToolObservation:
        try:
            if not args or args == ["status"]:
                goal = self.goal.load()
                if goal is None:
                    return ToolObservation.warning(
                        "No goal exists.", next_actions=["Start one with /goal OBJECTIVE."]
                    )
            elif args[0] == "prove":
                goal = self.goal.add_evidence(" ".join(args[1:]))
            elif args[0] == "verify":
                if len(args) < 3 or args[1].casefold() not in {"pass", "fail"}:
                    return self._control_usage(self.commands["goal"].usage)
                goal = self.goal.verify(args[1].casefold() == "pass", " ".join(args[2:]))
            elif args == ["complete"]:
                goal = self.goal.complete()
            elif args[0] == "block":
                goal = self.goal.block(" ".join(args[1:]))
            elif args == ["clear"]:
                self.goal.clear()
                return ToolObservation.success("Cleared the persistent goal.")
            else:
                goal = self.goal.start(" ".join(args))
        except GoalError as exc:
            return ToolObservation.error(
                f"Goal transition rejected: {exc}", "The evidence-gated goal state contract was not satisfied.",
                "Inspect /goal status and supply the missing objective, evidence, or verification.",
                "Stop before replacing or completing an active goal without proof.",
            )
        return ToolObservation.success(
            f"Goal is {goal['status']}: {goal['objective']}", data={"goal": goal}
        )
