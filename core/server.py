"""
FastAPI WebSocket Server for CASPER Prime.
Provides real-time updates and API endpoints.
"""

import asyncio
import json
import time
import re
from contextlib import asynccontextmanager, suppress
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional
from uuid import UUID, uuid4

import os
from pathlib import Path
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException, Query, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from dotenv import load_dotenv
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

from core.orchestrator.coordinator import AgentCoordinator
from core.orchestrator.task_analyzer import TaskAnalyzer
from core.context.manager import ContextManager
from core.agents.base import ProgressUpdate, TaskPriority, AgentStatus
from core.services.codebase import codebase_service
from core.services.approval import approval_service
from core.services.business import business_service
from core.services.development import development_service
from core.terminal import TerminalWebSocketHandler
from core.services.chat_service import chat_service
from core.routers import workspace as workspace_router
from core.routers import auth as auth_router
from core.routers import approvals as approvals_router
from core.routers import pipeline as pipeline_router
from core.routers import gateway as gateway_router
from core.services.metrics import (
    get_metrics,
    get_metrics_content_type,
    record_http_request,
    set_build_info,
)


load_dotenv()

# Rate limiter configuration - externalized via environment
limiter = Limiter(key_func=get_remote_address)
# Configurable rate limits via environment variables
TASK_RATE_LIMIT = os.environ.get("TASK_RATE_LIMIT", "10/minute")
ANALYSIS_RATE_LIMIT = os.environ.get("ANALYSIS_RATE_LIMIT", "20/minute")
FILE_RATE_LIMIT = os.environ.get("FILE_RATE_LIMIT", "120/minute")
FILETREE_RATE_LIMIT = os.environ.get("FILETREE_RATE_LIMIT", "60/minute")


@asynccontextmanager
async def lifespan(_: FastAPI):
    """Own server startup, periodic work, and deterministic cleanup."""
    await startup_event()
    background_task = asyncio.create_task(periodic_context_update())
    try:
        yield
    finally:
        background_task.cancel()
        with suppress(asyncio.CancelledError):
            await background_task
        await shutdown_event()


app = FastAPI(
    title="CASPER Prime API",
    version="0.1.0-beta.1",
    lifespan=lifespan,
)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
app.include_router(workspace_router.router)
app.include_router(auth_router.router)
app.include_router(approvals_router.router)
app.include_router(pipeline_router.router)
app.include_router(gateway_router.router)

# CORS configuration - externalized via environment
default_origins = [
    "http://localhost:3000",
    "http://localhost:5173",
    "http://127.0.0.1:5173",
    "http://localhost:9318",
    "http://127.0.0.1:9318",
]
cors_origins_env = os.environ.get("CORS_ALLOWED_ORIGINS", "")
allowed_origins = cors_origins_env.split(",") if cors_origins_env else default_origins
app.add_middleware(CORSMiddleware, allow_origins=allowed_origins, allow_credentials=True, allow_methods=["*"], allow_headers=["*"],)


# Request/Response Models
class TaskSubmission(BaseModel):
    task: str
    priority: str = "medium"


class TaskResponse(BaseModel):
    task_id: str
    status: str
    message: str


class SystemStatus(BaseModel):
    active_tasks: int
    queued_tasks: int
    total_agents: int
    busy_agents: int
    context_sessions: int


class WorkspaceRequest(BaseModel):
    path: str


class FileRequest(BaseModel):
    path: str


from pydantic import Field


class SettingsPayload(BaseModel):
    general: Dict[str, Any] = Field(default_factory=dict)
    agents: Dict[str, Any] = Field(default_factory=dict)
    repository: Dict[str, Any] = Field(default_factory=dict)


# Business API Request Models
class ProposalRequest(BaseModel):
    client_name: str
    project_description: str
    template_type: str = "standard"
    include_hours: bool = True


class EstimateRequest(BaseModel):
    project_description: str
    detailed: bool = True
    include_risks: bool = True


class InvoiceRequest(BaseModel):
    client_name: str
    project_name: str = ""
    hours: Optional[float] = None
    template: str = "standard"


class BusinessHistoryResponse(BaseModel):
    proposals: List[Dict[str, Any]]
    estimates: List[Dict[str, Any]]
    invoices: List[Dict[str, Any]]


# Development API Request Models
class MigrationRequest(BaseModel):
    action: str  # create, up, down, status, rollback
    name: Optional[str] = None


class SeedRequest(BaseModel):
    action: str  # run, create, rollback
    seeder_name: Optional[str] = None


class SecurityScanRequest(BaseModel):
    target: str = "all"  # all, deps, code
    auto_fix: bool = False


class LintRequest(BaseModel):
    file_pattern: Optional[str] = None
    auto_fix: bool = False
    scan_all: bool = False


class APIGenerationRequest(BaseModel):
    api_type: str  # rest, graphql
    resource_name: str
    include_crud: bool = False
    include_auth: bool = False


class LogAnalysisRequest(BaseModel):
    action: str = "tail"  # tail, search, errors
    pattern: Optional[str] = None
    follow: bool = False


# Global instances
coordinator: Optional[AgentCoordinator] = None
context_manager: Optional[ContextManager] = None
task_analyzer: Optional[TaskAnalyzer] = None
websocket_connections: List[WebSocket] = []
terminal_handler: Optional[TerminalWebSocketHandler] = None


async def startup_event():
    """Initialize CASPER Prime components."""
    global coordinator, context_manager, task_analyzer, terminal_handler

    os.environ.setdefault("CASPER_PROJECT_ROOT", str(Path.cwd()))

    context_manager = ContextManager()
    coordinator = AgentCoordinator(context_manager)
    task_analyzer = TaskAnalyzer()
    terminal_handler = TerminalWebSocketHandler()

    await coordinator.start()
    await terminal_handler.start()

    # Set build info for Prometheus metrics
    set_build_info(version="0.1.0-beta.1")

    # Register progress callback for WebSocket updates
    coordinator.register_progress_callback(broadcast_progress_update)

    # Register approval callback for WebSocket updates
    approval_service.add_notification_callback(broadcast_approval_request)

    print("CASPER Prime server started")


async def shutdown_event():
    """Cleanup on shutdown."""
    if coordinator:
        await coordinator.stop()
    if terminal_handler:
        await terminal_handler.stop()
    print("CASPER Prime server stopped")


# WebSocket endpoint
@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket connection for real-time updates."""
    await websocket.accept()
    websocket_connections.append(websocket)

    try:
        # Send initial connection confirmation
        await websocket.send_json({
            "type": "connection",
            "message": "Connected to CASPER Prime",
            "timestamp": datetime.now().isoformat()
        })

        # Keep connection alive and handle incoming messages
        while True:
            data = await websocket.receive_json()

            if data.get("type") == "submit_task":
                # Handle task submission via WebSocket
                task_response = await submit_task_internal(
                    data.get("task", ""),
                    data.get("priority", "medium")
                )
                await websocket.send_json({
                    "type": "task_submitted",
                    **task_response
                })

            elif data.get("type") == "chat_message":
                chat_message = data.get("message", "")
                session_id = data.get("session_id", "default")

                # Get response from ChatService
                response_message = await chat_service.get_chat_response(chat_message)

                # Send response back to the client
                await websocket.send_json({
                    "type": "agent_response",
                    "message": response_message,
                    "agent_role": "master",
                    "timestamp": datetime.now().isoformat()
                })

            elif data.get("type") == "ping":
                # Respond to ping
                await websocket.send_json({"type": "pong"})

    except WebSocketDisconnect:
        websocket_connections.remove(websocket)
    except Exception as e:
        print(f"WebSocket error: {e}")
        if websocket in websocket_connections:
            websocket_connections.remove(websocket)


# Terminal WebSocket endpoint
@app.websocket("/ws/terminal")
async def terminal_websocket_endpoint(websocket: WebSocket, token: str = Query(None)):
    """WebSocket endpoint for terminal sessions."""
    if terminal_handler:
        await terminal_handler.handle_connection(websocket, token)
    else:
        await websocket.close(code=1011, reason="Terminal handler not initialized")


async def broadcast_progress_update(update: ProgressUpdate):
    """Broadcast progress updates to all connected WebSocket clients."""
    update_data = {
        "type": "agent_update",
        "id": str(update.agent_id),
        "status": update.status.value if hasattr(update.status, 'value') else str(update.status),
        "progress": update.progress,
        "message": update.message,
        # Keep legacy top-level tokenUsage numeric
        "tokenUsage": update.token_usage.get("total", 0),
        "timestamp": update.timestamp.isoformat(),
        # Modern structured payload for UI store
        "data": {
            "status": update.status.value if hasattr(update.status, 'value') else str(update.status),
            "progress": update.progress,
            "token_usage": {
                "current": update.token_usage.get("total", 0),
                "limit": 1000000,
                "efficiency": 0,
            },
            "decisions": getattr(update, 'decisions', []),
            "context_size": update.token_usage.get("total", 0),
        },
    }

    # Broadcast to all connected clients
    disconnected = []
    for websocket in websocket_connections:
        try:
            await websocket.send_json(update_data)
        except:
            disconnected.append(websocket)

    # Remove disconnected clients
    for websocket in disconnected:
        if websocket in websocket_connections:
            websocket_connections.remove(websocket)


async def broadcast_context_update():
    """Broadcast context metrics to all clients."""
    if not coordinator:
        return

    stats = coordinator.get_coordinator_stats()
    total_tokens = stats.get("token_usage_total", 0)
    sessions = context_manager.get_active_sessions() if context_manager else []
    efficiency_scores: List[float] = []
    for session_id in sessions:
        metrics = context_manager.calculate_token_efficiency(session_id)
        efficiency_scores.append(metrics.get("efficiency_score", 0.0))

    efficiency = sum(efficiency_scores) / len(efficiency_scores) if efficiency_scores else 0.0

    cost_usd: Optional[float] = None
    cost_rate = os.environ.get("CASPER_COST_PER_1K_TOKENS")
    if cost_rate:
        try:
            rate_value = float(cost_rate)
            cost_usd = round((total_tokens / 1000) * rate_value, 4)
        except ValueError:
            cost_usd = None

    context_data = {
        "type": "context_update",
        "totalTokens": total_tokens,
        "efficiency": efficiency,
        "activeSessions": stats.get("context_sessions", 0)
    }

    if cost_usd is not None:
        context_data["costUSD"] = cost_usd

    disconnected = []
    for websocket in websocket_connections:
        try:
            await websocket.send_json(context_data)
        except:
            disconnected.append(websocket)

    for websocket in disconnected:
        if websocket in websocket_connections:
            websocket_connections.remove(websocket)


async def broadcast_approval_request(operation):
    """Broadcast approval requests to all connected WebSocket clients."""
    approval_data = {
        "type": "approval_request",
        **operation.to_dict()
    }

    disconnected = []
    for websocket in websocket_connections:
        try:
            await websocket.send_json(approval_data)
        except:
            disconnected.append(websocket)

    for websocket in disconnected:
        if websocket in websocket_connections:
            websocket_connections.remove(websocket)


# REST API endpoints
@app.post("/api/task", response_model=TaskResponse)
@limiter.limit(TASK_RATE_LIMIT)
async def submit_task(request: Request, submission: TaskSubmission):
    """Submit a new task to CASPER Prime."""
    return await submit_task_internal(submission.task, submission.priority)


# Alias to plural endpoint for compatibility
@app.post("/api/tasks", response_model=TaskResponse)
@limiter.limit(TASK_RATE_LIMIT)
async def submit_task_plural(request: Request, submission: Dict[str, str]):
    description = submission.get("description") or submission.get("task") or ""
    priority = submission.get("priority", "medium")
    return await submit_task_internal(description, priority)


async def submit_task_internal(task: str, priority: str) -> dict:
    """Internal task submission logic."""
    if not coordinator:
        raise HTTPException(status_code=503, detail="Coordinator not initialized")

    # Convert priority
    priority_map = {
        "high": TaskPriority.HIGH,
        "medium": TaskPriority.MEDIUM,
        "low": TaskPriority.LOW
    }
    task_priority = priority_map.get(priority.lower(), TaskPriority.MEDIUM)

    # Analyze task
    metrics, required_agents, _ = task_analyzer.analyze_task(task)

    # Submit to coordinator
    task_id = await coordinator.submit_task(task, task_priority)

    # Broadcast task submission
    task_data = {
        "type": "task_update",
        "id": str(task_id),
        "description": task[:200],
        "status": "pending",
        "priority": priority,
        "assignedAgents": [a.value for a in required_agents],
        "tokenUsage": 0,
        "createdAt": datetime.now().isoformat()
    }

    for websocket in websocket_connections:
        try:
            await websocket.send_json(task_data)
        except:
            pass

    return {
        "task_id": str(task_id),
        "status": "submitted",
        "message": f"Task submitted with {len(required_agents)} agents"
    }


@app.get("/api/status", response_model=SystemStatus)
async def get_system_status():
    """Get current system status."""
    if not coordinator:
        raise HTTPException(status_code=503, detail="Coordinator not initialized")

    stats = coordinator.get_coordinator_stats()

    return SystemStatus(
        active_tasks=stats["active_tasks"],
        queued_tasks=stats["queued_tasks"],
        total_agents=stats["agent_pool"]["total_agents"],
        busy_agents=stats["agent_pool"]["busy_agents"],
        context_sessions=stats["context_sessions"]
    )


@app.get("/api/task/{task_id}")
async def get_task_status(task_id: str):
    """Get status of a specific task."""
    if not coordinator:
        raise HTTPException(status_code=503, detail="Coordinator not initialized")

    try:
        task_uuid = UUID(task_id)
        status = await coordinator.get_task_status(task_uuid)
        return status
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid task ID")


@app.get("/api/tasks/{task_id}")
async def get_task_status_plural(task_id: str):
    return await get_task_status(task_id)


@app.get("/api/results")
async def get_recent_results(limit: int = 10):
    """Get recent task results."""
    if not coordinator:
        raise HTTPException(status_code=503, detail="Coordinator not initialized")

    results = await coordinator.get_results(limit)

    return [
        {
            "agent_id": str(r.agent_id),
            "agent_role": r.agent_role.value if hasattr(r.agent_role, 'value') else str(r.agent_role),
            "task_id": str(r.task_id),
            "status": r.status.value if hasattr(r.status, 'value') else str(r.status),
            "output": r.output[:500],  # Truncate long outputs
            "token_usage": r.token_usage,
            "errors": r.errors
        }
        for r in results
    ]


@app.get("/api/agents")
async def get_agent_pool_status():
    """Get current agent pool status."""
    if not coordinator:
        raise HTTPException(status_code=503, detail="Coordinator not initialized")

    stats = coordinator.agent_pool.get_pool_stats()
    return stats


# Background task for periodic updates
async def periodic_context_update():
    """Send periodic context updates to clients."""
    while True:
        await asyncio.sleep(5)  # Update every 5 seconds
        await broadcast_context_update()


@app.get("/api/health")
async def health():
    return {"status": "ok", "time": datetime.now().isoformat()}


@app.get("/metrics")
async def prometheus_metrics():
    """Prometheus metrics endpoint for monitoring and observability."""
    return Response(
        content=get_metrics(),
        media_type=get_metrics_content_type(),
    )


@app.get("/monitoring")
async def monitoring_dashboard():
    """Serve the CASPER monitoring dashboard HTML page."""
    from pathlib import Path
    dashboard_path = Path(__file__).parent.parent / "dashboard" / "monitoring.html"
    if dashboard_path.exists():
        return Response(
            content=dashboard_path.read_text(),
            media_type="text/html",
        )
    return Response(content="<h1>Monitoring dashboard not found</h1>", media_type="text/html")


@app.middleware("http")
async def metrics_middleware(request: Request, call_next):
    """Middleware to track HTTP request metrics."""
    start_time = time.time()
    response = await call_next(request)
    duration = time.time() - start_time
    # Normalize path to avoid high cardinality (strip IDs)
    path = request.url.path
    # Replace UUIDs and numeric IDs with placeholders
    path = re.sub(r"/[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}", "/{id}", path)
    path = re.sub(r"/\d+", "/{id}", path)
    record_http_request(
        method=request.method,
        path=path,
        status=response.status_code,
        duration=duration,
    )
    return response



@app.post("/api/task/analyze")
@limiter.limit(ANALYSIS_RATE_LIMIT)
async def analyze_task_endpoint(request: Request, task_data: Dict[str, str]):
    """Analyze a task to determine complexity and requirements."""
    if not task_analyzer:
        raise HTTPException(status_code=503, detail="Task analyzer not initialized")

    task_description = task_data.get("task") or task_data.get("description") or ""
    if not task_description.strip():
        raise HTTPException(status_code=400, detail="Task description is required")

    # Analyze the task
    metrics, required_agents, priority = task_analyzer.analyze_task(task_description)

    # Map AgentRole enum values to strings for frontend
    agent_roles = [role.value.replace("_prime", "").replace("_", " ").title() for role in required_agents]

    complexity_map = {
        1: "low", 2: "low", 3: "low", 4: "low",  # 1-4 -> low
        5: "medium", 6: "medium", 7: "medium",   # 5-7 -> medium
        8: "high", 9: "high", 10: "high"        # 8-10 -> high
    }
    complexity_score = task_analyzer._calculate_complexity_score(task_description.lower())
    complexity_level = complexity_map.get(complexity_score, "medium")

    priority_map = {
        TaskPriority.LOW: "low",
        TaskPriority.MEDIUM: "medium",
        TaskPriority.HIGH: "high"
    }
    suggested_priority = priority_map.get(priority, "medium")

    return {
        "complexity": complexity_level,
        "metrics": {
            "linesOfCode": metrics.lines_of_code_estimate,
            "files": metrics.file_count_estimate,
            "components": metrics.component_count,
            "integrationPoints": metrics.integration_points,
            "externalDependencies": metrics.external_dependencies,
            "estimatedTokens": metrics.lines_of_code_estimate * 2,  # Rough estimate
            "suggestedPriority": suggested_priority,
            "requiredAgents": agent_roles
        }
    }


# Approval System API Endpoints
@app.get("/api/approvals")
async def get_pending_approvals():
    """Get all pending approval requests."""
    return {
        "pending": approval_service.get_pending_approvals_dict(),
        "count": len(approval_service.pending_operations)
    }


@app.post("/api/approvals/{approval_id}/approve")
async def approve_operation(approval_id: str):
    """Approve a specific operation by ID."""
    success = approval_service.approve_operation(approval_id)
    if not success:
        raise HTTPException(status_code=404, detail="Approval request not found")

    # Broadcast approval update to WebSocket clients
    approval_update = {
        "type": "approval_response",
        "id": approval_id,
        "status": "approved",
        "timestamp": datetime.now().isoformat()
    }

    disconnected = []
    for websocket in websocket_connections:
        try:
            await websocket.send_json(approval_update)
        except:
            disconnected.append(websocket)

    for websocket in disconnected:
        if websocket in websocket_connections:
            websocket_connections.remove(websocket)

    return {"status": "approved", "id": approval_id}


@app.post("/api/approvals/{approval_id}/reject")
async def reject_operation(approval_id: str):
    """Reject a specific operation by ID."""
    success = approval_service.reject_operation(approval_id)
    if not success:
        raise HTTPException(status_code=404, detail="Approval request not found")

    # Broadcast rejection update to WebSocket clients
    approval_update = {
        "type": "approval_response",
        "id": approval_id,
        "status": "rejected",
        "timestamp": datetime.now().isoformat()
    }

    disconnected = []
    for websocket in websocket_connections:
        try:
            await websocket.send_json(approval_update)
        except:
            disconnected.append(websocket)

    for websocket in disconnected:
        if websocket in websocket_connections:
            websocket_connections.remove(websocket)

    return {"status": "rejected", "id": approval_id}


# Terminal Management API Endpoints
@app.get("/api/terminal/status")
async def get_terminal_status():
    """Get terminal handler status and statistics."""
    if not terminal_handler:
        raise HTTPException(status_code=503, detail="Terminal handler not initialized")

    stats = terminal_handler.get_connection_stats()
    return {
        "status": "running",
        "stats": stats,
        "timestamp": datetime.now().isoformat()
    }


@app.get("/api/terminal/sessions")
async def list_terminal_sessions():
    """List all active terminal sessions."""
    if not terminal_handler:
        raise HTTPException(status_code=503, detail="Terminal handler not initialized")

    sessions = terminal_handler.pty_manager.list_sessions()
    return {
        "sessions": sessions,
        "count": len(sessions)
    }


@app.post("/api/terminal/sessions/{session_id}/command")
async def execute_terminal_command(session_id: str, command_data: Dict[str, str]):
    """Execute a command in a specific terminal session."""
    if not terminal_handler:
        raise HTTPException(status_code=503, detail="Terminal handler not initialized")

    command = command_data.get("command", "")
    if not command:
        raise HTTPException(status_code=400, detail="Command is required")

    # Validate command through security middleware
    try:
        await terminal_handler.security.validate_input(command, session_id)
    except Exception as e:
        raise HTTPException(status_code=403, detail=f"Command blocked: {str(e)}")

    # Send command to session
    success = await terminal_handler.pty_manager.write_to_session(session_id, command + "\n")
    if not success:
        raise HTTPException(status_code=404, detail="Session not found or inactive")

    return {"status": "executed", "command": command, "session_id": session_id}


@app.get("/api/terminal/security/stats")
async def get_terminal_security_stats():
    """Get terminal security statistics and audit log."""
    if not terminal_handler:
        raise HTTPException(status_code=503, detail="Terminal handler not initialized")

    summary = terminal_handler.security.get_audit_summary(hours=24)
    return {
        "status": "active",
        "security_enabled": True,
        "audit_summary": summary,
        "timestamp": datetime.now().isoformat()
    }


@app.get("/api/terminal/security/audit")
async def get_security_audit_log(hours: int = 24, risk_level: str = None):
    """Get detailed security audit log."""
    if not terminal_handler:
        raise HTTPException(status_code=503, detail="Terminal handler not initialized")

    cutoff_time = datetime.now() - timedelta(hours=hours)

    # Filter audit events
    filtered_events = []
    for event in terminal_handler.security.audit_log:
        if event.timestamp >= cutoff_time:
            if not risk_level or event.risk_level.value == risk_level:
                filtered_events.append(event.to_dict())

    return {
        "events": filtered_events,
        "total_events": len(filtered_events),
        "hours": hours,
        "risk_level_filter": risk_level
    }


@app.post("/api/terminal/security/validate")
async def validate_command_security(command_data: Dict[str, str]):
    """Validate a command against security policies without executing."""
    if not terminal_handler:
        raise HTTPException(status_code=503, detail="Terminal handler not initialized")

    command = command_data.get("command", "")
    if not command:
        raise HTTPException(status_code=400, detail="Command is required")

    session_id = command_data.get("session_id", "validation_test")
    user_id = command_data.get("user_id")

    try:
        await terminal_handler.security.validate_command(command, session_id, user_id)
        return {
            "valid": True,
            "command": command,
            "message": "Command passed security validation"
        }
    except Exception as e:
        return {
            "valid": False,
            "command": command,
            "reason": str(e),
            "message": "Command blocked by security policy"
        }


@app.get("/api/terminal/sessions/active")
async def get_active_terminal_sessions():
    """Get detailed information about active terminal sessions."""
    if not terminal_handler:
        raise HTTPException(status_code=503, detail="Terminal handler not initialized")

    sessions = terminal_handler.get_active_sessions()
    return {
        "sessions": sessions,
        "count": len(sessions),
        "timestamp": datetime.now().isoformat()
    }


@app.get("/api/approvals/{approval_id}")
async def get_approval_details(approval_id: str):
    """Get details of a specific approval request."""
    operation = approval_service.get_operation_by_id(approval_id)
    if not operation:
        raise HTTPException(status_code=404, detail="Approval request not found")
    return operation.to_dict()


# Development API Endpoints
@app.post("/api/dev/migrate")
async def database_migration(request: MigrationRequest):
    """Database migration management."""
    try:
        result = await development_service.manage_migration(request.action, request.name)
        return {
            "success": result,
            "action": request.action,
            "name": request.name,
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Migration failed: {str(e)}")


@app.post("/api/dev/seed")
async def database_seeding(request: SeedRequest):
    """Database seeding management."""
    try:
        result = await development_service.manage_seeding(request.action, request.seeder_name)
        return {
            "success": result,
            "action": request.action,
            "seeder_name": request.seeder_name,
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Seeding failed: {str(e)}")


@app.post("/api/dev/scan")
async def security_scan(request: SecurityScanRequest):
    """Security vulnerability scanning."""
    try:
        issues = await development_service.security_scan(request.target, request.auto_fix)

        # Group issues by severity
        summary = {
            "critical": len([i for i in issues if i.severity == "critical"]),
            "high": len([i for i in issues if i.severity == "high"]),
            "medium": len([i for i in issues if i.severity == "medium"]),
            "low": len([i for i in issues if i.severity == "low"])
        }

        return {
            "success": True,
            "target": request.target,
            "auto_fix": request.auto_fix,
            "summary": summary,
            "total_issues": len(issues),
            "issues": [{
                "severity": issue.severity,
                "type": issue.type,
                "package": issue.package,
                "version": issue.version,
                "description": issue.description,
                "recommendation": issue.recommendation
            } for issue in issues],
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Security scan failed: {str(e)}")


@app.post("/api/dev/lint")
async def code_linting(request: LintRequest):
    """Code linting with auto-fix capabilities."""
    try:
        results = await development_service.run_linting(
            request.file_pattern,
            request.auto_fix,
            request.scan_all
        )

        total_issues = sum(r.total for r in results)
        fixable_issues = sum(r.fixable for r in results)

        return {
            "success": True,
            "file_pattern": request.file_pattern,
            "auto_fix": request.auto_fix,
            "scan_all": request.scan_all,
            "summary": {
                "files_checked": len(results),
                "total_issues": total_issues,
                "fixable_issues": fixable_issues
            },
            "results": [{
                "file": result.file,
                "total": result.total,
                "fixable": result.fixable,
                "issues": result.issues
            } for result in results],
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Linting failed: {str(e)}")


@app.post("/api/dev/api-gen")
async def api_generation(request: APIGenerationRequest):
    """Generate REST/GraphQL API scaffolding."""
    try:
        result = await development_service.generate_api(
            request.api_type,
            request.resource_name,
            request.include_crud,
            request.include_auth
        )

        return {
            "success": result,
            "api_type": request.api_type,
            "resource_name": request.resource_name,
            "include_crud": request.include_crud,
            "include_auth": request.include_auth,
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"API generation failed: {str(e)}")


@app.get("/api/dev/logs")
async def log_analysis(
    action: str = "tail",
    pattern: Optional[str] = None,
    follow: bool = False
):
    """Intelligent log analysis and error detection."""
    try:
        result = await development_service.analyze_logs(action, pattern, follow)

        return {
            "success": result,
            "action": action,
            "pattern": pattern,
            "follow": follow,
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Log analysis failed: {str(e)}")


# Business Operations API Endpoints
@app.post("/api/business/proposal")
async def create_proposal(request: ProposalRequest):
    """Generate AI-powered business proposal."""
    try:
        success = await business_service.generate_proposal(
            client_name=request.client_name,
            project_description=request.project_description,
            template_type=request.template_type,
            include_hours=request.include_hours
        )

        if success:
            return {
                "success": True,
                "message": f"Proposal generated for {request.client_name}",
                "client": request.client_name,
                "template": request.template_type,
                "timestamp": datetime.now().isoformat()
            }
        else:
            raise HTTPException(status_code=500, detail="Failed to generate proposal")

    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/api/business/estimate")
async def create_estimate(request: EstimateRequest):
    """Generate AI-powered project estimation."""
    try:
        estimate = await business_service.estimate_project(
            project_description=request.project_description,
            detailed=request.detailed,
            include_risks=request.include_risks
        )

        return {
            "success": True,
            "project_name": estimate.project_name,
            "total_hours": estimate.total_hours,
            "total_cost": estimate.total_cost,
            "breakdown": estimate.breakdown,
            "risks": estimate.risks,
            "confidence_level": estimate.confidence_level,
            "rate_per_hour": estimate.rate_per_hour,
            "timestamp": datetime.now().isoformat()
        }

    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/api/business/invoice")
async def create_invoice(request: InvoiceRequest):
    """Generate professional invoice."""
    try:
        success = await business_service.generate_invoice(
            client_name=request.client_name,
            project_name=request.project_name or None,
            hours=request.hours,
            template=request.template
        )

        if success:
            return {
                "success": True,
                "message": f"Invoice generated for {request.client_name}",
                "client": request.client_name,
                "project": request.project_name,
                "hours": request.hours,
                "template": request.template,
                "timestamp": datetime.now().isoformat()
            }
        else:
            raise HTTPException(status_code=500, detail="Failed to generate invoice")

    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.get("/api/business/history")
async def get_business_history():
    """Get history of business operations (proposals, estimates, invoices)."""
    try:
        # Read business directories
        proposals = []
        estimates = []
        invoices = []

        # Get proposals
        proposals_dir = business_service.proposals_dir
        if proposals_dir.exists():
            for proposal_file in proposals_dir.glob("*.md"):
                try:
                    stat = proposal_file.stat()
                    proposals.append({
                        "filename": proposal_file.name,
                        "path": str(proposal_file),
                        "created_at": datetime.fromtimestamp(stat.st_ctime).isoformat(),
                        "modified_at": datetime.fromtimestamp(stat.st_mtime).isoformat(),
                        "size": stat.st_size
                    })
                except Exception:
                    continue

        # Get estimates
        estimates_dir = business_service.estimates_dir
        if estimates_dir.exists():
            for estimate_file in estimates_dir.glob("*.json"):
                try:
                    with open(estimate_file, 'r') as f:
                        estimate_data = json.load(f)
                    estimates.append({
                        "filename": estimate_file.name,
                        "path": str(estimate_file),
                        "project": estimate_data.get("project", "Unknown"),
                        "total_hours": estimate_data.get("total_hours", 0),
                        "total_cost": estimate_data.get("total_cost", 0),
                        "confidence": estimate_data.get("confidence", "Medium"),
                        "created_at": estimate_data.get("created_at", ""),
                        "risks_count": len(estimate_data.get("risks", []))
                    })
                except Exception:
                    continue

        # Get invoices
        invoices_dir = business_service.invoices_dir
        if invoices_dir.exists():
            for invoice_file in invoices_dir.glob("*.json"):
                try:
                    with open(invoice_file, 'r') as f:
                        invoice_data = json.load(f)
                    invoices.append({
                        "filename": invoice_file.name,
                        "invoice_number": invoice_data.get("invoice_number", ""),
                        "client": invoice_data.get("client", ""),
                        "project": invoice_data.get("project", ""),
                        "hours": invoice_data.get("hours", 0),
                        "total": invoice_data.get("total", 0),
                        "created_at": invoice_data.get("created_at", ""),
                        "due_date": invoice_data.get("due_date", "")
                    })
                except Exception:
                    continue

        # Sort by created_at (most recent first)
        proposals.sort(key=lambda x: x.get("created_at", ""), reverse=True)
        estimates.sort(key=lambda x: x.get("created_at", ""), reverse=True)
        invoices.sort(key=lambda x: x.get("created_at", ""), reverse=True)

        return {
            "proposals": proposals,
            "estimates": estimates,
            "invoices": invoices,
            "summary": {
                "total_proposals": len(proposals),
                "total_estimates": len(estimates),
                "total_invoices": len(invoices),
                "total_invoice_amount": sum(inv.get("total", 0) for inv in invoices)
            },
            "timestamp": datetime.now().isoformat()
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to retrieve business history: {str(e)}")


if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", "8742"))
    uvicorn.run(app, host="0.0.0.0", port=port)
