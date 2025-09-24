#!/usr/bin/env python3
"""
CASPER Prime Menu Bar App - Enhanced Version
Always accessible in your menu bar
"""

import rumps
import subprocess
import webbrowser
import os
import time
import threading
from pathlib import Path

# Configuration
API_PORT = 8742
DASHBOARD_PORT = 9318
BASE_DIR = Path("/Volumes/Storage/Development/CASPER DEV/casper-prime")

class CasperPrimeStatusBar(rumps.App):
    def __init__(self):
        super(CasperPrimeStatusBar, self).__init__("🤖", quit_button="Quit CASPER")
        self.backend_process = None
        self.dashboard_process = None
        self.is_running = False
        
        # Set up menu
        self.setup_menu()
        
    def setup_menu(self):
        """Configure the menu items"""
        self.menu = [
            rumps.MenuItem("✨ Start CASPER Prime", callback=self.start_casper),
            rumps.MenuItem("🌐 Open Dashboard", callback=self.open_dashboard),
            rumps.MenuItem("📝 New Task...", callback=self.new_task),
            None,  # Separator
            rumps.MenuItem("📊 View Logs", callback=self.view_logs),
            rumps.MenuItem("⚙️ Settings", callback=self.settings),
            None,  # Separator
            rumps.MenuItem("🛑 Stop Services", callback=self.stop_casper),
            rumps.MenuItem("🔄 Restart Services", callback=self.restart_casper),
            None,  # Separator
            rumps.MenuItem("ℹ️ About", callback=self.about),
        ]
        
        # Initially disable some items
        self.menu["🌐 Open Dashboard"].enabled = False
        self.menu["📝 New Task..."].enabled = False
        self.menu["🛑 Stop Services"].enabled = False
        self.menu["🔄 Restart Services"].enabled = False
        
    @rumps.clicked("✨ Start CASPER Prime")
    def start_casper(self, sender):
        if self.is_running:
            rumps.notification("CASPER Prime", "Already Running", "Services are already active")
            return
            
        rumps.notification("CASPER Prime", "Starting...", "Initializing AI agents...")
        
        # Start in background thread
        threading.Thread(target=self._start_services).start()
        
    def _start_services(self):
        """Start backend and dashboard services"""
        try:
            # Kill any existing processes on our ports
            subprocess.run(f"lsof -ti:{API_PORT} | xargs kill -9", shell=True, capture_output=True)
            subprocess.run(f"lsof -ti:{DASHBOARD_PORT} | xargs kill -9", shell=True, capture_output=True)
            
            # Start backend
            os.chdir(BASE_DIR)
            self.backend_process = subprocess.Popen(
                f"source venv/bin/activate && python -m core.server --port {API_PORT}",
                shell=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            )
            
            time.sleep(2)
            
            # Start dashboard
            os.chdir(BASE_DIR / "dashboard")
            self.dashboard_process = subprocess.Popen(
                f"npm run dev -- --port {DASHBOARD_PORT}",
                shell=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            )
            
            time.sleep(3)
            
            # Update UI
            rumps.notification(
                "CASPER Prime", 
                "Ready!", 
                f"API: Port {API_PORT}\\nDashboard: Port {DASHBOARD_PORT}"
            )
            
            # Update menu bar icon
            self.icon = "🚀"
            self.is_running = True
            
            # Enable menu items
            self.menu["🌐 Open Dashboard"].enabled = True
            self.menu["📝 New Task..."].enabled = True
            self.menu["🛑 Stop Services"].enabled = True
            self.menu["🔄 Restart Services"].enabled = True
            self.menu["✨ Start CASPER Prime"].enabled = False
            
            # Open dashboard
            webbrowser.open(f"http://localhost:{DASHBOARD_PORT}")
            
        except Exception as e:
            rumps.alert(f"Error starting services: {e}")
            
    @rumps.clicked("🌐 Open Dashboard")
    def open_dashboard(self, _):
        webbrowser.open(f"http://localhost:{DASHBOARD_PORT}")
        
    @rumps.clicked("📝 New Task...")
    def new_task(self, _):
        window = rumps.Window(
            title="New CASPER Task",
            message="What would you like to build?",
            default_text="Build a user authentication system with JWT",
            ok="Submit",
            cancel="Cancel",
            dimensions=(320, 160)
        )
        response = window.run()
        
        if response.clicked:
            # Submit task via API
            import requests
            try:
                requests.post(
                    f"http://localhost:{API_PORT}/api/tasks",
                    json={"description": response.text}
                )
                rumps.notification("Task Submitted", "", response.text[:50] + "...")
                webbrowser.open(f"http://localhost:{DASHBOARD_PORT}")
            except:
                rumps.alert("Please ensure CASPER is running first")
                
    @rumps.clicked("📊 View Logs")
    def view_logs(self, _):
        subprocess.run(["open", "-a", "Console", "/tmp/casper-backend.log"])
        
    @rumps.clicked("⚙️ Settings")
    def settings(self, _):
        subprocess.run(["open", BASE_DIR / ".env"])
        
    @rumps.clicked("🛑 Stop Services")
    def stop_casper(self, _):
        if self.backend_process:
            self.backend_process.terminate()
        if self.dashboard_process:
            self.dashboard_process.terminate()
            
        # Kill processes on ports
        subprocess.run(f"lsof -ti:{API_PORT} | xargs kill -9", shell=True, capture_output=True)
        subprocess.run(f"lsof -ti:{DASHBOARD_PORT} | xargs kill -9", shell=True, capture_output=True)
        
        self.is_running = False
        self.icon = "🤖"
        
        # Update menu
        self.menu["🌐 Open Dashboard"].enabled = False
        self.menu["📝 New Task..."].enabled = False
        self.menu["🛑 Stop Services"].enabled = False
        self.menu["🔄 Restart Services"].enabled = False
        self.menu["✨ Start CASPER Prime"].enabled = True
        
        rumps.notification("CASPER Prime", "Stopped", "All services have been terminated")
        
    @rumps.clicked("🔄 Restart Services")
    def restart_casper(self, _):
        self.stop_casper(_)
        time.sleep(1)
        self.start_casper(_)
        
    @rumps.clicked("ℹ️ About")
    def about(self, _):
        rumps.alert(
            "CASPER Prime v0.1",
            "Autonomous AI Development Platform\\n\\n"
            "• Master Agent orchestration\\n"
            "• Context-aware handoffs\\n" 
            "• Fire & forget development\\n\\n"
            "Created by Legacy AI"
        )

if __name__ == "__main__":
    app = CasperPrimeStatusBar()
    app.run()
