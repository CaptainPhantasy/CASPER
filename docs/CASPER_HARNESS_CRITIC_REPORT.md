# CASPER Harness Critic Report

Date: 2026-07-15
Scope: canonical coding-harness migration
Decision: accepted as a beta foundation, not declared production-ready

## Cycle history

| Cycle | Score | Improvement | Harshest finding | Result |
|---:|---:|---:|---|---|
| 0 | 4.1/10 | baseline | Users launched a keyword-routed legacy terminal; CI selected no tests | Migration required |
| 1 | 8.4/10 | +104.9% | Generic command execution was under-classified; default provider could be chat-only | Command became high-risk/restricted; native providers added |
| 2 | 8.9/10 | +6.0% | Model text could claim completion after an unverified mutation; narrow output wrapped JSONL | Bounded verification recovery and soft-wrapped JSONL added |
| 3 | 9.1/10 | +2.2% | Active-run crash resume and instruction contents were incomplete | Both repaired and covered |
| 4 | 9.3/10 | +2.2% | Provider quota failover, `tests/harness` CI discovery, and compound Git security classification were incomplete | All three repaired and covered |
| 5 | 9.3/10 | +0.0% | No new in-scope critical defect in the final focused review | Plateau reached |

Cycles 4 and 5 improved by less than three percent consecutively, satisfying the
enterprise-loop plateau rule.

## Final scorecard

| Dimension | Score | Evidence or deduction |
|---|---:|---|
| Correctness | 9.3 | 115-test broader contract pass plus live installed round trip |
| Architectural coherence | 9.4 | One runtime/registry/policy/store/event boundary |
| Safety | 8.5 | Exact-call approvals, project containment, restricted commands; no OS sandbox yet |
| Recovery | 9.0 | Transaction undo, active resume, sticky provider failover, bounded verification retry |
| Observability | 9.1 | Versioned JSONL, ordered events, usage, deterministic errors |
| Test realism | 9.2 | Temp Git/files/SQLite, installed binary, real provider tool loop, headless browser CI |
| Documentation | 9.3 | Blueprint, feature truth, changelog, compatibility boundaries |
| Operator experience | 8.9 | Preserved banner, natural language, controls, policy flags; live streaming remains next |
| Compatibility | 9.0 | Existing direct subcommands retained; old TUI isolated behind `--legacy` |
| Maintainability | 9.3 | Narrow modules, typed contracts, Ruff clean, fail-closed CI |

Average: **9.1/10**

## Evidence receipts

- Focused canonical contracts: `41 passed` after provider failover and recovery
  repairs.
- Broader TUI/pipeline/model/goal/harness contracts: `115 passed, 1 skipped`.
- Behavioral terminal security gate: `22 passed`, including an explicit block on
  mutating Git commands.
- Installed `casper exec` emitted only valid `casper.events/v1` JSONL and returned
  exit `64` for invalid input.
- Installed natural-language run selected the native provider chain, fell through
  the quota-limited provider, called `list_files` and `read_file`, returned the
  exact project name/version, and exited `0`.
- CI YAML parsed with six fail-closed jobs; Python, security, Vitest, dashboard
  build, and headless Chromium gates have direct passing receipts.
- Ruff and `git diff --check` passed.

## Remaining first-class gates

These deductions are deliberate; they are not hidden behind a “done” label:

1. Add an OS-backed Seatbelt/container sandbox for generic processes.
2. Expand transactional snapshots from typed file patches to command-side changes.
3. Add the unified MCP/skills/hooks extension kernel.
4. Add bounded worktree-isolated agent DAG execution.
5. Stream events live into the interactive renderer and support process-group
   cancellation/background jobs.

## Strict unified-E2E goal closure — 2026-07-16

The clarified goal produced exactly ten new engines in each of five cycles: fifty
total. Earlier hardening passes are verification history, not extra feature cycles.

| Cycle | Feature range | Mechanical outcome |
|---:|---:|---|
| 1 | 1-10 | Canonical runtime, providers, tools, policy, workspace, context, persistence, events, evaluation, and terminal |
| 2 | 11-20 | Extension kernel, skills/MCP, agents, task DAGs, cancellation, jobs, health, and worktrees |
| 3 | 21-30 | Symbols, dependencies, search, diagnostics, test selection, impact, plans, schemas, prompts, and watching |
| 4 | 31-40 | Redaction, command risk, budgets, circuit/retry, audit, artifacts, telemetry, config, and trust |
| 5 | 41-50 | Slash/natural-language discovery, branching, diffs/conflicts, model routing, cache, portability, and doctor |

Authoritative command:

```bash
PYTHONDONTWRITEBYTECODE=1 python scripts/e2e_harness_50.py
```

The release condition is exactly `passed=50`, `total=50`, `status=PASS`, and
process exit code `0`. The runner performs no network calls and has no pytest
dependency.
