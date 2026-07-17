#!/usr/bin/env python3
"""
Demo script showcasing the CASPER Prime TerminalUI in action.
This demonstrates the multi-pane interface with live streaming updates.
"""

import asyncio
import sys
import os
from datetime import datetime
from pathlib import Path

# Add the project root to the Python path
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from core.terminal.ui.terminal_ui import create_terminal_ui
from core.terminal.interfaces import StreamChunk, WSMessageType


async def demo_coding_session():
    """Demonstrate a full coding session with streaming updates"""

    print("🚀 Starting CASPER Prime Terminal UI Demo")
    print("This will show the interactive multi-pane coding interface.")
    print("Press Ctrl+C to exit the demo.\n")

    await asyncio.sleep(2)

    # Create the terminal UI
    ui = create_terminal_ui("🎯 CASPER Prime - Live Demo")

    try:
        # Start the UI
        ui_task = asyncio.create_task(ui.start_ui())

        # Let UI initialize
        await asyncio.sleep(1)

        # Simulate a realistic coding session
        await simulate_task_analysis(ui)
        await simulate_code_generation(ui)
        await simulate_testing(ui)
        await simulate_completion(ui)

        # Keep UI running for user to observe
        print("\n✨ Demo complete! The terminal UI is running.")
        print("🎯 Features demonstrated:")
        print("   • Multi-pane layout with real-time updates")
        print("   • Syntax-highlighted code display")
        print("   • Reasoning chain visualization")
        print("   • Test result streaming")
        print("   • Progress indicators")
        print("   • Error handling")
        print("\nPress Ctrl+C to exit...")

        while True:
            await asyncio.sleep(1)

    except KeyboardInterrupt:
        print("\n👋 Demo interrupted by user")
    finally:
        await ui.shutdown()
        ui_task.cancel()
        try:
            await ui_task
        except asyncio.CancelledError:
            pass


async def simulate_task_analysis(ui):
    """Simulate the task analysis phase"""
    analysis_chunks = [
        StreamChunk(
            type="thought",
            content="🎯 Analyzing user request: 'Create a Python function to calculate Fibonacci numbers'",
            metadata={},
            timestamp=datetime.now(),
            sequence_number=1
        ),
        StreamChunk(
            type="thought",
            content="📝 Task breakdown:\n  1. Implement recursive Fibonacci function\n  2. Add memoization for optimization\n  3. Include error handling for negative inputs\n  4. Create comprehensive test cases",
            metadata={},
            timestamp=datetime.now(),
            sequence_number=2
        ),
        StreamChunk(
            type="thought",
            content="🧠 Complexity: MEDIUM - Single file, multiple functions, testing required",
            metadata={},
            timestamp=datetime.now(),
            sequence_number=3
        )
    ]

    # Stream analysis with delays for realism
    for chunk in analysis_chunks:
        await ui.display_stream(chunk)
        await ui.show_progress("Analyzing task...", (chunk.sequence_number / 3) * 25)
        await asyncio.sleep(1.5)


async def simulate_code_generation(ui):
    """Simulate the code generation phase"""

    # Show action
    action_chunk = StreamChunk(
        type="action",
        content="Implementing Fibonacci calculator with memoization",
        metadata={},
        timestamp=datetime.now(),
        sequence_number=4
    )
    await ui.display_stream(action_chunk)
    await ui.show_progress("Generating code...", 40)
    await asyncio.sleep(1)

    # Generate code in stages
    code_stages = [
        """# Fibonacci Calculator with Memoization
from functools import lru_cache
from typing import Dict, Optional

class FibonacciCalculator:
    \"\"\"Efficient Fibonacci calculator with multiple implementations\"\"\"

    def __init__(self):
        self._memo: Dict[int, int] = {}""",

        """
    @lru_cache(maxsize=None)
    def recursive_memoized(self, n: int) -> int:
        \"\"\"Calculate Fibonacci using recursive approach with memoization\"\"\"
        if n < 0:
            raise ValueError("Fibonacci not defined for negative numbers")
        if n <= 1:
            return n
        return self.recursive_memoized(n-1) + self.recursive_memoized(n-2)""",

        """
    def iterative(self, n: int) -> int:
        \"\"\"Calculate Fibonacci using iterative approach\"\"\"
        if n < 0:
            raise ValueError("Fibonacci not defined for negative numbers")
        if n <= 1:
            return n

        a, b = 0, 1
        for _ in range(2, n + 1):
            a, b = b, a + b
        return b""",

        """
    def get_sequence(self, length: int) -> List[int]:
        \"\"\"Generate Fibonacci sequence of given length\"\"\"
        return [self.iterative(i) for i in range(length)]

# Example usage
if __name__ == "__main__":
    calc = FibonacciCalculator()

    # Test various approaches
    n = 10
    print(f"Fibonacci({n}) recursive: {calc.recursive_memoized(n)}")
    print(f"Fibonacci({n}) iterative: {calc.iterative(n)}")
    print(f"First 10 numbers: {calc.get_sequence(10)}")"""
    ]

    full_code = ""
    for i, stage in enumerate(code_stages):
        full_code += stage

        code_chunk = StreamChunk(
            type="code",
            content=full_code,
            metadata={"language": "python"},
            timestamp=datetime.now(),
            sequence_number=5 + i
        )

        await ui.display_stream(code_chunk)
        await ui.show_progress("Generating code...", 40 + (i + 1) * 10)
        await asyncio.sleep(2)


async def simulate_testing(ui):
    """Simulate the testing phase"""

    await ui.show_progress("Running tests...", 80)

    test_chunks = [
        StreamChunk(
            type="test",
            content="🧪 Running unit tests for FibonacciCalculator...",
            metadata={},
            timestamp=datetime.now(),
            sequence_number=10
        ),
        StreamChunk(
            type="test",
            content="✅ test_recursive_memoized_basic: PASSED\n   Fibonacci(5) = 5",
            metadata={},
            timestamp=datetime.now(),
            sequence_number=11
        ),
        StreamChunk(
            type="test",
            content="✅ test_iterative_basic: PASSED\n   Fibonacci(10) = 55",
            metadata={},
            timestamp=datetime.now(),
            sequence_number=12
        ),
        StreamChunk(
            type="test",
            content="✅ test_negative_input_handling: PASSED\n   ValueError raised for negative input",
            metadata={},
            timestamp=datetime.now(),
            sequence_number=13
        ),
        StreamChunk(
            type="test",
            content="✅ test_sequence_generation: PASSED\n   Generated sequence: [0, 1, 1, 2, 3, 5, 8, 13, 21, 34]",
            metadata={},
            timestamp=datetime.now(),
            sequence_number=14
        ),
        StreamChunk(
            type="test",
            content="📊 Test Summary:\n   • Total tests: 4\n   • Passed: 4\n   • Failed: 0\n   • Coverage: 100%",
            metadata={},
            timestamp=datetime.now(),
            sequence_number=15
        )
    ]

    for chunk in test_chunks:
        await ui.display_stream(chunk)
        await asyncio.sleep(0.8)

    await ui.show_progress("Tests completed", 95)


async def simulate_completion(ui):
    """Simulate task completion"""

    completion_chunk = StreamChunk(
        type="result",
        content="🎉 Task completed successfully!\n\n✨ Deliverables:\n   • FibonacciCalculator class with recursive and iterative methods\n   • Comprehensive error handling for edge cases\n   • Memoization for optimal performance\n   • Full test coverage with all tests passing\n   • Clean, documented, production-ready code",
        metadata={},
        timestamp=datetime.now(),
        sequence_number=16
    )

    await ui.display_stream(completion_chunk)
    await ui.show_progress("Task completed!", 100)

    # Add final reasoning
    final_thought = StreamChunk(
        type="thought",
        content="✅ Task execution complete. Generated efficient Fibonacci calculator with multiple implementation strategies and comprehensive testing.",
        metadata={},
        timestamp=datetime.now(),
        sequence_number=17
    )

    await ui.display_stream(final_thought)


async def demo_error_handling():
    """Demonstrate error handling in the UI"""

    print("🔥 Demonstrating error handling capabilities...")

    ui = create_terminal_ui("🚨 CASPER Error Demo")

    try:
        ui_task = asyncio.create_task(ui.start_ui())
        await asyncio.sleep(1)

        # Simulate various error scenarios
        error_chunks = [
            StreamChunk(
                type="error",
                content="Import error: Module 'nonexistent_module' not found",
                metadata={"severity": "error", "type": "import_error"},
                timestamp=datetime.now(),
                sequence_number=1
            ),
            StreamChunk(
                type="error",
                content="Syntax error in generated code: Expected ':' after function definition",
                metadata={"severity": "error", "type": "syntax_error"},
                timestamp=datetime.now(),
                sequence_number=2
            ),
            StreamChunk(
                type="thought",
                content="🔧 Attempting to fix syntax error by regenerating function...",
                metadata={},
                timestamp=datetime.now(),
                sequence_number=3
            ),
            StreamChunk(
                type="result",
                content="✅ Error resolved! Code now compiles successfully.",
                metadata={},
                timestamp=datetime.now(),
                sequence_number=4
            )
        ]

        for chunk in error_chunks:
            await ui.display_stream(chunk)
            await asyncio.sleep(2)

        await asyncio.sleep(3)

    finally:
        await ui.shutdown()
        ui_task.cancel()


async def main():
    """Main demo function"""

    if "--errors" in sys.argv:
        await demo_error_handling()
    else:
        await demo_coding_session()


if __name__ == "__main__":
    print("🎯 CASPER Prime Terminal UI Demo")
    print("=" * 50)

    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n👋 Demo ended by user")

    print("\n✨ Demo complete! The TerminalUI is ready for production use.")