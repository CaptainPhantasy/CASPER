#!/usr/bin/env python3
"""
CASPER Prime Menu Bar App - Always accessible AI development
"""

import sys
import os
import subprocess
import webbrowser
import threading
from pathlib import Path

# Try to use rumps for menu bar, fallback to tkinter if not available
try:
    import rumps
    HAS_RUMPS = True
except ImportError:
    HAS_RUMPS = False
    import tkinter as tk
    from tkinter import messagebox

# Obscure ports unlikely to conflict
API_PORT = 8742
DASHBOARD_PORT = 9318

class CasperPrimeApp:
    def __init__(self):
        self.base_dir = Path("/Volumes/Storage/Development/CASPER DEV/casper-prime")
        self.backend_process = None
        self.dashboard_process = None
        self.is_running = False
        
    def start_services(self):
        """Start backend and dashboard services"""
        if self.is_running:
            return "CASPER Prime is already running!"
        
        try:
            # Start backend
            os.chdir(self.base_dir)
            self.backend_process = subprocess.Popen(
                [sys.executable, '-m', 'core.server', '--port', str(API_PORT)],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL
            )
            
            # Start dashboard
            os.chdir(self.base_dir / 'dashboard')
            self.dashboard_process = subprocess.Popen(
                ['npm', 'run', 'dev', '--', '--port', str(DASHBOARD_PORT)],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL
            )
            
            self.is_running = True
            threading.Timer(2.0, lambda: webbrowser.open(f'http://localhost:{DASHBOARD_PORT}')).start()
            
            return f"✅ CASPER Prime started!\nAPI: Port {API_PORT}\nDashboard: Port {DASHBOARD_PORT}"
            
        except Exception as e:
            return f"Error starting CASPER: {e}"
    
    def stop_services(self):
        """Stop all services"""
        if self.backend_process:
            self.backend_process.terminate()
        if self.dashboard_process:
            self.dashboard_process.terminate()
        self.is_running = False
        return "CASPER Prime stopped"
    
    def open_dashboard(self):
        """Open dashboard in browser"""
        webbrowser.open(f'http://localhost:{DASHBOARD_PORT}')
        return "Opening dashboard..."

if HAS_RUMPS:
    # macOS Menu Bar App
    class CasperMenuBar(rumps.App):
        def __init__(self):
            super(CasperMenuBar, self).__init__("🤖")
            self.app = CasperPrimeApp()
            self.menu = [
                rumps.MenuItem("Start CASPER Prime", callback=self.start_casper),
                rumps.MenuItem("Open Dashboard", callback=self.open_dashboard),
                None,  # Separator
                rumps.MenuItem("Stop CASPER", callback=self.stop_casper),
            ]
            
        def start_casper(self, _):
            result = self.app.start_services()
            rumps.notification("CASPER Prime", "", result)
            
        def stop_casper(self, _):
            result = self.app.stop_services()
            rumps.notification("CASPER Prime", "", result)
            
        def open_dashboard(self, _):
            self.app.open_dashboard()
            
    if __name__ == "__main__":
        CasperMenuBar().run()
        
else:
    # Fallback Tkinter GUI
    class CasperGUI:
        def __init__(self):
            self.app = CasperPrimeApp()
            self.root = tk.Tk()
            self.root.title("CASPER Prime")
            self.root.geometry("300x200")
            
            # Create buttons
            tk.Button(
                self.root, 
                text="🚀 Start CASPER Prime", 
                command=self.start_casper,
                height=2,
                width=25
            ).pack(pady=10)
            
            tk.Button(
                self.root, 
                text="🌐 Open Dashboard", 
                command=self.open_dashboard,
                height=2,
                width=25
            ).pack(pady=5)
            
            tk.Button(
                self.root, 
                text="🛑 Stop CASPER", 
                command=self.stop_casper,
                height=2,
                width=25
            ).pack(pady=5)
            
            self.status_label = tk.Label(self.root, text="Ready")
            self.status_label.pack(pady=10)
            
        def start_casper(self):
            result = self.app.start_services()
            self.status_label.config(text="Running")
            messagebox.showinfo("CASPER Prime", result)
            
        def stop_casper(self):
            result = self.app.stop_services()
            self.status_label.config(text="Stopped")
            messagebox.showinfo("CASPER Prime", result)
            
        def open_dashboard(self):
            self.app.open_dashboard()
            
        def run(self):
            self.root.mainloop()
            
    if __name__ == "__main__":
        CasperGUI().run()
