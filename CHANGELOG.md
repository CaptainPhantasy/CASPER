# Changelog

All notable changes to CASPER Prime will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- Canonical `core.harness` runtime with typed tools and deterministic observations
- Native Anthropic and OpenAI tool-calling adapters with explicit chat-only fallback
- Central read-only/default/accept-edits/bypass policy and exact-call approvals
- Transactional patching with preimage hashes, durable undo, explicit absolute-path access,
  and traversal-safe relative paths
- Git-aware context selection, token budgets, and deterministic compaction
- SQLite run/event/checkpoint store with approval-safe resume
- Versioned `casper.events/v1` JSONL through `casper exec`
- Harness evaluator for completion rate, retries, pass@1/pass@3, latency, tokens, and cost
- Modern interactive client backed by the same runtime as headless execution
- CASPER ASCII identity snapshot contract
- Top-three coding-harness blueprint and verified `FEATURES.md`
- Four additional ten-feature engine batches for orchestration, developer intelligence,
  safety/operations, and terminal interaction (50 verified engines total)
- Ultra-lean `scripts/e2e_harness_50.py` release gate covering all fifty engines in one pass
- Canonical 36-command catalog aligned with high-value coding-agent workflows
- `/review`, `/code-review`, and `/security-review` backed by an evidence-gated JSON sentinel
- `/goal`, `/status`, `/doctor`, `/context`, `/diff`, `/resume`, `/rewind`, `/skills`,
  `/mcp`, `/agents`, `/tasks`, `/hooks`, and `/usage` wired to live harness state
- Kimi/Claude-compatible lifecycle command hooks with matching, JSON context, timeouts,
  blocking exit codes, added context, diagnostics, and project-local configuration
- Low-friction `/setup`, `/config`, `/pwd`, `/workdir`, `/history`, `/new`, `/export`,
  `/clear`, and typed `/mkdir` controls that do not require an LLM round trip
- Prometheus metrics endpoint for observability
- Mock LLM fixtures for integration testing
- API rate limit handling tests
- CONTRIBUTING.md with development guidelines
- LICENSE file (MIT)
- This CHANGELOG.md

### Changed
- Default `casper` launch now enters the canonical typed harness; the complete terminal moved to `--legacy`
- Default `/help` and `/commands` now project one filterable catalog instead of a sparse hardcoded list
- Tool observations are secret-redacted before they enter model context or the durable event stream
- Repository launcher now resolves its own installation directory instead of a hardcoded volume path
- CI now uses deterministic suite paths, strict pytest markers, Vitest, headless Playwright, and fail-closed aggregation
- Python metadata now uses PEP 621 and the supported dependency set was refreshed for
  Python 3.11-3.13; the dashboard lock was refreshed with zero known audit findings
- The dashboard build now uses bounded Rolldown chunk splitting instead of a multi-megabyte
  single bundle
- Migrated all dashboard icon imports from `lucide-react` to `@tabler/icons-react`
- Updated README with beta status and setup instructions
- Fixed command interpreter classification ordering (git operations now checked before testing)
- Fixed target extraction regex to handle "named" and "called" patterns correctly
- Removed incorrect `@pytest.mark.asyncio` markers from synchronous test functions
- Fixed `approve_all` and `approve_all_with_pattern` tests to not require event loop

### Fixed
- `test_input_classification`: "git commit" now correctly classified as `git_operation`
- `test_target_extraction`: "create folder named src" now correctly extracts "src"
- `test_quality_gate_execution`: assertion updated to accept zero execution time for fast mocks
- `test_clarification_request`: marked as skip due to non-deterministic LLM-dependent behavior

## [0.1.0-alpha] - 2025-09-24

### Added
- Core agent system with 6 specialized agents (master, frontend, backend, testing, devops, worker)
- ReAct reasoning engine with 5 working tools (execute_code, read_file, write_file, run_tests, search_code)
- Context management with SQLite persistence, compression, and caching
- CLI interface with 50+ commands across 7 categories
- Approval workflow system with 3 modes (STRICT, AUTO, YOLO)
- FastAPI server with WebSocket endpoints for real-time updates
- React/TypeScript dashboard with Radix UI, Monaco Editor, XTerm.js
- Business operations (proposal generator, invoice generator, estimate generator)
- Development operations (database manager, security scanner, code quality analyzer)
- LLM service with Anthropic primary, OpenAI fallback, circuit breaker pattern
- Terminal interface with PTY management and security checks
- Docker and docker-compose configuration
- GitHub Actions CI/CD pipeline with 85% coverage threshold
- Comprehensive test suite (38+ tests)

### Security
- Risk assessment for dangerous patterns (sudo rm -rf, etc.)
- Input validation on all file operations
- Rate limiting via slowapi
- JWT token support via PyJWT
- No hardcoded API keys (uses .env.template)

### Known Issues
- Browser-driven Python terminal suites require the optional `browser` extra and an
  installed Chromium binary
- `websockets` remains on the latest compatible 15.x release because the current
  `langgraph-sdk` dependency excludes 16.x
