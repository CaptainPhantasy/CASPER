#!/usr/bin/env python3
"""
CASPER Prime Network Diagnostic and Fix
Finds out why your browser can't connect
"""

import subprocess
import socket
import time
import sys
import os
from pathlib import Path

def run_cmd(cmd):
    """Run command and return output"""
    try:
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
        return result.stdout.strip()
    except:
        return ""

def diagnose_network():
    print("\n🔍 NETWORK DIAGNOSTIC FOR CASPER PRIME")
    print("="*60)
    
    issues = []
    
    # 1. Check macOS firewall status
    print("\n1. Checking macOS Firewall...")
    firewall_status = run_cmd("/usr/libexec/ApplicationFirewall/socketfilterfw --getglobalstate")
    print(f"   Firewall: {firewall_status}")
    if "enabled" in firewall_status.lower():
        issues.append("firewall_enabled")
        
    # 2. Check if Python is allowed through firewall
    print("\n2. Checking Python firewall permissions...")
    allowed_apps = run_cmd("/usr/libexec/ApplicationFirewall/socketfilterfw --listapps")
    if "python" not in allowed_apps.lower():
        print("   ⚠️  Python may not be allowed through firewall")
        issues.append("python_not_allowed")
    else:
        print("   ✓ Python appears in firewall list")
    
    # 3. Test port binding
    print("\n3. Testing port availability...")
    for port in [8742, 9318]:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        # Test localhost binding
        try:
            sock.bind(('127.0.0.1', port))
            sock.close()
            print(f"   ✓ Port {port} available on localhost")
        except:
            print(f"   ❌ Port {port} blocked on localhost")
            issues.append(f"port_{port}_blocked")
            
        # Test all interfaces binding
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            sock.bind(('0.0.0.0', port))
            sock.close()
            print(f"   ✓ Port {port} available on all interfaces")
        except:
            print(f"   ❌ Port {port} blocked on all interfaces")
            
    # 4. Check for port conflicts
    print("\n4. Checking for conflicting processes...")
    for port in [8742, 9318]:
        result = run_cmd(f"lsof -i:{port}")
        if result:
            print(f"   ⚠️  Port {port} is in use:")
            print(f"      {result[:100]}")
            issues.append(f"port_{port}_conflict")
        else:
            print(f"   ✓ Port {port} is free")
            
    # 5. Check Chrome settings
    print("\n5. Chrome Security Check...")
    print("   Chrome may block localhost if:")
    print("   • Running in Incognito mode with extensions disabled")
    print("   • Security software is intercepting connections")
    print("   • Corporate proxy settings are interfering")
    
    # 6. Network interface check
    print("\n6. Network Interfaces...")
    interfaces = run_cmd("ifconfig | grep 'inet ' | grep -v '127.0.0.1'")
    print(f"   Active interfaces:\n   {interfaces}")
    
    return issues

def fix_issues(issues):
    print("\n🔧 APPLYING FIXES")
    print("="*60)
    
    if "firewall_enabled" in issues or "python_not_allowed" in issues:
        print("\n📍 Firewall Fix:")
        print("   We need to allow incoming connections to Python.")
        print("   Run this command in Terminal:")
        print("   sudo /usr/libexec/ApplicationFirewall/socketfilterfw --add /usr/bin/python3")
        print("   sudo /usr/libexec/ApplicationFirewall/socketfilterfw --unblockapp /usr/bin/python3")
        
    # Create a server that binds to all interfaces
    print("\n📍 Creating server with proper binding...")
    
    backend_code = '''
import uvicorn
from fastapi import FastAPI, WebSocket
from fastapi.middleware.cors import CORSMiddleware
from datetime import datetime

app = FastAPI()

# CRITICAL: Allow ALL origins for debugging
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow everything
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
async def root():
    return {"message": "CASPER Prime is running", "time": str(datetime.now())}

@app.get("/health")
async def health():
    return {"status": "healthy", "timestamp": str(datetime.now())}

@app.get("/test")
async def test():
    return {"test": "If you see this, the connection works!"}

if __name__ == "__main__":
    print("Starting on ALL network interfaces (0.0.0.0)")
    print("This allows connections from:")
    print("  - http://localhost:8742")
    print("  - http://127.0.0.1:8742")
    print("  - http://0.0.0.0:8742")
    print("  - http://[your-local-ip]:8742")
    uvicorn.run(app, host="0.0.0.0", port=8742, log_level="info")
'''
    
    Path("/tmp/test_backend.py").write_text(backend_code)
    
    # Create simple HTML test page
    html = '''<!DOCTYPE html>
<html>
<head><title>CASPER Connection Test</title></head>
<body style="font-family: Arial; padding: 40px; background: #1a1a1a; color: white;">
    <h1>🔌 CASPER Prime Connection Test</h1>
    
    <div id="status" style="margin: 20px 0; padding: 20px; background: #333; border-radius: 10px;">
        <h2>Testing Connections...</h2>
        <p>Backend API: <span id="backend">Testing...</span></p>
        <p>Direct Fetch: <span id="fetch">Testing...</span></p>
        <p>XMLHttpRequest: <span id="xhr">Testing...</span></p>
        <p>WebSocket: <span id="ws">Testing...</span></p>
    </div>
    
    <div id="results" style="margin: 20px 0; padding: 20px; background: #333; border-radius: 10px;">
        <h3>Connection Methods:</h3>
        <button onclick="testAll()">Test All Connections</button>
        <button onclick="testAlternatives()">Test Alternative Ports</button>
    </div>
    
    <script>
        async function testBackend() {
            try {
                const response = await fetch('http://localhost:8742/test');
                const data = await response.json();
                document.getElementById('backend').innerHTML = '✅ Connected: ' + JSON.stringify(data);
            } catch(e) {
                document.getElementById('backend').innerHTML = '❌ Failed: ' + e.message;
            }
        }
        
        function testXHR() {
            const xhr = new XMLHttpRequest();
            xhr.open('GET', 'http://localhost:8742/health', true);
            xhr.onload = function() {
                if (xhr.status === 200) {
                    document.getElementById('xhr').innerHTML = '✅ XHR Works';
                }
            };
            xhr.onerror = function() {
                document.getElementById('xhr').innerHTML = '❌ XHR Failed';
            };
            xhr.send();
        }
        
        function testWebSocket() {
            try {
                const ws = new WebSocket('ws://localhost:8742/ws');
                ws.onopen = () => {
                    document.getElementById('ws').innerHTML = '✅ WebSocket Connected';
                    ws.close();
                };
                ws.onerror = () => {
                    document.getElementById('ws').innerHTML = '❌ WebSocket Failed';
                };
            } catch(e) {
                document.getElementById('ws').innerHTML = '❌ WebSocket Error: ' + e.message;
            }
        }
        
        function testAll() {
            testBackend();
            testXHR();
            testWebSocket();
        }
        
        function testAlternatives() {
            // Try different addresses
            const addresses = ['127.0.0.1', '0.0.0.0', window.location.hostname];
            addresses.forEach(addr => {
                fetch(`http://${addr}:8742/test`)
                    .then(r => r.json())
                    .then(d => console.log(`✅ ${addr} works:`, d))
                    .catch(e => console.log(`❌ ${addr} failed:`, e));
            });
        }
        
        // Auto-test on load
        window.onload = testAll;
    </script>
</body>
</html>'''
    
    Path("/tmp/test_connection.html").write_text(html)
    
    print("   ✓ Created test backend: /tmp/test_backend.py")
    print("   ✓ Created test page: /tmp/test_connection.html")

def start_test_server():
    print("\n🚀 STARTING TEST SERVER")
    print("="*60)
    
    # Kill any existing processes
    subprocess.run("lsof -ti:8742 | xargs kill -9", shell=True, stderr=subprocess.DEVNULL)
    subprocess.run("lsof -ti:9318 | xargs kill -9", shell=True, stderr=subprocess.DEVNULL)
    time.sleep(2)
    
    # Start backend with explicit binding
    print("Starting backend on 0.0.0.0:8742 (all interfaces)...")
    backend_proc = subprocess.Popen(
        [sys.executable, "/tmp/test_backend.py"],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT
    )
    
    # Wait and check output
    time.sleep(3)
    
    # Test from Python directly
    print("\n📍 Testing from Python:")
    import socket
    for address in ['localhost', '127.0.0.1', '0.0.0.0']:
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(1)
            result = sock.connect_ex((address, 8742))
            sock.close()
            if result == 0:
                print(f"   ✅ Can connect to {address}:8742")
            else:
                print(f"   ❌ Cannot connect to {address}:8742")
        except Exception as e:
            print(f"   ❌ Error connecting to {address}: {e}")
    
    # Open test page in browser
    print("\n📍 Opening test page in your browser...")
    subprocess.run("open /tmp/test_connection.html", shell=True)
    
    print("\n" + "="*60)
    print("DIAGNOSTIC COMPLETE")
    print("="*60)
    print("\n📋 WHAT TO DO:")
    print("1. Check the browser test page that just opened")
    print("2. Look for any ❌ marks - those show the problem")
    print("3. Try clicking 'Test All Connections' button")
    print("4. Open Chrome DevTools (F12) and check Console for errors")
    print("5. If all connections fail, it's likely:")
    print("   • macOS firewall blocking Python")
    print("   • Chrome security policy")
    print("   • Corporate proxy/VPN interference")
    
    # Keep running
    print("\n✋ Press Ctrl+C to stop the test server")
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        backend_proc.terminate()
        print("\nTest server stopped")

if __name__ == "__main__":
    # Run diagnostic
    issues = diagnose_network()
    
    # Apply fixes
    fix_issues(issues)
    
    # Start test server
    start_test_server()
