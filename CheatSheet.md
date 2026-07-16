# CASPER Prime Codebase CheatSheet

*Precise file:line index for future agents to jump directly to code sections without hunting.*

## 🎯 Quick Context Lookup

### **Project Type**: Autonomous AI Development Platform
### **Architecture**: Multi-agent system with React dashboard + Python backend
### **Ports**: Backend (8742), Frontend (9318)

---

## 📍 **CRITICAL CODE LOCATIONS** - Jump Here First

### **🚀 Server Startup & Configuration**
- **Main Server**: `core/server.py:166-187` - startup_event(), coordinator/terminal init
- **FastAPI App**: `core/server.py:42-56` - CORS, rate limiting, middleware setup
- **WebSocket Endpoints**: `core/server.py:201-250` - /ws and /ws/terminal routes

### **🎭 Agent System Core**
- **Task Analysis**: `core/agents/master_prime.py:116-167` - TaskComplexityAnalyzer.analyze()
- **Agent Spawning**: `core/agents/master_prime.py:624-640` - spawn_and_delegate()
- **LLM Decomposition**: `core/agents/master_prime.py:289-362` - llm_decompose()
- **Agent Factory**: `core/orchestrator/coordinator.py:68-91` - _create_agent()

### **🔒 Security System**
- **Command Validation**: `core/terminal/security.py:87-100` - safe_commands whitelist
- **WebSocket Security**: `core/terminal/websocket_handler.py:264-291` - _handle_command()
- **Audit Logging**: `core/terminal/security.py:52-81` - AuditEvent class

### **🖥️ Terminal Integration**
- **WebSocket Handler**: `core/terminal/websocket_handler.py:93-128` - handle_connection()
- **PTY Session Create**: `core/terminal/websocket_handler.py:170-200` - PTY + sandbox setup
- **Frontend Terminal**: `dashboard/src/components/Terminal/TerminalComponent.tsx:18-30` - React component
- **Terminal Store**: `dashboard/src/stores/terminalStore.ts:36-67` - createSession()

---

## 🧠 **BACKEND CORE** (`core/`)

### **🎭 Agents System** (`core/agents/master_prime.py`)
```python
# Lines 23-28: Task Complexity Levels
class TaskComplexity(Enum):
    LOW = "low"     # Single file, simple logic
    MEDIUM = "medium" # Multiple files, moderate logic
    HIGH = "high"    # Multiple components, complex integration

# Lines 116-127: Core Analysis Function
@classmethod
def analyze(cls, task: str) -> Tuple[TaskComplexity, Set[AgentRole]]:
    """Analyze task complexity and required agents."""
    task_lower = task.lower()
    complexity = cls._determine_complexity(task_lower)
    required_agents = cls._determine_agents(task_lower, complexity)
    return complexity, required_agents
```

**Key Locations:**
- **Task Routing Logic**: `core/agents/master_prime.py:181-240` - execute_task()
- **Complexity Analysis**: `core/agents/master_prime.py:241-287` - perform_task_analysis()
- **Subtask Creation**: `core/agents/master_prime.py:364-489` - decompose_task()
- **Agent Keywords**: `core/agents/master_prime.py:94-114` - AGENT_KEYWORDS dict

### **🎼 Orchestration** (`core/orchestrator/coordinator.py`)
```python
# Lines 37-47: Agent Pool Management
class AgentPool:
    def __init__(self, max_agents_per_role: int = 5):
        self.available_agents: Dict[AgentRole, List[BaseAgent]] = {
            role: [] for role in AgentRole
        }
        self.busy_agents: Dict[UUID, AgentInstance] = {}
```

**Key Locations:**
- **Agent Pool**: `core/orchestrator/coordinator.py:37-100` - AgentPool class
- **Task Distribution**: `core/orchestrator/coordinator.py:150-200` - AgentCoordinator.submit_task()

### **🔌 Services** (`core/services/`)
**LLM Service** (`llm.py`)
- **LLM Generation**: `core/services/llm.py:50-80` - complete() function
- **Provider Switching**: `core/services/llm.py:20-40` - available() check

**Business Service** (`business.py`)
- **Proposal Generation**: `core/services/business.py:100-150` - generate_proposal()
- **Invoice Creation**: `core/services/business.py:200-250` - generate_invoice()

### **💻 Terminal System** (`core/terminal/`)

**Security Middleware** (`security.py:1-100`)
```python
# Lines 87-100: Safe Commands Whitelist
self.safe_commands: Set[str] = {
    # Basic file operations
    "ls", "cat", "head", "tail", "less", "more",
    # Directory navigation
    "pwd", "cd", "find", "locate", "which",
    # CASPER specific
    "casper", "poetry", "pytest", "black"
}
```

**WebSocket Handler** (`websocket_handler.py`)
```python
# Lines 93-106: Connection Setup
async def handle_connection(self, websocket: WebSocket, token: Optional[str] = None) -> str:
    try:
        session_id = await self.connect(websocket, token)
        # Message handling loop
        while True:
            data = await websocket.receive_json()
            await self.handle_message(session_id, data)
```

**Key Locations:**
- **Session Management**: `core/terminal/websocket_handler.py:130-200` - connect()
- **Command Handling**: `core/terminal/websocket_handler.py:264-291` - _handle_command()
- **Security Integration**: `core/terminal/websocket_handler.py:270-276` - validate_command()

---

## 🎨 **FRONTEND DASHBOARD** (`dashboard/src/`)

### **🖥️ Terminal Components**

**Main Terminal Component** (`components/Terminal/TerminalComponent.tsx:1-30`)
```tsx
export const TerminalComponent: React.FC<TerminalComponentProps> = ({
  sessionId,
  className,
}) => {
  const terminalRef = useRef<HTMLDivElement>(null);
  const terminalInstance = useRef<Terminal | null>(null);
  const fitAddon = useRef<FitAddon | null>(null);
```

**Terminal Store** (`stores/terminalStore.ts:36-67`)
```typescript
createSession: (title?: string, cwd?: string) => {
  const sessionId = generateSessionId();
  const session: TerminalSession = {
    id: sessionId,
    title: title || `Terminal ${get().sessions.size + 1}`,
    terminal: null,
    wsId: null,
    status: 'disconnected'
  };
```

**Key Locations:**
- **XTerm Setup**: `dashboard/src/components/Terminal/TerminalComponent.tsx:50-100` - Terminal initialization
- **WebSocket Connection**: `dashboard/src/services/terminalWebSocket.ts:50-100` - connection management
- **Session State**: `dashboard/src/stores/terminalStore.ts:113-128` - updateSession()

### **📐 Layout System** (`components/Layout/`)
- **Panel Layout**: `dashboard/src/components/Layout/PanelLayout.tsx:1-50` - Resizable panels
- **Layout Store**: `dashboard/src/stores/layoutStore.ts:1-50` - Panel state management

---

## 🧪 **TESTING INFRASTRUCTURE** (`tests/`)

### **🔒 Security Tests** (`test_terminal_security.py`)
```python
# Lines 50-70: Command Injection Tests
async def test_command_injection_prevention():
    security = SecurityMiddleware()
    malicious_commands = [
        "ls; rm -rf /",
        "cat file | sh",
        "$(wget malicious.sh)"
    ]
    for cmd in malicious_commands:
        with pytest.raises(SecurityViolation):
            await security.validate_command(cmd, "test_session")
```

### **🌐 WebSocket Tests** (`test_terminal_websocket.py`)
```python
# Lines 100-120: Connection Flow Tests
async def test_websocket_terminal_connection():
    handler = TerminalWebSocketHandler()
    mock_websocket = MockWebSocket()
    session_id = await handler.connect(mock_websocket)
    assert session_id in handler.sessions
    assert handler.sessions[session_id].is_active
```

**Key Test Locations:**
- **Security Validation**: `tests/test_terminal_security.py:50-150` - Command injection/privilege tests
- **WebSocket Flow**: `tests/test_terminal_websocket.py:100-200` - Connection lifecycle
- **E2E Workflows**: `tests/test_terminal_e2e.py:200-300` - Complete terminal sessions
- **Performance Tests**: `tests/test_terminal_performance.py:100-200` - Load testing

---

## ⚙️ **CONFIGURATION & STATE**

### **🔧 Configuration Files**
```bash
# Environment Setup (.env)
ANTHROPIC_API_KEY=your_key_here
OPENAI_API_KEY=your_backup_key
CASPER_PROJECT_ROOT=/path/to/project

# Rate Limiting (core/server.py:38-41)
TASK_RATE_LIMIT=10/minute
ANALYSIS_RATE_LIMIT=20/minute
FILE_RATE_LIMIT=120/minute
```

**Key Config Locations:**
- **Server Config**: `core/server.py:35-56` - Rate limits, CORS origins
- **Python Deps**: `pyproject.toml:1-50` - Poetry configuration
- **Frontend Deps**: `dashboard/package.json:1-30` - npm packages
- **CASPER Settings**: `.casper/config/settings.json` - Project-specific config

### **📁 State Management**
```python
# Context Bundle Structure (core/context/manager.py)
@dataclass
class ContextBundle:
    session_id: UUID
    parent_task: str
    max_tokens: int = 4000
    structural_pointers: Dict[str, str] = field(default_factory=dict)
    artifacts_created: List[str] = field(default_factory=list)
```

**State Locations:**
- **Context Storage**: `.casper/context/*.ctx` - Agent communication bundles
- **Output Results**: `.casper/output/{task_id}/` - Agent execution results
- **System Logs**: `logs/openai/*.json` - API interaction logs

---

## 🚀 **QUICK DEVELOPMENT TASKS** - Exact Steps

### **Adding New Agent**
```python
# 1. Create: core/agents/your_agent_prime.py
class YourAgentPrime(BaseAgent):
    def __init__(self):
        super().__init__(role=AgentRole.YOUR_PRIME)  # Add to AgentRole enum first

    async def execute_task(self, task: str, context: ContextBundle) -> AgentResult:
        # Your implementation here
        pass

# 2. Register: core/orchestrator/coordinator.py:76-90 (in _create_agent)
elif role == AgentRole.YOUR_PRIME:
    from core.agents.your_agent_prime import YourAgentPrime
    return YourAgentPrime()

# 3. Add Keywords: core/agents/master_prime.py:94-114 (in AGENT_KEYWORDS)
AgentRole.YOUR_PRIME: ["your", "keywords", "here"]
```

### **Adding Terminal Command**
```python
# 1. Whitelist: core/terminal/security.py:87-100
self.safe_commands.add("your_new_command")

# 2. Proxy: core/terminal/command_proxy.py (if CASPER command)
def handle_your_command(self, args: List[str]) -> Dict[str, Any]:
    return {"status": "success", "output": "Command executed"}

# 3. Test: tests/test_terminal_security.py
async def test_your_command_allowed():
    security = SecurityMiddleware()
    await security.validate_command("your_new_command", "test_session")
```

### **Adding API Endpoint**
```python
# 1. Server: core/server.py (after line 1160)
@app.post("/api/your/endpoint")
async def your_endpoint(request: YourRequest):
    try:
        result = await your_service.process(request)
        return {"success": True, "data": result}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

# 2. Frontend: dashboard/src/services/api.ts
export const callYourEndpoint = async (data: YourData) => {
  const response = await fetch('/api/your/endpoint', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data)
  });
  return response.json();
};
```

### **Adding React Component**
```tsx
# 1. Component: dashboard/src/components/YourComponent.tsx
import React from 'react';
import { useYourStore } from '@/stores/yourStore';

export const YourComponent: React.FC = () => {
  const { data, updateData } = useYourStore();
  return <div>{/* Your component */}</div>;
};

# 2. Store: dashboard/src/stores/yourStore.ts
import { create } from 'zustand';

interface YourState {
  data: YourData[];
  updateData: (newData: YourData) => void;
}

export const useYourStore = create<YourState>((set) => ({
  data: [],
  updateData: (newData) => set((state) => ({ data: [...state.data, newData] }))
}));
```

---

## 🔍 **CRITICAL CODE LOCATIONS** - Emergency Fixes

### **🚨 Agent System Failures**
```python
# Agent Not Spawning: core/agents/master_prime.py:624-640
async def spawn_and_delegate(self, delegations: List[TaskDelegation]):
    for delegation in delegations:
        self.active_delegations[delegation.context_bundle.session_id] = delegation
        # Check this loop - spawning might fail silently

# Task Analysis Broken: core/agents/master_prime.py:241-287
async def perform_task_analysis(self, task: str) -> TaskAnalysis:
    complexity, required_agents = self.analyzer.analyze(task)
    # LLM decomposition can fail - check llm_service.available()
```

### **🚨 Terminal Connection Issues**
```python
# WebSocket Failing: core/terminal/websocket_handler.py:130-154
async def connect(self, websocket: WebSocket, token: Optional[str] = None):
    await websocket.accept()  # This can timeout
    session_id = str(uuid4())
    # Check sandbox creation at line 172-180

# PTY Creation Failing: core/terminal/websocket_handler.py:170-200
pty_session_id = await self.pty_manager.create_session(
    working_dir=sandbox_context["sandbox_dir"],  # Dir might not exist
    env=sandbox_context["env_vars"]
)
```

### **🚨 Security Violations**
```python
# Command Blocked: core/terminal/security.py:87-100
self.safe_commands: Set[str] = {
    "ls", "cat", "head", "tail"  # Add your command here
}

# Security Event: core/terminal/websocket_handler.py:255-262
except SecurityViolation as e:
    await session.send_error("security_violation", str(e))
    # Check audit log for details
```

### **🚨 Frontend Terminal Issues**
```typescript
// Terminal Not Loading: dashboard/src/components/Terminal/TerminalComponent.tsx:50-80
useEffect(() => {
  if (terminalRef.current && !terminalInstance.current) {
    // XTerm creation can fail - check console errors
    const terminal = new Terminal({
      // Configuration might be invalid
    });
  }
}, []);

// WebSocket Connection: dashboard/src/services/terminalWebSocket.ts:20-50
connect(sessionId: string) {
  this.ws = new WebSocket(`ws://localhost:8742/ws/terminal`);
  // URL might be wrong, server might be down
}
```

### **🚨 Server Startup Failures**
```python
# Server Won't Start: core/server.py:166-187
@app.on_event("startup")
async def startup_event():
    coordinator = AgentCoordinator(context_manager)  # Can fail
    await coordinator.start()  # Database connection issues
    await terminal_handler.start()  # PTY manager issues

# Port Already in Use: core/server.py:1160-1164
if __name__ == "__main__":
    port = int(os.environ.get("PORT", "8742"))  # Check if port is free
    uvicorn.run(app, host="0.0.0.0", port=port)
```

---

## 🎯 **AGENT DECISION MATRIX** - Task Routing

| Task Type | Jump to File:Lines | Key Functions | Modify Here |
|-----------|-------------------|---------------|-------------|
| **Agent Spawning** | `core/agents/master_prime.py:624-640` | `spawn_and_delegate()` | Add new agent roles |
| **Task Analysis** | `core/agents/master_prime.py:241-287` | `perform_task_analysis()` | Change complexity logic |
| **Terminal Commands** | `core/terminal/security.py:87-100` | `safe_commands` set | Add/remove commands |
| **API Endpoints** | `core/server.py:356-415` | Route handlers | Add new endpoints |
| **WebSocket Messages** | `core/terminal/websocket_handler.py:228-263` | `handle_message()` | Add message types |
| **Frontend State** | `dashboard/src/stores/*.ts` | Zustand stores | Add new state |
| **React Components** | `dashboard/src/components/*.tsx` | Component logic | Add new UI |
| **Business Logic** | `core/services/business.py:100-200` | Service functions | Add operations |

---

## 🛠️ **DEBUGGING CHECKLIST** - When Things Break

### **Backend Issues**
1. **Check Logs**: `logs/openai/*.json` for API calls
2. **Agent Pool**: `core/orchestrator/coordinator.py:437-445` - get_pool_stats()
3. **Context Issues**: `.casper/context/*.ctx` files for corruption
4. **LLM Availability**: `core/services/llm.py:20-40` - available() check

### **Terminal Issues**
1. **Security Audit**: `core/terminal/security.py:322-334` - get_audit_summary()
2. **PTY Sessions**: `core/terminal/websocket_handler.py:720-732` - list_terminal_sessions
3. **WebSocket Status**: `core/terminal/websocket_handler.py:707-719` - get_terminal_status

### **Frontend Issues**
1. **Terminal Store**: `dashboard/src/stores/terminalStore.ts:143-159` - reset()
2. **WebSocket Connection**: Check browser dev tools Network tab
3. **Component Errors**: React error boundary in browser console

---

## 📚 **QUICK REFERENCE** - Copy/Paste Ready

### **Start Development**
```bash
# Backend (Terminal 1)
cd /path/to/casper
python3 -m core.server

# Frontend (Terminal 2)
cd dashboard && npm run dev

# Tests
pytest --cov=core tests/
```

### **Common File Paths**
```bash
# Core agent logic
core/agents/master_prime.py:181-240    # Main execution
core/agents/master_prime.py:624-640    # Agent spawning

# Terminal system
core/terminal/websocket_handler.py:130-200  # Connection setup
core/terminal/security.py:87-100            # Command whitelist

# Frontend terminal
dashboard/src/components/Terminal/TerminalComponent.tsx:18-80
dashboard/src/stores/terminalStore.ts:36-67

# API endpoints
core/server.py:356-415     # Task submission
core/server.py:242-250     # Terminal WebSocket
```

*This index eliminates codebase hunting - jump directly to exact locations for any modification.*