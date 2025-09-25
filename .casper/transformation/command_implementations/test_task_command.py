"""
Test for transformed task command
Verifies zero-tolerance requirement: commands MUST return data, not just print.
"""

import asyncio
import sys
import os

# Add the CASPER root to Python path
sys.path.insert(0, '/Volumes/Storage/Development/CASPER DEV')

from core.commands.task_command import TaskCommand
from core.commands.base import CommandResult


async def test_task_command_returns_data():
    """
    CRITICAL TEST: Verify task command returns CommandResult with data
    Zero tolerance for print-only commands
    """
    print("🧪 Testing task command transformation...")

    # Create command instance
    task_cmd = TaskCommand()

    # Test 1: Valid task input
    print("\n1. Testing valid task execution...")
    result = await task_cmd.safe_execute("Create a simple Python function", None)

    # Verify it returns CommandResult
    assert isinstance(result, CommandResult), f"Expected CommandResult, got {type(result)}"
    print(f"✅ Returns CommandResult: {type(result)}")

    # Verify it has data
    assert isinstance(result.data, dict), f"Expected dict data, got {type(result.data)}"
    assert len(result.data) > 0, "Data dictionary is empty"
    print(f"✅ Contains data: {len(result.data)} items")

    # Verify reasoning chain exists
    assert result.reasoning is not None, "Reasoning chain is None"
    assert len(result.reasoning) > 0, "Reasoning chain is empty"
    print(f"✅ Has reasoning chain: {len(result.reasoning)} steps")

    # Print the actual data returned (proof it's not just printing)
    print(f"\n📊 Data returned:")
    for key, value in result.data.items():
        if isinstance(value, dict):
            print(f"  {key}: {len(value)} items")
        else:
            print(f"  {key}: {str(value)[:100]}")

    # Test 2: Empty input validation
    print("\n2. Testing empty input validation...")
    empty_result = await task_cmd.safe_execute("", None)
    assert not empty_result.success, "Should fail with empty input"
    assert empty_result.error is not None, "Should have error message"
    print("✅ Properly validates empty input")

    # Test 3: Task with mock CASPER CLI context
    print("\n3. Testing with mock CASPER CLI context...")

    class MockCasperCLI:
        async def execute_task(self, task: str):
            # Simulate successful task execution
            return {"status": "completed", "task": task}

    mock_context = MockCasperCLI()
    context_result = await task_cmd.safe_execute("Test task with context", mock_context)

    assert context_result.success, "Should succeed with mock context"
    assert "casper_cli_delegation" in context_result.data["execution"]["method"]
    print("✅ Integrates with CASPER CLI context")

    print(f"\n🎉 ALL TESTS PASSED")
    print(f"📋 Task command successfully transformed:")
    print(f"   - Returns CommandResult ✅")
    print(f"   - Contains structured data ✅")
    print(f"   - Has ReAct reasoning ✅")
    print(f"   - Validates input ✅")
    print(f"   - Integrates with existing system ✅")

    return True


async def main():
    """Run the test"""
    try:
        await test_task_command_returns_data()
    except Exception as e:
        print(f"❌ TEST FAILED: {str(e)}")
        import traceback
        traceback.print_exc()
        return False
    return True


if __name__ == "__main__":
    result = asyncio.run(main())
    sys.exit(0 if result else 1)