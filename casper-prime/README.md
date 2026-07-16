# CASPER Prime - Autonomous AI Development Platform

**Fire and Forget Development** - Delegate complex tasks to specialized AI agent hierarchies.

## Overview

CASPER Prime is an autonomous AI development platform that enables indie developers to delegate complex tasks to specialized AI agent hierarchies. Unlike single-agent tools (Cursor, Copilot), CASPER Prime spawns specialized agents that work autonomously while providing real-time visibility.

## Core Features

- **Autonomous Agent Hierarchies**: Master orchestrator spawns specialized agents based on task complexity
- **R&D Framework**: Efficient context management with REDUCE & DELEGATE strategies
- **Fire and Forget**: Submit tasks and let agents handle the complexity
- **Real-time Visibility**: WebSocket dashboard shows agent activity and progress
- **Token Economics**: 60% more efficient than single-agent approaches

## Agent Roles

- **Master Prime**: Task analysis, complexity scoring, agent spawning decisions
- **Backend Prime**: APIs, databases, authentication, server architecture
- **Frontend Prime**: UI components, React, state management, responsive design
- **Testing Prime**: Unit tests, integration tests, e2e tests, coverage
- **Worker**: Simple tasks, single-file edits, quick fixes

## Quick Start

### Installation

```bash
# Clone the repository
git clone https://github.com/casper-prime/casper-prime.git
cd casper-prime

# Install dependencies
pip install -r requirements.txt

# Install in development mode
pip install -e .
```

### Basic Usage

```bash
# Execute a task
casper task "Build a complete user authentication system with JWT"

# Analyze task complexity without executing
casper analyze "Create a REST API for user management"

# Check system status
casper status

# List recent tasks
casper list
```

### Example: Authentication System

```bash
casper task "Build authentication with JWT, password reset, and email verification" --priority high
```

This will:
1. Master Prime analyzes the task complexity
2. Spawns Backend Prime for JWT and database
3. Spawns Frontend Prime for login/register forms
4. Spawns Testing Prime for comprehensive tests
5. Coordinates integration of all components

## Architecture

### Context Management (R&D Framework)

**REDUCE Strategy**: Minimize context to essential information
- Structural pointers instead of full content
- Archive completed work
- Load data on-demand

**DELEGATE Strategy**: Efficient handoffs between agents
- What I Did, What You Need, Where to Find More
- Maximum 2000 tokens per handoff
- Automatic compression if exceeded

### Task Execution Flow

```
User Task → Master Prime Analysis → Agent Spawning → Parallel/Sequential Execution → Integration → Result
```

## Configuration

Create a `.casper/config.yaml` file in your project:

```yaml
project:
  name: "My SaaS App"
  type: "web"

agents:
  max_per_role: 5
  token_limit: 10000

context:
  max_bundle_size: 2000
  compression_enabled: true

api:
  anthropic_key: "your-api-key"
  model_prime: "claude-3-sonnet"
  model_worker: "claude-3-haiku"
```

## Dashboard

The React dashboard provides real-time visibility:

```bash
# Start the dashboard
cd dashboard
npm install
npm run dev
```

Access at `http://localhost:3000` to see:
- Agent pipeline (Kanban view)
- Context token usage
- Task progress
- Real-time WebSocket updates

## Development

### Running Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=core tests/

# Run specific test file
pytest tests/test_agents.py
```

### Project Structure

```
casper-prime/
├── core/
│   ├── agents/          # Agent implementations
│   ├── context/         # Context management (R&D)
│   ├── orchestrator/    # Coordination & spawning
│   └── cli.py          # Command interface
├── dashboard/          # React real-time UI
├── templates/          # Agent templates
└── examples/          # Example projects
```

## Performance Metrics

- **Setup Time**: <5 minutes
- **Task Completion**: >85% without intervention
- **Token Efficiency**: >60% improvement vs single-agent
- **Context Handoff Success**: >95%

## Contributing

We welcome contributions! Please see [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

## License

MIT License - see [LICENSE](LICENSE) for details.

## Support

- Documentation: [docs.casper-prime.ai](https://docs.casper-prime.ai)
- Issues: [GitHub Issues](https://github.com/casper-prime/casper-prime/issues)
- Discord: [Join our community](https://discord.gg/casper-prime)

---

**Built with CASPER Prime** - The future of autonomous development is here.