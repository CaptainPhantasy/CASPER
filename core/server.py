"""
FastAPI WebSocket Server for CASPER Prime.
Provides real-time updates and API endpoints.
"""

import asyncio
import json
from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import UUID, uuid4

import os
from pathlib import Path
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from dotenv import load_dotenv

from core.orchestrator.coordinator import AgentCoordinator
from core.orchestrator.task_analyzer import TaskAnalyzer
from core.context.manager import ContextManager
from core.agents.base import ProgressUpdate, TaskPriority, AgentStatus
from core.services.codebase import codebase_service


load_dotenv()
app = FastAPI(title="CASPER Prime API", version="0.1.0")

# CORS configuration
allowed_origins = [
    "http://localhost:3000",
    "http://localhost:5173",
    "http://127.0.0.1:5173",
    "http://localhost:9318",
    "http://127.0.0.1:9318",
]
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


# Global instances
coordinator: Optional[AgentCoordinator] = None
context_manager: Optional[ContextManager] = None
task_analyzer: Optional[TaskAnalyzer] = None
websocket_connections: List[WebSocket] = []


@app.on_event("startup")
async def startup_event():
    """Initialize CASPER Prime components."""
    global coordinator, context_manager, task_analyzer

    os.environ.setdefault("CASPER_PROJECT_ROOT", str(Path.cwd()))

    context_manager = ContextManager()
    coordinator = AgentCoordinator(context_manager)
    task_analyzer = TaskAnalyzer()

    await coordinator.start()

    # Register progress callback for WebSocket updates
    coordinator.register_progress_callback(broadcast_progress_update)

    print("CASPER Prime server started")


@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown."""
    if coordinator:
        await coordinator.stop()
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

            elif data.get("type") == "ping":
                # Respond to ping
                await websocket.send_json({"type": "pong"})

    except WebSocketDisconnect:
        websocket_connections.remove(websocket)
    except Exception as e:
        print(f"WebSocket error: {e}")
        if websocket in websocket_connections:
            websocket_connections.remove(websocket)


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


# REST API endpoints
@app.post("/api/task", response_model=TaskResponse)
async def submit_task(submission: TaskSubmission):
    """Submit a new task to CASPER Prime."""
    return await submit_task_internal(submission.task, submission.priority)


# Alias to plural endpoint for compatibility
@app.post("/api/tasks", response_model=TaskResponse)
async def submit_task_plural(submission: Dict[str, str]):
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


# Start background task
@app.on_event("startup")
async def start_background_tasks():
    """Start background tasks."""
    asyncio.create_task(periodic_context_update())


if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", "8742"))
    uvicorn.run(app, host="0.0.0.0", port=port)
@app.get("/api/health")
async def health():
    return {"status": "ok", "time": datetime.now().isoformat()}


# Codebase Management Endpoints
@app.post("/api/workspace/open")
async def open_workspace(request: WorkspaceRequest):
    """Open a workspace/codebase for editing."""
    try:
        result = codebase_service.open_workspace(request.path)
        return result
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/api/task/analyze")
async def analyze_task_endpoint(task_data: Dict[str, str]):
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


@app.get("/api/workspace/filetree")
async def get_file_tree():
    """Get the current workspace file tree."""
    try:
        file_tree = codebase_service.get_file_tree()
        return {"file_tree": file_tree, "files": file_tree}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/api/workspace/file")
async def read_file(request: FileRequest):
    """Read a file from the current workspace."""
    try:
        file_data = codebase_service.read_file(request.path)
        return file_data
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="File not found")
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.get("/api/workspace/file")
async def read_file_get(path: str = Query(..., description="Path to file relative to workspace root")):
    """Support GET variant for compatibility."""
    try:
        return codebase_service.read_file(path)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="File not found")
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.get("/api/workspace/info")
async def get_workspace_info():
    """Get current workspace information."""
    if not codebase_service.current_workspace:
        raise HTTPException(status_code=400, detail="No workspace opened")

    return codebase_service.get_workspace_info()


@app.get("/api/workspace/recent")
async def get_recent_workspaces():
    """List recently opened workspaces."""
    return {"recent": codebase_service.get_recent_workspaces()}


@app.get("/api/workspace/search")
async def search_workspace(query: str = Query(..., min_length=1), limit: int = Query(20, ge=1, le=100)):
    """Search for files within the active workspace."""
    if not codebase_service.current_workspace:
        raise HTTPException(status_code=400, detail="No workspace opened")
    return {"results": codebase_service.search_files(query, limit)}


@app.get("/api/settings")
async def get_settings():
    """Return the persisted settings for the active workspace."""
    if not codebase_service.current_workspace:
        raise HTTPException(status_code=400, detail="No workspace opened")
    info = codebase_service.get_workspace_info()
    return info.get("settings", {})


@app.put("/api/settings")
async def update_settings(payload: SettingsPayload):
    """Update settings for the active workspace."""
    if not codebase_service.current_workspace:
        raise HTTPException(status_code=400, detail="No workspace opened")
    return codebase_service.update_settings(payload.dict())
