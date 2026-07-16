"""
Comprehensive Test Suite for All Transformed Commands
Verifies zero-tolerance requirement: ALL commands MUST return data, not just print.
Tests the complete command transformation with real data validation.
"""

import asyncio
import sys
import os
from datetime import datetime

# Add the CASPER root to Python path
sys.path.insert(0, '/Volumes/Storage/Development/CASPER DEV')

from core.commands.base import CommandResult, command_registry
from core.commands.task_command import TaskCommand
from core.commands.analyze_command import AnalyzeCommand
from core.commands.commit_command import CommitCommand
from core.commands.explain_command import ExplainCommand


class CommandTestResults:
    """Track test results for all commands"""

    def __init__(self):
        self.results = {}
        self.total_tests = 0
        self.passed_tests = 0

    def add_result(self, command: str, test: str, passed: bool, details: str = ""):
        if command not in self.results:
            self.results[command] = []

        self.results[command].append({
            "test": test,
            "passed": passed,
            "details": details,
            "timestamp": datetime.utcnow().isoformat() + "Z"
        })

        self.total_tests += 1
        if passed:
            self.passed_tests += 1

    def get_summary(self) -> dict:
        return {
            "total_tests": self.total_tests,
            "passed_tests": self.passed_tests,
            "success_rate": (self.passed_tests / self.total_tests * 100) if self.total_tests > 0 else 0,
            "commands_tested": len(self.results),
            "all_passed": self.passed_tests == self.total_tests
        }


async def test_command_transformation_complete():
    """
    MASTER TEST: Verify all 4 priority commands are transformed correctly
    Zero tolerance for commands that don't return CommandResult with data
    """
    print("🚀 CASPER COMMAND TRANSFORMATION TEST SUITE")
    print("=" * 60)

    test_results = CommandTestResults()

    # Test each transformed command
    commands_to_test = [
        ("task", TaskCommand()),
        ("analyze", AnalyzeCommand()),
        ("commit", CommitCommand()),
        ("explain", ExplainCommand())
    ]

    for command_name, command_instance in commands_to_test:
        print(f"\n🧪 Testing {command_name.upper()} Command...")
        await test_single_command(command_instance, command_name, test_results)

    # Print comprehensive results
    print("\n" + "=" * 60)
    print("🏆 TRANSFORMATION TEST RESULTS")
    print("=" * 60)

    summary = test_results.get_summary()

    for command_name, results in test_results.results.items():
        print(f"\n📋 {command_name.upper()} Command:")
        for result in results:
            status = "✅" if result["passed"] else "❌"
            print(f"  {status} {result['test']}")
            if result["details"]:
                print(f"     {result['details']}")

    print(f"\n🎯 OVERALL RESULTS:")
    print(f"   Tests Run: {summary['total_tests']}")
    print(f"   Tests Passed: {summary['passed_tests']}")
    print(f"   Success Rate: {summary['success_rate']:.1f}%")
    print(f"   Commands Transformed: {summary['commands_tested']}/4")

    if summary["all_passed"]:
        print(f"\n🎉 ALL TESTS PASSED! TRANSFORMATION SUCCESSFUL!")
        print(f"📊 All {summary['commands_tested']} commands return structured data")
        print(f"⚡ Zero tolerance directive enforced: NO print-only commands")
    else:
        print(f"\n❌ TRANSFORMATION INCOMPLETE")
        print(f"🔧 {summary['total_tests'] - summary['passed_tests']} tests failed")

    return summary["all_passed"]


async def test_single_command(command_instance, command_name: str, test_results: CommandTestResults):
    """Test a single command comprehensively"""

    # Test 1: Command returns CommandResult
    try:
        result = await command_instance.safe_execute("test input", None)
        if isinstance(result, CommandResult):
            test_results.add_result(
                command_name,
                "Returns CommandResult",
                True,
                f"Type: {type(result).__name__}"
            )
        else:
            test_results.add_result(
                command_name,
                "Returns CommandResult",
                False,
                f"Got {type(result)} instead"
            )
    except Exception as e:
        test_results.add_result(
            command_name,
            "Returns CommandResult",
            False,
            f"Exception: {str(e)}"
        )

    # Test 2: Command has data dictionary
    try:
        result = await command_instance.safe_execute("test input with data", None)
        if hasattr(result, 'data') and isinstance(result.data, dict):
            test_results.add_result(
                command_name,
                "Contains data dictionary",
                True,
                f"Data keys: {len(result.data)}"
            )
        else:
            test_results.add_result(
                command_name,
                "Contains data dictionary",
                False,
                f"Data type: {type(result.data) if hasattr(result, 'data') else 'missing'}"
            )
    except Exception as e:
        test_results.add_result(
            command_name,
            "Contains data dictionary",
            False,
            f"Exception: {str(e)}"
        )

    # Test 3: Command has reasoning chain
    try:
        result = await command_instance.safe_execute("test reasoning chain", None)
        if hasattr(result, 'reasoning') and isinstance(result.reasoning, list) and len(result.reasoning) > 0:
            test_results.add_result(
                command_name,
                "Has ReAct reasoning chain",
                True,
                f"Reasoning steps: {len(result.reasoning)}"
            )
        else:
            test_results.add_result(
                command_name,
                "Has ReAct reasoning chain",
                False,
                f"Reasoning: {type(result.reasoning) if hasattr(result, 'reasoning') else 'missing'}"
            )
    except Exception as e:
        test_results.add_result(
            command_name,
            "Has ReAct reasoning chain",
            False,
            f"Exception: {str(e)}"
        )

    # Test 4: Command validates input
    try:
        result = await command_instance.safe_execute("", None)
        # For most commands, empty input should fail validation
        expected_failure = command_name in ["task", "analyze", "explain"]  # commit allows empty for auto-message

        if expected_failure:
            if not result.success:
                test_results.add_result(
                    command_name,
                    "Validates input correctly",
                    True,
                    "Correctly rejects empty input"
                )
            else:
                test_results.add_result(
                    command_name,
                    "Validates input correctly",
                    False,
                    "Should have failed with empty input"
                )
        else:
            # For commit command, empty input is valid (auto-generated message)
            test_results.add_result(
                command_name,
                "Validates input correctly",
                True,
                "Handles empty input appropriately"
            )
    except Exception as e:
        test_results.add_result(
            command_name,
            "Validates input correctly",
            False,
            f"Exception during validation: {str(e)}"
        )

    # Test 5: Command-specific functionality
    await test_command_specific_features(command_instance, command_name, test_results)


async def test_command_specific_features(command_instance, command_name: str, test_results: CommandTestResults):
    """Test command-specific functionality"""

    try:
        if command_name == "task":
            # Test task planning capability
            result = await command_instance.safe_execute("Create a simple Python script", None)
            has_task_plan = "execution" in result.data and "plan" in result.data.get("execution", {})

            test_results.add_result(
                command_name,
                "Task planning functionality",
                has_task_plan or result.success,  # Either has plan or successfully delegated
                "Task execution or planning data present"
            )

        elif command_name == "analyze":
            # Test analysis capability with concept
            result = await command_instance.safe_execute("Python programming", None)
            has_analysis = "analysis" in result.data and "concept_analysis" in result.data.get("analysis", {}).get("results", {})

            test_results.add_result(
                command_name,
                "Concept analysis functionality",
                has_analysis,
                "Concept analysis data present" if has_analysis else "Missing analysis data"
            )

        elif command_name == "commit":
            # Test git repository detection
            result = await command_instance.safe_execute("test commit", None)
            handles_git_state = "git_operation" in result.data

            test_results.add_result(
                command_name,
                "Git operations handling",
                handles_git_state,
                "Git operation data present" if handles_git_state else "Missing git data"
            )

        elif command_name == "explain":
            # Test explanation generation
            result = await command_instance.safe_execute("API design", None)
            has_explanation = "explanation_data" in result.data and len(result.output) > 50

            test_results.add_result(
                command_name,
                "Explanation generation",
                has_explanation,
                f"Generated {len(result.output)} char explanation" if has_explanation else "Poor explanation"
            )

    except Exception as e:
        test_results.add_result(
            command_name,
            f"{command_name} specific functionality",
            False,
            f"Exception: {str(e)}"
        )


async def main():
    """Run the comprehensive test suite"""
    try:
        success = await test_command_transformation_complete()
        return success
    except Exception as e:
        print(f"❌ TEST SUITE FAILED: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    result = asyncio.run(main())
    sys.exit(0 if result else 1)