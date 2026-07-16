# CASPER TUI Coding-Agent Slash Command Manifest

**Batch:** 2 of N
**Design:** familiar coding-agent commands backed by narrow CASPER engines
**Observation contract:** every result includes `status`, `summary`, `next_actions`, and `artifacts`; errors additionally include a root-cause hint, safe retry, and stop condition.

| # | Command | Engine | Verification |
|---|---|---|---|
| 1 | `/init` | Project marker/instruction discovery and guarded initialization | `test_init_engine` |
| 2 | `/status` | Git branch, head, and dirty-worktree inspection | `test_status_engine` |
| 3 | `/doctor` | Runtime, build-system, and project-marker diagnostics | `test_doctor_engine` |
| 4 | `/model` | Live LLM model discovery and persisted provider/model selection | `test_model_engine` |
| 5 | `/permissions` | Enforced session permission mode | `test_permissions_engine` |
| 6 | `/diff` | Bounded Git diff and diff-stat reader | `test_diff_engine` |
| 7 | `/review` | LLM-backed review of the current diff or a scoped file | `test_review_engine` |
| 8 | `/plan` | `InputCompiler` frozen-spec engine without execution | `test_plan_engine` |
| 9 | `/task` | Full reversible `Pipeline.run()` execution path | `test_task_engine` |
| 10 | `/test` | Detected real test command with optional scoped target | `test_test_engine` |
| 11 | `/lint` | Stack-aware lint or compile-check fallback | `test_lint_engine` |
| 12 | `/build` | Detected real build command | `test_build_engine` |
| 13 | `/context` | Live repository/context-budget snapshot | `test_context_engine` |
| 14 | `/compact` | Actual transcript compaction with autosaved state | `test_compact_engine` |
| 15 | `/resume` | Named TUI session list/load engine | `test_resume_engine` |
| 16 | `/skills` | Project/shared CASPER skill discovery and search | `test_skills_engine` |
| 17 | `/mcp` | Live MCP server capability and connection state | `test_mcp_engine` |
| 18 | `/agents` | Live CASPER agent-layer initialization state | `test_agents_engine` |
| 19 | `/rewind` | `ChangeLedger` inspection and permission-gated reversal | `test_rewind_engine` |
| 20 | `/usage` | Persisted command counts, latency, and failure metrics | `test_usage_engine` |

## Safety boundaries

- Argument lists are executed without a shell.
- Paths are constrained to the active project root.
- Output is bounded before entering the TUI context.
- Mutating `/init`, `/model set`, `/task`, and `/rewind undo` operations require an explicit mutation-capable permission mode.
- `/task` uses CASPER's pipeline autonomy and reversibility ledger; it does not bypass them.
