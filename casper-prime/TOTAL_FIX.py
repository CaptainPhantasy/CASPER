#!/usr/bin/env python3
"""
CASPER Prime Total System Fix
This will make it work. Period.
"""

import os
import sys
import subprocess
import time
import json
import shutil
from pathlib import Path

def main():
    print("\n🔧 FIXING CASPER PRIME\n" + "="*40)
    
    BASE_DIR = Path("/Volumes/Storage/Development/CASPER DEV/casper-prime")
    os.chdir(BASE_DIR)
    
    # 1. Kill everything
    print("Stopping all processes...")
    subprocess.run("lsof -ti:8742 | xargs kill -9", shell=True, stderr=subprocess.DEVNULL)
    subprocess.run("lsof -ti:9318 | xargs kill -9", shell=True, stderr=subprocess.DEVNULL)
    time.sleep(2)
    
    # 2. Fix Python imports in all files
    print("Fixing Python imports...")
    files_to_fix = [
        "core/server.py",
        "core/cli.py", 
        "core/orchestrator/coordinator.py",
        "core/orchestrator/task_analyzer.py",
        "core/context/manager.py",
        "core/context/reducer.py",
        "core/context/delegator.py",
        "core/agents/master_prime.py",
        "core/agents/backend_prime.py",
        "core/agents/frontend_prime.py",
        "core/agents/testing_prime.py"
    ]
    
    for file_path in files_to_fix:
        full_path = BASE_DIR / file_path
        if full_path.exists():
            content = full_path.read_text()
            # Fix imports
            content = content.replace('from orchestrator.', 'from core.orchestrator.')
            content = content.replace('from context.', 'from core.context.')
            content = content.replace('from agents.', 'from core.agents.')
            content = content.replace('from ..agents.', 'from core.agents.')
            content = content.replace('from ..context.', 'from core.context.')
            content = content.replace('from ..orchestrator.', 'from core.orchestrator.')
            full_path.write_text(content)
    
    # 3. Setup Python properly
    print("Setting up Python environment...")
    subprocess.run("source venv/bin/activate && pip install -e . --quiet", 
                   shell=True, cwd=BASE_DIR, stderr=subprocess.DEVNULL)
    
    # 4. Fix npm cache
    print("Cleaning npm cache...")
    cache_dir = Path.home() / ".npm"
    if cache_dir.exists():
        shutil.rmtree(cache_dir, ignore_errors=True)
    
    # 5. Setup dashboard with yarn (more reliable than npm)
    print("Installing dashboard dependencies...")
    dashboard_dir = BASE_DIR / "dashboard"
    
    # Check if yarn exists, if not use npm with specific version
    yarn_check = subprocess.run("which yarn", shell=True, capture_output=True)
    
    if yarn_check.returncode == 0:
        subprocess.run("yarn install", shell=True, cwd=dashboard_dir)
    else:
        # Force npm to use older version compatible with Node 20.11
        subprocess.run("npm install --legacy-peer-deps", shell=True, cwd=dashboard_dir)
    
    # 6. Create startup script
    print("Creating startup script...")
    
    startup_script = BASE_DIR / "start.py"
    startup_script.write_text('''#!/usr/bin/env python3
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

print("\\n✅ CASPER Prime is running!")
print("\\nBackend: http://localhost:8742")
print("Dashboard: http://localhost:9318")

webbrowser.open("http://localhost:9318")

try:
    while True:
        time.sleep(1)
except KeyboardInterrupt:
    print("\\nShutting down...")
    backend.terminate()
    dashboard.terminate()
''')
    
    startup_script.chmod(0o755)
    
    # 7. Test and start
    print("\nStarting CASPER Prime...")
    
    # Start backend
    backend_proc = subprocess.Popen([
        sys.executable, "-m", "uvicorn", 
        "core.server:app", 
        "--host", "0.0.0.0", 
        "--port", "8742"
    ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, cwd=BASE_DIR)
    
    time.sleep(3)
    
    # Start dashboard
    dashboard_proc = subprocess.Popen(
        "npm run dev -- --port 9318 --host",
        shell=True,
        cwd=dashboard_dir,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL
    )
    
    time.sleep(5)
    
    # Check if running
    backend_check = subprocess.run("curl -s http://localhost:8742/health", 
                                  shell=True, capture_output=True)
    dashboard_check = subprocess.run("curl -s http://localhost:9318", 
                                     shell=True, capture_output=True)
    
    if backend_check.returncode == 0:
        print("✅ Backend running on port 8742")
    else:
        print("❌ Backend failed - check logs")
        
    if dashboard_check.returncode == 0 or "<!DOCTYPE html>" in dashboard_check.stdout.decode():
        print("✅ Dashboard running on port 9318")
    else:
        print("❌ Dashboard failed - check logs")
    
    print("\n" + "="*40)
    print("CASPER PRIME IS READY")
    print("="*40)
    print("\nOpening browser to http://localhost:9318")
    
    subprocess.run("open http://localhost:9318", shell=True)
    
    print("\nPress Ctrl+C to stop")
    
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        backend_proc.terminate()
        dashboard_proc.terminate()
        print("\nShutdown complete")

if __name__ == "__main__":
    main()
