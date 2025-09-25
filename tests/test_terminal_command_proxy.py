"""
Tests for Terminal Command Proxy and CLI Integration.
Comprehensive unit tests for CASPER CLI command execution through terminal interface.
"""

import asyncio
import json
import pytest
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from pathlib import Path
from datetime import datetime
from uuid import uuid4

from core.terminal.command_proxy import CommandProxy
from core.agents.base import TaskPriority, AgentStatus
from core.orchestrator.task_analyzer import TaskMetrics


class TestCommandProxy:
    """Test CommandProxy functionality."""

    @pytest.fixture
    async def command_proxy(self):
        """Create a command proxy for testing."""
        proxy = CommandProxy()

        # Mock dependencies
        with patch('core.terminal.command_proxy.ContextManager') as mock_context, \
             patch('core.terminal.command_proxy.AgentCoordinator') as mock_coordinator, \
             patch('core.terminal.command_proxy.TaskAnalyzer') as mock_analyzer:

            # Set up mocks
            proxy.context_manager = Mock()
            proxy.coordinator = AsyncMock()
            proxy.task_analyzer = Mock()
            proxy._initialized = True

            yield proxy

    @pytest.mark.asyncio
    async def test_initialization(self):
        """Test command proxy initialization."""
        proxy = CommandProxy()

        with patch('core.terminal.command_proxy.ContextManager') as mock_context, \
             patch('core.terminal.command_proxy.AgentCoordinator') as mock_coordinator, \
             patch('core.terminal.command_proxy.TaskAnalyzer') as mock_analyzer:

            mock_coordinator_instance = AsyncMock()
            mock_coordinator.return_value = mock_coordinator_instance

            await proxy.initialize()

            assert proxy._initialized is True
            assert proxy.context_manager is not None
            assert proxy.coordinator is not None
            assert proxy.task_analyzer is not None
            mock_coordinator_instance.start.assert_called_once()

    @pytest.mark.asyncio
    async def test_initialization_failure(self):
        """Test command proxy initialization failure."""
        proxy = CommandProxy()

        with patch('core.terminal.command_proxy.ContextManager') as mock_context:
            mock_context.side_effect = Exception("Initialization failed")

            with pytest.raises(Exception, match="Initialization failed"):
                await proxy.initialize()

            assert proxy._initialized is False

    @pytest.mark.asyncio
    async def test_shutdown(self, command_proxy):
        """Test command proxy shutdown."""
        await command_proxy.shutdown()

        command_proxy.coordinator.stop.assert_called_once()
        assert command_proxy._initialized is False

    @pytest.mark.asyncio
    async def test_execute_casper_command_task(self, command_proxy):
        """Test executing 'casper task' command."""
        # Mock task analyzer response
        metrics = TaskMetrics(
            lines_of_code_estimate=50,
            file_count_estimate=3,
            component_count=2,
            integration_points=1,
            external_dependencies=0
        )

        from core.agents.base import AgentRole
        required_agents = [AgentRole.BACKEND_PRIME]
        suggested_priority = TaskPriority.MEDIUM

        command_proxy.task_analyzer.analyze_task.return_value = (
            metrics, required_agents, suggested_priority
        )

        # Mock coordinator response
        task_id = uuid4()
        command_proxy.coordinator.submit_task.return_value = task_id

        # Execute command
        result = await command_proxy.execute_casper_command(
            "task", ["Create a new API endpoint"]
        )

        # Verify result
        assert result["success"] is True
        assert result["command"] == "task"
        assert result["args"] == ["Create a new API endpoint"]
        assert result["task_id"] == str(task_id)
        assert "execution_time_ms" in result
        assert "timestamp" in result

        # Verify calls
        command_proxy.task_analyzer.analyze_task.assert_called_with(
            "Create a new API endpoint"
        )
        command_proxy.coordinator.submit_task.assert_called_with(
            "Create a new API endpoint", TaskPriority.MEDIUM
        )

    @pytest.mark.asyncio
    async def test_execute_casper_command_task_with_priority(self, command_proxy):
        """Test executing 'casper task' command with priority option."""
        # Mock responses
        metrics = TaskMetrics(
            lines_of_code_estimate=100,
            file_count_estimate=5,
            component_count=3,
            integration_points=2,
            external_dependencies=1
        )

        from core.agents.base import AgentRole
        command_proxy.task_analyzer.analyze_task.return_value = (
            metrics, [AgentRole.FRONTEND_PRIME], TaskPriority.HIGH
        )
        command_proxy.coordinator.submit_task.return_value = uuid4()

        # Execute with priority
        result = await command_proxy.execute_casper_command(
            "task", ["Create dashboard", "--priority", "high"]
        )

        assert result["success"] is True
        command_proxy.coordinator.submit_task.assert_called_with(
            "Create dashboard", TaskPriority.HIGH
        )

    @pytest.mark.asyncio
    async def test_execute_casper_command_task_missing_description(self, command_proxy):
        """Test executing 'casper task' command without description."""
        result = await command_proxy.execute_casper_command("task", [])

        assert result["success"] is False
        assert "Missing task description" in result["error"]
        assert "Usage:" in result["message"]

    @pytest.mark.asyncio
    async def test_execute_casper_command_status(self, command_proxy):
        """Test executing 'casper status' command."""
        # Mock coordinator stats
        mock_stats = {
            "active_tasks": 2,
            "queued_tasks": 1,
            "context_sessions": 3,
            "agent_pool": {
                "total_agents": 10,
                "busy_agents": 3,
                "available_by_role": {
                    "backend_prime": 2,
                    "frontend_prime": 1
                }
            },
            "token_usage_total": 5000
        }

        command_proxy.coordinator.get_coordinator_stats.return_value = mock_stats

        result = await command_proxy.execute_casper_command("status", [])

        assert result["success"] is True
        assert result["data"]["system_status"]["active_tasks"] == 2
        assert result["data"]["agent_pool"]["total_agents"] == 10
        assert result["data"]["token_usage"]["total"] == 5000

    @pytest.mark.asyncio
    async def test_execute_casper_command_analyze(self, command_proxy):
        """Test executing 'casper analyze' command."""
        # Mock task analyzer
        metrics = TaskMetrics(
            lines_of_code_estimate=200,
            file_count_estimate=8,
            component_count=5,
            integration_points=3,
            external_dependencies=2
        )

        from core.agents.base import AgentRole
        command_proxy.task_analyzer.analyze_task.return_value = (
            metrics, [AgentRole.BACKEND_PRIME, AgentRole.DEVOPS_PRIME], TaskPriority.HIGH
        )
        command_proxy.task_analyzer._calculate_complexity_score.return_value = 8

        # Mock static method
        with patch.object(command_proxy.task_analyzer.__class__, 'estimate_completion_time') as mock_estimate:
            mock_estimate.return_value = 120

            result = await command_proxy.execute_casper_command(
                "analyze", ["Implement authentication system"]
            )

        assert result["success"] is True
        assert result["data"]["analysis"]["lines_of_code_estimate"] == 200
        assert result["data"]["analysis"]["complexity_score"] == 8
        assert result["data"]["analysis"]["estimated_time_minutes"] == 120
        assert "backend_prime" in [agent.lower() for agent in result["data"]["analysis"]["required_agents"]]

    @pytest.mark.asyncio
    async def test_execute_casper_command_analyze_missing_description(self, command_proxy):
        """Test executing 'casper analyze' command without description."""
        result = await command_proxy.execute_casper_command("analyze", [])

        assert result["success"] is False
        assert "Missing task description" in result["error"]

    @pytest.mark.asyncio
    async def test_execute_casper_command_list(self, command_proxy):
        """Test executing 'casper list' command."""
        # Mock results
        from core.agents.base import AgentRole
        mock_results = [
            Mock(
                task_id=uuid4(),
                agent_role=AgentRole.BACKEND_PRIME,
                status=AgentStatus.COMPLETED,
                token_usage={"total": 1500},
                output="Successfully created API endpoint for user management",
                errors=[]
            ),
            Mock(
                task_id=uuid4(),
                agent_role=AgentRole.FRONTEND_PRIME,
                status=AgentStatus.IN_PROGRESS,
                token_usage={"total": 800},
                output="Working on dashboard component...",
                errors=["Minor styling issue"]
            )
        ]

        command_proxy.coordinator.get_results.return_value = mock_results

        result = await command_proxy.execute_casper_command("list", ["5"])

        assert result["success"] is True
        assert len(result["data"]["tasks"]) == 2
        assert result["data"]["count"] == 2

        # Verify task data structure
        task_data = result["data"]["tasks"][0]
        assert "task_id" in task_data
        assert task_data["agent_role"] == "backend_prime"
        assert task_data["status"] == "completed"
        assert task_data["token_usage"] == 1500

    @pytest.mark.asyncio
    async def test_execute_casper_command_help(self, command_proxy):
        """Test executing 'casper help' command."""
        result = await command_proxy.execute_casper_command("help", [])

        assert result["success"] is True
        assert "commands" in result["data"]
        assert "options" in result["data"]
        assert "examples" in result["data"]

        # Verify command definitions
        commands = result["data"]["commands"]
        assert "task <description>" in commands
        assert "status" in commands
        assert "analyze <description>" in commands

    @pytest.mark.asyncio
    async def test_execute_casper_command_init(self, command_proxy):
        """Test executing 'casper init' command."""
        with patch('pathlib.Path.mkdir') as mock_mkdir, \
             patch('pathlib.Path.write_text') as mock_write:

            result = await command_proxy.execute_casper_command("init", [])

            assert result["success"] is True
            assert "project_directory" in result["data"]
            assert "config_file" in result["data"]
            assert "created_directories" in result["data"]

            # Verify directories were created
            assert mock_mkdir.call_count >= 7  # Multiple directories
            mock_write.assert_called_once()

    @pytest.mark.asyncio
    async def test_execute_casper_command_init_with_project_path(self, command_proxy):
        """Test executing 'casper init' command with custom project path."""
        with patch('pathlib.Path.mkdir') as mock_mkdir, \
             patch('pathlib.Path.write_text') as mock_write:

            result = await command_proxy.execute_casper_command(
                "init", ["--project", "/custom/path"]
            )

            assert result["success"] is True
            assert "/custom/path" in result["data"]["project_directory"]

    @pytest.mark.asyncio
    async def test_execute_casper_command_unknown(self, command_proxy):
        """Test executing unknown command."""
        result = await command_proxy.execute_casper_command("unknown", [])

        assert result["success"] is False
        assert "Unknown command" in result["error"]
        assert "casper help" in result["message"]

    @pytest.mark.asyncio
    async def test_execute_casper_command_exception_handling(self, command_proxy):
        """Test exception handling during command execution."""
        # Mock coordinator to raise exception
        command_proxy.coordinator.get_coordinator_stats.side_effect = Exception("Database error")

        result = await command_proxy.execute_casper_command("status", [])

        assert result["success"] is False
        assert "Database error" in result["error"]
        assert "Command execution failed" in result["message"]
        assert "execution_time_ms" in result

    @pytest.mark.asyncio
    async def test_auto_initialization(self):
        """Test automatic initialization when not initialized."""
        proxy = CommandProxy()

        with patch('core.terminal.command_proxy.ContextManager') as mock_context, \
             patch('core.terminal.command_proxy.AgentCoordinator') as mock_coordinator, \
             patch('core.terminal.command_proxy.TaskAnalyzer') as mock_analyzer:

            mock_coordinator_instance = AsyncMock()
            mock_coordinator.return_value = mock_coordinator_instance
            mock_coordinator_instance.get_coordinator_stats.return_value = {"active_tasks": 0}

            # Execute command without manual initialization
            result = await proxy.execute_casper_command("status", [])

            assert proxy._initialized is True
            assert result["success"] is True
            mock_coordinator_instance.start.assert_called_once()

    def test_get_available_commands(self, command_proxy):
        """Test getting list of available commands."""
        commands = command_proxy.get_available_commands()

        expected_commands = ["task", "status", "analyze", "list", "help", "init"]
        assert set(commands) == set(expected_commands)

    def test_is_valid_command(self, command_proxy):
        """Test command validation."""
        assert command_proxy.is_valid_command("task") is True
        assert command_proxy.is_valid_command("status") is True
        assert command_proxy.is_valid_command("invalid") is False
        assert command_proxy.is_valid_command("") is False


class TestCommandProxyIntegration:
    """Integration tests for CommandProxy with real components."""

    @pytest.mark.asyncio
    async def test_full_task_workflow(self):
        """Test complete task submission workflow."""
        proxy = CommandProxy()

        # Use real components but with mocked external dependencies
        with patch('core.orchestrator.coordinator.AgentCoordinator') as mock_coordinator_class, \
             patch('core.context.manager.ContextManager') as mock_context_class, \
             patch('core.orchestrator.task_analyzer.TaskAnalyzer') as mock_analyzer_class:

            # Set up realistic mocks
            mock_coordinator = AsyncMock()
            mock_coordinator_class.return_value = mock_coordinator

            mock_context = Mock()
            mock_context_class.return_value = mock_context

            mock_analyzer = Mock()
            mock_analyzer_class.return_value = mock_analyzer

            # Set up analyzer response
            metrics = TaskMetrics(75, 4, 2, 1, 0)
            from core.agents.base import AgentRole
            mock_analyzer.analyze_task.return_value = (
                metrics, [AgentRole.BACKEND_PRIME], TaskPriority.MEDIUM
            )

            # Set up coordinator response
            task_id = uuid4()
            mock_coordinator.submit_task.return_value = task_id

            # Execute task command
            result = await proxy.execute_casper_command(
                "task", ["Create REST API for user authentication"]
            )

            # Verify workflow
            assert result["success"] is True
            assert result["task_id"] == str(task_id)

            # Verify component interactions
            mock_analyzer.analyze_task.assert_called_with(
                "Create REST API for user authentication"
            )
            mock_coordinator.submit_task.assert_called_with(
                "Create REST API for user authentication", TaskPriority.MEDIUM
            )

    @pytest.mark.asyncio
    async def test_error_propagation(self):
        """Test error propagation through the command proxy."""
        proxy = CommandProxy()

        with patch('core.terminal.command_proxy.ContextManager') as mock_context:
            # Simulate context manager failure
            mock_context.side_effect = ConnectionError("Service unavailable")

            result = await proxy.execute_casper_command("status", [])

            assert result["success"] is False
            assert "Service unavailable" in result["error"]

    @pytest.mark.asyncio
    async def test_concurrent_command_execution(self):
        """Test concurrent command execution."""
        proxy = CommandProxy()

        with patch('core.terminal.command_proxy.ContextManager'), \
             patch('core.terminal.command_proxy.AgentCoordinator') as mock_coordinator_class, \
             patch('core.terminal.command_proxy.TaskAnalyzer'):

            mock_coordinator = AsyncMock()
            mock_coordinator_class.return_value = mock_coordinator
            mock_coordinator.get_coordinator_stats.return_value = {"active_tasks": 0}

            # Execute multiple commands concurrently
            tasks = [
                proxy.execute_casper_command("status", []),
                proxy.execute_casper_command("help", []),
                proxy.execute_casper_command("status", [])
            ]

            results = await asyncio.gather(*tasks)

            # All should succeed
            assert all(result["success"] for result in results)
            assert len(results) == 3

    @pytest.mark.asyncio
    async def test_memory_cleanup(self):
        """Test proper memory cleanup after command execution."""
        proxy = CommandProxy()

        with patch('core.terminal.command_proxy.ContextManager'), \
             patch('core.terminal.command_proxy.AgentCoordinator') as mock_coordinator_class, \
             patch('core.terminal.command_proxy.TaskAnalyzer'):

            mock_coordinator = AsyncMock()
            mock_coordinator_class.return_value = mock_coordinator
            mock_coordinator.get_coordinator_stats.return_value = {"active_tasks": 0}

            # Execute command
            result = await proxy.execute_casper_command("status", [])
            assert result["success"] is True

            # Shutdown should cleanup resources
            await proxy.shutdown()
            mock_coordinator.stop.assert_called_once()
            assert proxy._initialized is False


@pytest.mark.performance
class TestCommandProxyPerformance:
    """Performance tests for CommandProxy."""

    @pytest.mark.asyncio
    async def test_command_execution_speed(self):
        """Test command execution performance."""
        proxy = CommandProxy()

        with patch('core.terminal.command_proxy.ContextManager'), \
             patch('core.terminal.command_proxy.AgentCoordinator') as mock_coordinator_class, \
             patch('core.terminal.command_proxy.TaskAnalyzer'):

            mock_coordinator = AsyncMock()
            mock_coordinator_class.return_value = mock_coordinator
            mock_coordinator.get_coordinator_stats.return_value = {"active_tasks": 0}

            import time
            start_time = time.time()

            # Execute multiple commands
            for i in range(10):
                result = await proxy.execute_casper_command("status", [])
                assert result["success"] is True

            execution_time = time.time() - start_time

            # Should execute 10 status commands in under 1 second
            assert execution_time < 1.0, f"Execution took {execution_time}s, expected < 1.0s"

    @pytest.mark.asyncio
    async def test_initialization_performance(self):
        """Test initialization performance."""
        with patch('core.terminal.command_proxy.ContextManager'), \
             patch('core.terminal.command_proxy.AgentCoordinator') as mock_coordinator_class, \
             patch('core.terminal.command_proxy.TaskAnalyzer'):

            mock_coordinator = AsyncMock()
            mock_coordinator_class.return_value = mock_coordinator

            import time
            start_time = time.time()

            proxy = CommandProxy()
            await proxy.initialize()

            init_time = time.time() - start_time

            # Initialization should be fast
            assert init_time < 0.5, f"Initialization took {init_time}s, expected < 0.5s"
            assert proxy._initialized is True

    @pytest.mark.asyncio
    async def test_memory_usage(self):
        """Test memory usage during command execution."""
        import psutil
        import os

        process = psutil.Process(os.getpid())
        initial_memory = process.memory_info().rss

        proxy = CommandProxy()

        with patch('core.terminal.command_proxy.ContextManager'), \
             patch('core.terminal.command_proxy.AgentCoordinator') as mock_coordinator_class, \
             patch('core.terminal.command_proxy.TaskAnalyzer'):

            mock_coordinator = AsyncMock()
            mock_coordinator_class.return_value = mock_coordinator
            mock_coordinator.get_coordinator_stats.return_value = {"active_tasks": 0}

            # Execute many commands
            for i in range(100):
                await proxy.execute_casper_command("status", [])

            final_memory = process.memory_info().rss
            memory_increase = final_memory - initial_memory

            # Memory increase should be reasonable (less than 50MB)
            assert memory_increase < 50 * 1024 * 1024, f"Memory increased by {memory_increase} bytes"