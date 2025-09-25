#!/usr/bin/env python3
"""
EPSILON QA Testing Framework
CASPER Enterprise Transformation

ZERO TOLERANCE DIRECTIVE:
- NO passing tests for broken code
- NO marking complete without verification
- ONLY sign off on PRODUCTION-READY implementations
"""

import pytest
import asyncio
import os
import sys
import json
from pathlib import Path
from typing import Dict, Any, List, Optional
from dataclasses import dataclass
from datetime import datetime, timezone
import importlib.util
import subprocess


@dataclass
class VerificationResult:
    """Result of a verification test"""
    component: str
    test_name: str
    passed: bool
    error: Optional[str] = None
    timestamp: str = None
    details: Dict[str, Any] = None

    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now(timezone.utc).isoformat()


class ProductionTestSuite:
    """EPSILON's production-ready test suite"""

    def __init__(self):
        self.results: List[VerificationResult] = []
        self.test_root = Path("/Volumes/Storage/Development/CASPER DEV/.casper/transformation")
        self.project_root = Path("/Volumes/Storage/Development/CASPER DEV")

    def log_result(self, result: VerificationResult):
        """Log a verification result"""
        self.results.append(result)
        print(f"🔍 EPSILON: {result.component} - {result.test_name} - {'✅ PASS' if result.passed else '❌ FAIL'}")
        if result.error:
            print(f"   Error: {result.error}")

    def can_import_module(self, module_path: str) -> bool:
        """Check if we can import a module"""
        try:
            spec = importlib.util.spec_from_file_location("test_module", module_path)
            if spec is None:
                return False
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            return True
        except Exception:
            return False

    def file_exists_and_valid(self, file_path: Path) -> bool:
        """Check if file exists and has content"""
        return file_path.exists() and file_path.stat().st_size > 0

    async def test_react_engine(self) -> VerificationResult:
        """Test Agent ALPHA's ReAct Engine implementation"""
        react_path = self.test_root / "react_implementations" / "react_engine.py"

        if not self.file_exists_and_valid(react_path):
            return VerificationResult(
                component="ReAct Engine",
                test_name="File Existence",
                passed=False,
                error=f"ReAct engine file not found or empty at {react_path}"
            )

        # Test if we can import it
        if not self.can_import_module(str(react_path)):
            return VerificationResult(
                component="ReAct Engine",
                test_name="Import Test",
                passed=False,
                error="Cannot import ReAct engine module"
            )

        try:
            # Dynamic import and test
            spec = importlib.util.spec_from_file_location("react_engine", react_path)
            react_module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(react_module)

            # Look for ProductionReActEngine class
            if not hasattr(react_module, 'ProductionReActEngine'):
                return VerificationResult(
                    component="ReAct Engine",
                    test_name="Class Structure",
                    passed=False,
                    error="ProductionReActEngine class not found"
                )

            # Test instantiation
            engine = react_module.ProductionReActEngine()

            # Test basic methods exist
            required_methods = ['reason', 'execute', 'observe']
            missing_methods = [method for method in required_methods if not hasattr(engine, method)]

            if missing_methods:
                return VerificationResult(
                    component="ReAct Engine",
                    test_name="Method Structure",
                    passed=False,
                    error=f"Missing required methods: {missing_methods}"
                )

            return VerificationResult(
                component="ReAct Engine",
                test_name="Basic Structure",
                passed=True,
                details={"methods": required_methods, "instantiable": True}
            )

        except Exception as e:
            return VerificationResult(
                component="ReAct Engine",
                test_name="Runtime Test",
                passed=False,
                error=f"Runtime error: {str(e)}"
            )

    async def test_state_management(self) -> VerificationResult:
        """Test Agent BETA's State Management implementation"""
        state_path = self.test_root / "state_management" / "langgraph_orchestrator.py"

        if not self.file_exists_and_valid(state_path):
            return VerificationResult(
                component="State Management",
                test_name="File Existence",
                passed=False,
                error=f"State management file not found at {state_path}"
            )

        if not self.can_import_module(str(state_path)):
            return VerificationResult(
                component="State Management",
                test_name="Import Test",
                passed=False,
                error="Cannot import state management module"
            )

        try:
            spec = importlib.util.spec_from_file_location("state_manager", state_path)
            state_module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(state_module)

            if not hasattr(state_module, 'ProductionStateManager'):
                return VerificationResult(
                    component="State Management",
                    test_name="Class Structure",
                    passed=False,
                    error="ProductionStateManager class not found"
                )

            manager = state_module.ProductionStateManager()
            required_methods = ['save_state', 'load_state', 'create_checkpoint']
            missing_methods = [method for method in required_methods if not hasattr(manager, method)]

            if missing_methods:
                return VerificationResult(
                    component="State Management",
                    test_name="Method Structure",
                    passed=False,
                    error=f"Missing required methods: {missing_methods}"
                )

            return VerificationResult(
                component="State Management",
                test_name="Basic Structure",
                passed=True,
                details={"methods": required_methods, "instantiable": True}
            )

        except Exception as e:
            return VerificationResult(
                component="State Management",
                test_name="Runtime Test",
                passed=False,
                error=f"Runtime error: {str(e)}"
            )

    async def test_command_base(self) -> VerificationResult:
        """Test Agent DELTA's Command Base Class"""
        command_path = self.test_root / "command_implementations" / "base.py"

        if not self.file_exists_and_valid(command_path):
            return VerificationResult(
                component="Command Base",
                test_name="File Existence",
                passed=False,
                error=f"Command base file not found at {command_path}"
            )

        if not self.can_import_module(str(command_path)):
            return VerificationResult(
                component="Command Base",
                test_name="Import Test",
                passed=False,
                error="Cannot import command base module"
            )

        try:
            spec = importlib.util.spec_from_file_location("command_base", command_path)
            command_module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(command_module)

            if not hasattr(command_module, 'CommandResult'):
                return VerificationResult(
                    component="Command Base",
                    test_name="CommandResult Class",
                    passed=False,
                    error="CommandResult class not found"
                )

            if not hasattr(command_module, 'BaseCommand'):
                return VerificationResult(
                    component="Command Base",
                    test_name="BaseCommand Class",
                    passed=False,
                    error="BaseCommand class not found"
                )

            # Test CommandResult instantiation
            result = command_module.CommandResult(
                success=True,
                message="test",
                data={"test": "data"}
            )

            required_attrs = ['success', 'message', 'data', 'timestamp']
            missing_attrs = [attr for attr in required_attrs if not hasattr(result, attr)]

            if missing_attrs:
                return VerificationResult(
                    component="Command Base",
                    test_name="CommandResult Attributes",
                    passed=False,
                    error=f"Missing required attributes: {missing_attrs}"
                )

            return VerificationResult(
                component="Command Base",
                test_name="Basic Structure",
                passed=True,
                details={"classes": ["CommandResult", "BaseCommand"], "instantiable": True}
            )

        except Exception as e:
            return VerificationResult(
                component="Command Base",
                test_name="Runtime Test",
                passed=False,
                error=f"Runtime error: {str(e)}"
            )

    async def run_all_tests(self) -> Dict[str, Any]:
        """Run all available tests"""
        print("🔍 EPSILON: Starting comprehensive verification suite...")

        test_tasks = [
            self.test_react_engine(),
            self.test_state_management(),
            self.test_command_base()
        ]

        results = await asyncio.gather(*test_tasks, return_exceptions=True)

        for result in results:
            if isinstance(result, Exception):
                self.log_result(VerificationResult(
                    component="Test Suite",
                    test_name="Execution",
                    passed=False,
                    error=f"Test execution failed: {str(result)}"
                ))
            else:
                self.log_result(result)

        # Summary
        passed = sum(1 for r in self.results if r.passed)
        total = len(self.results)

        summary = {
            "total_tests": total,
            "passed": passed,
            "failed": total - passed,
            "success_rate": (passed / total * 100) if total > 0 else 0,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "results": [
                {
                    "component": r.component,
                    "test": r.test_name,
                    "passed": r.passed,
                    "error": r.error,
                    "timestamp": r.timestamp
                }
                for r in self.results
            ]
        }

        return summary

    def generate_report(self, summary: Dict[str, Any]) -> str:
        """Generate verification report"""
        report = f"""
# EPSILON VERIFICATION REPORT
**Timestamp:** {summary['timestamp']}
**Tests Run:** {summary['total_tests']}
**Success Rate:** {summary['success_rate']:.1f}%

## Results Summary
- ✅ Passed: {summary['passed']}
- ❌ Failed: {summary['failed']}

## Detailed Results
"""

        for result in summary['results']:
            status = "✅ PASS" if result['passed'] else "❌ FAIL"
            report += f"### {result['component']} - {result['test']}\n"
            report += f"**Status:** {status}\n"
            if result['error']:
                report += f"**Error:** {result['error']}\n"
            report += f"**Time:** {result['timestamp']}\n\n"

        return report


async def main():
    """Main test runner"""
    suite = ProductionTestSuite()
    summary = await suite.run_all_tests()

    # Save results
    results_file = Path("/Volumes/Storage/Development/CASPER DEV/.casper/transformation/test_results/verification_results.json")
    with open(results_file, 'w') as f:
        json.dump(summary, f, indent=2)

    # Generate report
    report = suite.generate_report(summary)
    report_file = Path("/Volumes/Storage/Development/CASPER DEV/.casper/transformation/test_results/verification_report.md")
    with open(report_file, 'w') as f:
        f.write(report)

    print(f"\n🔍 EPSILON: Verification complete. Success rate: {summary['success_rate']:.1f}%")
    print(f"📊 Report saved to: {report_file}")
    print(f"📊 Results saved to: {results_file}")

    return summary['success_rate'] == 100.0


if __name__ == "__main__":
    asyncio.run(main())