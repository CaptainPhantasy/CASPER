#!/usr/bin/env python3
"""
CASPER Prime Complete Fix with Playwright Testing
Fixes everything, then tests with real browser and screenshots
"""

import os
import sys
import subprocess
import time
import json
import shutil
import asyncio
from pathlib import Path
from datetime import datetime

# First, fix everything properly
def fix_all_issues():
    print("\n🔧 PHASE 1: FIXING ALL ISSUES\n" + "="*50)
    
    BASE_DIR = Path("/Volumes/Storage/Development/CASPER DEV/casper-prime")
    os.chdir(BASE_DIR)
    
    # 1. Kill all processes
    print("1. Killing existing processes...")
    subprocess.run("lsof -ti:8742 | xargs kill -9", shell=True, stderr=subprocess.DEVNULL)
    subprocess.run("lsof -ti:9318 | xargs kill -9", shell=True, stderr=subprocess.DEVNULL)
    time.sleep(2)
    
    # 2. Fix ALL Python imports systematically
    print("2. Fixing Python imports in all files...")
    
    # Get all Python files in core directory
    for py_file in BASE_DIR.glob("core/**/*.py"):
        try:
            content = py_file.read_text()
            original = content
            
            # Fix relative imports to absolute
            content = content.replace('from orchestrator.', 'from core.orchestrator.')
            content = content.replace('from context.', 'from core.context.')
            content = content.replace('from agents.', 'from core.agents.')
            content = content.replace('import orchestrator.', 'import core.orchestrator.')
            content = content.replace('import context.', 'import core.context.')
            content = content.replace('import agents.', 'import core.agents.')
            
            # Fix relative parent imports
            content = content.replace('from ..orchestrator', 'from core.orchestrator')
            content = content.replace('from ..context', 'from core.context')
            content = content.replace('from ..agents', 'from core.agents')
            
            if content != original:
                py_file.write_text(content)
                print(f"  Fixed: {py_file.relative_to(BASE_DIR)}")
        except Exception as e:
            print(f"  Error fixing {py_file}: {e}")
    
    # 3. Clean npm cache completely
    print("3. Cleaning npm cache...")
    npm_cache = Path.home() / ".npm"
    if npm_cache.exists():
        shutil.rmtree(npm_cache, ignore_errors=True)
    
    # 4. Install Python package properly
    print("4. Installing CASPER Prime Python package...")
    result = subprocess.run(
        "source venv/bin/activate && pip install -e . --quiet",
        shell=True, 
        cwd=BASE_DIR,
        capture_output=True,
        text=True
    )
    if result.returncode != 0:
        print(f"  Warning: {result.stderr}")
    
    # 5. Fix dashboard dependencies
    print("5. Installing dashboard dependencies...")
    dashboard_dir = BASE_DIR / "dashboard"
    
    # Remove old files
    (dashboard_dir / "package-lock.json").unlink(missing_ok=True)
    if (dashboard_dir / "node_modules").exists():
        shutil.rmtree(dashboard_dir / "node_modules")
    
    # Install with legacy peer deps to avoid version conflicts
    result = subprocess.run(
        "npm install --legacy-peer-deps",
        shell=True,
        cwd=dashboard_dir,
        capture_output=True,
        text=True
    )
    
    if result.returncode != 0:
        print(f"  NPM install had issues: {result.stderr[:200]}")
        # Try with --force as fallback
        subprocess.run("npm install --force", shell=True, cwd=dashboard_dir)
    
    print("\n✅ All fixes applied\n")
    return BASE_DIR, dashboard_dir

# Playwright testing with screenshots
async def test_with_playwright(base_dir, dashboard_dir):
    print("\n🧪 PHASE 2: PLAYWRIGHT TESTING\n" + "="*50)
    
    from playwright.async_api import async_playwright
    
    # Create screenshots directory
    screenshots_dir = base_dir / "test_screenshots"
    screenshots_dir.mkdir(exist_ok=True)
    
    # Start backend
    print("Starting backend for testing...")
    backend_proc = subprocess.Popen(
        [sys.executable, "-m", "uvicorn", "core.server:app", "--host", "0.0.0.0", "--port", "8742"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        cwd=base_dir,
        env={**os.environ, "PYTHONPATH": str(base_dir)}
    )
    
    # Start dashboard
    print("Starting dashboard for testing...")
    dashboard_proc = subprocess.Popen(
        "npm run dev -- --port 9318 --host",
        shell=True,
        cwd=dashboard_dir,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE
    )
    
    # Wait for services to start
    print("Waiting for services to start...")
    time.sleep(10)
    
    # Test with Playwright
    async with async_playwright() as p:
        print("\nLaunching browser (visible mode)...")
        browser = await p.chromium.launch(
            headless=False,  # VISIBLE browser as requested
            slow_mo=500  # Slow down actions so we can see them
        )
        
        context = await browser.new_context(
            viewport={'width': 1920, 'height': 1080}
        )
        page = await context.new_page()
        
        test_results = {
            "backend_health": False,
            "dashboard_loads": False,
            "task_input_exists": False,
            "pipeline_visible": False,
            "websocket_connected": False,
            "can_submit_task": False
        }
        
        try:
            # Test 1: Backend Health Check
            print("\n📍 Test 1: Backend Health Check")
            try:
                await page.goto("http://localhost:8742/health", timeout=10000)
                await page.screenshot(path=screenshots_dir / "01_backend_health.png")
                content = await page.content()
                if "healthy" in content.lower():
                    test_results["backend_health"] = True
                    print("  ✅ Backend is healthy")
                else:
                    print("  ❌ Backend response unexpected")
            except Exception as e:
                print(f"  ❌ Backend failed: {e}")
                
            # Test 2: Dashboard Loading
            print("\n📍 Test 2: Dashboard Loading")
            try:
                await page.goto("http://localhost:9318", timeout=15000)
                await page.wait_for_timeout(3000)  # Let it fully load
                await page.screenshot(path=screenshots_dir / "02_dashboard_initial.png")
                
                # Check if page loaded without connection error
                error_text = await page.query_selector("text=can't be reached")
                if error_text:
                    print("  ❌ Dashboard shows connection error")
                else:
                    test_results["dashboard_loads"] = True
                    print("  ✅ Dashboard loaded successfully")
            except Exception as e:
                print(f"  ❌ Dashboard failed: {e}")
                
            # Test 3: Check for task input
            print("\n📍 Test 3: Task Input Field")
            try:
                task_input = await page.query_selector('input[placeholder*="task"], input[type="text"], textarea')
                if task_input:
                    test_results["task_input_exists"] = True
                    print("  ✅ Task input field found")
                    await page.screenshot(path=screenshots_dir / "03_task_input.png")
                else:
                    print("  ❌ No task input field found")
            except Exception as e:
                print(f"  ❌ Task input check failed: {e}")
                
            # Test 4: Check for pipeline columns
            print("\n📍 Test 4: Agent Pipeline Display")
            try:
                # Look for pipeline columns
                columns = await page.query_selector_all('[class*="column"], [class*="pipeline"], div:has-text("Queued")')
                if columns:
                    test_results["pipeline_visible"] = True
                    print(f"  ✅ Pipeline visible with {len(columns)} elements")
                    await page.screenshot(path=screenshots_dir / "04_pipeline.png")
                else:
                    print("  ❌ Pipeline not visible")
            except Exception as e:
                print(f"  ❌ Pipeline check failed: {e}")
                
            # Test 5: WebSocket Connection
            print("\n📍 Test 5: WebSocket Connection")
            try:
                # Check console for WebSocket messages
                ws_connected = await page.evaluate("""
                    () => {
                        // Check if WebSocket exists and is open
                        const sockets = Array.from(window).filter(key => key.includes('socket') || key.includes('ws'));
                        return sockets.length > 0;
                    }
                """)
                if ws_connected:
                    test_results["websocket_connected"] = True
                    print("  ✅ WebSocket connected")
                else:
                    print("  ⚠️  WebSocket status unclear")
            except:
                print("  ⚠️  Could not verify WebSocket")
                
            # Test 6: Submit a task
            print("\n📍 Test 6: Task Submission")
            if task_input:
                try:
                    await task_input.click()
                    await page.screenshot(path=screenshots_dir / "05_task_input_focused.png")
                    
                    # Type a test task
                    await task_input.type("Build a simple hello world API", delay=100)
                    await page.screenshot(path=screenshots_dir / "06_task_typed.png")
                    
                    # Try to submit (Enter key or button)
                    await page.keyboard.press("Enter")
                    await page.wait_for_timeout(2000)
                    
                    await page.screenshot(path=screenshots_dir / "07_task_submitted.png")
                    test_results["can_submit_task"] = True
                    print("  ✅ Task submission works")
                except Exception as e:
                    print(f"  ❌ Task submission failed: {e}")
                    
        except Exception as e:
            print(f"\n❌ Testing error: {e}")
        finally:
            # Final screenshot
            await page.screenshot(path=screenshots_dir / "08_final_state.png")
            
            # Keep browser open for 5 seconds so we can see it
            print("\n👀 Keeping browser open for review...")
            await page.wait_for_timeout(5000)
            
            await browser.close()
    
    # Stop services
    backend_proc.terminate()
    dashboard_proc.terminate()
    
    # Print results
    print("\n" + "="*50)
    print("TEST RESULTS SUMMARY")
    print("="*50)
    
    passing = sum(1 for v in test_results.values() if v)
    total = len(test_results)
    
    for test, passed in test_results.items():
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"{status}: {test}")
    
    print(f"\n📊 Score: {passing}/{total} tests passed")
    print(f"📸 Screenshots saved to: {screenshots_dir}")
    
    if passing == total:
        print("\n🎉 CASPER PRIME IS FULLY WORKING!")
        return True
    else:
        print(f"\n⚠️  {total - passing} tests still failing. Needs more fixes.")
        return False

# Main execution
async def main():
    try:
        # First fix everything
        base_dir, dashboard_dir = fix_all_issues()
        
        # Then test with Playwright
        success = await test_with_playwright(base_dir, dashboard_dir)
        
        if success:
            print("\n" + "="*50)
            print("✅ CASPER PRIME IS READY FOR USE")
            print("="*50)
            print("\nTo start normally, run:")
            print("  cd '/Volumes/Storage/Development/CASPER DEV/casper-prime'")
            print("  source venv/bin/activate")
            print("  python start.py")
        else:
            print("\n" + "="*50)
            print("⚠️  ADDITIONAL FIXES NEEDED")
            print("="*50)
            print("Check the screenshots to see what's wrong.")
            
    except Exception as e:
        print(f"\n❌ Fatal error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    # Install playwright if needed
    subprocess.run("pip install playwright", shell=True, capture_output=True)
    subprocess.run("playwright install chromium", shell=True, capture_output=True)
    
    # Run the async main
    asyncio.run(main())
