"""Typed coding-agent slash commands backed by real CASPER engines."""

from __future__ import annotations

import asyncio
import json
import os
import platform
import shlex
import shutil
import subprocess
import sys
import time
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Optional

from .feature_manager import LocalCommandResult, TranscriptEntry


MAX_OUTPUT = 16_000
PERMISSION_MODES = {"default", "accept-edits", "plan", "bypass"}


@dataclass
class CommandObservation:
    status: str
    summary: str
    next_actions: list[str] = field(default_factory=list)
    artifacts: list[str] = field(default_factory=list)
    data: dict[str, Any] = field(default_factory=dict)
    root_cause_hint: str = ""
    safe_retry: str = ""
    stop_condition: str = ""

    def render(self) -> str:
        payload = {
            "status": self.status,
            "summary": self.summary,
            "next_actions": self.next_actions,
            "artifacts": self.artifacts,
        }
        if self.data:
            payload["data"] = self.data
        if self.root_cause_hint:
            payload["root_cause_hint"] = self.root_cause_hint
            payload["safe_retry"] = self.safe_retry
            payload["stop_condition"] = self.stop_condition
        return json.dumps(payload, indent=2, sort_keys=True, default=str)


@dataclass(frozen=True)
class CodingCommandSpec:
    name: str
    usage: str
    description: str
    handler: str
    mutates: bool = False
    aliases: tuple[str, ...] = ()


CODING_COMMANDS: tuple[CodingCommandSpec, ...] = (
    CodingCommandSpec(
        "/init", "/init", "Initialize or locate project instructions", "_cmd_init", True
    ),
    CodingCommandSpec(
        "/status", "/status", "Inspect repository and worktree state", "_cmd_status"
    ),
    CodingCommandSpec(
        "/doctor",
        "/doctor",
        "Diagnose runtimes, markers, and build system",
        "_cmd_doctor",
    ),
    CodingCommandSpec(
        "/model",
        "/model [list|set PROVIDER MODEL]",
        "Inspect or select the active model",
        "_cmd_model",
    ),
    CodingCommandSpec(
        "/permissions",
        "/permissions [set MODE]",
        "Inspect or set enforced permission mode",
        "_cmd_permissions",
    ),
    CodingCommandSpec(
        "/diff",
        "/diff [--stat|--cached] [-- PATH]",
        "Show a bounded Git diff",
        "_cmd_diff",
    ),
    CodingCommandSpec(
        "/review", "/review [PATH]", "Review current changes or one file", "_cmd_review"
    ),
    CodingCommandSpec(
        "/plan", "/plan REQUEST", "Compile a request into a frozen spec", "_cmd_plan"
    ),
    CodingCommandSpec(
        "/task",
        "/task REQUEST",
        "Run the reversible CASPER pipeline",
        "_cmd_task",
        True,
    ),
    CodingCommandSpec("/test", "/test [PATH]", "Run detected tests", "_cmd_test"),
    CodingCommandSpec("/lint", "/lint [PATH]", "Run detected lint checks", "_cmd_lint"),
    CodingCommandSpec(
        "/build", "/build", "Run the detected build command", "_cmd_build"
    ),
    CodingCommandSpec(
        "/context",
        "/context",
        "Show repository and transcript context budget",
        "_cmd_context",
    ),
    CodingCommandSpec(
        "/compact", "/compact", "Compact older transcript entries", "_cmd_compact"
    ),
    CodingCommandSpec(
        "/resume",
        "/resume [SESSION]",
        "List or load named TUI sessions",
        "_cmd_resume",
        aliases=("/continue",),
    ),
    CodingCommandSpec(
        "/skills",
        "/skills [QUERY]",
        "List or search installed CASPER skills",
        "_cmd_skills",
    ),
    CodingCommandSpec("/mcp", "/mcp", "Show live MCP server state", "_cmd_mcp"),
    CodingCommandSpec(
        "/agents", "/agents", "Show initialized agent-layer state", "_cmd_agents"
    ),
    CodingCommandSpec(
        "/rewind",
        "/rewind [list|undo ID]",
        "Inspect or reverse ledgered changes",
        "_cmd_rewind",
    ),
    CodingCommandSpec(
        "/usage", "/usage", "Show actual local command telemetry", "_cmd_usage"
    ),
)


class CodingCommandDispatcher:
    """Hybrid harness: familiar commands, typed observations, narrow engines."""

    def __init__(
        self,
        project_root: Path | str,
        feature_manager: Any,
        integration: Any = None,
        model_service: Any = None,
        config_adapter: Any = None,
        compiler_factory: Optional[Callable[[], Any]] = None,
        pipeline_factory: Optional[Callable[[str], Any]] = None,
        ledger_factory: Optional[Callable[[str], Any]] = None,
    ) -> None:
        self.project_root = Path(project_root).expanduser().resolve()
        self.features = feature_manager
        self.integration = integration
        self.model_service = model_service
        self.config_adapter = config_adapter
        self.compiler_factory = compiler_factory
        self.pipeline_factory = pipeline_factory
        self.ledger_factory = ledger_factory
        self.usage_path = self.features.state_root / "coding-command-usage.json"
        self._specs: dict[str, CodingCommandSpec] = {}
        for spec in CODING_COMMANDS:
            self._specs[spec.name] = spec
            for alias in spec.aliases:
                self._specs[alias] = spec

    def bind_integration(self, integration: Any) -> None:
        self.integration = integration

    def help_entries(self) -> dict[str, str]:
        return {spec.name: spec.description for spec in CODING_COMMANDS}

    def palette(self, query: str = "") -> list[str]:
        needle = query.casefold()
        return [
            f"{spec.usage} — {spec.description}"
            for spec in CODING_COMMANDS
            if needle in spec.name.casefold() or needle in spec.description.casefold()
        ]

    async def execute(self, ui: Any, command_line: str) -> LocalCommandResult:
        try:
            parts = shlex.split(command_line.strip())
        except ValueError as exc:
            return LocalCommandResult(
                True,
                self._error(
                    f"Could not parse command: {exc}",
                    "The quoting or escaping is incomplete.",
                    "Close each quote and retry the same command.",
                    "Stop if the intended argument cannot be represented without changing it.",
                ).render(),
            )
        if not parts:
            return LocalCommandResult(False)
        spec = self._specs.get(parts[0].casefold())
        if not spec:
            return LocalCommandResult(False)
        started = time.perf_counter()
        try:
            handler = getattr(self, spec.handler)
            observation = await handler(ui, parts[1:])
        except Exception as exc:
            observation = self._error(
                f"{spec.name} failed: {exc}",
                f"The {spec.name} engine raised {type(exc).__name__}.",
                f"Run {spec.usage} after correcting the reported input or environment.",
                "Stop after the same root cause repeats; inspect /doctor and /status.",
            )
        elapsed_ms = round((time.perf_counter() - started) * 1000, 2)
        observation.data.setdefault("command", spec.name)
        observation.data.setdefault("elapsed_ms", elapsed_ms)
        self._record_usage(spec.name, observation.status, elapsed_ms)
        return LocalCommandResult(True, observation.render())

    @staticmethod
    def _ok(
        summary: str,
        *,
        data: Optional[dict[str, Any]] = None,
        artifacts: Optional[list[str]] = None,
        next_actions: Optional[list[str]] = None,
    ) -> CommandObservation:
        return CommandObservation(
            "success", summary, next_actions or [], artifacts or [], data or {}
        )

    @staticmethod
    def _warning(
        summary: str,
        *,
        data: Optional[dict[str, Any]] = None,
        artifacts: Optional[list[str]] = None,
        next_actions: Optional[list[str]] = None,
    ) -> CommandObservation:
        return CommandObservation(
            "warning", summary, next_actions or [], artifacts or [], data or {}
        )

    @staticmethod
    def _error(
        summary: str,
        root_cause: str,
        retry: str,
        stop: str,
        *,
        data: Optional[dict[str, Any]] = None,
    ) -> CommandObservation:
        return CommandObservation(
            "error",
            summary,
            [retry],
            [],
            data or {},
            root_cause_hint=root_cause,
            safe_retry=retry,
            stop_condition=stop,
        )

    def _permission_mode(self) -> str:
        return str(self.features.settings.get("permission_mode", "default"))

    def _mutation_gate(self, command: str) -> Optional[CommandObservation]:
        mode = self._permission_mode()
        if mode in {"accept-edits", "bypass"}:
            return None
        return self._warning(
            f"{command} did not mutate the project because permission mode is {mode}.",
            data={"permission_mode": mode},
            next_actions=[
                "Run /permissions set accept-edits, inspect the command, then retry."
            ],
        )

    def _safe_path(self, raw: str) -> Path:
        path = (
            (self.project_root / raw).resolve()
            if not os.path.isabs(raw)
            else Path(raw).resolve()
        )
        if path != self.project_root and self.project_root not in path.parents:
            raise ValueError("path escapes the active project root")
        return path

    async def _run(
        self, argv: list[str], cwd: Optional[Path] = None, timeout: int = 120
    ) -> CommandObservation:
        if not argv or not shutil.which(argv[0]):
            return self._error(
                f"Executable not found: {argv[0] if argv else 'empty command'}",
                "The detected toolchain is not installed or not on PATH.",
                "Run /doctor, install the reported toolchain, then retry.",
                "Stop if the repository does not use that toolchain.",
            )
        process = await asyncio.create_subprocess_exec(
            *argv,
            cwd=str(cwd or self.project_root),
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        try:
            stdout, stderr = await asyncio.wait_for(
                process.communicate(), timeout=timeout
            )
        except asyncio.TimeoutError:
            process.kill()
            await process.wait()
            return self._error(
                f"Command timed out after {timeout}s: {' '.join(argv)}",
                "The process exceeded the bounded execution window.",
                "Narrow the target or run the underlying command directly with a larger timeout.",
                "Stop if it hangs again on the same target.",
            )
        output = (stdout.decode(errors="replace") + stderr.decode(errors="replace"))[
            -MAX_OUTPUT:
        ]
        data = {"argv": argv, "exit_code": process.returncode, "output": output}
        if process.returncode == 0:
            return self._ok(f"Command passed: {' '.join(argv)}", data=data)
        return self._error(
            f"Command failed with exit code {process.returncode}: {' '.join(argv)}",
            "The invoked project tool reported a non-zero exit code.",
            "Use the bounded output to fix the first concrete failure, then rerun the same command.",
            "Stop when the failure requires credentials, external services, or destructive changes.",
            data=data,
        )

    def _git(self, args: list[str]) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            ["git", *args],
            cwd=self.project_root,
            text=True,
            capture_output=True,
            timeout=20,
            check=False,
        )

    async def _cmd_init(self, ui: Any, args: list[str]) -> CommandObservation:
        if args:
            return self._error(
                "Usage: /init",
                "Unexpected arguments were provided.",
                "Run /init without arguments.",
                "Stop if a different project root is intended.",
            )
        markers = [
            name
            for name in ("AGENTS.md", "FLOYD.md", "CLAUDE.md")
            if (self.project_root / name).exists()
        ]
        if markers:
            return self._ok(
                "Project instructions already exist.",
                artifacts=[str(self.project_root / name) for name in markers],
            )
        gate = self._mutation_gate("/init")
        if gate:
            return gate
        target = self.project_root / "AGENTS.md"
        target.write_text(
            "# Project Instructions\n\n"
            "- Verify the live working directory before changes.\n"
            "- Preserve unrelated worktree changes.\n"
            "- Run repository-native tests before completion claims.\n",
            encoding="utf-8",
        )
        return self._ok(
            "Initialized project instructions.",
            artifacts=[str(target)],
            next_actions=["Review AGENTS.md and add project-specific commands."],
        )

    async def _cmd_status(self, ui: Any, args: list[str]) -> CommandObservation:
        if args:
            return self._error(
                "Usage: /status",
                "Unexpected arguments were provided.",
                "Run /status without arguments.",
                "Stop if a scoped status was intended; use /diff -- PATH.",
            )
        inside = self._git(["rev-parse", "--is-inside-work-tree"])
        if inside.returncode != 0:
            return self._warning(
                "The active directory is not a Git worktree.",
                data={"cwd": str(self.project_root)},
            )
        branch = self._git(["branch", "--show-current"]).stdout.strip() or "detached"
        head = self._git(["rev-parse", "--short", "HEAD"]).stdout.strip()
        porcelain = self._git(["status", "--short"]).stdout.splitlines()
        return self._ok(
            f"Git worktree on {branch} at {head}; {len(porcelain)} changed path(s).",
            data={
                "cwd": str(self.project_root),
                "branch": branch,
                "head": head,
                "changes": porcelain,
            },
        )

    async def _cmd_doctor(self, ui: Any, args: list[str]) -> CommandObservation:
        if args:
            return self._error(
                "Usage: /doctor",
                "Unexpected arguments were provided.",
                "Run /doctor without arguments.",
                "Stop if live credential validation is required; this doctor is local-only.",
            )
        from core.pipeline.buildsystems import detect_build_system

        runtimes: dict[str, dict[str, Any]] = {}
        for binary in ("python3", "node", "npm", "git"):
            path = shutil.which(binary)
            version = ""
            if path:
                probe = subprocess.run(
                    [path, "--version"], capture_output=True, text=True, timeout=8
                )
                version = (probe.stdout or probe.stderr).strip().splitlines()[0]
            runtimes[binary] = {"present": bool(path), "path": path, "version": version}
        build = detect_build_system(str(self.project_root)).to_dict()
        markers = [
            name
            for name in ("FLOYD.md", "AGENTS.md", "CLAUDE.md", "README.md")
            if (self.project_root / name).exists()
        ]
        missing = [
            name
            for name, item in runtimes.items()
            if not item["present"] and name in {"python3", "git"}
        ]
        status = self._warning if missing or not build["available"] else self._ok
        return status(
            (
                "Local diagnostics found blockers."
                if missing
                else "Local runtime and project diagnostics completed."
            ),
            data={
                "platform": platform.platform(),
                "python": sys.version.split()[0],
                "runtimes": runtimes,
                "build_system": build,
                "markers": markers,
            },
            next_actions=(
                ["Install missing required runtimes and rerun /doctor."]
                if missing
                else []
            ),
        )

    def _get_config_adapter(self) -> Any:
        if self.config_adapter is None:
            from core.services.user_config import user_config

            self.config_adapter = user_config
        return self.config_adapter

    def _get_model_service(self) -> Any:
        if self.model_service is None:
            from core.services.llm import llm_service

            self.model_service = llm_service
        return self.model_service

    async def _cmd_model(self, ui: Any, args: list[str]) -> CommandObservation:
        config = self._get_config_adapter()
        if args and args[0] == "list":
            models = await self._get_model_service().list_available_models()
            return self._ok("Resolved available models.", data={"models": models})
        if args and args[0] == "set":
            if len(args) < 3:
                return self._error(
                    "Usage: /model set PROVIDER MODEL",
                    "Provider or model is missing.",
                    "Supply both provider and model.",
                    "Stop if the model is not available from /model list.",
                )
            gate = self._mutation_gate("/model set")
            if gate:
                return gate
            config.set_default_model(args[1], " ".join(args[2:]))
        elif args:
            return self._error(
                "Usage: /model [list|set PROVIDER MODEL]",
                "Unknown model action.",
                "Run /model, /model list, or /model set PROVIDER MODEL.",
                "Stop if provider credentials are unavailable.",
            )
        provider = config.get_default_provider()
        model = config.get_default_model(None, provider)
        return self._ok(
            f"Active model: {provider}/{model or 'auto'}",
            data={"provider": provider, "model": model or "auto"},
        )

    async def _cmd_permissions(self, ui: Any, args: list[str]) -> CommandObservation:
        if args and args[0] == "set":
            if len(args) != 2 or args[1] not in PERMISSION_MODES:
                return self._error(
                    "Usage: /permissions set default|accept-edits|plan|bypass",
                    "The permission mode is invalid.",
                    "Choose one of the listed modes.",
                    "Stop before using bypass unless unrestricted mutation is intentional.",
                )
            self.features.settings["permission_mode"] = args[1]
            self.features.save_settings()
        elif args:
            return self._error(
                "Usage: /permissions [set MODE]",
                "Unknown permission action.",
                "Run /permissions or /permissions set MODE.",
                "Stop if policy changes require operator approval.",
            )
        mode = self._permission_mode()
        return self._ok(
            f"Permission mode: {mode}",
            data={
                "mode": mode,
                "mutations_allowed": mode in {"accept-edits", "bypass"},
            },
        )

    async def _cmd_diff(self, ui: Any, args: list[str]) -> CommandObservation:
        allowed_flags = {"--stat", "--cached"}
        git_args = ["diff"]
        path: Optional[Path] = None
        while args:
            value = args.pop(0)
            if value in allowed_flags:
                git_args.append(value)
            elif value == "--" and args:
                path = self._safe_path(args.pop(0))
                if args:
                    raise ValueError("only one diff path is supported")
            else:
                raise ValueError(f"unsupported diff argument: {value}")
        if path:
            git_args.extend(["--", str(path.relative_to(self.project_root))])
        result = self._git(git_args)
        if result.returncode != 0:
            return self._error(
                "Git diff failed.",
                result.stderr.strip() or "Git rejected the arguments.",
                "Run /status, then retry with /diff or /diff -- PATH.",
                "Stop if the active directory is not the intended repository.",
            )
        output = result.stdout[-MAX_OUTPUT:]
        return self._ok(
            "Git diff collected." if output else "Git diff is empty.",
            data={"output": output, "truncated": len(result.stdout) > MAX_OUTPUT},
        )

    async def _cmd_review(self, ui: Any, args: list[str]) -> CommandObservation:
        if len(args) > 1:
            return self._error(
                "Usage: /review [PATH]",
                "Only one review target is supported.",
                "Provide one repo-relative path or no path for the diff.",
                "Stop if review scope remains ambiguous.",
            )
        artifacts: list[str] = []
        if args:
            path = self._safe_path(args[0])
            if not path.is_file():
                return self._error(
                    "Review target is not a file.",
                    "The scoped path does not exist as a file.",
                    "Correct the path and retry.",
                    "Stop if the file is generated or outside the repository.",
                )
            content = path.read_text(encoding="utf-8", errors="replace")[:MAX_OUTPUT]
            artifacts = [str(path)]
        else:
            content = self._git(["diff", "--no-ext-diff"]).stdout[:MAX_OUTPUT]
        if not content.strip():
            return self._warning(
                "There is no reviewable content in the selected scope.",
                artifacts=artifacts,
            )
        review = await self._get_model_service().complete(
            prompt=content,
            system="Review this code for concrete correctness, security, and regression risks. Return findings with severity and file/line evidence. Do not praise or summarize unchanged code.",
            tier="frontier",
            max_tokens=1800,
        )
        if not review:
            return self._error(
                "The review engine returned no findings or explanation.",
                "All configured LLM providers were unavailable or returned empty output.",
                "Run /model list and /doctor, then retry /review.",
                "Stop after provider authentication or quota fails again.",
            )
        return self._ok(
            "Code review completed.", data={"review": review}, artifacts=artifacts
        )

    async def _cmd_plan(self, ui: Any, args: list[str]) -> CommandObservation:
        request = " ".join(args).strip()
        if not request:
            return self._error(
                "Usage: /plan REQUEST",
                "No planning request was supplied.",
                "Add a concrete coding request after /plan.",
                "Stop if the desired outcome is not yet known.",
            )
        if self.compiler_factory:
            compiler = self.compiler_factory()
        else:
            from core.pipeline.compiler import InputCompiler

            compiler = InputCompiler()
        try:
            spec = await compiler.compile(request)
            payload = spec.to_dict()
            return self._ok(
                "Request compiled into a frozen specification; no code was executed.",
                data={"spec": payload},
            )
        except Exception as exc:
            questions = getattr(exc, "questions", None)
            partial = getattr(exc, "partial_spec", None)
            if questions is not None:
                return self._warning(
                    "Planning needs bounded clarification; no code was executed.",
                    data={
                        "questions": [q.to_dict() for q in questions],
                        "partial_spec": partial.to_dict() if partial else None,
                    },
                )
            raise

    async def _cmd_task(self, ui: Any, args: list[str]) -> CommandObservation:
        request = " ".join(args).strip()
        if not request:
            return self._error(
                "Usage: /task REQUEST",
                "No execution request was supplied.",
                "Add a concrete coding task after /task.",
                "Stop if the intended files and acceptance conditions are unknown.",
            )
        gate = self._mutation_gate("/task")
        if gate:
            return gate
        if self.pipeline_factory:
            pipeline = self.pipeline_factory(str(self.project_root))
        else:
            from core.pipeline.pipeline import Pipeline

            pipeline = Pipeline(str(self.project_root))
        result = await pipeline.run(request)
        payload = result.to_dict()
        status = payload.get("status")
        if status == "done":
            return self._ok(
                payload.get("human_summary") or "Pipeline completed.",
                data={"run": payload},
                artifacts=list(payload.get("artifacts") or []),
            )
        return self._warning(
            payload.get("human_summary") or f"Pipeline ended with status {status}.",
            data={"run": payload},
            artifacts=list(payload.get("artifacts") or []),
            next_actions=[
                "Answer returned clarification questions or inspect the blocked detail before retrying."
            ],
        )

    def _build_system(self):
        from core.pipeline.buildsystems import detect_build_system

        return detect_build_system(str(self.project_root))

    async def _cmd_test(self, ui: Any, args: list[str]) -> CommandObservation:
        if len(args) > 1:
            return self._error(
                "Usage: /test [PATH]",
                "Only one scoped test target is supported.",
                "Provide one repo-relative path or no target.",
                "Stop if the test runner needs custom flags; run it directly.",
            )
        build = self._build_system()
        command = list(build.test_cmd or [])
        if args:
            target = self._safe_path(args[0])
            if build.kind == "python":
                command = [sys.executable, "-m", "pytest", "-q", str(target)]
            else:
                return self._warning(
                    "Scoped test targets are currently supported only for Python projects.",
                    data={"build_system": build.to_dict()},
                )
        if not command:
            return self._warning(
                "No test command was detected.",
                data={"build_system": build.to_dict()},
                next_actions=["Add a repository-native test script, then rerun /test."],
            )
        return await self._run(command)

    async def _cmd_lint(self, ui: Any, args: list[str]) -> CommandObservation:
        if len(args) > 1:
            return self._error(
                "Usage: /lint [PATH]",
                "Only one lint target is supported.",
                "Provide one repo-relative path or no target.",
                "Stop if custom lint flags are required.",
            )
        target = self._safe_path(args[0]) if args else self.project_root
        build = self._build_system()
        if build.kind == "node":
            command = ["npm", "run", "lint", "--if-present"]
        elif build.kind == "python" and shutil.which("ruff"):
            command = ["ruff", "check", str(target)]
        elif build.kind == "python" and shutil.which("flake8"):
            command = ["flake8", str(target)]
        elif build.kind == "python":
            command = [sys.executable, "-m", "compileall", "-q", str(target)]
        elif build.kind == "rust":
            command = ["cargo", "clippy", "--", "-D", "warnings"]
        elif build.kind == "go":
            command = ["go", "vet", "./..."]
        else:
            return self._warning(
                "No lint engine was detected.", data={"build_system": build.to_dict()}
            )
        return await self._run(command)

    async def _cmd_build(self, ui: Any, args: list[str]) -> CommandObservation:
        if args:
            return self._error(
                "Usage: /build",
                "Build does not accept free-form arguments.",
                "Run /build without arguments.",
                "Stop if the project requires a custom build command; configure it first.",
            )
        build = self._build_system()
        if not build.build_cmd:
            return self._warning(
                "No build command was detected.", data={"build_system": build.to_dict()}
            )
        return await self._run(list(build.build_cmd))

    async def _cmd_context(self, ui: Any, args: list[str]) -> CommandObservation:
        if args:
            return self._error(
                "Usage: /context",
                "Unexpected context arguments were provided.",
                "Run /context without arguments.",
                "Stop if a named context was intended; use /resume for sessions.",
            )
        tracked = self._git(["ls-files"]).stdout.splitlines()
        transcript_chars = sum(len(item.content) for item in self.features.transcript)
        head = self._git(["rev-parse", "--short", "HEAD"]).stdout.strip()
        return self._ok(
            "Live context snapshot collected.",
            data={
                "project_root": str(self.project_root),
                "git_head": head or None,
                "tracked_files": len(tracked),
                "transcript_entries": len(self.features.transcript),
                "transcript_characters": transcript_chars,
                "approx_tokens": (transcript_chars + 3) // 4,
            },
        )

    async def _cmd_compact(self, ui: Any, args: list[str]) -> CommandObservation:
        if args:
            return self._error(
                "Usage: /compact",
                "Unexpected compact arguments were provided.",
                "Run /compact without arguments.",
                "Stop if an export is required before compaction; run /export first.",
            )
        entries = self.features.transcript
        if len(entries) <= 10:
            return self._warning(
                "Transcript is already compact; no entries were removed.",
                data={"entries": len(entries)},
            )
        older, recent = entries[:-10], entries[-10:]
        counts = Counter(f"{item.pane}/{item.kind}" for item in older)
        summary = "Compacted transcript: " + ", ".join(
            f"{key}={value}" for key, value in sorted(counts.items())
        )
        compacted = TranscriptEntry(
            timestamp=older[-1].timestamp,
            pane="reasoning",
            kind="compact-summary",
            content=summary,
        )
        self.features.transcript = [compacted, *recent]
        self.features.autosave(ui.panes)
        return self._ok(
            f"Compacted {len(older)} older entries into one summary.",
            data={
                "before": len(entries),
                "after": len(self.features.transcript),
                "summary": summary,
            },
            next_actions=[
                "Use /export before future compaction when full fidelity must be retained."
            ],
        )

    async def _cmd_resume(self, ui: Any, args: list[str]) -> CommandObservation:
        if len(args) > 1:
            return self._error(
                "Usage: /resume [SESSION]",
                "Only one session name is supported.",
                "Provide one session name or no arguments to list.",
                "Stop if the session file is corrupt; preserve it for inspection.",
            )
        if not args:
            sessions = self.features.list_sessions()
            return self._ok(
                f"Found {len(sessions)} saved session(s).", data={"sessions": sessions}
            )
        path = self.features.sessions_dir / f"{self.features._safe_name(args[0])}.json"
        restored = self.features.restore(ui.panes, path)
        if not restored:
            return self._error(
                "Session was not found or could not be read.",
                "The named session file is missing or invalid.",
                "Run /resume to list exact session names, then retry.",
                "Stop if the session file contains invalid JSON; preserve it before repair.",
            )
        ui.rebuild_layout()
        return self._ok("Session restored.", artifacts=[str(path)])

    async def _cmd_skills(self, ui: Any, args: list[str]) -> CommandObservation:
        query = " ".join(args).casefold()
        dirs = [self.project_root / ".casper" / "skills"]
        shared = os.environ.get("CASPER_SKILLS_HOME")
        if shared:
            dirs.append(Path(shared).expanduser())
        skills: list[dict[str, Any]] = []
        seen: set[Path] = set()
        for directory in dirs:
            try:
                resolved = directory.resolve()
            except OSError:
                continue
            if resolved in seen or not resolved.exists():
                continue
            seen.add(resolved)
            for path in sorted(resolved.glob("*.json")):
                try:
                    payload = json.loads(path.read_text(encoding="utf-8"))
                except (OSError, json.JSONDecodeError):
                    continue
                haystack = json.dumps(payload).casefold()
                if not query or query in haystack:
                    skills.append(
                        {
                            "id": payload.get("id", path.stem),
                            "name": payload.get("name", path.stem),
                            "description": payload.get("description", ""),
                            "path": str(path),
                        }
                    )
        return self._ok(
            f"Found {len(skills)} matching skill(s).",
            data={"skills": skills},
            artifacts=[item["path"] for item in skills],
        )

    async def _cmd_mcp(self, ui: Any, args: list[str]) -> CommandObservation:
        if args:
            return self._error(
                "Usage: /mcp",
                "Unexpected MCP arguments were provided.",
                "Run /mcp without arguments.",
                "Stop if MCP configuration changes are required; this command is status-only.",
            )
        server = (
            getattr(self.integration, "mcp_server", None) if self.integration else None
        )
        if not server:
            return self._warning(
                "MCP server is not initialized.",
                next_actions=["Initialize the terminal integration, then rerun /mcp."],
            )
        stats = dict(getattr(server, "stats", {}))
        return self._ok(
            "MCP server state collected.",
            data={
                "port": getattr(server, "port", None),
                "stats": stats,
                "connections": len(getattr(server, "connections", {})),
            },
        )

    async def _cmd_agents(self, ui: Any, args: list[str]) -> CommandObservation:
        if args:
            return self._error(
                "Usage: /agents",
                "Unexpected agent arguments were provided.",
                "Run /agents without arguments.",
                "Stop if agent reconfiguration is required; this command is status-only.",
            )
        session = (
            getattr(self.integration, "agent_session", None)
            if self.integration
            else None
        )
        if not session:
            return self._warning(
                "Agent layers are not initialized.",
                next_actions=[
                    "Initialize the terminal integration, then rerun /agents."
                ],
            )
        return self._ok(
            "Agent-layer state collected.",
            data={
                "session_id": session.get("session_id"),
                "status": session.get("status"),
                "layers": session.get("layers", {}),
            },
        )

    def _get_ledger(self):
        if self.ledger_factory:
            return self.ledger_factory(str(self.project_root))
        from core.pipeline.progress import ChangeLedger

        return ChangeLedger(str(self.project_root))

    async def _cmd_rewind(self, ui: Any, args: list[str]) -> CommandObservation:
        ledger = self._get_ledger()
        if not args or args[0] == "list":
            changes = ledger.human_log()
            return self._ok(
                f"Found {len(changes)} ledgered change(s).", data={"changes": changes}
            )
        if len(args) == 2 and args[0] == "undo":
            gate = self._mutation_gate("/rewind undo")
            if gate:
                return gate
            result = ledger.undo(args[1])
            if result.get("status") in {"ok", "noop"}:
                return self._ok(
                    result.get("message", "Rewind completed."),
                    data={"ledger_result": result},
                )
            return self._error(
                result.get("message", "Rewind failed."),
                "The ledger entry is missing, irreversible, or lacks a restore snapshot.",
                "Run /rewind list and retry with a reversible, not-undone ID.",
                "Stop before manual restoration if the source artifact is missing.",
            )
        return self._error(
            "Usage: /rewind [list|undo ID]",
            "The rewind action is invalid.",
            "Run /rewind list or /rewind undo ID.",
            "Stop if the requested entry is irreversible.",
        )

    async def _cmd_usage(self, ui: Any, args: list[str]) -> CommandObservation:
        if args:
            return self._error(
                "Usage: /usage",
                "Unexpected usage arguments were provided.",
                "Run /usage without arguments.",
                "Stop if provider billing data is required; this reports local command telemetry only.",
            )
        data = self._read_usage()
        return self._ok(
            "Local command telemetry collected; this is not provider billing data.",
            data=data,
        )

    def _read_usage(self) -> dict[str, Any]:
        try:
            value = json.loads(self.usage_path.read_text(encoding="utf-8"))
            return value if isinstance(value, dict) else {"commands": {}}
        except (OSError, json.JSONDecodeError):
            return {"commands": {}}

    def _record_usage(self, command: str, status: str, elapsed_ms: float) -> None:
        data = self._read_usage()
        commands = data.setdefault("commands", {})
        item = commands.setdefault(
            command, {"count": 0, "errors": 0, "total_elapsed_ms": 0.0}
        )
        item["count"] += 1
        item["errors"] += int(status == "error")
        item["total_elapsed_ms"] = round(
            float(item["total_elapsed_ms"]) + elapsed_ms, 2
        )
        item["last_status"] = status
        data["updated_at"] = time.time()
        self.features._write_json(self.usage_path, data)
