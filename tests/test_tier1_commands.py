#!/usr/bin/env python3
"""
Comprehensive tests for Tier 1 commands following COT methodology.
Tests help, exit/quit, task, analyze, and status commands.
"""

import asyncio
import pytest
import sys
from pathlib import Path
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from io import StringIO

# Add project to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from casper_terminal_simple import (
    handle_help,
    handle_exit,
    handle_task,
    handle_analyze,
    handle_status,
    handle_list,
    COMMAND_CATEGORIES,
)
from rich.console import Console


class TestHelpCommand:
    """Test suite for help command"""

    @pytest.mark.asyncio
    async def test_help_basic_functionality(self):
        """Test basic help command displays all categories"""
        # Setup
        output = StringIO()
        console = Console(file=output, force_terminal=True, width=120)

        # Execute
        await handle_help(console)

        # Verify
        output_text = output.getvalue()
        assert "CASPER2 Commands" in output_text
        assert "Core Commands:" in output_text
        assert "Workflow Commands:" in output_text
        assert "Development Commands:" in output_text
        assert "help" in output_text
        assert "task" in output_text
        assert "analyze" in output_text

    @pytest.mark.asyncio
    async def test_help_with_category_filter(self):
        """Test help command with category filter"""
        # Setup
        output = StringIO()
        console = Console(file=output, force_terminal=True, width=120)

        # Execute
        await handle_help(console, "core")

        # Verify
        output_text = output.getvalue()
        assert "Core Commands" in output_text
        assert "help" in output_text
        assert "exit" in output_text
        # Should not show other categories
        assert "Workflow Commands:" not in output_text
        assert "/task" not in output_text

    @pytest.mark.asyncio
    async def test_help_invalid_category(self):
        """Test help command with invalid category"""
        # Setup
        output = StringIO()
        console = Console(file=output, force_terminal=True, width=120)

        # Execute
        await handle_help(console, "invalid")

        # Verify
        output_text = output.getvalue()
        assert "Unknown category: invalid" in output_text
        assert "Available categories:" in output_text

    @pytest.mark.asyncio
    async def test_help_edge_cases(self):
        """Test help command edge cases"""
        output = StringIO()
        console = Console(file=output, force_terminal=True, width=120)

        # Test with empty string (should show all)
        await handle_help(console, "")
        assert "CASPER2 Commands" in output.getvalue()

        # Test with whitespace
        output.truncate(0)
        await handle_help(console, "  ")
        assert "Unknown category" in output.getvalue()

    def test_help_performance(self):
        """Test help command performance"""
        import time

        output = StringIO()
        console = Console(file=output, force_terminal=True, width=120)

        async def measure_time():
            start = time.time()
            await handle_help(console)
            return time.time() - start

        elapsed = asyncio.run(measure_time())
        assert elapsed < 0.5  # Should complete in under 500ms


class TestExitCommand:
    """Test suite for exit/quit commands"""

    @pytest.mark.asyncio
    async def test_exit_basic_functionality(self):
        """Test basic exit command functionality"""
        # Setup
        output = StringIO()
        console = Console(file=output, force_terminal=True, width=120)
        mock_cli = AsyncMock()
        mock_cli.shutdown = AsyncMock()

        # Execute
        result = await handle_exit(console, mock_cli)

        # Verify
        assert result is True  # Should return True to exit loop
        mock_cli.shutdown.assert_called_once()
        output_text = output.getvalue()
        assert "Shutting down CASPER2" in output_text
        assert "shutdown complete" in output_text

    @pytest.mark.asyncio
    async def test_exit_with_shutdown_error(self):
        """Test exit command when shutdown fails"""
        # Setup
        output = StringIO()
        console = Console(file=output, force_terminal=True, width=120)
        mock_cli = AsyncMock()
        mock_cli.shutdown = AsyncMock(side_effect=Exception("Shutdown error"))

        # Execute
        result = await handle_exit(console, mock_cli)

        # Verify
        assert result is True  # Should still return True
        output_text = output.getvalue()
        assert "Shutdown warning" in output_text

    @pytest.mark.asyncio
    async def test_exit_cleanup(self):
        """Test that exit properly cleans up resources"""
        output = StringIO()
        console = Console(file=output, force_terminal=True, width=120)
        mock_cli = AsyncMock()
        mock_cli.shutdown = AsyncMock()

        # Execute multiple times to ensure idempotency
        for _ in range(3):
            result = await handle_exit(console, mock_cli)
            assert result is True

        # Shutdown should be called 3 times
        assert mock_cli.shutdown.call_count == 3


class TestTaskCommand:
    """Test suite for task command"""

    @pytest.mark.asyncio
    async def test_task_basic_functionality(self):
        """Test basic task execution"""
        # Setup
        output = StringIO()
        console = Console(file=output, force_terminal=True, width=120)
        mock_cli = AsyncMock()
        mock_cli.execute_task = AsyncMock()

        # Execute
        await handle_task(console, mock_cli, "implement user authentication")

        # Verify
        mock_cli.execute_task.assert_called_once_with("implement user authentication")
        output_text = output.getvalue()
        assert "Executing task:" in output_text
        assert "implement user authentication" in output_text

    @pytest.mark.asyncio
    async def test_task_no_args(self):
        """Test task command without arguments"""
        # Setup
        output = StringIO()
        console = Console(file=output, force_terminal=True, width=120)
        mock_cli = AsyncMock()

        # Execute
        await handle_task(console, mock_cli, "")

        # Verify
        mock_cli.execute_task.assert_not_called()
        output_text = output.getvalue()
        assert "Usage:" in output_text
        # Check for the essential parts (Rich formatting may change exact text)
        assert "task" in output_text
        assert "description" in output_text

    @pytest.mark.asyncio
    async def test_task_with_approval(self):
        """Test task command with pending approvals"""
        # Setup
        output = StringIO()
        console = Console(file=output, force_terminal=True, width=120)
        mock_cli = AsyncMock()
        mock_cli.execute_task = AsyncMock()

        # Mock approval service
        with patch("casper_terminal_simple.ApprovalService") as mock_approval:
            mock_service = AsyncMock()
            mock_approval.return_value = mock_service

            # Mock pending operations
            mock_op = Mock()
            mock_op.id = "op1"
            mock_op.operation_type = "file_write"
            mock_service.get_pending_operations = AsyncMock(return_value=[mock_op])
            mock_service.approve = AsyncMock()

            # Execute
            await handle_task(console, mock_cli, "test task")

            # Verify
            mock_service.get_pending_operations.assert_called_once()
            mock_service.approve.assert_called_once_with("op1")
            output_text = output.getvalue()
            assert "Auto-approved" in output_text

    @pytest.mark.asyncio
    async def test_task_execution_error(self):
        """Test task command with execution error"""
        # Setup
        output = StringIO()
        console = Console(file=output, force_terminal=True, width=120)
        mock_cli = AsyncMock()
        mock_cli.execute_task = AsyncMock(side_effect=Exception("Task failed"))

        # Execute
        await handle_task(console, mock_cli, "failing task")

        # Verify
        output_text = output.getvalue()
        assert "Task execution failed" in output_text
        assert "Task failed" in output_text


class TestAnalyzeCommand:
    """Test suite for analyze command"""

    @pytest.mark.asyncio
    async def test_analyze_basic_functionality(self):
        """Test basic analyze functionality"""
        # Setup
        output = StringIO()
        console = Console(file=output, force_terminal=True, width=120)
        mock_cli = AsyncMock()
        mock_cli.analyze_only = AsyncMock()

        # Execute
        await handle_analyze(console, mock_cli, "add unit tests")

        # Verify
        mock_cli.analyze_only.assert_called_once_with("add unit tests")
        output_text = output.getvalue()
        assert "Analyzing task:" in output_text
        assert "add unit tests" in output_text

    @pytest.mark.asyncio
    async def test_analyze_no_args(self):
        """Test analyze command without arguments"""
        # Setup
        output = StringIO()
        console = Console(file=output, force_terminal=True, width=120)
        mock_cli = AsyncMock()

        # Execute
        await handle_analyze(console, mock_cli, "")

        # Verify
        mock_cli.analyze_only.assert_not_called()
        output_text = output.getvalue()
        assert "Usage:" in output_text
        # Check for the essential parts (Rich formatting may change exact text)
        assert "analyze" in output_text
        assert "description" in output_text

    @pytest.mark.asyncio
    async def test_analyze_error(self):
        """Test analyze command with error"""
        # Setup
        output = StringIO()
        console = Console(file=output, force_terminal=True, width=120)
        mock_cli = AsyncMock()
        mock_cli.analyze_only = AsyncMock(side_effect=Exception("Analysis failed"))

        # Execute
        await handle_analyze(console, mock_cli, "complex task")

        # Verify
        output_text = output.getvalue()
        assert "Analysis failed" in output_text


class TestStatusCommand:
    """Test suite for status command"""

    @pytest.mark.asyncio
    async def test_status_basic_functionality(self):
        """Test basic status functionality"""
        # Setup
        output = StringIO()
        console = Console(file=output, force_terminal=True, width=120)
        mock_cli = AsyncMock()
        mock_cli.show_status = AsyncMock()

        # Execute
        await handle_status(console, mock_cli)

        # Verify
        mock_cli.show_status.assert_called_once()
        output_text = output.getvalue()
        assert "Fetching system status" in output_text

    @pytest.mark.asyncio
    async def test_status_error(self):
        """Test status command with error"""
        # Setup
        output = StringIO()
        console = Console(file=output, force_terminal=True, width=120)
        mock_cli = AsyncMock()
        mock_cli.show_status = AsyncMock(side_effect=Exception("Status check failed"))

        # Execute
        await handle_status(console, mock_cli)

        # Verify
        output_text = output.getvalue()
        assert "Status check failed" in output_text

    @pytest.mark.asyncio
    async def test_status_performance(self):
        """Test status command performance"""
        import time

        output = StringIO()
        console = Console(file=output, force_terminal=True, width=120)
        mock_cli = AsyncMock()
        mock_cli.show_status = AsyncMock()

        # Measure execution time
        start = time.time()
        await handle_status(console, mock_cli)
        elapsed = time.time() - start

        # Should complete quickly (under 100ms for mock)
        assert elapsed < 0.1


class TestListCommand:
    """Test suite for list command"""

    @pytest.mark.asyncio
    async def test_list_basic_functionality(self):
        """Test basic list functionality"""
        # Setup
        output = StringIO()
        console = Console(file=output, force_terminal=True, width=120)

        # Execute
        await handle_list(console)

        # Verify
        output_text = output.getvalue()
        assert "Available CASPER2 Agents" in output_text
        assert "Master Prime" in output_text
        assert "Orchestrator" in output_text
        assert "Alpha Prime" in output_text
        assert "React Developer" in output_text

    @pytest.mark.asyncio
    async def test_list_all_agents_present(self):
        """Test that all expected agents are listed"""
        output = StringIO()
        console = Console(file=output, force_terminal=True, width=120)

        await handle_list(console)

        output_text = output.getvalue()
        expected_agents = [
            "Master Prime",
            "Alpha Prime",
            "Beta Prime",
            "Gamma Prime",
            "Delta Prime",
            "Epsilon Prime",
        ]

        for agent in expected_agents:
            assert agent in output_text


class TestCommandIntegration:
    """Integration tests for command interaction"""

    @pytest.mark.asyncio
    async def test_help_shows_all_commands(self):
        """Test that help shows all implemented commands"""
        output = StringIO()
        console = Console(file=output, force_terminal=True, width=120)

        await handle_help(console)

        output_text = output.getvalue()
        # Check core commands are shown
        for cmd in ["help", "task", "analyze", "status", "exit"]:
            assert cmd in output_text

    @pytest.mark.asyncio
    async def test_command_categories_consistency(self):
        """Test that COMMAND_CATEGORIES is consistent"""
        # All categories should have descriptions
        for category, commands in COMMAND_CATEGORIES.items():
            assert isinstance(commands, dict)
            for cmd, desc in commands.items():
                assert isinstance(cmd, str)
                assert isinstance(desc, str)
                assert len(desc) > 0

    @pytest.mark.asyncio
    async def test_slash_command_parity(self):
        """Test that slash commands have same functionality as regular"""
        # This verifies the design principle that /command == command
        slash_commands = []
        regular_commands = []

        for category, commands in COMMAND_CATEGORIES.items():
            for cmd in commands.keys():
                if cmd.startswith("/"):
                    slash_commands.append(cmd[1:])
                else:
                    regular_commands.append(cmd)

        # Core commands should have slash equivalents
        for cmd in ["task", "analyze", "status", "help"]:
            assert cmd in regular_commands
            assert cmd in slash_commands


# Performance test suite
class TestPerformance:
    """Performance tests for all commands"""

    @pytest.mark.asyncio
    async def test_all_commands_under_2_seconds(self):
        """Test that all commands complete within 2 seconds"""
        import time

        output = StringIO()
        console = Console(file=output, force_terminal=True, width=120)
        mock_cli = AsyncMock()
        mock_cli.execute_task = AsyncMock()
        mock_cli.analyze_only = AsyncMock()
        mock_cli.show_status = AsyncMock()
        mock_cli.shutdown = AsyncMock()

        commands_to_test = [
            (handle_help, [console]),
            (handle_exit, [console, mock_cli]),
            (handle_task, [console, mock_cli, "test"]),
            (handle_analyze, [console, mock_cli, "test"]),
            (handle_status, [console, mock_cli]),
            (handle_list, [console]),
        ]

        for handler, args in commands_to_test:
            start = time.time()
            await handler(*args)
            elapsed = time.time() - start
            # Each command should complete in under 2 seconds
            assert elapsed < 2.0, f"{handler.__name__} took {elapsed:.2f}s"


if __name__ == "__main__":
    # Run tests
    pytest.main([__file__, "-v"])
