# CASPER Prime 🚀

**Version 0.1.0-beta.1**

Autonomous AI Development Platform for Indie Developers

Turn natural language into production code. Delegate like you have a team. Ship like you're on fire.

---

## Status: **BETA**

CASPER Prime is in public beta. Core functionality is stable and tested. The CLI is production-ready; the dashboard is functional with ongoing UX improvements.

```
╔═══════════════════════════════════════════════════════════════════╗
║  Component           │ Status       │ Tests                       ║
╠═══════════════════════════════════════════════════════════════════╣
║  CLI (50+ commands)  │ ✅ Stable    │ 55+ unit tests passing      ║
║  Agent System (6)    │ ✅ Stable    │ Integration tests passing   ║
║  ReAct Engine        │ ✅ Stable    │ 5 tools verified             ║
║  Approval Workflow   │ ✅ Stable    │ 18 unit tests passing       ║
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
# Start the CASPER terminal
python3 casper_terminal_complete.py

# Or run a task directly
python3 casper_terminal_complete.py "Build a REST API endpoint"

# Enable YOLO mode (auto-approve all operations)
python3 casper_terminal_complete.py --yolo "Create a React component"

# Enable AUTO mode (auto-approve safe operations only)
python3 casper_terminal_complete.py --auto "Add unit tests for auth module"
```

### Using the Dashboard

```bash
# Start the API server
python3 -m uvicorn core.server:app --reload --port 8000

# Start the dashboard (in another terminal)
cd dashboard && npm install && npm run dev

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

50+ commands across 7 categories:

```
System:     help, status, config, setup, clear, init
Workflow:   task, analyze, react, session, resume
Development:gen, refactor, review, addroute, pr, fixbug, testfail, deploy, standup
AI:         explain, debug, sync, todo, custom
Business:   proposal, estimate, invoice
Testing:    test, testfail, coverage, lint, security
Utility:    files, filetree, search, grep, open, save, sessions
```

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
