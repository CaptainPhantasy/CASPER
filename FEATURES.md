# CASPER Features

This document describes verified feature boundaries in the current checkout. It
does not count dormant modules or mock-only behavior as a product capability.

## Cycle 1: canonical coding harness

| # | Engine | Implemented behavior | Current boundary |
|---:|---|---|---|
| 1 | Canonical runtime | One bounded `HarnessRuntime` owns model turns, tools, policy, events, and persistence | Legacy terminals remain available only for migration |
| 2 | Native tool-calling providers | OpenAI and Anthropic adapters normalize tool calls, results, usage, and stop reasons | Text-only provider is clearly reported as degraded chat mode |
| 3 | Typed tool kernel | JSON-Schema inputs, duplicate protection, timeouts, and deterministic success/warning/error observations | Built-in surface is intentionally narrow |
| 4 | Central policy gate | Read-only, default, accept-edits, and bypass profiles; approval is scoped to one call ID | This is policy enforcement, not an OS-level sandbox |
| 5 | Transactional workspace | Project containment, exact patch anchors, preimage hashes, atomic replacement, durable ledger, safe undo | Generic commands use a restricted verification profile |
| 6 | Repository context | Git-aware file/symbol index, scoped instruction discovery, relevance selection, token budget, compaction | Full Tree-sitter/LSP dependency graph is a later enhancement |
| 7 | Durable runs/checkpoints | SQLite WAL store for run state, ordered events, checkpoints, resume, and approval continuation | Conversation fork UI is not yet exposed |
| 8 | Versioned event/headless protocol | `casper exec` emits `casper.events/v1` JSONL and meaningful exit codes | Streaming is turn-buffered in the current terminal client |
| 9 | Evidence and evaluation | Tool observations carry artifacts and errors; evaluator reports completion, retry, pass@1/pass@3, latency, tokens, and cost/success | Quality still depends on the configured model and project verifier |
| 10 | Modern terminal client | Natural language and `/task` share the runtime; one canonical catalog projects 27 typed commands into help, completion, and dispatch | The older multipane TUI is not the canonical executor |

## Cycle 2: extensions and orchestration

| # | Engine | Implemented behavior |
|---:|---|---|
| 11 | Lifecycle hooks | Ordered, timeout-bounded sync/async lifecycle handlers with visible failures |
| 12 | Extension registry | Namespaced, versioned capability registration without parallel plugin registries |
| 13 | Skill discovery | Deterministic `SKILL.md` metadata discovery with duplicate reporting |
| 14 | MCP registry | Validated stdio/HTTP server definitions, enable controls, and secret-safe rendering |
| 15 | Agent profiles | Explicit prompts, models, allowed tools, permission mode, and step bounds |
| 16 | Task DAG scheduler | Dependency validation, bounded concurrency, failure blocking, and structured results |
| 17 | Cancellation | Parent/child cooperative cancellation with stable operator reasons |
| 18 | Background jobs | Bounded submission, state tracking, results, errors, waiting, and cancellation |
| 19 | Health diagnostics | Concurrent timeout-bounded checks aggregated as healthy/degraded/unhealthy |
| 20 | Worktree leases | Deterministic worktree plans plus exclusive, expiring writer leases |

## Cycle 3: developer intelligence

| # | Engine | Implemented behavior |
|---:|---|---|
| 21 | Symbol index | Qualified Python and JavaScript/TypeScript symbol discovery |
| 22 | Dependency graph | Relative import resolution plus transitive dependencies and dependents |
| 23 | Repository search | Deterministic phrase, identifier, path, and token ranking |
| 24 | Diagnostic parser | Normalized Ruff, mypy, and TypeScript compiler diagnostics |
| 25 | Test selector | Targeted tests chosen from filename, symbol, and import evidence |
| 26 | Change impact | Reverse dependencies, affected tests, and change-risk classification |
| 27 | Plan tracker | Dependency-aware durable steps that cannot complete without passing proof |
| 28 | JSON Schema validator | Dependency-free nested structured-output validation and useful issues |
| 29 | Prompt library | Versioned, checksummed templates with strict variable validation |
| 30 | File watcher | Portable create/modify/delete detection based on content hashes |

## Cycle 4: safety and operations

| # | Engine | Implemented behavior |
|---:|---|---|
| 31 | Secret redaction | Nested-field and token-pattern redaction without erasing safe values |
| 32 | Command risk | Parsed chained-command classification for destructive and remote-code patterns |
| 33 | Resource budgets | Atomic step, tool, token, cost, and elapsed-time enforcement |
| 34 | Circuit breaker | Closed/open/half-open failure isolation with one bounded recovery probe |
| 35 | Retry policy | Error-aware bounded exponential backoff for transient failures only |
| 36 | Audit chain | Canonical SHA-256 event chaining with tamper and discontinuity detection |
| 37 | Artifact registry | Contained, content-addressed artifacts with metadata and mutation verification |
| 38 | Telemetry | Success/error spans, durations, counters, observations, and snapshots |
| 39 | Layered config | Deep defaults-to-CLI resolution with dotted provenance |
| 40 | Workspace trust | Fail-closed exact/inherited trust profiles with atomic persistence |

## Cycle 5: terminal interaction and portability

| # | Engine | Implemented behavior |
|---:|---|---|
| 41 | Slash commands | Twenty-seven Claude Code-aligned commands share one catalog, strict shell-free parsing, aliases, help filtering, and real runtime handlers |
| 42 | Natural-language routing | Transparent intent scoring with an explicit unknown threshold |
| 43 | Command palette | Deterministic fuzzy search across commands, tools, and actions |
| 44 | Session branching | Isolated conversation forks without shared mutable message state |
| 45 | Diff preview | Unified diffs with exact addition/deletion statistics |
| 46 | Conflict detection | Preimage fingerprints prevent applying edits over concurrent changes |
| 47 | Model routing | Lowest-cost model selection by required capabilities and context size |
| 48 | Content cache | Bounded TTL/LRU cache with stable content-addressed keys |
| 49 | Session bundles | Validated versioned JSON export/import for portable sessions |
| 50 | Onboarding doctor | Actionable project, permission, and executable readiness checks |

## Terminal identity

The nine-line CASPER ASCII mark is intentionally preserved. A snapshot test locks
its bytes and geometry, and rendering uses soft wrapping so captured or narrow
terminal output does not reshape it.

## Canonical agentic commands

Run `/commands` for the complete live catalog or filter it, for example
`/commands review`. The default terminal now exposes the standard coding-harness
workflow directly: `/status`, `/doctor`, `/context`, `/diff`, `/review`,
`/code-review`, `/security-review`, `/goal`, `/plan`, `/task`, `/verify`,
`/permissions`, `/runs`, `/resume`, `/rewind`, `/skills`, `/mcp`, `/agents`,
`/tasks`, `/hooks`, and `/usage`.

`/review` is the fast high-signal path. `/code-review [low|medium|high] [PATH]`
uses the five-lens sentinel. `/security-review [PATH]` suppresses non-security
findings. Review input is project-contained, size-bounded, includes eligible
untracked files, and is secret-redacted before provider submission. Model output
is accepted only after deterministic JSON, confidence, reachability, evidence,
file-scope, severity, and fix-tier validation; malformed output receives one
bounded correction attempt and then fails closed.

## Unified fifty-engine verification

Run the complete lightweight harness gate with:

```bash
python scripts/e2e_harness_50.py
```

The script uses one temporary workspace and no network or pytest dependency. It
prints exactly fifty numbered feature results plus one JSON summary, and exits
`0` only when all fifty engines pass. This same command is required by harness CI.

Use `casper --features` for the complete terminal-readable catalog or `/features`
inside the canonical interactive client.

## Safety boundary

CASPER contains repo-relative paths, honors user-supplied absolute local paths,
enforces exact-call approval, and restricts verification commands to argv execution
(shells may run reviewed script files, never inline expressions). It does **not** yet
provide an OS-backed Seatbelt/container sandbox. `bypass` means bypassing non-critical
policy prompts; it must not be described as a security sandbox.

## Quarantined compatibility surfaces

`casper_terminal_complete.py`, the legacy slash registry, regex ReAct engines, and
keyword intent classifiers remain in the repository for migration compatibility.
They are not the architecture for new feature work. Use `casper --legacy` only when
a handler has not yet been ported.

## Next maturity gates

- OS-backed process sandbox profiles
- Shadow-Git whole-workspace checkpoints for command-side mutations
- Wire extension registries to real supervised MCP/plugin processes
- Tree-sitter/LSP adapters behind the new symbol/dependency contracts
- Live event rendering and process-group cancellation in the terminal client
