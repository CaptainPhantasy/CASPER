#!/usr/bin/env python3
"""
CASPER Prime - Working Implementation
This WILL work. No complex imports, no npm issues.
"""

import os
import sys
import subprocess
import time
import asyncio
from pathlib import Path
from datetime import datetime

BASE_DIR = Path("/Volumes/Storage/Development/CASPER DEV/casper-prime")

# Create a simple working backend
def create_working_backend():
    backend_code = '''
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
'''
    
    backend_file = BASE_DIR / "working_backend.py"
    backend_file.write_text(backend_code)
    print("✅ Created working backend")
    return backend_file

# Create a simple HTML dashboard
def create_working_dashboard():
    dashboard_html = '''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>CASPER Prime Dashboard</title>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
            background: linear-gradient(135deg, #1e3c72 0%, #2a5298 100%);
            color: white;
            padding: 20px;
            min-height: 100vh;
        }
        
        .container {
            max-width: 1400px;
            margin: 0 auto;
        }
        
        h1 {
            text-align: center;
            margin-bottom: 30px;
            font-size: 2.5rem;
            text-shadow: 2px 2px 4px rgba(0,0,0,0.3);
        }
        
        .status {
            background: rgba(255,255,255,0.1);
            padding: 15px;
            border-radius: 10px;
            margin-bottom: 20px;
            display: flex;
            justify-content: space-around;
        }
        
        .status-item {
            text-align: center;
        }
        
        .status-dot {
            width: 10px;
            height: 10px;
            background: #00ff00;
            border-radius: 50%;
            display: inline-block;
            animation: pulse 2s infinite;
        }
        
        @keyframes pulse {
            0% { opacity: 1; }
            50% { opacity: 0.5; }
            100% { opacity: 1; }
        }
        
        .task-input {
            background: rgba(255,255,255,0.1);
            padding: 20px;
            border-radius: 10px;
            margin-bottom: 30px;
        }
        
        #taskInput {
            width: 100%;
            padding: 15px;
            font-size: 16px;
            border: 2px solid rgba(255,255,255,0.3);
            border-radius: 5px;
            background: rgba(255,255,255,0.1);
            color: white;
            margin-bottom: 15px;
        }
        
        #taskInput::placeholder {
            color: rgba(255,255,255,0.6);
        }
        
        #submitBtn {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            border: none;
            padding: 15px 30px;
            font-size: 16px;
            border-radius: 5px;
            cursor: pointer;
            transition: transform 0.2s;
        }
        
        #submitBtn:hover {
            transform: scale(1.05);
        }
        
        .pipeline {
            display: grid;
            grid-template-columns: repeat(5, 1fr);
            gap: 15px;
        }
        
        .column {
            background: rgba(255,255,255,0.1);
            padding: 15px;
            border-radius: 10px;
            min-height: 200px;
        }
        
        .column h3 {
            margin-bottom: 15px;
            font-size: 1.1rem;
            opacity: 0.9;
        }
        
        .agent-card {
            background: rgba(255,255,255,0.2);
            padding: 10px;
            border-radius: 5px;
            margin-bottom: 10px;
            animation: slideIn 0.5s;
        }
        
        @keyframes slideIn {
            from {
                opacity: 0;
                transform: translateX(-20px);
            }
            to {
                opacity: 1;
                transform: translateX(0);
            }
        }
        
        #wsStatus {
            position: fixed;
            top: 20px;
            right: 20px;
            padding: 10px 20px;
            background: rgba(0,0,0,0.5);
            border-radius: 20px;
            font-size: 14px;
        }
    </style>
</head>
<body>
    <div id="wsStatus">
        <span class="status-dot"></span> <span id="statusText">Connecting...</span>
    </div>
    
    <div class="container">
        <h1>🚀 CASPER Prime Dashboard</h1>
        
        <div class="status">
            <div class="status-item">
                <strong>Backend:</strong> <span id="backendStatus">Checking...</span>
            </div>
            <div class="status-item">
                <strong>Agents:</strong> <span id="agentCount">0</span>
            </div>
            <div class="status-item">
                <strong>Tasks:</strong> <span id="taskCount">0</span>
            </div>
        </div>
        
        <div class="task-input">
            <input type="text" id="taskInput" placeholder="Describe what you want to build... (e.g., 'Build a user authentication system')">
            <button id="submitBtn">Submit Task</button>
        </div>
        
        <div class="pipeline">
            <div class="column">
                <h3>📋 Queued</h3>
                <div id="queued"></div>
            </div>
            <div class="column">
                <h3>🔍 Planning</h3>
                <div id="planning"></div>
            </div>
            <div class="column">
                <h3>🔨 Building</h3>
                <div id="building"></div>
            </div>
            <div class="column">
                <h3>✅ Reviewing</h3>
                <div id="reviewing"></div>
            </div>
            <div class="column">
                <h3>🚢 Shipped</h3>
                <div id="shipped"></div>
            </div>
        </div>
    </div>
    
    <script>
        let ws = null;
        let agents = new Map();
        
        // Check backend health
        async function checkBackend() {
            try {
                const response = await fetch('http://localhost:8742/health');
                const data = await response.json();
                if (data.status === 'healthy') {
                    document.getElementById('backendStatus').textContent = '✅ Online';
                }
            } catch (e) {
                document.getElementById('backendStatus').textContent = '❌ Offline';
            }
        }
        
        // Connect WebSocket
        function connectWebSocket() {
            ws = new WebSocket('ws://localhost:8742/ws');
            
            ws.onopen = () => {
                document.getElementById('statusText').textContent = 'Connected';
                document.querySelector('.status-dot').style.background = '#00ff00';
            };
            
            ws.onmessage = (event) => {
                const data = JSON.parse(event.data);
                console.log('WebSocket message:', data);
                
                if (data.type === 'agent_spawned') {
                    addAgent(data.data);
                }
            };
            
            ws.onclose = () => {
                document.getElementById('statusText').textContent = 'Disconnected';
                document.querySelector('.status-dot').style.background = '#ff0000';
                setTimeout(connectWebSocket, 3000);
            };
        }
        
        // Add agent to pipeline
        function addAgent(agent) {
            agents.set(agent.id, agent);
            updateAgentCount();
            
            const card = document.createElement('div');
            card.className = 'agent-card';
            card.innerHTML = \`
                <div style="font-weight: bold;">\${agent.type}</div>
                <div style="font-size: 12px; opacity: 0.8;">\${agent.currentTask || 'Idle'}</div>
                <div style="margin-top: 5px;">
                    <div style="background: rgba(255,255,255,0.2); height: 4px; border-radius: 2px;">
                        <div style="background: #00ff00; height: 100%; width: \${agent.progress || 0}%; border-radius: 2px;"></div>
                    </div>
                </div>
            \`;
            
            const column = document.getElementById(agent.status) || document.getElementById('planning');
            column.appendChild(card);
        }
        
        function updateAgentCount() {
            document.getElementById('agentCount').textContent = agents.size;
        }
        
        // Submit task
        document.getElementById('submitBtn').addEventListener('click', async () => {
            const input = document.getElementById('taskInput');
            const task = input.value.trim();
            
            if (!task) return;
            
            try {
                const response = await fetch('http://localhost:8742/api/tasks', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({description: task})
                });
                
                if (response.ok) {
                    input.value = '';
                    document.getElementById('taskCount').textContent = 
                        parseInt(document.getElementById('taskCount').textContent) + 1;
                }
            } catch (e) {
                console.error('Failed to submit task:', e);
            }
        });
        
        // Enter key to submit
        document.getElementById('taskInput').addEventListener('keypress', (e) => {
            if (e.key === 'Enter') {
                document.getElementById('submitBtn').click();
            }
        });
        
        // Initialize
        checkBackend();
        connectWebSocket();
        setInterval(checkBackend, 5000);
    </script>
</body>
</html>'''
    
    dashboard_file = BASE_DIR / "dashboard" / "working_dashboard.html"
    dashboard_file.write_text(dashboard_html)
    print("✅ Created working dashboard")
    return dashboard_file

# Simple HTTP server for dashboard
def create_dashboard_server():
    server_code = '''
import http.server
import socketserver
import os

os.chdir("/Volumes/Storage/Development/CASPER DEV/casper-prime/dashboard")

class MyHTTPRequestHandler(http.server.SimpleHTTPRequestHandler):
    def end_headers(self):
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', '*')
        super().end_headers()
    
    def do_GET(self):
        if self.path == '/':
            self.path = '/working_dashboard.html'
        return super().do_GET()

PORT = 9318
with socketserver.TCPServer(("", PORT), MyHTTPRequestHandler) as httpd:
    print(f"Dashboard serving at http://localhost:{PORT}")
    httpd.serve_forever()
'''
    
    server_file = BASE_DIR / "dashboard_server.py"
    server_file.write_text(server_code)
    print("✅ Created dashboard server")
    return server_file

# Test with Playwright
async def test_working_solution():
    from playwright.async_api import async_playwright
    
    print("\n🧪 TESTING WITH PLAYWRIGHT")
    print("="*50)
    
    screenshots_dir = BASE_DIR / "test_screenshots"
    screenshots_dir.mkdir(exist_ok=True)
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False, slow_mo=300)
        page = await browser.new_page()
        
        results = []
        
        try:
            # Test 1: Backend health
            print("Testing backend health...")
            await page.goto("http://localhost:8742/health")
            await page.screenshot(path=screenshots_dir / "backend_health.png", full_page=True)
            content = await page.content()
            results.append(("Backend Health", "healthy" in content))
            
            # Test 2: Dashboard loads
            print("Testing dashboard...")
            await page.goto("http://localhost:9318")
            await page.wait_for_timeout(2000)
            await page.screenshot(path=screenshots_dir / "dashboard.png", full_page=True)
            
            # Test 3: Task input exists
            task_input = await page.query_selector('#taskInput')
            results.append(("Task Input", task_input is not None))
            
            # Test 4: Submit a task
            if task_input:
                print("Testing task submission...")
                await task_input.type("Build a REST API for user management")
                await page.screenshot(path=screenshots_dir / "task_typed.png", full_page=True)
                
                await page.click('#submitBtn')
                await page.wait_for_timeout(2000)
                await page.screenshot(path=screenshots_dir / "task_submitted.png", full_page=True)
                
                # Check if agent appeared
                agent_cards = await page.query_selector_all('.agent-card')
                results.append(("Task Submission", len(agent_cards) > 0))
            
            # Keep open for inspection
            await page.wait_for_timeout(5000)
            
        finally:
            await browser.close()
    
    # Print results
    print("\n" + "="*50)
    print("TEST RESULTS")
    print("="*50)
    for test, passed in results:
        status = "✅" if passed else "❌"
        print(f"{status} {test}")
    
    return all(p for _, p in results)

# Main execution
async def main():
    os.chdir(BASE_DIR)
    
    print("\n🚀 CASPER PRIME - CREATING WORKING SOLUTION")
    print("="*50)
    
    # Kill any existing processes
    subprocess.run("lsof -ti:8742 | xargs kill -9", shell=True, stderr=subprocess.DEVNULL)
    subprocess.run("lsof -ti:9318 | xargs kill -9", shell=True, stderr=subprocess.DEVNULL)
    time.sleep(2)
    
    # Create working files
    backend_file = create_working_backend()
    dashboard_file = create_working_dashboard()
    server_file = create_dashboard_server()
    
    # Start backend
    print("\n🚀 Starting backend...")
    backend_proc = subprocess.Popen(
        [sys.executable, str(backend_file)],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE
    )
    
    # Start dashboard server
    print("🚀 Starting dashboard...")
    dashboard_proc = subprocess.Popen(
        [sys.executable, str(server_file)],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE
    )
    
    # Wait for services to start
    print("⏳ Waiting for services to start...")
    time.sleep(5)
    
    # Test with Playwright
    success = await test_working_solution()
    
    if success:
        print("\n" + "="*50)
        print("✅ CASPER PRIME IS WORKING!")
        print("="*50)
        print("\nAccess at: http://localhost:9318")
        print("Backend API: http://localhost:8742")
        print("\nPress Ctrl+C to stop")
        
        # Keep running
        try:
            while True:
                await asyncio.sleep(1)
        except KeyboardInterrupt:
            pass
    else:
        print("\n⚠️ Some tests failed, but services are running.")
        print("Check http://localhost:9318 manually.")
    
    # Cleanup
    backend_proc.terminate()
    dashboard_proc.terminate()

if __name__ == "__main__":
    asyncio.run(main())
