"""Interactive and headless clients for the canonical CASPER harness runtime."""

from __future__ import annotations

import json
import shlex
from pathlib import Path
from typing import Optional

from rich.console import Console
from rich.panel import Panel
from rich.prompt import Confirm, Prompt
from rich.table import Table
from rich.text import Text

from core.harness import HarnessRuntime, PermissionMode, RunResult, RunStatus
from core.harness.catalog import FEATURE_GROUPS, feature_count
from core.harness.commands import HARNESS_COMMANDS, command_index, command_palette


CONTROL_HELP: tuple[tuple[str, str], ...] = tuple(
    (spec.usage, spec.description) for spec in HARNESS_COMMANDS
)


def _status_style(status: str) -> str:
    return {
        "complete": "green",
        "awaiting_approval": "yellow",
        "blocked": "yellow",
        "failed": "red",
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
        if not Confirm.ask("Approve this exact tool call?", default=False, console=console):
            return result
        result = await runtime.resume(result.run_id, approved_call_ids=[call.id])
    return result


async def run_interactive(
    project_root: Path | str = ".",
    *,
    permission_mode: PermissionMode | str = PermissionMode.DEFAULT,
    console: Optional[Console] = None,
) -> int:
    """Run CASPER's preserved-brand conversational TUI client."""
    console = console or Console()
    runtime = HarnessRuntime(project_root, permission_mode=permission_mode)
    console.print(
        "[bold bright_cyan]CASPER coding harness[/bold bright_cyan] "
        f"[dim]· {runtime.project_root} · {runtime.policy.mode.value}[/dim]"
    )
    if runtime.degraded_mode:
        console.print(
            "[yellow]Chat-only provider fallback is active; configure Anthropic or "
            "OpenAI for native tool execution.[/yellow]"
        )
    console.print("[dim]Describe work naturally, or type /help. Ctrl-C cancels input; /quit exits.[/dim]")
    while True:
        try:
            value = Prompt.ask("[bold bright_cyan]casper[/bold bright_cyan]", console=console).strip()
        except (EOFError, KeyboardInterrupt):
            console.print()
            return 0
        if not value:
            continue
        if value.casefold() in {"/quit", "/exit", "quit", "exit"}:
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
        control = await runtime.handle_control(value)
        if control is not None:
            console.print(control.render())
            continue
        try:
            prompt = _agentic_prompt(value)
            result = await runtime.run(prompt)
            result = await _resolve_approvals(console, runtime, result)
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
    try:
        runtime = HarnessRuntime(project_root, permission_mode=permission_mode)
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
    return {
        RunStatus.COMPLETE: 0,
        RunStatus.AWAITING_APPROVAL: 2,
        RunStatus.BLOCKED: 3,
        RunStatus.FAILED: 1,
    }.get(result.status, 1)
