"""Interactive and headless clients for the canonical CASPER harness runtime."""

from __future__ import annotations

import json
import os
import re
import shlex
import uuid
from pathlib import Path
from typing import Optional

from prompt_toolkit import PromptSession
from prompt_toolkit.auto_suggest import AutoSuggestFromHistory
from prompt_toolkit.completion import FuzzyCompleter, WordCompleter
from prompt_toolkit.history import FileHistory
from prompt_toolkit.key_binding import KeyBindings
from rich.console import Console
from rich.panel import Panel
from rich.prompt import Prompt
from rich.table import Table
from rich.text import Text

from core.harness import (
    HarnessRuntime,
    ObservationStatus,
    PermissionMode,
    RunResult,
    RunStatus,
    ToolObservation,
)
from core.harness.providers import ProviderChain
from core.harness.catalog import FEATURE_GROUPS, feature_count
from core.harness.commands import HARNESS_COMMANDS, command_index, command_palette


CONTROL_HELP: tuple[tuple[str, str], ...] = tuple(
    (spec.usage, spec.description) for spec in HARNESS_COMMANDS
)


def _normalize_input(raw: str) -> str:
    """Normalize familiar terminal spellings before any text reaches the model."""
    value = raw.strip()
    lowered = value.casefold()
    explicit_casper = False
    if lowered.startswith("casper:"):
        value = value.split(":", 1)[1].strip()
        explicit_casper = True
    elif lowered.startswith("casper "):
        value = value.split(None, 1)[1].strip()
        explicit_casper = True
    if not value:
        return value
    directory_patterns = (
        re.compile(
            r"^create\s+(?:a\s+)?(?:new\s+)?(?:directory|folder)\s+"
            r"(?:in|at|under)\s+(?P<parent>.+?)\s+named\s+(?P<name>[^/]+)$", re.IGNORECASE,
        ),
        re.compile(
            r"^create\s+(?:a\s+)?(?:new\s+)?(?:directory|folder)\s+named\s+"
            r"(?P<name>.+?)\s+(?:in|at|under)\s+(?P<parent>.+)$", re.IGNORECASE,
        ),
    )
    for pattern in directory_patterns:
        match = pattern.match(value)
        if match:
            parent = HarnessRuntime.normalize_local_path(match.group("parent").strip().strip("'\""))
            name = match.group("name").strip().strip("'\"")
            if name and name not in {".", ".."} and "/" not in name:
                return "/mkdir " + shlex.quote(str(Path(parent) / name))
    try:
        parts = shlex.split(value)
    except ValueError:
        return value
    if not parts or parts[0].startswith("/"):
        return value
    command = parts[0].casefold()
    if command in command_index() and (
        explicit_casper or len(parts) == 1 or command in {"help", "commands"}
    ):
        return "/" + value
    return value


def _tui_history_path() -> Path:
    root = os.environ.get("CASPER_TUI_HOME")
    if root:
        return Path(root).expanduser().resolve() / "history.txt"
    state = Path(os.environ.get("XDG_STATE_HOME", Path.home() / ".local" / "state"))
    return state / "casper" / "tui" / "history.txt"


def _build_prompt_session(runtime: HarnessRuntime) -> PromptSession[str]:
    history_path = _tui_history_path()
    history_path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    commands = sorted({
        name for spec in HARNESS_COMMANDS for name in (f"/{spec.name}", *(f"/{alias}" for alias in spec.aliases))
    })
    completer = FuzzyCompleter(WordCompleter(commands, ignore_case=True, sentence=True))
    bindings = KeyBindings()

    @bindings.add("escape", "enter")
    def _insert_newline(event) -> None:
        event.current_buffer.insert_text("\n")

    @bindings.add("c-o")
    def _open_editor(event) -> None:
        event.current_buffer.open_in_editor(validate_and_handle=False)

    return PromptSession(
        history=FileHistory(str(history_path)),
        auto_suggest=AutoSuggestFromHistory(),
        completer=completer,
        key_bindings=bindings,
        complete_while_typing=False,
        bottom_toolbar=lambda: (
            f" {runtime.project_root}  ·  {runtime.policy.mode.value}  ·  "
            "Tab complete  ↑↓ history  Alt-Enter newline  Ctrl-O editor  Ctrl-C cancel  Ctrl-D quit "
        ),
    )


def _status_style(status: str) -> str:
    return {
        "complete": "green",
        "success": "green",
        "awaiting_approval": "yellow",
        "blocked": "yellow",
        "warning": "yellow",
        "failed": "red",
        "error": "red",
    }.get(status, "cyan")


def render_help(console: Console, runtime: HarnessRuntime, query: str = "") -> None:
    matches = command_palette(query)
    title = "CASPER coding harness" + (f" · {query}" if query else "")
    table = Table(title=title, border_style="cyan")
    table.add_column("Command", style="bright_cyan", no_wrap=True)
    table.add_column("Group", style="dim", no_wrap=True)
    table.add_column("Purpose")
    for spec in matches:
        table.add_row(Text(spec.usage), spec.category, spec.description)
    console.print(table)
    console.print(
        f"[dim]{len(matches)} commands · {len(runtime.registry.specs())} typed tools. "
        "Plain language and /task use the same bounded runtime; /commands filters this list.[/dim]"
    )


def render_tools(console: Console, runtime: HarnessRuntime) -> None:
    table = Table(title="Active typed tools", border_style="cyan")
    table.add_column("Tool", style="bright_cyan")
    table.add_column("Risk")
    table.add_column("Mutates")
    table.add_column("Purpose")
    for spec in runtime.registry.specs():
        table.add_row(spec.name, spec.risk, "yes" if spec.mutates else "no", spec.description)
    console.print(table)


def render_features(console: Console) -> None:
    table = Table(title=f"Verified harness engines ({feature_count()})", border_style="cyan")
    table.add_column("Cycle", style="bright_cyan", no_wrap=True)
    table.add_column("Engine group")
    table.add_column("Features")
    for group in FEATURE_GROUPS:
        table.add_row(str(group.cycle), group.name, ", ".join(group.features))
    console.print(table)


def _agentic_prompt(command_line: str) -> str:
    """Compile supported agentic slash commands into explicit natural-language contracts."""
    parts = shlex.split(command_line)
    if not parts or not parts[0].startswith("/"):
        return command_line
    spec = command_index().get(parts[0][1:].casefold())
    if spec is None or not spec.agentic:
        return command_line
    command = spec.name
    request = " ".join(parts[1:]).strip()
    if command == "task":
        if not request:
            raise ValueError("Usage: /task REQUEST")
        return request
    if command == "plan":
        if not request:
            raise ValueError("Usage: /plan REQUEST")
        return (
            "Plan this coding task without mutating files. Inspect repository evidence, identify "
            "dependencies and verification steps, and return a concise executable plan: " + request
        )
    if command == "verify":
        focus = request or "the current pending change"
        return (
            "Verify " + focus + ". Use direct runtime or test evidence, do not change product code, "
            "and report PASS only when the observed result proves the behavior."
        )
    return command_line


def render_result(console: Console, result: RunResult) -> None:
    status = result.status.value
    body = result.text or result.error or "Run paused."
    details = [f"run: {result.run_id}", f"steps: {result.steps}"]
    if result.usage:
        details.append("usage: " + ", ".join(f"{key}={value}" for key, value in sorted(result.usage.items())))
    if result.artifacts:
        details.append("artifacts:\n" + "\n".join(f"  {item}" for item in result.artifacts))
    console.print(Panel(body, title=f"CASPER · {status}", border_style=_status_style(status)))
    console.print("[dim]" + " · ".join(details[:2]) + "[/dim]")
    for item in details[2:]:
        console.print(f"[dim]{item}[/dim]")


def render_observation(console: Console, observation: ToolObservation) -> None:
    """Render deterministic controls for humans while retaining structured data in tests/API."""
    status = observation.status.value
    console.print(Panel(
        Text(observation.summary), title=f"CASPER · {status}", border_style=_status_style(status),
    ))
    if observation.data:
        table = Table(show_header=False, box=None, padding=(0, 1))
        table.add_column("Field", style="bright_cyan", no_wrap=True)
        table.add_column("Value")
        for key, value in observation.data.items():
            if isinstance(value, list):
                rendered = json.dumps(value[:50], indent=2, default=str)
                if len(value) > 50:
                    rendered += f"\n… {len(value) - 50} more"
            elif isinstance(value, dict):
                rendered = json.dumps(value, indent=2, default=str)
            else:
                rendered = str(value)
            if len(rendered) > 8_000:
                rendered = rendered[:8_000] + "\n… output truncated; use /export for full data"
            table.add_row(Text(str(key)), Text(rendered))
        console.print(table)
    if observation.root_cause_hint:
        console.print(Text("Cause: " + observation.root_cause_hint, style="yellow"))
    for action in observation.next_actions:
        console.print(Text("Next: " + action, style="cyan"))


async def _resolve_approvals(
    console: Console, runtime: HarnessRuntime, result: RunResult
) -> RunResult:
    while result.status == RunStatus.AWAITING_APPROVAL and result.pending_calls:
        call = result.pending_calls[0]
        console.print(
            Panel(
                json.dumps(call.to_dict(), indent=2, sort_keys=True),
                title="Approval required",
                border_style="yellow",
            )
        )
        while True:
            answer = Prompt.ask(
                "Approve this exact tool call? [y/n]", default="n", console=console,
            ).strip().casefold()
            if answer in {"y", "yes", "approve", "approved"}:
                break
            if answer in {"n", "no", "reject", "rejected"}:
                return result
            console.print("[yellow]Type y/yes/approve or n/no/reject.[/yellow]")
        result = await runtime.resume(result.run_id, approved_call_ids=[call.id])
    return result


async def run_interactive(
    project_root: Path | str = ".",
    *,
    permission_mode: PermissionMode | str = PermissionMode.ACCEPT_EDITS,
    console: Optional[Console] = None,
) -> int:
    """Run CASPER's preserved-brand conversational TUI client."""
    console = console or Console()
    runtime = HarnessRuntime(project_root, permission_mode=permission_mode)
    session_hooks = await runtime.start_session("interactive")
    prompt_session = _build_prompt_session(runtime)
    console.print(
        "[bold bright_cyan]CASPER coding harness[/bold bright_cyan] "
        f"[dim]· {runtime.project_root} · {runtime.policy.mode.value}[/dim]"
    )
    if runtime.degraded_mode:
        console.print(
            "[yellow]Chat-only provider fallback is active; configure Anthropic or "
            "OpenAI for native tool execution.[/yellow]"
        )
    if session_hooks.failures:
        console.print(
            f"[yellow]{len(session_hooks.failures)} session hook(s) failed open; run /hooks for details.[/yellow]"
        )
    console.print(
        "[dim]Describe work naturally, or type help. Ctrl-C cancels the current input/run; /quit exits.[/dim]"
    )
    while True:
        try:
            value = (await prompt_session.prompt_async("casper: ")).strip()
        except (EOFError, KeyboardInterrupt):
            console.print()
            await runtime.end_session("operator_exit")
            return 0
        value = _normalize_input(value)
        if not value:
            continue
        if value.casefold() in {"/quit", "/exit", "quit", "exit"}:
            await runtime.end_session("operator_exit")
            return 0
        if value.casefold().startswith("/help") or value.casefold().startswith("/commands"):
            try:
                parts = shlex.split(value)
            except ValueError as exc:
                console.print(Panel(str(exc), title="CASPER · invalid command", border_style="red"))
                continue
            render_help(console, runtime, " ".join(parts[1:]))
            continue
        if value.casefold() == "/tools":
            render_tools(console, runtime)
            continue
        if value.casefold() == "/features":
            render_features(console)
            continue
        if value.casefold() == "/clear":
            console.clear()
            continue
        if value.casefold() == "/setup":
            try:
                from core.services.setup import SetupService

                SetupService().interactive_setup()
                runtime.reload_provider()
                console.print("[green]Provider configuration reloaded for this session.[/green]")
            except KeyboardInterrupt:
                console.print("\n[yellow]Setup cancelled; the existing configuration is unchanged.[/yellow]")
            except Exception as exc:
                console.print(Panel(str(exc), title="CASPER · setup failed", border_style="red"))
            continue
        try:
            control_parts = shlex.split(value)
        except ValueError:
            control_parts = []
        control_spec = (
            command_index().get(control_parts[0][1:].casefold())
            if control_parts and control_parts[0].startswith("/") else None
        )
        if control_spec and control_spec.name == "history":
            query = " ".join(control_parts[1:]).casefold()
            entries = [item for item in prompt_session.history.get_strings() if not query or query in item.casefold()]
            if entries:
                for index, entry in enumerate(entries[-100:], start=max(1, len(entries) - 99)):
                    console.print(Text(f"{index:>4}  {entry}"))
            else:
                console.print("[dim]No matching input history.[/dim]")
            continue
        if control_spec and control_spec.name == "workdir":
            if len(control_parts) != 2:
                console.print("[yellow]Usage: /workdir PATH[/yellow]")
                continue
            target = runtime.workspace.resolve(control_parts[1])
            if not target.is_dir():
                console.print(Panel(f"Directory not found: {target}", title="CASPER · error", border_style="red"))
                continue
            mode = runtime.policy.mode
            await runtime.end_session("workdir_change")
            runtime = HarnessRuntime(target, permission_mode=mode)
            await runtime.start_session("workdir_change")
            prompt_session = _build_prompt_session(runtime)
            console.print(f"[green]Active project switched to {target}[/green]")
            continue
        control = await runtime.handle_control(value)
        if control is not None:
            render_observation(console, control)
            continue
        try:
            prompt = _agentic_prompt(value)
            provider_failures = len(runtime.provider.failures) if isinstance(runtime.provider, ProviderChain) else 0
            with console.status("[bright_cyan]CASPER is inspecting and acting…[/bright_cyan]", spinner="dots"):
                result = await runtime.run(prompt)
            result = await _resolve_approvals(console, runtime, result)
            if isinstance(runtime.provider, ProviderChain) and len(runtime.provider.failures) > provider_failures:
                newest = runtime.provider.failures[provider_failures:]
                names = ", ".join(item["provider"] for item in newest)
                console.print(
                    f"[yellow]Provider failover used after {names} failed; continued with "
                    f"{type(runtime.provider.active).__name__}. Run /config for the active provider.[/yellow]"
                )
            render_result(console, result)
        except KeyboardInterrupt:
            console.print("[yellow]Run cancelled by operator.[/yellow]")
        except Exception as exc:
            console.print(Panel(str(exc), title="CASPER · failed", border_style="red"))


async def run_exec(
    prompt: str,
    *,
    project_root: Path | str = ".",
    permission_mode: PermissionMode | str = PermissionMode.READ_ONLY,
    output: Optional[Console] = None,
) -> int:
    """Run one headless turn and emit a stable JSONL event protocol."""
    output = output or Console(force_terminal=False, color_system=None, highlight=False)
    runtime: Optional[HarnessRuntime] = None
    try:
        runtime = HarnessRuntime(project_root, permission_mode=permission_mode)
        await runtime.start_session("exec")
        control = await runtime.handle_control(prompt)
        if control is not None:
            run_id = f"control_{uuid.uuid4().hex[:16]}"
            output.print(json.dumps({
                "protocol": "casper.events/v1",
                "type": "control.completed",
                "run_id": run_id,
                "observation": control.to_dict(),
            }, sort_keys=True), soft_wrap=True)
            result = RunResult(
                run_id=run_id,
                status=(
                    RunStatus.FAILED
                    if control.status == ObservationStatus.ERROR
                    else RunStatus.COMPLETE
                ),
                text=control.summary,
                artifacts=tuple(control.artifacts),
                error=control.root_cause_hint,
            )
        else:
            result = await runtime.run(prompt)
        for event in runtime.events:
            output.print(
                json.dumps({"protocol": "casper.events/v1", **event.to_dict()}, sort_keys=True),
                soft_wrap=True,
            )
        output.print(
            json.dumps({"protocol": "casper.events/v1", "type": "result", **result.to_dict()}, sort_keys=True),
            soft_wrap=True,
        )
    except (TypeError, ValueError) as exc:
        output.print(json.dumps({
            "protocol": "casper.events/v1", "type": "result", "status": "invalid_input",
            "summary": str(exc), "artifacts": [], "usage": {},
        }, sort_keys=True), soft_wrap=True)
        return 64
    except Exception as exc:
        output.print(json.dumps({
            "protocol": "casper.events/v1", "type": "result", "status": "failed",
            "summary": str(exc), "artifacts": [], "usage": {},
        }, sort_keys=True), soft_wrap=True)
        return 1
    finally:
        if runtime is not None:
            await runtime.end_session("exec_complete")
    return {
        RunStatus.COMPLETE: 0,
        RunStatus.AWAITING_APPROVAL: 2,
        RunStatus.BLOCKED: 3,
        RunStatus.FAILED: 1,
    }.get(result.status, 1)
