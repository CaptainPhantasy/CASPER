#!/usr/bin/env python3
"""
CASPER Prime Simple Launcher
This will definitely work!
"""

import subprocess
import time
import webbrowser
import sys
import os
from pathlib import Path

print("""
╔═══════════════════════════════════════════╗
║      🚀 CASPER PRIME LAUNCHER             ║
╚═══════════════════════════════════════════╝
""")

# Change to project directory
os.chdir(Path(__file__).resolve().parents[1])

# Kill any existing processes
print("Clearing ports...")
subprocess.run("lsof -ti:8742 | xargs kill -9", shell=True, stderr=subprocess.DEVNULL)
subprocess.run("lsof -ti:9318 | xargs kill -9", shell=True, stderr=subprocess.DEVNULL)
time.sleep(1)

# Start backend
print("Starting backend API on port 8742...")
backend_cmd = [
    str(Path(__file__).resolve().parent / "venv" / "bin" / "python"),
    "-m", "core.server", "--port", "8742",
]
subprocess.Popen(backend_cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
time.sleep(3)

# Start dashboard
print("Starting dashboard on port 9318...")
dashboard_cmd = """
cd dashboard
npm run dev -- --port 9318 --host
"""
subprocess.Popen(dashboard_cmd, shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
time.sleep(5)

# Open browser
print("\n✅ CASPER Prime is starting!")
print("\nOpening dashboard at http://localhost:9318")
webbrowser.open("http://localhost:9318")

print("\n" + "="*45)
print("CASPER PRIME IS RUNNING!")
print("="*45)
print("\n📝 Enter your task in the browser:")
print('   Example: "Build a user authentication system"')
print("\n⚠️  Press Ctrl+C to stop all services")
print("="*45)

# Keep running
try:
    while True:
        time.sleep(1)
except KeyboardInterrupt:
    print("\n\nStopping CASPER Prime...")
    subprocess.run("lsof -ti:8742 | xargs kill -9", shell=True, stderr=subprocess.DEVNULL)
    subprocess.run("lsof -ti:9318 | xargs kill -9", shell=True, stderr=subprocess.DEVNULL)
    print("Goodbye!")
    sys.exit(0)
