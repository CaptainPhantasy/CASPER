# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## ⚡ **CRITICAL: USE THE CHEATSHEET FIRST**

**🎯 ALWAYS read `CheatSheet.md` first - it contains exact file:line locations for all code.**

## Project Overview

**CASPER Prime**: Enterprise-grade multi-agent AI development platform
- **Architecture**: 4-layer system with ReAct loop and MCP protocol support
- **Backend**: Python FastAPI (8742) - Agent orchestration, terminal, WebSocket
- **Frontend**: React TypeScript (9318) - Dashboard with XTerm.js terminal
- **CLI**: Python Rich-based interface with agent coordination

## Commands

### Development
```bash
# Backend server
python3 -m core.server          # Start on port 8742

# Frontend dashboard
cd dashboard && npm run dev      # Start on port 9318

# CLI usage
poetry run casper task "your task here"  # Execute task
poetry run casper analyze "task"         # Analyze complexity
poetry run casper status                 # System status
poetry run casper init                   # Initialize project

# Testing
pytest --cov=core tests/                    # Backend tests with coverage
cd dashboard && npm run test:commands       # Terminal command tests
cd dashboard && playwright test             # E2E tests (multi-browser)

# Linting & Formatting
black core/ tests/                          # Python formatting
flake8 core/                               # Python linting
cd dashboard && npm run lint                # TypeScript linting
```

### Single Test Execution
```bash
pytest tests/test_terminal_security.py::test_command_injection_prevention -xvs
pytest tests/test_terminal_websocket.py -k "connection" --tb=short
```

## High-Level Architecture

### Multi-Agent System (Master-Delegate Pattern)
```
User Request → Master Prime (Orchestrator)
    ↓
Task Analysis & Complexity Assessment
    ↓
Agent Pool Selection & Spawning
    ↓
Parallel/Sequential Execution
    ↓
Context Bundle Communication
```

**Key Components:**
- **Task Complexity Analyzer**: Evaluates LOW/MEDIUM/HIGH complexity
- **Agent Pool**: Max 5 agents per role with lifecycle management
- **Context Bundles**: Structured inter-agent communication
- **ReAct Loop**: Reason → Plan → Act → Observe cycle

### Terminal Integration Architecture
```
Frontend (XTerm.js) ↔ WebSocket ↔ Backend (PTY Manager)
                          ↓
                  Security Middleware
                          ↓
                  Command Sandbox
```

**Security Layers:**
- Command whitelisting with risk assessment
- Sandboxed PTY execution environments
- Audit logging for all terminal operations
- JWT-based session authentication

### WebSocket Communication Pattern
- **Main**: `ws://localhost:8742/ws` - Agent status updates
- **Terminal**: `ws://localhost:8742/ws/terminal` - Terminal sessions
- **Protocol**: JSON messages with type-based routing
- **Reconnection**: Automatic with exponential backoff

## Configuration

### Environment Variables (.env)
```bash
ANTHROPIC_API_KEY=your_key        # Primary LLM
OPENAI_API_KEY=backup_key         # Fallback LLM
CASPER_PROJECT_ROOT=/path/to/project
```

### Rate Limiting
- Task submissions: 10/minute
- Analysis requests: 20/minute
- File operations: 120/minute

### Project Settings (.casper/config/casper.json)
```json
{
  "agents": {
    "max_parallel_agents": 4,
    "default_priority": "medium"
  },
  "repository": {
    "require_human_approval": true,
    "auto_format_on_apply": true
  }
}
```

## Critical Code Locations

### Agent System
- **Task Routing**: `core/agents/master_prime.py:181-240` - execute_task()
- **Agent Spawning**: `core/agents/master_prime.py:624-640` - spawn_and_delegate()
- **Complexity Analysis**: `core/agents/master_prime.py:116-167` - analyze()
- **Agent Factory**: `core/orchestrator/coordinator.py:68-91` - _create_agent()

### Terminal System
- **WebSocket Handler**: `core/terminal/websocket_handler.py:93-128` - handle_connection()
- **Security Validation**: `core/terminal/security.py:87-100` - safe_commands whitelist
- **PTY Management**: `core/terminal/websocket_handler.py:170-200` - session creation

### Frontend Integration
- **Terminal Component**: `dashboard/src/components/Terminal/TerminalComponent.tsx:18-30`
- **Terminal Store**: `dashboard/src/stores/terminalStore.ts:36-67` - session management
- **WebSocket Service**: `dashboard/src/services/terminalWebSocket.ts:50-100`

## Development Guidelines

### Adding New Features

**New Agent Role:**
1. Add to `AgentRole` enum in `core/agents/base.py`
2. Create agent class in `core/agents/your_agent_prime.py`
3. Register in `core/orchestrator/coordinator.py:76-90`
4. Add keywords in `core/agents/master_prime.py:94-114`

**New Terminal Command:**
1. Whitelist in `core/terminal/security.py:87-100`
2. Add handler in `core/terminal/command_proxy.py`
3. Test in `tests/test_terminal_security.py`

**New API Endpoint:**
1. Add route in `core/server.py` after line 1160
2. Create service in `core/services/`
3. Add frontend API call in `dashboard/src/services/api.ts`

### Testing Requirements
- Always write tests for new agents
- Security test all terminal commands
- E2E test WebSocket interactions
- Performance test agent pools under load

### Security Best Practices
- Never log sensitive information (API keys, tokens)
- Validate all terminal commands through SecurityMiddleware
- Use sandboxed environments for command execution
- Implement rate limiting for all endpoints

## Agent Standards

### Task Execution Protocol
1. Analyze complexity before execution
2. Create context bundle for communication
3. Log with ISO 8601 timestamps
4. Report progress via WebSocket
5. Clean up resources on completion

### Progress Reporting Format
```json
{
  "task_id": "uuid",
  "agent": "role",
  "status": "planning|building|reviewing|completed",
  "progress": 0-100,
  "message": "Current action",
  "timestamp": "2024-01-01T00:00:00Z"
}
```

## Troubleshooting

### Common Issues & Solutions

**Agent Not Spawning:**
Check `core/agents/master_prime.py:624-640` - Ensure pool has available agents

**Terminal Connection Failed:**
Verify `core/terminal/websocket_handler.py:130-154` - Check sandbox directory exists

**WebSocket Disconnecting:**
Review `dashboard/src/services/terminalWebSocket.ts:20-50` - Verify port 8742 is open

**LLM Provider Failing:**
Check `core/services/llm.py:20-40` - Ensure API keys are valid and provider is available

## Important Files

- **Agent Decision Matrix**: See `CheatSheet.md:404-416`
- **Context Storage**: `.casper/context/*.ctx` - Agent communication
- **Output Results**: `.casper/output/{task_id}/` - Task artifacts
- **API Logs**: `logs/openai/*.json` - LLM interactions

## Notes

- Prefer editing existing files over creating new ones
- Use CheatSheet.md for exact code locations
- Follow existing code patterns and conventions
- Test security implications of all changes
- Document complex agent interactions