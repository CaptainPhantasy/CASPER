# CASPER Prime 🚀

## Autonomous AI Development Platform for Indie Developers

Turn natural language into production code. Delegate like you have a team. Ship like you're on fire.

### ✅ Project Successfully Created!

Your CASPER Prime installation is located at:
`/Volumes/Storage/Development/CASPER DEV/`

### Quick Start

```bash
# Navigate to the project
cd "/Volumes/Storage/Development/CASPER DEV"

# Install dependencies (using Python 3.13)
pip install poetry
poetry install

# Initialize CASPER in a test project
cd /path/to/your/test/project
poetry run casper init

# Execute your first task
poetry run casper task "Build a simple REST API endpoint"

# Analyze without executing
poetry run casper task "Create user authentication" --dry-run
```

### What's Been Built

✅ **Core Agent System**
- Master Prime Agent with task analysis
- Backend Prime Agent for API development
- Frontend Prime Agent (stub for expansion)
- Context bundling and handoff system

✅ **CLI Interface**
- `casper init` - Initialize in any project
- `casper task` - Execute development tasks
- `casper dashboard` - Launch web UI (coming soon)

✅ **Configuration**
- API keys secured in .env file
- Project-scoped .casper directory
- Token tracking and cost estimation

### Test It Now!

Try these commands to test the system:

```bash
# Simple test
poetry run casper task "Create a function to validate email addresses" --dry-run

# More complex test
poetry run casper task "Build a REST API endpoint for user registration with email validation"
```

### Current Features

- 🤖 **Task Analysis** - Master Prime analyzes complexity and spawns agents
- 💰 **Cost Estimation** - Know the cost before execution
- 🔄 **Agent Coordination** - Multiple agents work together
- 📊 **Progress Tracking** - CLI shows real-time progress
- 🎯 **Dry Run Mode** - Analyze without spending tokens

### Project Structure

```
CASPER DEV/
├── core/                 # Agent system implementation
│   ├── agents/          # Agent classes
│   │   ├── base.py      # Base agent class
│   │   ├── master_prime.py  # Orchestrator
│   │   ├── backend_prime.py # Backend specialist
│   │   └── frontend_prime.py # Frontend specialist
│   ├── cli.py           # Command-line interface
│   └── context/         # Context management
├── .env                 # API keys (don't commit!)
├── pyproject.toml       # Python dependencies
└── .casper/            # Project configuration
```

### Next Steps for Development

1. **Test the Current System**
   - Run simple tasks to verify agent coordination
   - Check token usage and cost tracking
   - Test context handoffs between agents

2. **Expand Agent Capabilities**
   - Implement Frontend Prime fully
   - Add Testing Prime for automated tests
   - Create Worker agents for specific tasks

3. **Build Dashboard** (Week 2)
   - React + TypeScript UI
   - WebSocket for real-time updates
   - Kanban view of agent pipeline

### API Keys Configured

✅ Anthropic API Key (Primary)
✅ OpenAI API Key (Fallback)

### Need Help?

The system is ready for testing! Try running a simple task first to see the agents in action.

---
Built by Douglas Talley | LegacyAI.info
