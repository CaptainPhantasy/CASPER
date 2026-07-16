#!/usr/bin/env python3
"""
CASPER Prime Launcher - One-click autonomous AI development
"""

import os
import sys
import subprocess
import webbrowser
import time
import socket
from pathlib import Path
import json

# Use obscure ports unlikely to be in use
API_PORT = 8742
DASHBOARD_PORT = 9318

def find_free_port(start_port):
    """Find an available port starting from the given port"""
    for port in range(start_port, start_port + 100):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            try:
                s.bind(('', port))
                return port
            except:
                continue
    return start_port

def create_app_icon():
    """Create a simple icon for the app"""
    icon_script = '''
    tell application "Finder"
        set theFile to POSIX file "/Volumes/Storage/Development/CASPER DEV/casper-prime/CASPER.app"
        set icon of theFile to POSIX file "/System/Library/CoreServices/CoreTypes.bundle/Contents/Resources/ExecutableBinaryIcon.icns"
    end tell
    '''
    subprocess.run(['osascript', '-e', icon_script], capture_output=True)

def main():
    base_dir = Path("/Volumes/Storage/Development/CASPER DEV/casper-prime")
    os.chdir(base_dir)
    
    # Find available ports
    api_port = find_free_port(API_PORT)
    dashboard_port = find_free_port(DASHBOARD_PORT)
    
    print("""
    ╔═══════════════════════════════════════════════════════════╗
    ║   ____    _    ____  ____  _____ ____    ____  ____      ║
    ║  / ___|  / \  / ___||  _ \| ____|  _ \  |  _ \|  _ \     ║
    ║ | |     / _ \ \___ \| |_) |  _| | |_) | | |_) | |_) |    ║
    ║ | |___ / ___ \ ___) |  __/| |___|  _ <  |  __/|  _ <     ║
    ║  \____/_/   \_\____/|_|   |_____|_| \_\ |_|   |_| \_\    ║
    ║                                                           ║
    ║         🚀 Starting Autonomous AI Development...          ║
    ╚═══════════════════════════════════════════════════════════╝
    """)
    
    # Update config with selected ports
    env_path = base_dir / ".env"
    if env_path.exists():
        with open(env_path, 'a') as f:
            f.write(f"\nCASPER_API_PORT={api_port}")
            f.write(f"\nCASPER_DASHBOARD_PORT={dashboard_port}")
    
    print(f"✓ API Port: {api_port}")
    print(f"✓ Dashboard Port: {dashboard_port}")
    
    # Start backend in background
    print("\n⚡ Starting CASPER Prime backend...")
    backend = subprocess.Popen(
        [sys.executable, '-m', 'core.server', '--port', str(api_port)],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        cwd=base_dir
    )
    
    # Give backend time to start
    time.sleep(3)
    
    # Start dashboard in background
    print("🎨 Starting dashboard...")
    dashboard = subprocess.Popen(
        ['npm', 'run', 'dev', '--', '--port', str(dashboard_port)],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        cwd=base_dir / 'dashboard'
    )
    
    # Give dashboard time to start
    time.sleep(3)
    
    # Open browser to dashboard
    print(f"🌐 Opening dashboard at http://localhost:{dashboard_port}")
    webbrowser.open(f'http://localhost:{dashboard_port}')
    
    print("""
    ✅ CASPER Prime is running!
    
    📝 Enter your development task in the browser
    👁️ Watch agents work autonomously
    💾 Output saved to: /output directory
    
    Press Ctrl+C to stop CASPER Prime
    """)
    
    try:
        # Keep running until interrupted
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n🛑 Shutting down CASPER Prime...")
        backend.terminate()
        dashboard.terminate()
        print("Goodbye! 👋")

if __name__ == "__main__":
    main()
