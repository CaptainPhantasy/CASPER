# CASPER First-Class Coding Harness Blueprint

Status: implementation contract
Reference date: 2026-07-15
Reference products: Codex CLI, Claude Code, Gemini CLI

## Product direction

CASPER will be a modern coding harness with its own terminal identity. The existing
CASPER ASCII logo is a compatibility surface and must remain recognizable. The
migration replaces fragmented execution internals; it does not turn CASPER into a
generic clone or measure maturity by command count.

The canonical architecture is:

```text
interactive TUI       casper exec       future API/MCP clients
       \                  |                     /
        +--------- versioned event stream -----+
                           |
                    HarnessRuntime
              planning <-> typed tool loop
                           |
        registry -> hooks -> policy -> workspace transaction
                           |
              verification -> bounded recovery
                           |
          durable runs/checkpoints + context + telemetry
```

One runtime owns natural language, slash commands, tools, permissions, sessions,
and evidence. The TUI is a client of the runtime. It is not an alternate executor.

## Why the existing default path is quarantined

The repository currently has several independent command and intent stacks. The
no-argument launcher enters `casper_terminal_complete.py`, whose natural-language
path generates text and then keyword-matches an intent. The newer typed command
dispatcher and pipeline are not the default user path. That makes help output,
permissions, verification, and actual execution disagree.

The following modules are legacy compatibility code and must receive no new
features:

- `casper_terminal_complete.py`
- `core/services/slash_commands.py`
- `core/reasoning/react_engine.py`
- `core/commands/react_engine.py`
- `core/ai/command_interpreter.py`
- `core/ai/enhanced_command_interpreter.py`
- `core/terminal/nlp/intent_parser.py`
- `core/terminal/integration/adapters.py`
- `core/terminal/ui/terminal.py`

Useful handlers are ported behind the canonical registry before those files are
removed. `--legacy` is the only acceptable route to the old complete terminal
during the migration window.

## Top-three reference matrix

| Capability | Codex CLI pattern | Claude Code pattern | Gemini CLI pattern | CASPER contract |
|---|---|---|---|---|
| Agent loop | Typed turn/item events and tool execution | Stable built-in tool names | Schema-driven core tool loop | One typed registry and observation envelope |
| Safety | Sandboxes plus approval policy | Hooks, deny/ask/allow rules, permission modes | Tool policies, trusted folders, sandbox | Every action crosses one policy gate |
| Recovery | Durable thread resume and fork | Code/conversation checkpoints | Shadow-Git checkpoint before edits | Transaction plus conversation/tool-call checkpoint |
| Context | Instructions, skills, subagent isolation | Nested rules and progressive skills | Hierarchical memory and compression | Scoped instructions, lazy skills, budgeted context |
| Automation | JSONL and schema output | JSON/stream JSON and schema output | Structured headless output | Same event stream for TUI and `exec` |
| Extensibility | MCP, skills, agents | MCP, hooks, agents, plugins, LSP | Extensions containing MCP/context/commands | One namespaced extension kernel |
| Operations | Turn events and token usage | Lifecycle hooks and transcripts | OpenTelemetry metrics and traces | Events plus completion-quality evaluation |

Primary references:

- [Codex app-server protocol](https://github.com/openai/codex/blob/main/codex-rs/app-server/README.md)
- [Codex configuration schema](https://github.com/openai/codex/blob/main/codex-rs/core/config.schema.json)
- [Claude Code hooks](https://code.claude.com/docs/en/hooks)
- [Claude Code permissions](https://code.claude.com/docs/en/permissions)
- [Gemini CLI checkpointing](https://google-gemini.github.io/gemini-cli/docs/cli/checkpointing.html)
- [Gemini CLI extensions](https://google-gemini.github.io/gemini-cli/docs/extensions/)

## The ten engines, ranked by delivery order

| # | Engine | Required behavior | Acceptance evidence |
|---:|---|---|---|
| 1 | Typed tool and observation kernel | JSON-Schema inputs, narrow tools, risk, timeout, cancellation, deterministic observations | Registry rejects duplicates; every result validates |
| 2 | Verification and bounded recovery | Targeted checks after mutation, retry budget, explicit root cause/retry/stop | Scripted retry and non-retryable tests |
| 3 | Policy and sandbox | Allow/ask/deny by tool, arguments, path, network, and workspace trust | Escape, symlink, destructive command, and unapproved-write tests |
| 4 | Context intelligence | Instructions, file/symbol ranking, ignores, token budget, phase compaction | Recall, exclusion, and budget tests |
| 5 | Transactional checkpointing | Preimage hashes, atomic writes, snapshots, inspect/restore/fork | File plus run state restore tests |
| 6 | Durable run/goal/session store | Append-only events, state machine, budgets, resume/fork, evidence hashes | Crash-tail recovery and no-replay tests |
| 7 | Event bus and headless protocol | Versioned session/turn/tool/edit/approval/usage/failure JSONL | Every line parses; stable final event and exit code |
| 8 | Telemetry, evaluation, and budgets | Completion, retries, pass@1/pass@3, latency, token/cost per success | Versioned benchmark artifact |
| 9 | Bounded agent/worktree scheduler | Dependency DAG, bounded concurrency, read-only explorers, isolated writers | Ordering, isolation, conflict, cancellation tests |
| 10 | Unified extension kernel | Namespaced skills, MCP, hooks, agents and plugin lifecycle | Discovery, collision, timeout and reload tests |

## Non-negotiable quality gates

1. Ordinary language and `/task` converge on the same runtime and verifier.
2. A denied policy decision cannot mutate the workspace.
3. Success cannot be produced from `TODO`, `pass`, `assert True`, or user-asserted
   evidence alone.
4. A completed tool event is durable before a model continuation, so resume cannot
   repeat the side effect.
5. The installed `casper` executable must identify this checkout/version in an
   acceptance test.
6. TUI help, completion, headless schemas, and model tools are projections of one
   registry.
7. Private chain-of-thought is never rendered; the event stream shows plans,
   actions, observations, and evidence.
8. The CASPER ASCII logo remains recognizable and is covered by a snapshot test.

## Enterprise critic rubric

Each delivery cycle is scored from 0 to 10 on correctness, architectural
coherence, safety, recovery, observability, test realism, documentation, operator
experience, compatibility, and maintainability. A cycle is accepted only when no
critical item is below 8, all deterministic gates pass, and two consecutive critic
cycles improve by less than three percent.
