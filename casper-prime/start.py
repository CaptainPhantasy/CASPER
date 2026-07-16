#!/usr/bin/env python3
import subprocess
import time
import webbrowser
import sys
import os

os.chdir("/Volumes/Storage/Development/CASPER DEV/casper-prime")

# Start backend
print("Starting backend...")
backend = subprocess.Popen([
    sys.executable, "-m", "uvicorn", 
    "core.server:app", 
    "--host", "0.0.0.0", 
    "--port", "8742"
], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

time.sleep(3)

# Start dashboard
print("Starting dashboard...")
dashboard = subprocess.Popen(
    "cd dashboard && npm run dev -- --port 9318 --host",
    shell=True,
    stdout=subprocess.DEVNULL, 
    stderr=subprocess.DEVNULL
)

time.sleep(5)

print("\n✅ CASPER Prime is running!")
print("\nBackend: http://localhost:8742")
print("Dashboard: http://localhost:9318")

webbrowser.open("http://localhost:9318")

try:
    while True:
        time.sleep(1)
except KeyboardInterrupt:
    print("\nShutting down...")
    backend.terminate()
    dashboard.terminate()
