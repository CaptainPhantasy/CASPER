#!/usr/bin/env python3
"""
Terminal Testing Runner Script
Comprehensive test runner for CASPER terminal infrastructure with reporting and analysis.
"""

import argparse
import sys
import subprocess
import json
import time
from pathlib import Path
from typing import Dict, List, Any, Optional
import xml.etree.ElementTree as ET


class TerminalTestRunner:
    """Test runner for terminal infrastructure."""

    def __init__(self, project_root: Path):
        self.project_root = project_root
        self.test_results = {}
        self.coverage_data = {}

    def run_unit_tests(self, verbose: bool = False) -> bool:
        """Run unit tests for terminal components."""
        print("🧪 Running terminal unit tests...")

        cmd = [
            "python", "-m", "pytest",
            "tests/test_terminal_pty.py",
            "tests/test_terminal_websocket.py",
            "tests/test_terminal_command_proxy.py",
            "tests/test_terminal_server_integration.py",
            "--cov=core.terminal",
            "--cov-report=xml:coverage-unit.xml",
            "--cov-report=html:htmlcov-unit",
            "--cov-fail-under=85",
            "--junit-xml=unit-test-results.xml",
            "-m", "unit and not slow"
        ]

        if verbose:
            cmd.append("-v")

        try:
            result = subprocess.run(cmd, cwd=self.project_root, capture_output=True, text=True)
            self.test_results["unit_tests"] = {
                "returncode": result.returncode,
                "stdout": result.stdout,
                "stderr": result.stderr
            }

            if result.returncode == 0:
                print("✅ Unit tests passed")
                return True
            else:
                print("❌ Unit tests failed")
                if verbose:
                    print(result.stdout)
                    print(result.stderr)
                return False

        except Exception as e:
            print(f"❌ Error running unit tests: {e}")
            return False

    def run_integration_tests(self, verbose: bool = False) -> bool:
        """Run integration tests."""
        print("🔗 Running terminal integration tests...")

        cmd = [
            "python", "-m", "pytest",
            "tests/test_terminal_layout_integration.py",
            "--cov=core.terminal",
            "--cov-append",
            "--cov-report=xml:coverage-integration.xml",
            "--junit-xml=integration-test-results.xml",
            "-m", "integration"
        ]

        if verbose:
            cmd.append("-v")

        try:
            result = subprocess.run(cmd, cwd=self.project_root, capture_output=True, text=True)
            self.test_results["integration_tests"] = {
                "returncode": result.returncode,
                "stdout": result.stdout,
                "stderr": result.stderr
            }

            if result.returncode == 0:
                print("✅ Integration tests passed")
                return True
            else:
                print("❌ Integration tests failed")
                if verbose:
                    print(result.stdout)
                    print(result.stderr)
                return False

        except Exception as e:
            print(f"❌ Error running integration tests: {e}")
            return False

    def run_security_tests(self, verbose: bool = False) -> bool:
        """Run security tests."""
        print("🔒 Running terminal security tests...")

        cmd = [
            "python", "-m", "pytest",
            "tests/test_terminal_security.py",
            "--cov=core.terminal.security",
            "--cov-report=xml:coverage-security.xml",
            "--junit-xml=security-test-results.xml",
            "-m", "security"
        ]

        if verbose:
            cmd.append("-v")

        try:
            result = subprocess.run(cmd, cwd=self.project_root, capture_output=True, text=True)
            self.test_results["security_tests"] = {
                "returncode": result.returncode,
                "stdout": result.stdout,
                "stderr": result.stderr
            }

            if result.returncode == 0:
                print("✅ Security tests passed")
                return True
            else:
                print("❌ Security tests failed")
                if verbose:
                    print(result.stdout)
                    print(result.stderr)
                return False

        except Exception as e:
            print(f"❌ Error running security tests: {e}")
            return False

    def run_performance_tests(self, verbose: bool = False) -> bool:
        """Run performance tests."""
        print("⚡ Running terminal performance tests...")

        cmd = [
            "python", "-m", "pytest",
            "tests/test_terminal_performance.py",
            "--junit-xml=performance-test-results.xml",
            "-m", "performance",
            "--tb=short"
        ]

        if verbose:
            cmd.append("-v")

        try:
            result = subprocess.run(cmd, cwd=self.project_root, capture_output=True, text=True)
            self.test_results["performance_tests"] = {
                "returncode": result.returncode,
                "stdout": result.stdout,
                "stderr": result.stderr
            }

            if result.returncode == 0:
                print("✅ Performance tests passed")
                return True
            else:
                print("❌ Performance tests failed")
                if verbose:
                    print(result.stdout)
                    print(result.stderr)
                return False

        except Exception as e:
            print(f"❌ Error running performance tests: {e}")
            return False

    def run_e2e_tests(self, headless: bool = True, verbose: bool = False) -> bool:
        """Run E2E tests with Playwright."""
        print("🌐 Running terminal E2E tests...")

        # First, check if Playwright browsers are installed
        try:
            subprocess.run(
                ["npx", "playwright", "install", "--with-deps", "chromium"],
                cwd=self.project_root / "dashboard",
                check=True,
                capture_output=True
            )
        except subprocess.CalledProcessError:
            print("⚠️  Could not install Playwright browsers, skipping E2E tests")
            return True

        cmd = [
            "python", "-m", "pytest",
            "tests/test_terminal_e2e.py",
            "--junit-xml=e2e-test-results.xml",
            "-m", "e2e"
        ]

        if verbose:
            cmd.append("-v")

        # Set environment for headless mode
        env = {"PLAYWRIGHT_HEADLESS": "true" if headless else "false"}

        try:
            result = subprocess.run(
                cmd,
                cwd=self.project_root,
                capture_output=True,
                text=True,
                env={**subprocess.os.environ, **env}
            )

            self.test_results["e2e_tests"] = {
                "returncode": result.returncode,
                "stdout": result.stdout,
                "stderr": result.stderr
            }

            if result.returncode == 0:
                print("✅ E2E tests passed")
                return True
            else:
                print("❌ E2E tests failed")
                if verbose:
                    print(result.stdout)
                    print(result.stderr)
                return False

        except Exception as e:
            print(f"❌ Error running E2E tests: {e}")
            return False

    def analyze_coverage(self) -> Dict[str, Any]:
        """Analyze test coverage from XML reports."""
        print("📊 Analyzing test coverage...")

        coverage_files = [
            "coverage-unit.xml",
            "coverage-integration.xml",
            "coverage-security.xml"
        ]

        combined_coverage = {
            "lines_covered": 0,
            "lines_total": 0,
            "coverage_percentage": 0.0,
            "modules": {}
        }

        for coverage_file in coverage_files:
            coverage_path = self.project_root / coverage_file
            if coverage_path.exists():
                try:
                    tree = ET.parse(coverage_path)
                    root = tree.getroot()

                    # Parse coverage data (format depends on coverage.py XML output)
                    for package in root.findall('.//package'):
                        package_name = package.get('name', '')
                        if 'terminal' in package_name:
                            lines_covered = int(package.get('lines-covered', 0))
                            lines_valid = int(package.get('lines-valid', 0))

                            combined_coverage["lines_covered"] += lines_covered
                            combined_coverage["lines_total"] += lines_valid

                            if lines_valid > 0:
                                module_coverage = (lines_covered / lines_valid) * 100
                                combined_coverage["modules"][package_name] = {
                                    "lines_covered": lines_covered,
                                    "lines_total": lines_valid,
                                    "percentage": module_coverage
                                }

                except Exception as e:
                    print(f"⚠️  Could not parse coverage file {coverage_file}: {e}")

        # Calculate overall coverage
        if combined_coverage["lines_total"] > 0:
            combined_coverage["coverage_percentage"] = (
                combined_coverage["lines_covered"] / combined_coverage["lines_total"]
            ) * 100

        self.coverage_data = combined_coverage
        return combined_coverage

    def generate_test_report(self) -> Dict[str, Any]:
        """Generate comprehensive test report."""
        print("📋 Generating test report...")

        report = {
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S UTC", time.gmtime()),
            "project": "CASPER Terminal Infrastructure",
            "test_suites": {},
            "summary": {
                "total_suites": 0,
                "passed_suites": 0,
                "failed_suites": 0,
                "success_rate": 0.0
            },
            "coverage": self.coverage_data
        }

        # Process test results
        junit_files = [
            ("unit_tests", "unit-test-results.xml"),
            ("integration_tests", "integration-test-results.xml"),
            ("security_tests", "security-test-results.xml"),
            ("performance_tests", "performance-test-results.xml"),
            ("e2e_tests", "e2e-test-results.xml")
        ]

        for suite_name, junit_file in junit_files:
            junit_path = self.project_root / junit_file
            suite_data = {
                "name": suite_name,
                "passed": False,
                "tests": 0,
                "failures": 0,
                "errors": 0,
                "time": 0.0,
                "details": self.test_results.get(suite_name, {})
            }

            if junit_path.exists():
                try:
                    tree = ET.parse(junit_path)
                    root = tree.getroot()

                    suite_data.update({
                        "tests": int(root.get("tests", 0)),
                        "failures": int(root.get("failures", 0)),
                        "errors": int(root.get("errors", 0)),
                        "time": float(root.get("time", 0))
                    })

                    suite_data["passed"] = (suite_data["failures"] + suite_data["errors"]) == 0

                except Exception as e:
                    print(f"⚠️  Could not parse JUnit file {junit_file}: {e}")
                    suite_data["passed"] = self.test_results.get(suite_name, {}).get("returncode", 1) == 0

            else:
                # Use return code if JUnit file doesn't exist
                suite_data["passed"] = self.test_results.get(suite_name, {}).get("returncode", 1) == 0

            report["test_suites"][suite_name] = suite_data
            report["summary"]["total_suites"] += 1
            if suite_data["passed"]:
                report["summary"]["passed_suites"] += 1
            else:
                report["summary"]["failed_suites"] += 1

        # Calculate success rate
        if report["summary"]["total_suites"] > 0:
            report["summary"]["success_rate"] = (
                report["summary"]["passed_suites"] / report["summary"]["total_suites"]
            ) * 100

        return report

    def save_report(self, report: Dict[str, Any], output_file: str = "terminal-test-report.json"):
        """Save test report to file."""
        report_path = self.project_root / output_file
        with open(report_path, 'w') as f:
            json.dump(report, f, indent=2)

        print(f"📄 Test report saved to {report_path}")

    def print_summary(self, report: Dict[str, Any]):
        """Print test summary to console."""
        print("\n" + "="*60)
        print("🎯 TERMINAL TESTING SUMMARY")
        print("="*60)

        print(f"📊 Test Suites: {report['summary']['total_suites']}")
        print(f"✅ Passed: {report['summary']['passed_suites']}")
        print(f"❌ Failed: {report['summary']['failed_suites']}")
        print(f"📈 Success Rate: {report['summary']['success_rate']:.1f}%")

        if report["coverage"]:
            coverage = report["coverage"]
            print(f"📋 Test Coverage: {coverage['coverage_percentage']:.1f}%")
            print(f"📝 Lines Covered: {coverage['lines_covered']}/{coverage['lines_total']}")

        print("\n📋 Suite Details:")
        for suite_name, suite_data in report["test_suites"].items():
            status = "✅" if suite_data["passed"] else "❌"
            print(f"  {status} {suite_name}: {suite_data['tests']} tests, "
                  f"{suite_data['failures']} failures, {suite_data['errors']} errors")

        # Coverage by module
        if report["coverage"] and report["coverage"]["modules"]:
            print("\n📊 Coverage by Module:")
            for module, data in report["coverage"]["modules"].items():
                print(f"  {module}: {data['percentage']:.1f}% "
                      f"({data['lines_covered']}/{data['lines_total']} lines)")

        print("="*60)


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Run CASPER terminal tests")

    parser.add_argument("--unit", action="store_true", help="Run unit tests")
    parser.add_argument("--integration", action="store_true", help="Run integration tests")
    parser.add_argument("--security", action="store_true", help="Run security tests")
    parser.add_argument("--performance", action="store_true", help="Run performance tests")
    parser.add_argument("--e2e", action="store_true", help="Run E2E tests")
    parser.add_argument("--all", action="store_true", help="Run all tests")
    parser.add_argument("--verbose", "-v", action="store_true", help="Verbose output")
    parser.add_argument("--headless", action="store_true", default=True, help="Run E2E tests in headless mode")
    parser.add_argument("--output", "-o", default="terminal-test-report.json", help="Output report file")

    args = parser.parse_args()

    # Default to all tests if no specific test type is selected
    if not any([args.unit, args.integration, args.security, args.performance, args.e2e]):
        args.all = True

    project_root = Path(__file__).parent.parent
    runner = TerminalTestRunner(project_root)

    print("🚀 Starting CASPER Terminal Testing Suite")
    print(f"📁 Project Root: {project_root}")
    print("-" * 60)

    results = []
    start_time = time.time()

    try:
        if args.all or args.unit:
            results.append(runner.run_unit_tests(args.verbose))

        if args.all or args.integration:
            results.append(runner.run_integration_tests(args.verbose))

        if args.all or args.security:
            results.append(runner.run_security_tests(args.verbose))

        if args.all or args.performance:
            results.append(runner.run_performance_tests(args.verbose))

        if args.all or args.e2e:
            results.append(runner.run_e2e_tests(args.headless, args.verbose))

        # Analyze coverage and generate report
        runner.analyze_coverage()
        report = runner.generate_test_report()
        runner.save_report(report, args.output)
        runner.print_summary(report)

        execution_time = time.time() - start_time
        print(f"\n⏱️  Total execution time: {execution_time:.2f} seconds")

        # Exit with appropriate code
        if all(results):
            print("🎉 All tests completed successfully!")
            sys.exit(0)
        else:
            print("💥 Some tests failed!")
            sys.exit(1)

    except KeyboardInterrupt:
        print("\n⚠️  Test execution interrupted by user")
        sys.exit(130)
    except Exception as e:
        print(f"💥 Unexpected error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()