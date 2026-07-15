"""
Performance Benchmark Tests for Terminal Operations.
Comprehensive performance testing for all terminal components with benchmarks and monitoring.
"""

import asyncio
import time
import pytest
import psutil
import os
import json
import statistics
from typing import List, Dict, Any, Optional
from unittest.mock import Mock, AsyncMock, patch
from concurrent.futures import ThreadPoolExecutor
import threading
from dataclasses import dataclass
from datetime import datetime, timedelta

from core.terminal.pty_manager import PTYManager
from core.terminal.websocket_handler import TerminalWebSocketHandler
from core.terminal.command_proxy import CommandProxy


@dataclass
class PerformanceMetric:
    """Performance metric data structure."""

    name: str
    value: float
    unit: str
    threshold: float
    description: str
    timestamp: datetime


class PerformanceBenchmark:
    """Performance benchmark helper class."""

    def __init__(self, name: str):
        self.name = name
        self.start_time: Optional[float] = None
        self.metrics: List[PerformanceMetric] = []
        self.process = psutil.Process()

    def start(self):
        """Start performance measurement."""
        self.start_time = time.perf_counter()
        return self

    def stop(self) -> float:
        """Stop measurement and return duration."""
        if self.start_time is None:
            raise ValueError("Benchmark not started")

        duration = time.perf_counter() - self.start_time
        self.start_time = None
        return duration

    def add_metric(
        self,
        name: str,
        value: float,
        unit: str,
        threshold: float,
        description: str = "",
    ):
        """Add a performance metric."""
        metric = PerformanceMetric(
            name=name,
            value=value,
            unit=unit,
            threshold=threshold,
            description=description,
            timestamp=datetime.now(),
        )
        self.metrics.append(metric)

    def get_memory_usage(self) -> int:
        """Get current memory usage in bytes."""
        return self.process.memory_info().rss

    def get_cpu_usage(self) -> float:
        """Get current CPU usage percentage."""
        return self.process.cpu_percent()

    def assert_all_thresholds(self):
        """Assert all metrics are within thresholds."""
        failures = []
        for metric in self.metrics:
            if metric.value > metric.threshold:
                failures.append(
                    f"{metric.name}: {metric.value}{metric.unit} > {metric.threshold}{metric.unit} - {metric.description}"
                )

        if failures:
            raise AssertionError(
                f"Performance thresholds exceeded:\n" + "\n".join(failures)
            )

    def __enter__(self):
        return self.start()

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.start_time is not None:
            self.stop()


class TestPTYManagerPerformance:
    """Performance tests for PTY Manager."""

    @pytest.mark.asyncio
    async def test_pty_session_creation_performance(self):
        """Test PTY session creation performance."""
        manager = PTYManager()
        await manager.start()

        try:
            with PerformanceBenchmark("PTY Session Creation") as bench:
                session_ids = []

                # Create multiple sessions and measure time
                create_start = time.perf_counter()
                for i in range(10):
                    session_id = await manager.create_session()
                    session_ids.append(session_id)
                create_time = time.perf_counter() - create_start

                bench.add_metric(
                    "session_creation_time",
                    create_time,
                    "s",
                    2.0,
                    "Time to create 10 PTY sessions",
                )

                bench.add_metric(
                    "avg_creation_time",
                    create_time / 10,
                    "s",
                    0.2,
                    "Average time per session creation",
                )

                # Test session cleanup performance
                cleanup_start = time.perf_counter()
                for session_id in session_ids:
                    await manager.close_session(session_id)
                cleanup_time = time.perf_counter() - cleanup_start

                bench.add_metric(
                    "session_cleanup_time",
                    cleanup_time,
                    "s",
                    1.0,
                    "Time to cleanup 10 PTY sessions",
                )

                bench.assert_all_thresholds()

        finally:
            await manager.stop()

    @pytest.mark.asyncio
    async def test_pty_concurrent_session_performance(self):
        """Test concurrent PTY session handling performance."""
        manager = PTYManager()
        await manager.start()

        try:
            with PerformanceBenchmark("Concurrent PTY Sessions") as bench:
                initial_memory = bench.get_memory_usage()

                # Create sessions concurrently
                async def create_session():
                    return await manager.create_session()

                create_start = time.perf_counter()
                tasks = [create_session() for _ in range(20)]
                session_ids = await asyncio.gather(*tasks)
                create_time = time.perf_counter() - create_start

                bench.add_metric(
                    "concurrent_creation_time",
                    create_time,
                    "s",
                    3.0,
                    "Time to create 20 sessions concurrently",
                )

                final_memory = bench.get_memory_usage()
                memory_per_session = (final_memory - initial_memory) / len(session_ids)

                bench.add_metric(
                    "memory_per_session",
                    memory_per_session / (1024 * 1024),
                    "MB",
                    10.0,
                    "Memory usage per PTY session",
                )

                # Test concurrent operations
                async def write_to_session(session_id):
                    await manager.write_to_session(session_id, "echo test\n")

                write_start = time.perf_counter()
                write_tasks = [write_to_session(sid) for sid in session_ids]
                await asyncio.gather(*write_tasks)
                write_time = time.perf_counter() - write_start

                bench.add_metric(
                    "concurrent_write_time",
                    write_time,
                    "s",
                    2.0,
                    "Time for concurrent writes to 20 sessions",
                )

                # Cleanup
                cleanup_start = time.perf_counter()
                cleanup_tasks = [manager.close_session(sid) for sid in session_ids]
                await asyncio.gather(*cleanup_tasks)
                cleanup_time = time.perf_counter() - cleanup_start

                bench.add_metric(
                    "concurrent_cleanup_time",
                    cleanup_time,
                    "s",
                    2.0,
                    "Time for concurrent cleanup of 20 sessions",
                )

                bench.assert_all_thresholds()

        finally:
            await manager.stop()

    @pytest.mark.asyncio
    async def test_pty_throughput_performance(self):
        """Test PTY write/read throughput performance."""
        manager = PTYManager()
        await manager.start()

        try:
            session_id = await manager.create_session()

            with PerformanceBenchmark("PTY Throughput") as bench:
                # Test write throughput
                test_data = "echo 'throughput test data'\n" * 100
                data_size = len(test_data)

                write_start = time.perf_counter()
                await manager.write_to_session(session_id, test_data)
                write_time = time.perf_counter() - write_start

                throughput = data_size / write_time

                bench.add_metric(
                    "write_throughput",
                    throughput / 1024,
                    "KB/s",
                    100.0,
                    "PTY write throughput",
                )

                bench.add_metric(
                    "write_latency",
                    write_time * 1000,
                    "ms",
                    500.0,
                    "PTY write latency for large data",
                )

                # Test resize performance
                resize_start = time.perf_counter()
                for i in range(10):
                    await manager.resize_session(session_id, 24 + i, 80 + i)
                resize_time = time.perf_counter() - resize_start

                bench.add_metric(
                    "resize_latency",
                    (resize_time / 10) * 1000,
                    "ms",
                    50.0,
                    "Average PTY resize latency",
                )

                bench.assert_all_thresholds()

            await manager.close_session(session_id)

        finally:
            await manager.stop()

    @pytest.mark.asyncio
    async def test_pty_memory_stability(self):
        """Test PTY memory usage stability over time."""
        manager = PTYManager()
        await manager.start()

        try:
            with PerformanceBenchmark("PTY Memory Stability") as bench:
                session_id = await manager.create_session()
                initial_memory = bench.get_memory_usage()

                # Perform many operations
                for i in range(100):
                    await manager.write_to_session(
                        session_id, f"echo 'Memory test {i}'\n"
                    )
                    await asyncio.sleep(0.01)

                    if i % 20 == 0:
                        current_memory = bench.get_memory_usage()
                        memory_growth = current_memory - initial_memory

                        if memory_growth > 100 * 1024 * 1024:  # 100MB growth limit
                            break

                final_memory = bench.get_memory_usage()
                total_growth = final_memory - initial_memory

                bench.add_metric(
                    "memory_growth",
                    total_growth / (1024 * 1024),
                    "MB",
                    50.0,
                    "Memory growth after 100 operations",
                )

                await manager.close_session(session_id)
                bench.assert_all_thresholds()

        finally:
            await manager.stop()


class TestWebSocketHandlerPerformance:
    """Performance tests for WebSocket Handler."""

    @pytest.fixture
    async def handler_with_mocks(self):
        """Create WebSocket handler with mocked dependencies."""
        with (
            patch("core.terminal.websocket_handler.PTYManager") as mock_pty,
            patch("core.terminal.websocket_handler.CommandProxy") as mock_proxy,
            patch(
                "core.terminal.websocket_handler.SecurityMiddleware"
            ) as mock_security,
        ):

            handler = TerminalWebSocketHandler()

            # Set up mocks
            mock_pty_instance = AsyncMock()
            mock_pty_instance.create_session.return_value = "test-pty-session"
            mock_pty_instance.write_to_session.return_value = True
            handler.pty_manager = mock_pty_instance

            mock_proxy_instance = AsyncMock()
            handler.command_proxy = mock_proxy_instance

            mock_security_instance = AsyncMock()
            mock_security_instance.create_sandbox.return_value = {
                "sandbox_dir": "/tmp/sandbox",
                "env_vars": {},
            }
            handler.security = mock_security_instance

            await handler.start()
            yield handler
            await handler.stop()

    @pytest.mark.asyncio
    async def test_websocket_connection_performance(self, handler_with_mocks):
        """Test WebSocket connection establishment performance."""
        handler = handler_with_mocks

        with PerformanceBenchmark("WebSocket Connection Performance") as bench:
            # Mock WebSocket connections
            mock_websockets = []

            for i in range(20):
                mock_ws = AsyncMock()
                mock_ws.accept = AsyncMock()
                mock_ws.send_json = AsyncMock()
                mock_websockets.append(mock_ws)

            # Test concurrent connection establishment
            async def establish_connection(ws, idx):
                session_id = await handler.connect(ws)
                return session_id

            connect_start = time.perf_counter()
            connection_tasks = [
                establish_connection(ws, i) for i, ws in enumerate(mock_websockets)
            ]
            session_ids = await asyncio.gather(*connection_tasks)
            connect_time = time.perf_counter() - connect_start

            bench.add_metric(
                "connection_establishment_time",
                connect_time,
                "s",
                2.0,
                "Time to establish 20 WebSocket connections",
            )

            bench.add_metric(
                "avg_connection_time",
                connect_time / len(mock_websockets),
                "s",
                0.1,
                "Average time per connection establishment",
            )

            # Test connection cleanup performance
            disconnect_start = time.perf_counter()
            for session_id in session_ids:
                await handler.disconnect(session_id)
            disconnect_time = time.perf_counter() - disconnect_start

            bench.add_metric(
                "disconnection_time",
                disconnect_time,
                "s",
                1.0,
                "Time to disconnect all sessions",
            )

            bench.assert_all_thresholds()

    @pytest.mark.asyncio
    async def test_message_handling_performance(self, handler_with_mocks):
        """Test WebSocket message handling performance."""
        handler = handler_with_mocks

        with PerformanceBenchmark("Message Handling Performance") as bench:
            # Create a test session
            mock_ws = AsyncMock()
            session_id = await handler.connect(mock_ws)

            # Test different message types
            message_types = [
                {"type": "input", "data": "echo test\n"},
                {"type": "resize", "rows": 24, "cols": 80},
                {"type": "ping"},
                {"type": "get_history"},
                {"type": "security_status"},
            ]

            # Measure message handling latency
            latencies = []

            for msg_type in message_types * 20:  # 100 total messages
                msg_start = time.perf_counter()
                await handler.handle_message(session_id, msg_type)
                msg_latency = time.perf_counter() - msg_start
                latencies.append(msg_latency)

            avg_latency = statistics.mean(latencies) * 1000
            max_latency = max(latencies) * 1000
            p95_latency = (
                statistics.quantiles(latencies, n=20)[18] * 1000
            )  # 95th percentile

            bench.add_metric(
                "avg_message_latency",
                avg_latency,
                "ms",
                50.0,
                "Average message handling latency",
            )

            bench.add_metric(
                "max_message_latency",
                max_latency,
                "ms",
                200.0,
                "Maximum message handling latency",
            )

            bench.add_metric(
                "p95_message_latency",
                p95_latency,
                "ms",
                100.0,
                "95th percentile message handling latency",
            )

            await handler.disconnect(session_id)
            bench.assert_all_thresholds()

    @pytest.mark.asyncio
    async def test_concurrent_session_performance(self, handler_with_mocks):
        """Test concurrent session handling performance."""
        handler = handler_with_mocks

        with PerformanceBenchmark("Concurrent Session Performance") as bench:
            initial_memory = bench.get_memory_usage()

            # Create multiple concurrent sessions
            sessions = []
            mock_websockets = []

            create_start = time.perf_counter()
            for i in range(50):
                mock_ws = AsyncMock()
                session_id = await handler.connect(mock_ws)
                sessions.append(session_id)
                mock_websockets.append(mock_ws)
            create_time = time.perf_counter() - create_start

            bench.add_metric(
                "concurrent_session_creation_time",
                create_time,
                "s",
                5.0,
                "Time to create 50 concurrent sessions",
            )

            current_memory = bench.get_memory_usage()
            memory_per_session = (current_memory - initial_memory) / len(sessions)

            bench.add_metric(
                "memory_per_websocket_session",
                memory_per_session / 1024,
                "KB",
                500.0,
                "Memory usage per WebSocket session",
            )

            # Test concurrent message broadcasting
            broadcast_start = time.perf_counter()
            await handler.broadcast_message(
                "test_broadcast", {"message": "performance test"}
            )
            broadcast_time = time.perf_counter() - broadcast_start

            bench.add_metric(
                "broadcast_latency",
                broadcast_time * 1000,
                "ms",
                500.0,
                f"Time to broadcast to {len(sessions)} sessions",
            )

            # Cleanup sessions
            cleanup_start = time.perf_counter()
            for session_id in sessions:
                await handler.disconnect(session_id)
            cleanup_time = time.perf_counter() - cleanup_start

            bench.add_metric(
                "session_cleanup_time",
                cleanup_time,
                "s",
                3.0,
                "Time to cleanup all concurrent sessions",
            )

            bench.assert_all_thresholds()


class TestCommandProxyPerformance:
    """Performance tests for Command Proxy."""

    @pytest.fixture
    async def command_proxy(self):
        """Create command proxy with mocked dependencies."""
        with (
            patch("core.terminal.command_proxy.ContextManager"),
            patch(
                "core.terminal.command_proxy.AgentCoordinator"
            ) as mock_coordinator_class,
            patch("core.terminal.command_proxy.TaskAnalyzer") as mock_analyzer_class,
        ):

            proxy = CommandProxy()

            # Set up mocks
            mock_coordinator = AsyncMock()
            mock_coordinator.get_coordinator_stats.return_value = {
                "active_tasks": 0,
                "queued_tasks": 0,
                "context_sessions": 0,
                "agent_pool": {
                    "total_agents": 10,
                    "busy_agents": 2,
                    "available_by_role": {},
                },
                "token_usage_total": 1000,
            }
            mock_coordinator.submit_task.return_value = "test-task-id"
            mock_coordinator_class.return_value = mock_coordinator

            mock_analyzer = Mock()
            from core.orchestrator.task_analyzer import TaskMetrics
            from core.agents.base import AgentRole, TaskPriority

            mock_analyzer.analyze_task.return_value = (
                TaskMetrics(50, 3, 2, 1, 0),
                [AgentRole.BACKEND_PRIME],
                TaskPriority.MEDIUM,
            )
            mock_analyzer._calculate_complexity_score.return_value = 5
            mock_analyzer_class.return_value = mock_analyzer

            proxy.coordinator = mock_coordinator
            proxy.task_analyzer = mock_analyzer
            proxy.context_manager = Mock()
            proxy._initialized = True

            yield proxy

    @pytest.mark.asyncio
    async def test_command_execution_performance(self, command_proxy):
        """Test CASPER command execution performance."""
        proxy = command_proxy

        with PerformanceBenchmark("Command Execution Performance") as bench:
            # Test different command types
            commands = [
                ("status", []),
                ("help", []),
                ("analyze", ["Test task description"]),
                ("list", ["10"]),
            ]

            execution_times = []

            for command, args in commands * 10:  # 40 total executions
                exec_start = time.perf_counter()
                result = await proxy.execute_casper_command(command, args)
                exec_time = time.perf_counter() - exec_start
                execution_times.append(exec_time)

                assert (
                    result["success"] is True or command == "task"
                )  # task might fail without description

            avg_execution_time = statistics.mean(execution_times) * 1000
            max_execution_time = max(execution_times) * 1000

            bench.add_metric(
                "avg_command_execution_time",
                avg_execution_time,
                "ms",
                100.0,
                "Average command execution time",
            )

            bench.add_metric(
                "max_command_execution_time",
                max_execution_time,
                "ms",
                500.0,
                "Maximum command execution time",
            )

            bench.assert_all_thresholds()

    @pytest.mark.asyncio
    async def test_concurrent_command_performance(self, command_proxy):
        """Test concurrent command execution performance."""
        proxy = command_proxy

        with PerformanceBenchmark("Concurrent Command Performance") as bench:
            # Execute multiple commands concurrently
            async def execute_status():
                return await proxy.execute_casper_command("status", [])

            concurrent_start = time.perf_counter()
            tasks = [execute_status() for _ in range(20)]
            results = await asyncio.gather(*tasks)
            concurrent_time = time.perf_counter() - concurrent_start

            bench.add_metric(
                "concurrent_execution_time",
                concurrent_time,
                "s",
                2.0,
                "Time for 20 concurrent status commands",
            )

            # Verify all commands succeeded
            successful_commands = sum(1 for result in results if result["success"])
            success_rate = successful_commands / len(results) * 100

            bench.add_metric(
                "concurrent_success_rate",
                success_rate,
                "%",
                90.0,
                "Success rate for concurrent commands",
            )

            bench.assert_all_thresholds()

    @pytest.mark.asyncio
    async def test_rate_limiting_performance(self, command_proxy):
        """Test rate limiting performance impact."""
        proxy = command_proxy

        with PerformanceBenchmark("Rate Limiting Performance") as bench:
            # Test rapid command execution
            rapid_start = time.perf_counter()

            for i in range(50):
                try:
                    await proxy.execute_casper_command(
                        "status", [], user_id="test-user"
                    )
                except Exception:
                    pass  # Expected due to rate limiting

            rapid_time = time.perf_counter() - rapid_start

            bench.add_metric(
                "rate_limited_execution_time",
                rapid_time,
                "s",
                3.0,
                "Time for 50 rapid commands with rate limiting",
            )

            # Test rate limit recovery
            await asyncio.sleep(1)  # Wait for rate limit to reset

            recovery_start = time.perf_counter()
            result = await proxy.execute_casper_command(
                "status", [], user_id="test-user"
            )
            recovery_time = time.perf_counter() - recovery_start

            bench.add_metric(
                "rate_limit_recovery_time",
                recovery_time * 1000,
                "ms",
                200.0,
                "Command execution time after rate limit recovery",
            )

            assert result["success"] is True
            bench.assert_all_thresholds()


class TestIntegratedPerformance:
    """Integrated performance tests for complete terminal system."""

    @pytest.mark.asyncio
    async def test_end_to_end_performance(self):
        """Test end-to-end terminal performance."""
        with PerformanceBenchmark("End-to-End Performance") as bench:
            # This would test the complete flow from WebSocket to PTY
            # For now, we'll test component integration performance

            pty_manager = PTYManager()
            await pty_manager.start()

            try:
                # Simulate complete terminal workflow
                workflow_start = time.perf_counter()

                # 1. Create PTY session
                session_id = await pty_manager.create_session()

                # 2. Execute commands
                for i in range(10):
                    await pty_manager.write_to_session(
                        session_id, f"echo 'Command {i}'\n"
                    )
                    await asyncio.sleep(0.1)  # Small delay to simulate real usage

                # 3. Resize terminal
                await pty_manager.resize_session(session_id, 50, 120)

                # 4. More commands
                for i in range(5):
                    await pty_manager.write_to_session(session_id, f"pwd && ls\n")
                    await asyncio.sleep(0.1)

                # 5. Cleanup
                await pty_manager.close_session(session_id)

                workflow_time = time.perf_counter() - workflow_start

                bench.add_metric(
                    "complete_workflow_time",
                    workflow_time,
                    "s",
                    5.0,
                    "Complete terminal workflow time",
                )

                bench.assert_all_thresholds()

            finally:
                await pty_manager.stop()

    @pytest.mark.asyncio
    async def test_system_resource_usage(self):
        """Test system resource usage under load."""
        with PerformanceBenchmark("System Resource Usage") as bench:
            initial_cpu = bench.get_cpu_usage()
            initial_memory = bench.get_memory_usage()

            # Simulate high load
            managers = []
            session_ids = []

            try:
                # Create multiple PTY managers
                for i in range(5):
                    manager = PTYManager()
                    await manager.start()
                    managers.append(manager)

                    # Create sessions in each manager
                    for j in range(5):
                        session_id = await manager.create_session()
                        session_ids.append((manager, session_id))

                # Wait for CPU usage to stabilize
                await asyncio.sleep(2)

                final_cpu = bench.get_cpu_usage()
                final_memory = bench.get_memory_usage()

                memory_usage = (final_memory - initial_memory) / (1024 * 1024)
                cpu_increase = max(0, final_cpu - initial_cpu)

                bench.add_metric(
                    "total_memory_usage",
                    memory_usage,
                    "MB",
                    200.0,
                    "Total memory usage for 25 PTY sessions",
                )

                bench.add_metric(
                    "cpu_usage_increase",
                    cpu_increase,
                    "%",
                    50.0,
                    "CPU usage increase under load",
                )

                # Test cleanup performance
                cleanup_start = time.perf_counter()
                for manager, session_id in session_ids:
                    await manager.close_session(session_id)

                for manager in managers:
                    await manager.stop()

                cleanup_time = time.perf_counter() - cleanup_start

                bench.add_metric(
                    "mass_cleanup_time",
                    cleanup_time,
                    "s",
                    5.0,
                    "Time to cleanup all resources",
                )

                bench.assert_all_thresholds()

            except Exception:
                # Emergency cleanup
                for manager, session_id in session_ids:
                    try:
                        await manager.close_session(session_id)
                    except:
                        pass

                for manager in managers:
                    try:
                        await manager.stop()
                    except:
                        pass
                raise


def generate_performance_report(
    benchmarks: List[PerformanceBenchmark],
) -> Dict[str, Any]:
    """Generate performance report from benchmarks."""
    report = {
        "timestamp": datetime.now().isoformat(),
        "system_info": {
            "cpu_count": psutil.cpu_count(),
            "memory_total": psutil.virtual_memory().total,
            "python_version": f"{os.sys.version_info.major}.{os.sys.version_info.minor}.{os.sys.version_info.micro}",
        },
        "benchmarks": [],
    }

    for benchmark in benchmarks:
        benchmark_data = {"name": benchmark.name, "metrics": []}

        for metric in benchmark.metrics:
            benchmark_data["metrics"].append(
                {
                    "name": metric.name,
                    "value": metric.value,
                    "unit": metric.unit,
                    "threshold": metric.threshold,
                    "passed": metric.value <= metric.threshold,
                    "description": metric.description,
                    "timestamp": metric.timestamp.isoformat(),
                }
            )

        report["benchmarks"].append(benchmark_data)

    return report


@pytest.mark.performance
class TestPerformanceReporting:
    """Test performance reporting and monitoring."""

    def test_performance_report_generation(self):
        """Test performance report generation."""
        # Create sample benchmarks
        benchmark1 = PerformanceBenchmark("Test Benchmark 1")
        benchmark1.add_metric("latency", 50.0, "ms", 100.0, "Test latency")
        benchmark1.add_metric("throughput", 1000.0, "ops/s", 500.0, "Test throughput")

        benchmark2 = PerformanceBenchmark("Test Benchmark 2")
        benchmark2.add_metric("memory", 25.0, "MB", 50.0, "Memory usage")
        benchmark2.add_metric("cpu", 15.0, "%", 30.0, "CPU usage")

        # Generate report
        report = generate_performance_report([benchmark1, benchmark2])

        # Verify report structure
        assert "timestamp" in report
        assert "system_info" in report
        assert "benchmarks" in report
        assert len(report["benchmarks"]) == 2

        # Verify metric data
        first_benchmark = report["benchmarks"][0]
        assert first_benchmark["name"] == "Test Benchmark 1"
        assert len(first_benchmark["metrics"]) == 2

        latency_metric = first_benchmark["metrics"][0]
        assert latency_metric["name"] == "latency"
        assert latency_metric["value"] == 50.0
        assert latency_metric["passed"] is True

    def test_performance_threshold_validation(self):
        """Test performance threshold validation."""
        benchmark = PerformanceBenchmark("Threshold Test")

        # Add metrics that pass thresholds
        benchmark.add_metric("good_latency", 50.0, "ms", 100.0, "Good latency")
        benchmark.add_metric("good_memory", 25.0, "MB", 50.0, "Good memory")

        # Should not raise exception
        benchmark.assert_all_thresholds()

        # Add metric that fails threshold
        benchmark.add_metric("bad_latency", 200.0, "ms", 100.0, "Bad latency")

        # Should raise exception
        with pytest.raises(AssertionError, match="Performance thresholds exceeded"):
            benchmark.assert_all_thresholds()


if __name__ == "__main__":
    # Run performance tests
    pytest.main([__file__, "-v", "-m", "performance", "--tb=short"])
