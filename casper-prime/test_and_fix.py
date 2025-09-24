#!/usr/bin/env python3
"""
CASPER Prime Dashboard Tester with Playwright
Tests and fixes the dashboard issues
"""

import asyncio
import subprocess
import time
import json
from pathlib import Path
from playwright.async_api import async_playwright

async def test_dashboard():
    print("🔍 Testing CASPER Prime Dashboard...")
    
    # First check if services are actually running
    try:
        # Check backend
        import httpx
        async with httpx.AsyncClient() as client:
            try:
                response = await client.get("http://localhost:8742/health", timeout=5)
                print(f"✅ Backend health check: {response.status_code}")
            except:
                print("❌ Backend not responding on port 8742")
                return False
                
        # Check dashboard
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            page = await browser.new_page()
            
            try:
                print("📱 Opening dashboard at http://localhost:9318...")
                await page.goto("http://localhost:9318", timeout=10000)
                
                # Check if page loaded
                title = await page.title()
                print(f"📄 Page title: {title}")
                
                # Check for error messages
                error_elements = await page.query_selector_all('.error, [class*="error"]')
                if error_elements:
                    print("⚠️  Error elements found on page")
                    
                # Check if main app element exists
                app_element = await page.query_selector('#root, .App, [class*="app"]')
                if app_element:
                    print("✅ App container found")
                else:
                    print("❌ App container not found")
                    
                # Take screenshot for debugging
                await page.screenshot(path="/tmp/casper-dashboard.png")
                print("📸 Screenshot saved to /tmp/casper-dashboard.png")
                
                # Check console errors
                page.on("console", lambda msg: print(f"Console: {msg.text}"))
                
                await browser.close()
                return True
                
            except Exception as e:
                print(f"❌ Dashboard error: {e}")
                await browser.close()
                return False
                
    except Exception as e:
        print(f"❌ Test failed: {e}")
        return False

async def check_services():
    """Check what's actually running on our ports"""
    print("\n🔍 Checking services...")
    
    # Check port 8742 (backend)
    result = subprocess.run("lsof -i:8742", shell=True, capture_output=True, text=True)
    if result.stdout:
        print("✅ Port 8742 (backend) is active")
    else:
        print("❌ Port 8742 (backend) is not active")
        
    # Check port 9318 (dashboard)  
    result = subprocess.run("lsof -i:9318", shell=True, capture_output=True, text=True)
    if result.stdout:
        print("✅ Port 9318 (dashboard) is active")
    else:
        print("❌ Port 9318 (dashboard) is not active")

async def fix_and_restart():
    """Fix issues and restart services properly"""
    print("\n🔧 Fixing and restarting services...")
    
    # Kill everything first
    subprocess.run("lsof -ti:8742 | xargs kill -9", shell=True, stderr=subprocess.DEVNULL)
    subprocess.run("lsof -ti:9318 | xargs kill -9", shell=True, stderr=subprocess.DEVNULL)
    time.sleep(2)
    
    # Check if npm modules are installed
    dashboard_path = Path("/Volumes/Storage/Development/CASPER DEV/casper-prime/dashboard")
    if not (dashboard_path / "node_modules").exists():
        print("📦 Installing dashboard dependencies...")
        subprocess.run("cd dashboard && npm install", shell=True, cwd="/Volumes/Storage/Development/CASPER DEV/casper-prime")
    
    # Start backend with proper error handling
    print("🚀 Starting backend...")
    backend_cmd = """
cd "/Volumes/Storage/Development/CASPER DEV/casper-prime"
source venv/bin/activate
python -m core.server --port 8742 2>&1 | tee /tmp/backend.log &
"""
    subprocess.Popen(backend_cmd, shell=True)
    time.sleep(3)
    
    # Start dashboard with Vite properly
    print("🎨 Starting dashboard...")
    dashboard_cmd = """
cd "/Volumes/Storage/Development/CASPER DEV/casper-prime/dashboard"
npm run dev -- --port 9318 --host 0.0.0.0 2>&1 | tee /tmp/dashboard.log &
"""
    subprocess.Popen(dashboard_cmd, shell=True)
    time.sleep(5)
    
    print("✅ Services restarted")

async def main():
    # Check current state
    await check_services()
    
    # Test dashboard
    success = await test_dashboard()
    
    if not success:
        print("\n🔧 Dashboard not working, applying fixes...")
        await fix_and_restart()
        
        # Test again
        print("\n🔍 Testing after fixes...")
        time.sleep(5)
        success = await test_dashboard()
        
        if success:
            print("\n✅ CASPER Prime is now working!")
            print("🌐 Opening dashboard...")
            subprocess.run("open http://localhost:9318", shell=True)
        else:
            print("\n⚠️  Still having issues. Checking logs...")
            print("\nBackend log:")
            subprocess.run("tail -20 /tmp/backend.log", shell=True)
            print("\nDashboard log:")
            subprocess.run("tail -20 /tmp/dashboard.log", shell=True)
    else:
        print("\n✅ Dashboard is working!")

if __name__ == "__main__":
    asyncio.run(main())
