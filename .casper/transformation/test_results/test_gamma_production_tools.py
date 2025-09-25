#!/usr/bin/env python3
"""
EPSILON GAMMA TOOLS VERIFICATION - REVISED
Testing Agent GAMMA's actual ProductionTools implementation

ZERO TOLERANCE DIRECTIVE:
- NO passing tests for broken code
- Tools must ACTUALLY WORK, not just import
- Comprehensive functional testing required
"""

import sys
import os
import asyncio
import json
from pathlib import Path
from datetime import datetime, timezone

# Add the project root to the path
sys.path.insert(0, '/Volumes/Storage/Development/CASPER DEV')

try:
    from core.tools.production_tools import ProductionTools, ToolResult
    TOOLS_IMPORTABLE = True
except ImportError as e:
    TOOLS_IMPORTABLE = False
    IMPORT_ERROR = str(e)


class EpsilonGammaVerifier:
    """EPSILON comprehensive verification of Agent GAMMA's ProductionTools"""

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
        if details and passed:
            print(f"   Details: {details}")

    def test_imports_and_structure(self):
        """Test if ProductionTools can be imported and instantiated"""
        if not TOOLS_IMPORTABLE:
            self.log_result(
                "ProductionTools",
                "Import Test",
                False,
                IMPORT_ERROR
            )
            return False

        try:
            # Test instantiation
            tools = ProductionTools()

            # Check required methods exist
            required_methods = [
                'initialize', 'store_memory', 'search_memory', 'git_status',
                'git_commit', 'web_search', 'launch_browser', 'browse_url',
                'cleanup', 'health_check'
            ]

            missing_methods = [method for method in required_methods if not hasattr(tools, method)]

            if missing_methods:
                self.log_result(
                    "ProductionTools",
                    "Method Structure",
                    False,
                    f"Missing required methods: {missing_methods}"
                )
                return False

            # Test ToolResult structure
            test_result = ToolResult(success=True, data="test", tool="test")
            required_attrs = ['success', 'data', 'error', 'timestamp', 'tool']
            missing_attrs = [attr for attr in required_attrs if not hasattr(test_result, attr)]

            if missing_attrs:
                self.log_result(
                    "ToolResult",
                    "Structure Test",
                    False,
                    f"Missing required attributes: {missing_attrs}"
                )
                return False

            self.log_result(
                "ProductionTools",
                "Import and Structure",
                True,
                details={
                    "methods_found": len(required_methods),
                    "tool_result_working": True,
                    "instantiable": True
                }
            )
            return True

        except Exception as e:
            self.log_result(
                "ProductionTools",
                "Structure Test",
                False,
                f"Instantiation/structure error: {str(e)}"
            )
            return False

    async def test_initialization(self):
        """Test ProductionTools initialization"""
        if not TOOLS_IMPORTABLE:
            return False

        try:
            tools = ProductionTools()

            # Test initialization
            init_result = await tools.initialize()

            if not isinstance(init_result, ToolResult):
                self.log_result(
                    "ProductionTools",
                    "Initialization Return Type",
                    False,
                    f"Expected ToolResult, got {type(init_result)}"
                )
                return False

            self.log_result(
                "ProductionTools",
                "Initialization",
                init_result.success,
                init_result.error if not init_result.success else None,
                {
                    "success": init_result.success,
                    "has_data": bool(init_result.data),
                    "tool": init_result.tool
                }
            )
            return init_result.success

        except Exception as e:
            self.log_result(
                "ProductionTools",
                "Initialization Test",
                False,
                f"Runtime error: {str(e)}"
            )
            return False

    async def test_memory_operations(self, tools):
        """Test memory storage and retrieval"""
        try:
            test_data = {
                "test_key": "test_value",
                "timestamp": self.timestamp,
                "component": "EPSILON_TEST"
            }

            # Test memory storage
            store_result = await tools.store_memory(
                memory_key="epsilon_test",
                content=test_data,
                tags=["test", "epsilon"]
            )

            if not isinstance(store_result, ToolResult):
                self.log_result(
                    "Memory Operations",
                    "Store Return Type",
                    False,
                    f"Expected ToolResult, got {type(store_result)}"
                )
                return False

            # Test memory search
            search_result = await tools.search_memory(
                query="epsilon test",
                limit=5
            )

            if not isinstance(search_result, ToolResult):
                self.log_result(
                    "Memory Operations",
                    "Search Return Type",
                    False,
                    f"Expected ToolResult, got {type(search_result)}"
                )
                return False

            # Verify functionality
            store_success = store_result.success
            search_success = search_result.success

            self.log_result(
                "Memory Operations",
                "Store and Search",
                store_success and search_success,
                None if (store_success and search_success) else f"Store: {store_result.error}, Search: {search_result.error}",
                {
                    "store_success": store_success,
                    "search_success": search_success,
                    "search_results_count": len(search_result.data) if search_success and search_result.data else 0
                }
            )
            return store_success and search_success

        except Exception as e:
            self.log_result(
                "Memory Operations",
                "Runtime Test",
                False,
                f"Runtime error: {str(e)}"
            )
            return False

    async def test_git_operations(self, tools):
        """Test git functionality"""
        try:
            # Test git status
            status_result = await tools.git_status()

            if not isinstance(status_result, ToolResult):
                self.log_result(
                    "Git Operations",
                    "Status Return Type",
                    False,
                    f"Expected ToolResult, got {type(status_result)}"
                )
                return False

            self.log_result(
                "Git Operations",
                "Git Status",
                status_result.success,
                status_result.error if not status_result.success else None,
                {
                    "success": status_result.success,
                    "has_data": bool(status_result.data),
                    "tool": status_result.tool
                }
            )
            return status_result.success

        except Exception as e:
            self.log_result(
                "Git Operations",
                "Runtime Test",
                False,
                f"Runtime error: {str(e)}"
            )
            return False

    async def test_web_search(self, tools):
        """Test web search functionality"""
        try:
            # Test web search
            search_result = await tools.web_search(
                query="Python FastAPI",
                max_results=3
            )

            if not isinstance(search_result, ToolResult):
                self.log_result(
                    "Web Search",
                    "Search Return Type",
                    False,
                    f"Expected ToolResult, got {type(search_result)}"
                )
                return False

            self.log_result(
                "Web Search",
                "DuckDuckGo Search",
                search_result.success,
                search_result.error if not search_result.success else None,
                {
                    "success": search_result.success,
                    "results_count": len(search_result.data) if search_result.success and search_result.data else 0,
                    "tool": search_result.tool
                }
            )
            return search_result.success

        except Exception as e:
            self.log_result(
                "Web Search",
                "Runtime Test",
                False,
                f"Runtime error: {str(e)}"
            )
            return False

    async def test_browser_automation(self, tools):
        """Test browser automation functionality"""
        try:
            # Test browser launch (headless)
            launch_result = await tools.launch_browser(headless=True)

            if not isinstance(launch_result, ToolResult):
                self.log_result(
                    "Browser Automation",
                    "Launch Return Type",
                    False,
                    f"Expected ToolResult, got {type(launch_result)}"
                )
                return False

            if launch_result.success:
                # Test URL browsing
                browse_result = await tools.browse_url(
                    url="https://httpbin.org/html",
                    extract_text=True
                )

                # Cleanup browser
                cleanup_result = await tools.cleanup()

                browse_success = isinstance(browse_result, ToolResult) and browse_result.success
                cleanup_success = isinstance(cleanup_result, ToolResult) and cleanup_result.success

                self.log_result(
                    "Browser Automation",
                    "Full Browser Workflow",
                    launch_result.success and browse_success and cleanup_success,
                    None if (launch_result.success and browse_success and cleanup_success) else "Some operations failed",
                    {
                        "launch": launch_result.success,
                        "browse": browse_success,
                        "cleanup": cleanup_success,
                        "extracted_content": bool(browse_result.data) if browse_success else False
                    }
                )
                return launch_result.success and browse_success and cleanup_success

            else:
                self.log_result(
                    "Browser Automation",
                    "Browser Launch",
                    False,
                    launch_result.error
                )
                return False

        except Exception as e:
            self.log_result(
                "Browser Automation",
                "Runtime Test",
                False,
                f"Runtime error: {str(e)}"
            )
            return False

    async def test_health_check(self, tools):
        """Test health check functionality"""
        try:
            health_result = await tools.health_check()

            if not isinstance(health_result, ToolResult):
                self.log_result(
                    "Health Check",
                    "Return Type",
                    False,
                    f"Expected ToolResult, got {type(health_result)}"
                )
                return False

            self.log_result(
                "Health Check",
                "System Health",
                health_result.success,
                health_result.error if not health_result.success else None,
                {
                    "success": health_result.success,
                    "health_data": bool(health_result.data),
                    "tool": health_result.tool
                }
            )
            return health_result.success

        except Exception as e:
            self.log_result(
                "Health Check",
                "Runtime Test",
                False,
                f"Runtime error: {str(e)}"
            )
            return False

    async def run_comprehensive_verification(self):
        """Run all verification tests"""
        print("🔍 EPSILON: Starting comprehensive Agent GAMMA ProductionTools verification...")

        # Test imports and structure first
        if not self.test_imports_and_structure():
            print("❌ EPSILON: Structure test failed, skipping functional tests")
            return self.generate_summary()

        # Initialize tools for functional tests
        try:
            tools = ProductionTools()

            # Test initialization
            init_success = await self.test_initialization()

            if not init_success:
                print("❌ EPSILON: Initialization failed, skipping advanced tests")
                return self.generate_summary()

            # Run functional tests
            await asyncio.gather(
                self.test_memory_operations(tools),
                self.test_git_operations(tools),
                self.test_web_search(tools),
                self.test_browser_automation(tools),
                self.test_health_check(tools)
            )

        except Exception as e:
            self.log_result(
                "Comprehensive Test",
                "Test Suite Setup",
                False,
                f"Test setup error: {str(e)}"
            )

        return self.generate_summary()

    def generate_summary(self):
        """Generate comprehensive verification summary"""
        passed = sum(1 for r in self.results if r['passed'])
        total = len(self.results)

        summary = {
            "agent": "GAMMA",
            "component": "ProductionTools",
            "timestamp": self.timestamp,
            "total_tests": total,
            "passed": passed,
            "failed": total - passed,
            "success_rate": (passed / total * 100) if total > 0 else 0,
            "production_ready": passed == total and total > 0,
            "results": self.results,
            "verification_level": "COMPREHENSIVE"
        }

        print(f"\n🔍 EPSILON: Agent GAMMA ProductionTools verification complete")
        print(f"📊 Total Tests: {total}")
        print(f"✅ Passed: {passed}")
        print(f"❌ Failed: {total - passed}")
        print(f"🎯 Success Rate: {summary['success_rate']:.1f}%")
        print(f"🏭 Production Ready: {'YES' if summary['production_ready'] else 'NO'}")

        if summary['production_ready']:
            print("🎉 EPSILON APPROVAL: Agent GAMMA's ProductionTools are PRODUCTION READY")
        else:
            print("⚠️  EPSILON REJECTION: Agent GAMMA's ProductionTools need fixes before production")

        return summary


async def main():
    """Main verification runner"""
    verifier = EpsilonGammaVerifier()
    summary = await verifier.run_comprehensive_verification()

    # Save results
    results_file = Path("/Volumes/Storage/Development/CASPER DEV/.casper/transformation/test_results/gamma_comprehensive_verification.json")
    with open(results_file, 'w') as f:
        json.dump(summary, f, indent=2)

    print(f"📄 Comprehensive results saved to: {results_file}")
    return summary['production_ready']


if __name__ == "__main__":
    asyncio.run(main())