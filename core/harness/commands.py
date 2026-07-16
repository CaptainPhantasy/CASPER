"""Canonical slash-command catalog for CASPER's typed harness.

The catalog is deliberately renderer-neutral.  Interactive clients, command
palettes, and help output all project the same command surface instead of
maintaining separate lists that drift over time.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class HarnessCommandSpec:
    name: str
    usage: str
    description: str
    category: str
    agentic: bool = False
    aliases: tuple[str, ...] = ()


HARNESS_COMMANDS: tuple[HarnessCommandSpec, ...] = (
    HarnessCommandSpec("help", "/help [query]", "Show or filter canonical commands", "session"),
    HarnessCommandSpec("commands", "/commands [query]", "Search the command palette", "session"),
    HarnessCommandSpec("status", "/status", "Show repository, provider, and policy status", "session"),
    HarnessCommandSpec("doctor", "/doctor", "Run actionable local harness diagnostics", "session"),
    HarnessCommandSpec("context", "/context [query]", "Inspect the bounded repository context pack", "session"),
    HarnessCommandSpec("diff", "/diff [--stat|--cached] [-- PATH]", "Show a bounded project Git diff", "code"),
    HarnessCommandSpec("review", "/review [PATH]", "Run a fast evidence-gated review", "code", True),
    HarnessCommandSpec(
        "code-review", "/code-review [low|medium|high] [PATH]",
        "Run the deterministic five-lens review sentinel", "code", True,
    ),
    HarnessCommandSpec(
        "security-review", "/security-review [PATH]",
        "Review pending changes for reachable security defects", "code", True,
    ),
    HarnessCommandSpec("plan", "/plan REQUEST", "Plan a change without mutating files", "workflow", True),
    HarnessCommandSpec("task", "/task REQUEST", "Run a bounded coding task", "workflow", True),
    HarnessCommandSpec("verify", "/verify [REQUEST]", "Prove a change using direct runtime evidence", "workflow", True),
    HarnessCommandSpec(
        "goal", "/goal [status|prove TEXT|verify pass|fail TEXT|complete|block TEXT|clear|OBJECTIVE]",
        "Manage an evidence-gated persistent goal", "workflow",
    ),
    HarnessCommandSpec("tools", "/tools", "List active typed tools and risk levels", "capabilities"),
    HarnessCommandSpec("runs", "/runs", "List durable harness runs", "session"),
    HarnessCommandSpec("resume", "/resume [RUN_ID]", "Inspect a resumable durable run", "session", aliases=("continue",)),
    HarnessCommandSpec(
        "rewind", "/rewind [list|undo CHANGE_ID]", "Inspect or reverse a transactional change",
        "session", aliases=("changes",),
    ),
    HarnessCommandSpec(
        "permissions", "/permissions [set MODE]", "Inspect or set the enforced permission mode",
        "capabilities", aliases=("allowed-tools",),
    ),
    HarnessCommandSpec("model", "/model", "Show the active provider and execution mode", "capabilities"),
    HarnessCommandSpec("skills", "/skills [query]", "Discover project and shared Agent Skills", "capabilities"),
    HarnessCommandSpec("mcp", "/mcp", "Show registered MCP server definitions", "capabilities"),
    HarnessCommandSpec("agents", "/agents", "Show registered agent profiles", "capabilities"),
    HarnessCommandSpec("tasks", "/tasks", "Show supervised background jobs", "capabilities"),
    HarnessCommandSpec("hooks", "/hooks", "Show lifecycle hook registrations", "capabilities"),
    HarnessCommandSpec("usage", "/usage", "Show measured local run token usage", "session", aliases=("cost", "stats")),
    HarnessCommandSpec("features", "/features", "Show all verified harness engine groups", "capabilities"),
    HarnessCommandSpec("quit", "/quit", "Leave CASPER", "session", aliases=("exit",)),
)


def command_index() -> dict[str, HarnessCommandSpec]:
    """Return canonical and alias names mapped to one immutable specification."""
    result: dict[str, HarnessCommandSpec] = {}
    for spec in HARNESS_COMMANDS:
        for name in (spec.name, *spec.aliases):
            if name in result:
                raise ValueError(f"duplicate harness command: {name}")
            result[name] = spec
    return result


def command_palette(query: str = "") -> tuple[HarnessCommandSpec, ...]:
    """Filter commands deterministically by name, usage, category, or description."""
    terms = tuple(part.casefold() for part in query.split() if part)
    matches: list[HarnessCommandSpec] = []
    for spec in HARNESS_COMMANDS:
        haystack = " ".join((spec.name, spec.usage, spec.category, spec.description)).casefold()
        if all(term in haystack for term in terms):
            matches.append(spec)
    return tuple(matches)
