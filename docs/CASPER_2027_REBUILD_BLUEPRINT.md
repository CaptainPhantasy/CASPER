# CASPER 2027 Rebuild Blueprint

This document is the implementation blueprint for recreating CASPER as a low-friction,
evidence-gated coding harness. It is derived from the live CASPER repository, the
installed Kimi CLI 1.48.0 package, Kimi's public hook documentation, and Claude Code's
public hook contracts. Donor behavior is translated into CASPER-native contracts; donor
source is not copied.

Primary references:

- Kimi CLI repository: <https://github.com/MoonshotAI/kimi-cli>
- Kimi hook documentation: <https://moonshotai.github.io/kimi-cli/en/customization/hooks.html>
- Claude Code hook reference: <https://code.claude.com/docs/en/hooks>
- Claude Code hook guide: <https://code.claude.com/docs/en/hooks-guide>

## 1. Platform overview

CASPER is a local-first coding harness with one canonical runtime shared by its
interactive terminal and headless JSONL interface. The runtime owns model selection,
conversation context, filesystem tools, command execution, permissions, approvals,
lifecycle hooks, skill discovery, durable run state, verification gates, and exports.

The active project is the default context root, not a filesystem sandbox. Explicit
absolute paths supplied by the operator are valid local targets. Policy gates control
mutation risk; misleading synthetic claims about unavailable paths are forbidden.

The terminal must make simple actions simple. Deterministic controls such as help,
configuration, directory creation, history, export, and working-directory changes do
not consume model tokens. Agentic work uses the same typed tools and policy engine in
interactive and headless modes.

## 2. Feature catalog

| Capability | User contract | CASPER implementation |
|---|---|---|
| Conversational follow-ups | Corrections and references survive the next turn | Bounded, project-scoped `conversation.json` context with `/new` reset |
| Persistent input history | Up/down recall and `/history` search survive restart | prompt-toolkit `FileHistory` under the CASPER TUI state root |
| Command completion | Tab completes canonical commands and aliases | Fuzzy completion projected from `HARNESS_COMMANDS` |
| Multiline/editor input | Alt-Enter inserts a line; Ctrl-O opens `$VISUAL`/`$EDITOR` | prompt-toolkit key bindings |
| Working feedback | Long model calls do not look frozen | Rich status spinner around each run |
| Provider failover visibility | Failover is visible and names the failed/active adapters | Provider-chain failure delta shown after the run |
| Explicit file context | `@path` includes a bounded local text file | Up to five files and 16,000 characters each, recorded as context events |
| Absolute local paths | `/Volumes/...` and explicit paths work outside the launch repo | Runtime workspace allows explicit local paths; shorthand `Volumes/...` is normalized |
| Working-directory switch | Change project without restarting | `/workdir PATH` and `/cd PATH`; startup `--workdir/-C` |
| Deterministic mkdir | A simple directory request does not launch an agent workflow | Natural-language fast path and `/mkdir PATH`, followed by `is_dir()` proof |
| Shared skills | Project, user, and skillsdump libraries are searched automatically | Ordered discovery across `.casper`, `.claude`, `~/.codex`, `~/.agents`, and skillsdump |
| In-TUI setup | Provider setup does not become an LLM prompt | `/setup` and `casper setup` invoke the setup service and hot-reload providers |
| Configuration view | Show effective config without exposing credentials | `/config` returns provider, mode, roots, and configured provider names only |
| Human-readable controls | Slash commands render as terminal output, not raw API JSON | Rich panels and bounded key/value rendering |
| Durable runs | Every agentic turn has state, events, usage, and artifacts | SQLite `RunStore` |
| Export | Session evidence can be exported without a model | `/export [json|markdown] [PATH]` with secret redaction |
| Rewind | Transactional text patches can be reversed safely | Hash-guarded workspace ledger and `/rewind` |
| Plan mode | Analyze without product mutations | `/plan`, compiled into a read-only model contract |
| Permission modes | Read-only, default, accept-edits, and bypass are explicit | One `PolicyEngine`; interactive default is accept-edits |
| Low-friction verification | Tests and read-only checks do not ask for approval | Call-shape classification for pytest, lint, Git inspection, and JSON validation |
| Destructive safety | Elevated or unclassified mutations remain gated | Exact-call approval or denial by mode |
| Lifecycle hooks | Automation and policy run at actual lifecycle points | Config-loaded, matcher-filtered, timeout-bounded command/Python hooks |
| Hook observability | Operators can see sources, commands, failures, and recent results | `/hooks` exposes registrations, warnings, and bounded history |
| Hook containment | Broken hooks do not crash CASPER | Non-blocking failures fail open; exit 2 and structured deny block applicable actions |
| Clean cancellation | Ctrl-C cancels input/run without a traceback | TUI catches interrupts and returns to the prompt; session-end hooks run on exit |
| Headless automation | CI can consume stable machine output | `casper exec` JSONL `casper.events/v1` protocol |

High-value donor capabilities retained for later isolated slices are background tool
execution with live attach, session forks, side questions, image paste/vision, ACP/IDE
transport, and a browser UI. They must reuse the canonical runtime rather than introduce
another command or policy stack.

## 3. Domain model and data schema

### Runtime entities

- `HarnessRuntime`: active project, state root, provider chain, tool registry, policy,
  hook engine, conversation context, run store, and deterministic commands.
- `RunState`: `run_id`, objective, status, step, messages, pending calls, artifacts,
  measured usage, final text/error, and timestamps.
- `RunEvent`: append-only `(run_id, sequence, type, payload, created_at)` evidence.
- `ToolSpec`: name, description, JSON input schema, mutation flag, risk, timeout, and
  capability labels.
- `ToolCall`: stable call ID, tool name, and structured arguments.
- `ToolObservation`: status, summary, data, artifacts, direct retry/stop guidance,
  elapsed time, and call ID.
- `PolicyDecision`: allow, exact-call approval, or deny with reason/consequence.
- `HookRegistration`: event, matcher, source, priority, timeout, and Python handler or
  argv command.
- `HookExecution`: action, duration, exit code, bounded stdout/stderr, and additional
  context flag.
- `SkillMetadata`: name, description, version, tags, and canonical `SKILL.md` path.

### Persistent storage

`runs.sqlite3` stores runs, ordered events, and checkpoints. `conversation.json` stores
at most 40 user/assistant messages and uses mode 0600. Workspace backups and the patch
ledger live below the project-keyed harness state root. TUI history and exports live
below `XDG_STATE_HOME/casper` or the configured override.

No provider secrets are stored in run/event/export payloads. Provider names may be
shown; keys remain in the encrypted per-user configuration service.

## 4. API surface and contracts

### CLI

- `casper [--permission-mode MODE] [--workdir PATH]`: interactive TUI.
- `casper exec REQUEST --project PATH --permission-mode MODE`: one JSONL run.
- `casper setup`: provider configuration.
- `casper init --project PATH`: initialize project-local CASPER metadata.

Plain `help`, `commands`, `status`, `setup`, and other exact canonical command names are
normalized before model routing. `casper COMMAND` and `casper: COMMAND` are accepted
inside the TUI.

### Typed tools

- `read_file(path)`: bounded UTF-8 read of a repo-relative or absolute local file.
- `list_files(path, limit)`: bounded directory listing.
- `patch_file(path, old_text, new_text, expected_sha256)`: exact transactional patch.
- `make_directory(path, parents)`: idempotent local directory creation.
- `run_command(argv, timeout_seconds, cwd)`: argv-only development process; inline
  shells, privilege tools, destructive utilities, and network clients remain denied.
- `search_repository(query, limit)`: tracked-file and symbol selection.

### Hook configuration

CASPER loads existing files in this order:

1. `$CASPER_HOOKS_FILE`
2. `~/.casper/hooks.json`
3. `<project>/.casper/hooks.json`
4. `<project>/.casper/config/hooks.json`
5. `<project>/.casper/hooks.local.json`

The configuration follows the familiar event → matcher group → handler form:

```json
{
  "hooks": {
    "PreToolUse": [
      {
        "matcher": "patch_file|run_command",
        "hooks": [
          {
            "type": "command",
            "name": "local-policy",
            "command": ["python3", ".casper/hooks/local_policy.py"],
            "timeout": 10,
            "priority": 50
          }
        ]
      }
    ]
  }
}
```

Supported external names map to CASPER events: `SessionStart`, `SessionEnd`,
`UserPromptSubmit`, `RunStart`, `BeforeModel`, `AfterModel`, `PreToolUse`,
`PostToolUse`, `PostToolUseFailure`, `Stop`, and `StopFailure`.

Command hooks receive JSON on stdin containing `hook_event_name`, `session_id`, `cwd`,
and event fields such as `tool_name`, `tool_input`, and `tool_call_id`. Exit 0 allows.
Exit 2 blocks prompts or tools where blocking is meaningful. Other non-zero exits and
timeouts are recorded and fail open. Exit-0 JSON can return `decision: "block"`,
`additionalContext`, or Claude-compatible `hookSpecificOutput` fields.

Commands are argv arrays or safely tokenized strings and do not receive implicit shell
expansion. Projects that need pipes or shell syntax must point to a reviewed script.

## 5. CSS and styling system blueprint

The terminal uses Rich semantic styles rather than hard-coded ANSI sequences:

- primary: `bright_cyan` for CASPER identity and interactive affordances;
- success: green;
- warning/approval/blocked: yellow;
- error/failed: red;
- metadata: dim neutral text.

All structured controls render through `render_observation`; agentic outcomes render
through `render_result`. Color is supplementary: status words, summaries, and direct
next actions remain readable when color is disabled.

The dashboard uses its existing Tailwind/Vite stack. It must project the same statuses,
commands, tools, hook events, and permission modes from canonical schemas. It must not
maintain a second feature list or invent command availability.

## 6. UI and screen inventory

### Interactive terminal

- startup identity: product name, active project, permission mode, provider warning;
- input line: persistent history, fuzzy completion, auto-suggestion, multiline/editor
  shortcuts, working directory and mode toolbar;
- working state: visible spinner while provider/runtime work is active;
- approval view: exact tool call plus approve/reject vocabulary;
- result view: status panel, run ID, steps, measured usage, and artifacts;
- deterministic control view: summary panel, bounded fields, cause, and next action;
- `/help`: canonical command table;
- `/tools`: typed tool/risk table;
- `/hooks`: hook source/matcher/type plus recent execution diagnostics;
- `/config`: effective provider/policy/path/skill configuration;
- `/runs` and `/resume`: durable recovery surfaces.

### Headless interface

No banner, animation, prompt, or terminal color. Emit ordered JSONL events followed by
one result object and a meaningful process exit code.

### Dashboard and future web UI

Required screens: session list, live run timeline, pending approvals, diff/artifacts,
hook diagnostics, provider/config health, skill/tool inventory, background tasks, and
usage. The browser UI must consume the canonical runtime API and event schema.

## 7. Workflows, automations, and background jobs

### Coding turn

1. Normalize deterministic terminal input.
2. Fire `UserPromptSubmit`; stop if a hook blocks.
3. Build repository, conversation, session-hook, and explicit-`@file` context.
4. Fire `RunStart`, then `BeforeModel`/`AfterModel` around each provider turn.
5. Apply policy and `PreToolUse` before each tool.
6. Record the observation before another model turn.
7. Fire `PostToolUse` or `PostToolUseFailure`.
8. Require a successful verification after workspace mutation.
9. Fire `Stop` or `StopFailure`, persist the conversation, and render proof.

### Provider failover

Try configured native tool providers in preference order. Stick to the first healthy
provider. Record failure details, surface that failover happened, and never silently
degrade a tool-executing request into a text-only claim.

### Background work

The existing `BackgroundJobSupervisor` is the single future integration point. A later
slice may add Kimi-style detach/list/attach/kill, but jobs must preserve run IDs, emit
events, survive TUI redraws, reconcile stale workers on startup, and stop cleanly unless
the operator explicitly chooses keep-alive behavior.

## 8. Security, permissions, and multi-tenancy model

CASPER is single-user and project-scoped, not a SaaS tenant server. Isolation is by OS
user, project-keyed state root, file modes, and explicit permission mode.

- `read_only`: no product mutation; bounded verification call shapes are allowed.
- `default`: low-risk reads/checks proceed; mutations request exact approval.
- `accept_edits`: local reversible moderate changes proceed; high/critical actions do
  not receive blanket approval.
- `bypass`: non-critical actions proceed; critical actions still require approval.

Absolute filesystem access is not the same as mutation permission. The user may place
an external path in scope, but patches and commands still cross policy and hooks.

Hook security rules:

- only configured local command hooks execute;
- commands are argv-based, receive JSON on stdin, and have bounded timeouts/output;
- hook failures are observable and non-blocking unless the hook explicitly exits 2 or
  returns a deny decision;
- secrets are redacted from exported observations;
- `/hooks` shows provenance so a surprising decision can be traced to its config file.

## 9. Infrastructure and configuration notes

- Python 3.11+; Poetry packaging; `casper = core.cli:main`.
- prompt-toolkit owns interactive input; Rich owns output rendering.
- SQLite owns durable runs/events/checkpoints.
- provider adapters normalize OpenAI, Anthropic, Gemini, and compatibility responses
  into `ModelTurn`.
- project state: `.casper`; user secrets/config: `~/.casper`; durable runtime state:
  `XDG_STATE_HOME/casper`.
- CI must run Python unit/integration tests, terminal contract tests, dashboard lint/test/
  build, E2E where browsers are available, security scans, ASCII identity verification,
  packaging checks, and a clean editable-install smoke test.

The command catalog, tool registry, and event schema are single sources of truth. Help,
dashboard affordances, docs, and tests project these registries rather than duplicating
manual counts.

## 10. Ready-to-use recreation prompt for an automated builder

Rebuild CASPER as a local-first coding harness with one canonical runtime shared by an
interactive prompt-toolkit/Rich TUI and a headless JSONL interface. Use Python 3.11+,
SQLite for durable runs/events/checkpoints, and typed provider-neutral model/tool
contracts. Implement persistent bounded conversation continuity, explicit `@file`
context, project switching, shared skill discovery, provider setup and failover,
transactional patches, directory creation, bounded command execution with selectable
working directory, evidence-required completion, and exact-call approvals.

Implement configurable lifecycle hooks loaded from user/project JSON. Support session,
prompt, model, pre/post-tool, tool-failure, and stop events; regex matchers; ordered
priorities; argv command handlers; JSON stdin; bounded timeout/output; exit-2 and
structured deny blocking; additional context; fail-open diagnostics; and `/hooks`
provenance/history. Wire every event into the real runtime rather than only exposing a
registry.

The interactive UI must provide persistent history, fuzzy slash completion, history
auto-suggestions, Alt-Enter multiline input, Ctrl-O external editor, Ctrl-C cancellation,
visible working feedback, human-readable control output, deterministic local handling
for help/setup/config/export/workdir/mkdir, and explicit provider-failover notices. Keep
destructive operations gated while making tests, lint, Git inspection, and JSON checks
approval-free. Treat the active project as the context anchor, not a fabricated
filesystem sandbox; honor operator-supplied absolute paths.

Verify the application itself through focused unit tests, full Python tests, clean
installation, dashboard lint/test/build, E2E where available, security checks, and an
installed `casper` round trip. Do not claim completion from code shape alone. Preserve
the existing CASPER ASCII asset byte-for-byte.
