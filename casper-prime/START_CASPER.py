#!/usr/bin/env python3
"""
CASPER Prime Quick Launcher
One-click start for autonomous AI development
"""

import subprocess
import webbrowser
import time
import os
from pathlib import Path

# Use obscure ports that are unlikely to be in use
API_PORT = 8742
DASHBOARD_PORT = 9318

print("""
╔═══════════════════════════════════════════╗
║         🚀 CASPER PRIME                    ║
║   Autonomous AI Development Platform       ║
╚═══════════════════════════════════════════╝
""")

# Set working directory
os.chdir("/Volumes/Storage/Development/CASPER DEV/casper-prime")

# Kill any existing processes on our ports
subprocess.run(f"lsof -ti:{API_PORT} | xargs kill -9", shell=True, capture_output=True)
subprocess.run(f"lsof -ti:{DASHBOARD_PORT} | xargs kill -9", shell=True, capture_output=True)

print(f"Starting backend on port {API_PORT}...")
subprocess.Popen(
    "source venv/bin/activate && python -m core.server --port 8742",
    shell=True,
    stdout=subprocess.DEVNULL,
    stderr=subprocess.DEVNULL
)

time.sleep(2)

print(f"Starting dashboard on port {DASHBOARD_PORT}...")
subprocess.Popen(
    f"cd dashboard && npm run dev -- --port {DASHBOARD_PORT}",
    shell=True,
    stdout=subprocess.DEVNULL,
    stderr=subprocess.DEVNULL
)

time.sleep(3)

print("\n✅ CASPER Prime is running!")
print(f"\n🌐 Opening browser to http://localhost:{DASHBOARD_PORT}")
webbrowser.open(f"http://localhost:{DASHBOARD_PORT}")

print("\n📝 Just type what you want to build!")
print("💡 Example: 'Build a user authentication system with JWT'")
print("\nPress Ctrl+C to stop")

try:
    while True:
        time.sleep(1)
except KeyboardInterrupt:
    print("\nShutting down CASPER Prime...")
    subprocess.run(f"lsof -ti:{API_PORT} | xargs kill -9", shell=True, capture_output=True)
    subprocess.run(f"lsof -ti:{DASHBOARD_PORT} | xargs kill -9", shell=True, capture_output=True)
    print("Goodbye! 👋")
