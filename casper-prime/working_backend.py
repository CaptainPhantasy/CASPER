
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import uvicorn
import json
import uuid
from datetime import datetime

app = FastAPI(title="CASPER Prime API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# In-memory storage
agents = {}
tasks = {}
connections = []

@app.get("/")
async def root():
    return {"message": "CASPER Prime API Running"}

@app.get("/health")
async def health():
    return {"status": "healthy", "timestamp": datetime.now().isoformat()}

@app.get("/api/agents")
async def get_agents():
    return list(agents.values())

@app.post("/api/tasks")
async def create_task(data: dict = {}):
    task_id = str(uuid.uuid4())
    task = {
        "id": task_id,
        "description": data.get("description", "Test task"),
        "status": "queued",
        "created_at": datetime.now().isoformat()
    }
    tasks[task_id] = task
    
    # Simulate agent spawn
    agent = {
        "id": str(uuid.uuid4()),
        "type": "Master",
        "status": "planning",
        "currentTask": task["description"],
        "progress": 25,
        "startedAt": datetime.now().timestamp() * 1000
    }
    agents[agent["id"]] = agent
    
    # Broadcast to WebSocket clients
    for connection in connections:
        try:
            await connection.send_json({
                "type": "agent_spawned",
                "data": agent
            })
        except:
            pass
    
    return task

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    connections.append(websocket)
    
    try:
        # Send initial connection message
        await websocket.send_json({
            "type": "connected",
            "data": {"message": "Connected to CASPER Prime"}
        })
        
        while True:
            data = await websocket.receive_text()
            # Echo back
            await websocket.send_json({
                "type": "message",
                "data": json.loads(data)
            })
    except WebSocketDisconnect:
        connections.remove(websocket)

if __name__ == "__main__":
    print("Starting CASPER Prime Backend on port 8742...")
    uvicorn.run(app, host="0.0.0.0", port=8742)
