# CASPER Prime 🚀

**Version 0.1.0-beta.1**

Autonomous AI Development Platform for Indie Developers

Turn natural language into production code. Delegate like you have a team. Ship like you're on fire.

---

## Status: **BETA — CANONICAL HARNESS MIGRATION**

CASPER Prime is in public beta. The typed coding-harness runtime and its focused
tests are active; legacy agent, dashboard, and terminal surfaces are still being
migrated. This checkout must not be described as production-ready until OS-backed
sandboxing, installed-binary proof, and the full regression suite are green.

```
╔═══════════════════════════════════════════════════════════════════╗
║  Component           │ Status       │ Tests                       ║
╠═══════════════════════════════════════════════════════════════════╣
║  Canonical Harness   │ ✅ Active    │ Focused contract tests       ║
║  Legacy CLI/Agents   │ ⚠️ Migrating │ Compatibility only           ║
║  Typed Tool Loop     │ ✅ Active    │ Native providers + fixtures  ║
║  Policy Workflow     │ ✅ Active    │ Exact-call approval          ║
║  FastAPI Server      │ ✅ Stable    │ WebSocket + REST endpoints  ║
║  Dashboard (React)   │ ⚠️  Beta     │ Playwright E2E tests        ║
║  Prometheus Metrics  │ ✅ New       │ /metrics endpoint           ║
║  Monitoring Dashboard│ ✅ New       │ /monitoring page            ║
╚═══════════════════════════════════════════════════════════════════╝
```

---

## Quick Start

### Prerequisites

- Python 3.11 or higher
- Node.js 18 or higher (for dashboard only)
- An Anthropic API key (required for LLM features)
- An OpenAI API key (optional, used as fallback)

### Installation

```bash
# Clone the repository
git clone <repository-url>
cd CASPER-DEV

# Install Python dependencies
pip install poetry
poetry install

# Or use pip directly
pip install -r requirements.txt

# Create environment file
cp .env.template .env
# Edit .env and add your API keys

# Verify installation
python3 -c "from core.services.llm import llm_service; print('✓ LLM service ready')"
```

### Using the CLI

```bash
# Start the canonical CASPER terminal
casper

# Run a machine-readable headless task
casper exec "Inspect the authentication flow" --permission-mode read_only

# Accept reversible local edits but keep high-risk approval prompts
casper --auto

# Temporary migration escape hatch
casper --legacy
```

Inside the default terminal, `/commands` shows the complete live command catalog
and `/commands review` filters it. Core coding workflows include:

```text
Inspect:   /status /doctor /context /diff /tools /usage
Act:       /goal /plan /task /verify /resume /rewind
Review:    /review /code-review [low|medium|high] /security-review
Extend:    /skills /mcp /agents /tasks /hooks
Policy:    /permissions [set read_only|default|accept_edits|bypass]
```

Plain-language requests and `/task` use the same typed runtime. Review commands
fail closed when the model returns malformed JSON, sub-threshold confidence,
unsupported files, or missing evidence bundles. Repo-relative paths stay contained;
explicit absolute paths are honored when the user names work outside the launch folder.

### Using the Dashboard

```bash
# Start the API server
python3 -m uvicorn core.server:app --reload --port 8000

# Start the dashboard (in another terminal)
cd dashboard && npm ci && npm run dev

# Open http://localhost:5173
```

### Monitoring

```bash
# Prometheus metrics endpoint
curl http://localhost:8000/metrics

# Monitoring dashboard
open http://localhost:8000/monitoring
```

---

## Features

### 🤖 Multi-Agent System

Six specialized agents coordinate to complete development tasks:

| Agent | Role | Specialization |
|-------|------|----------------|
| `master_prime` | Orchestrator | Task decomposition, agent routing |
| `backend_prime` | Backend Dev | API design, database, server logic |
| `frontend_prime` | Frontend Dev | UI components, React, styling |
| `testing_prime` | QA Engineer | Test automation, coverage analysis |
| `devops_prime` | DevOps | Deployment, CI/CD, infrastructure |
| `worker` | Generalist | File operations, simple tasks |

### 🧠 ReAct Reasoning Engine

Production-grade reasoning with 5 working tools:
- `execute_code` — Run Python code snippets
- `read_file` — Read file contents
- `write_file` — Write files with security checks
- `run_tests` — Execute test suites
- `search_code` — Search codebase by pattern

### 🔒 Approval Workflow System

Three modes for human-in-the-loop control:

| Mode | Behavior | Use Case |
|------|----------|----------|
| **STRICT** | All operations require manual approval | Production environments |
| **AUTO** | Safe operations auto-approved, risky ones require approval | Development |
| **YOLO** | All operations auto-approved | Rapid prototyping |

Risk assessment:
- **Critical**: `sudo rm -rf`, system-level commands → always blocked in AUTO
- **High**: Folder deletion, production deployment → requires approval
- **Medium**: File deletion → requires approval in STRICT
- **Low**: File creation, documentation → auto-approved in AUTO

### 🖥️ CLI Interface

The default terminal exposes 36 canonical agentic commands from one registry.
The larger historical command collection remains available only through
`casper --legacy` while those workflows are migrated onto typed engines.

### 📊 Observability

- **Prometheus metrics** at `/metrics` — HTTP requests, task counts, LLM calls, agent pool, system resources
- **Monitoring dashboard** at `/monitoring` — Real-time HTML dashboard with auto-refresh
- **Structured logging** via `structlog`
- **Circuit breakers** for LLM providers with automatic state transitions

### 🌐 FastAPI Server

- WebSocket endpoints for real-time updates (`/ws`, `/ws/terminal`)
- REST API for task submission, status, and results
- Rate limiting via `slowapi`
- CORS configuration
- Terminal PTY management

### 💼 Business Operations

- Proposal generator
- Estimate generator
- Invoice generator

---

## Architecture

```
CASPER DEV/
├── core/
│   ├── agents/              # 6 specialized agent implementations
│   ├── orchestrator/        # Agent coordination and task routing
│   ├── context/             # Context management with compression
│   ├── reasoning/           # ReAct engine with 5 tools
│   ├── services/            # 20+ service modules
│   │   ├── llm.py           # LLM service with circuit breaker
│   │   ├── enhanced_approval.py  # Approval workflow
│   │   ├── metrics.py       # Prometheus metrics
│   │   └── ...
│   ├── terminal/            # Terminal interface (PTY, WebSocket, security)
│   ├── ai/                  # AI command interpreter
│   ├── routers/             # FastAPI routers
│   └── server.py            # FastAPI server
├── dashboard/               # React/TypeScript dashboard
│   ├── src/components/      # 17+ React components
│   ├── monitoring.html      # Prometheus monitoring dashboard
│   └── tests/               # Playwright E2E tests
├── tests/                   # Python test suite
├── Dockerfile               # Container configuration
├── docker-compose.yml       # Multi-container setup
├── pyproject.toml           # Python dependencies
└── .github/workflows/       # CI/CD pipeline
```

---

## Testing

```bash
# Run all unit tests
python3 -m pytest tests/ -v

# Run with coverage
python3 -m pytest tests/ --cov=core --cov-report=term-missing

# Run specific test suite
python3 -m pytest tests/test_llm_rate_limits.py -v
python3 -m pytest tests/test_enhanced_approval.py -v
python3 -m pytest tests/test_command_interpreter.py -v

# Dashboard tests
cd dashboard && npm test
```

---

## Configuration

### Environment Variables

```bash
# Required
ANTHROPIC_API_KEY=your_key_here

# Optional (fallback provider)
OPENAI_API_KEY=your_key_here

# Optional (defaults to development)
CASPER_MODE=development  # or production
```

### Rate Limits (configurable via environment)

```bash
TASK_RATE_LIMIT=10/minute
ANALYSIS_RATE_LIMIT=20/minute
FILE_RATE_LIMIT=120/minute
```

---

## Docker

```bash
# Build and run
docker-compose up -d

# Or build manually
docker build -t casper-prime .
docker run -p 8000:8000 --env-file .env casper-prime
```

---

## CI/CD

GitHub Actions pipeline (`.github/workflows/terminal-testing.yml`):
- Python 3.11 test environment
- 85% coverage threshold
- Backend + frontend test jobs
- Path-based trigger filtering

---

## Changelog

See [CHANGELOG.md](CHANGELOG.md) for version history.

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for development guidelines.

## License

MIT — See [LICENSE](LICENSE) file.

---

## Known Limitations (Beta)

- Integration tests may fail when Anthropic API rate limits are hit (unit tests use mocked LLM)
- Dashboard icon migration from Lucide to Tabler Icons recently completed
- Some terminal E2E tests require `psutil` and `slowapi` dependencies
- WebSocket reconnection handling could be more robust

---

## Roadmap

- [ ] PyPI package publication
- [ ] Homebrew tap formula
- [ ] Plugin architecture for custom agents
- [ ] Multi-model routing optimization
- [ ] Dashboard UX polish (Phase 2)

---

Built by Douglas Talley | [LegacyAI.info](https://legacyai.info)
