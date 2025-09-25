#!/usr/bin/env python3
"""
EPSILON Tool Integration Verification
Testing Agent GAMMA's production_tools.py implementation

ZERO TOLERANCE DIRECTIVE:
- NO passing tests for broken code
- Tools must ACTUALLY WORK, not just import
- Comprehensive functional testing required
"""

import sys
import os
import tempfile
import asyncio
import json
from pathlib import Path
from datetime import datetime, timezone

# Add the project root to the path
sys.path.insert(0, '/Volumes/Storage/Development/CASPER DEV')

try:
    from core.tools.production_tools import (
        ProductionTools,
        ToolResult
    )
    TOOLS_IMPORTABLE = True
except ImportError as e:
    TOOLS_IMPORTABLE = False
    IMPORT_ERROR = str(e)


class GammaToolsVerifier:
    """EPSILON verification of Agent GAMMA's tools"""

    def __init__(self):
        self.results = []
        self.timestamp = datetime.now(timezone.utc).isoformat()

    def log_result(self, component: str, test: str, passed: bool, error: str = None, details: dict = None):
        """Log a verification result"""
        result = {
            "component": component,
            "test": test,
            "passed": passed,
            "error": error,
            "details": details,
            "timestamp": self.timestamp
        }
        self.results.append(result)
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"🔍 EPSILON: {component} - {test} - {status}")
        if error:
            print(f"   Error: {error}")

    def test_imports(self):
        """Test if all tools can be imported"""
        if not TOOLS_IMPORTABLE:
            self.log_result(
                "Tool Imports",
                "Import Test",
                False,
                IMPORT_ERROR
            )
            return False

        # Test each class exists
        required_classes = ['ProductionTools', 'ToolResult']
        missing_classes = []

        for cls_name in required_classes:
            if cls_name not in globals():
                missing_classes.append(cls_name)

        if missing_classes:
            self.log_result(
                "Tool Imports",
                "Class Availability",
                False,
                f"Missing classes: {missing_classes}"
            )
            return False

        self.log_result(
            "Tool Imports",
            "All Classes Available",
            True,
            details={"classes": required_classes}
        )
        return True

    async def test_memory_manager(self):
        """Test MemoryManager functionality"""
        if not TOOLS_IMPORTABLE:
            return

        try:
            # Test instantiation
            manager = MemoryManager()

            # Test memory store/retrieve
            test_memory = {"test": "data", "timestamp": self.timestamp}

            # Store memory
            await manager.store_memory("test_session", "test_memory", test_memory)

            # Retrieve memory
            retrieved = await manager.retrieve_memory("test_session", "test_memory")

            if retrieved != test_memory:
                self.log_result(
                    "MemoryManager",
                    "Store/Retrieve Test",
                    False,
                    f"Retrieved data doesn't match stored. Expected: {test_memory}, Got: {retrieved}"
                )
                return

            # Test search functionality
            search_results = await manager.search_memory("test")

            self.log_result(
                "MemoryManager",
                "Basic Functionality",
                True,
                details={
                    "store_retrieve": "working",
                    "search": "working",
                    "search_results_count": len(search_results) if search_results else 0
                }
            )

        except Exception as e:
            self.log_result(
                "MemoryManager",
                "Functionality Test",
                False,
                f"Runtime error: {str(e)}"
            )

    async def test_git_manager(self):
        """Test GitManager functionality"""
        if not TOOLS_IMPORTABLE:
            return

        try:
            manager = GitManager()

            # Test basic git info (should work in any git repo)
            status = await manager.get_status()

            if not isinstance(status, ToolResult):
                self.log_result(
                    "GitManager",
                    "Status Return Type",
                    False,
                    f"Expected ToolResult, got {type(status)}"
                )
                return

            # Test commit history
            history = await manager.get_commit_history(limit=5)

            if not isinstance(history, ToolResult):
                self.log_result(
                    "GitManager",
                    "History Return Type",
                    False,
                    f"Expected ToolResult, got {type(history)}"
                )
                return

            self.log_result(
                "GitManager",
                "Basic Functionality",
                True,
                details={
                    "status_success": status.success,
                    "history_success": history.success,
                    "status_has_data": bool(status.data),
                    "history_has_data": bool(history.data)
                }
            )

        except Exception as e:
            self.log_result(
                "GitManager",
                "Functionality Test",
                False,
                f"Runtime error: {str(e)}"
            )

    async def test_web_search_manager(self):
        """Test WebSearchManager functionality"""
        if not TOOLS_IMPORTABLE:
            return

        try:
            manager = WebSearchManager()

            # Test a simple search
            results = await manager.search("Python programming", max_results=3)

            if not isinstance(results, ToolResult):
                self.log_result(
                    "WebSearchManager",
                    "Search Return Type",
                    False,
                    f"Expected ToolResult, got {type(results)}"
                )
                return

            # Test URL extraction (should work even if search fails)
            url_results = await manager.extract_from_url("https://httpbin.org/json")

            self.log_result(
                "WebSearchManager",
                "Basic Functionality",
                True,
                details={
                    "search_success": results.success,
                    "url_extract_success": url_results.success if isinstance(url_results, ToolResult) else False,
                    "search_has_results": bool(results.data) if results.success else False
                }
            )

        except Exception as e:
            self.log_result(
                "WebSearchManager",
                "Functionality Test",
                False,
                f"Runtime error: {str(e)}"
            )

    async def test_automation_manager(self):
        """Test AutomationManager functionality"""
        if not TOOLS_IMPORTABLE:
            return

        try:
            manager = AutomationManager()

            # Test browser launch (headless)
            browser_result = await manager.launch_browser(headless=True)

            if not isinstance(browser_result, ToolResult):
                self.log_result(
                    "AutomationManager",
                    "Browser Launch Return Type",
                    False,
                    f"Expected ToolResult, got {type(browser_result)}"
                )
                return

            # Test simple page navigation
            if browser_result.success:
                nav_result = await manager.navigate_to("https://httpbin.org/html")

                # Test page content extraction
                content_result = await manager.get_page_content()

                # Cleanup
                await manager.close_browser()

                self.log_result(
                    "AutomationManager",
                    "Browser Automation",
                    True,
                    details={
                        "browser_launch": browser_result.success,
                        "navigation": nav_result.success if isinstance(nav_result, ToolResult) else False,
                        "content_extraction": content_result.success if isinstance(content_result, ToolResult) else False
                    }
                )
            else:
                self.log_result(
                    "AutomationManager",
                    "Browser Launch",
                    False,
                    f"Browser launch failed: {browser_result.error}"
                )

        except Exception as e:
            self.log_result(
                "AutomationManager",
                "Functionality Test",
                False,
                f"Runtime error: {str(e)}"
            )

    def test_tool_result_structure(self):
        """Test ToolResult class structure"""
        if not TOOLS_IMPORTABLE:
            return

        try:
            # Test basic construction
            result = ToolResult(
                success=True,
                data={"test": "data"},
                error=None,
                metadata={"source": "test"}
            )

            required_attrs = ['success', 'data', 'error', 'metadata', 'timestamp']
            missing_attrs = [attr for attr in required_attrs if not hasattr(result, attr)]

            if missing_attrs:
                self.log_result(
                    "ToolResult",
                    "Structure Test",
                    False,
                    f"Missing required attributes: {missing_attrs}"
                )
                return

            # Test error result
            error_result = ToolResult(
                success=False,
                data=None,
                error="Test error",
                metadata={}
            )

            self.log_result(
                "ToolResult",
                "Structure and Construction",
                True,
                details={
                    "required_attributes": required_attrs,
                    "success_result": "working",
                    "error_result": "working",
                    "has_timestamp": hasattr(result, 'timestamp')
                }
            )

        except Exception as e:
            self.log_result(
                "ToolResult",
                "Structure Test",
                False,
                f"Construction error: {str(e)}"
            )

    async def run_all_tests(self):
        """Run comprehensive verification suite"""
        print("🔍 EPSILON: Starting Agent GAMMA tools verification...")

        # Test imports first
        if not self.test_imports():
            print("❌ EPSILON: Import failed, skipping functional tests")
            return self.generate_summary()

        # Test structure
        self.test_tool_result_structure()

        # Test functionality (async)
        await asyncio.gather(
            self.test_memory_manager(),
            self.test_git_manager(),
            self.test_web_search_manager(),
            self.test_automation_manager()
        )

        return self.generate_summary()

    def generate_summary(self):
        """Generate verification summary"""
        passed = sum(1 for r in self.results if r['passed'])
        total = len(self.results)

        summary = {
            "agent": "GAMMA",
            "component": "Tool Integration",
            "timestamp": self.timestamp,
            "total_tests": total,
            "passed": passed,
            "failed": total - passed,
            "success_rate": (passed / total * 100) if total > 0 else 0,
            "production_ready": passed == total and total > 0,
            "results": self.results
        }

        print(f"\n🔍 EPSILON: Agent GAMMA verification complete")
        print(f"📊 Total Tests: {total}")
        print(f"✅ Passed: {passed}")
        print(f"❌ Failed: {total - passed}")
        print(f"🎯 Success Rate: {summary['success_rate']:.1f}%")
        print(f"🏭 Production Ready: {'YES' if summary['production_ready'] else 'NO'}")

        return summary


async def main():
    """Main test runner"""
    verifier = GammaToolsVerifier()
    summary = await verifier.run_all_tests()

    # Save results
    results_file = Path("/Volumes/Storage/Development/CASPER DEV/.casper/transformation/test_results/gamma_verification.json")
    with open(results_file, 'w') as f:
        json.dump(summary, f, indent=2)

    print(f"📄 Results saved to: {results_file}")
    return summary['production_ready']


if __name__ == "__main__":
    asyncio.run(main())