"""
Terminal-specific test configuration and fixtures.
Provides shared fixtures and configuration for terminal testing infrastructure.
"""

import asyncio
import pytest
import tempfile
import shutil
from pathlib import Path
from unittest.mock import Mock, AsyncMock, patch
from typing import Dict, Any, List, Optional

# Import pytest markers for categorizing tests
pytest_plugins = ["pytest_asyncio"]


def pytest_configure(config):
    """Configure pytest with custom markers."""
    config.addinivalue_line(
        "markers", "unit: marks tests as unit tests"
    )
    config.addinivalue_line(
        "markers", "integration: marks tests as integration tests"
    )
    config.addinivalue_line(
        "markers", "e2e: marks tests as end-to-end tests"
    )
    config.addinivalue_line(
        "markers", "performance: marks tests as performance tests"
    )
    config.addinivalue_line(
        "markers", "security: marks tests as security tests"
    )
    config.addinivalue_line(
        "markers", "slow: marks tests as slow running"
    )


def pytest_collection_modifyitems(config, items):
    """Automatically mark tests based on their names and paths."""
    for item in items:
        # Mark tests based on filename patterns
        if "performance" in str(item.fspath):
            item.add_marker(pytest.mark.performance)
            item.add_marker(pytest.mark.slow)
        elif "security" in str(item.fspath):
            item.add_marker(pytest.mark.security)
        elif "e2e" in str(item.fspath):
            item.add_marker(pytest.mark.e2e)
            item.add_marker(pytest.mark.slow)
        elif "integration" in str(item.fspath):
            item.add_marker(pytest.mark.integration)
        elif "test_terminal_" in str(item.fspath):
            # Terminal-specific tests
            if not any(marker in str(item.fspath) for marker in ["performance", "security", "e2e", "integration"]):
                item.add_marker(pytest.mark.unit)


# Shared fixtures for terminal testing
@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    yield loop
    loop.close()


@pytest.fixture
async def temp_workspace():
    """Create a temporary workspace directory for testing."""
    temp_dir = Path(tempfile.mkdtemp(prefix="casper_test_"))

    # Create basic project structure
    (temp_dir / "src").mkdir()
    (temp_dir / "tests").mkdir()
    (temp_dir / ".git").mkdir()
    (temp_dir / "package.json").write_text('{"name": "test-project", "version": "1.0.0"}')
    (temp_dir / "README.md").write_text("# Test Project")
    (temp_dir / "src" / "main.py").write_text('print("Hello, World!")')

    yield temp_dir

    # Cleanup
    shutil.rmtree(temp_dir, ignore_errors=True)


@pytest.fixture
def mock_pty_manager():
    """Create a mock PTY manager for testing."""
    with patch('core.terminal.pty_manager.PTYManager') as mock_class:
        mock_instance = AsyncMock()
        mock_instance.sessions = {}
        mock_instance.create_session.return_value = "test-session-id"
        mock_instance.write_to_session.return_value = True
        mock_instance.resize_session.return_value = True
        mock_instance.close_session.return_value = True
        mock_instance.list_sessions.return_value = []
        mock_instance.get_session_info.return_value = {
            "session_id": "test-session-id",
            "is_active": True,
            "last_activity": 1234567890.0,
            "process_pid": 12345
        }
        mock_class.return_value = mock_instance
        yield mock_instance


@pytest.fixture
def mock_websocket():
    """Create a mock WebSocket for testing."""
    mock_ws = AsyncMock()
    mock_ws.accept = AsyncMock()
    mock_ws.send_text = AsyncMock()
    mock_ws.send_json = AsyncMock()
    mock_ws.receive_text = AsyncMock()
    mock_ws.receive_json = AsyncMock()
    mock_ws.close = AsyncMock()
    mock_ws.client_state = "CONNECTED"
    return mock_ws


@pytest.fixture
def mock_security_middleware():
    """Create a mock security middleware for testing."""
    with patch('core.terminal.security.SecurityMiddleware') as mock_class:
        mock_instance = AsyncMock()
        mock_instance.validate_command = AsyncMock()
        mock_instance.validate_casper_command = AsyncMock()
        mock_instance.validate_input = AsyncMock(return_value=True)
        mock_instance.create_sandbox.return_value = {
            "sandbox_dir": "/tmp/test_sandbox",
            "env_vars": {"HOME": "/tmp/test_sandbox", "CASPER_SANDBOX": "true"}
        }
        mock_instance.cleanup_sandbox = AsyncMock()
        mock_instance.audit_log = []
        mock_instance.get_security_stats.return_value = {
            "total_events": 0,
            "blocked_commands": 0,
            "allowed_commands": 0,
            "risk_distribution": {"low": 0, "medium": 0, "high": 0, "critical": 0}
        }
        mock_instance.get_audit_summary.return_value = {
            "timeframe": "Last 24 hours",
            "total_events": 0,
            "unique_sessions": 0,
            "unique_users": 0,
            "risk_levels": {"low": 0, "medium": 0, "high": 0, "critical": 0}
        }
        mock_class.return_value = mock_instance
        yield mock_instance


@pytest.fixture
def mock_command_proxy():
    """Create a mock command proxy for testing."""
    with patch('core.terminal.command_proxy.CommandProxy') as mock_class:
        mock_instance = AsyncMock()
        mock_instance._initialized = True
        mock_instance.initialize = AsyncMock()
        mock_instance.shutdown = AsyncMock()
        mock_instance.execute_casper_command.return_value = {
            "command": "status",
            "args": [],
            "success": True,
            "message": "System status retrieved",
            "execution_time_ms": 50.0,
            "timestamp": "2023-01-01T00:00:00",
            "data": {
                "system_status": {
                    "active_tasks": 0,
                    "queued_tasks": 0,
                    "context_sessions": 0
                }
            }
        }
        mock_instance.get_available_commands.return_value = [
            "task", "status", "analyze", "list", "help", "init"
        ]
        mock_instance.is_valid_command.return_value = True
        mock_class.return_value = mock_instance
        yield mock_instance


@pytest.fixture
def mock_task_analyzer():
    """Create a mock task analyzer for testing."""
    with patch('core.orchestrator.task_analyzer.TaskAnalyzer') as mock_class:
        mock_instance = Mock()

        # Mock TaskMetrics
        from core.orchestrator.task_analyzer import TaskMetrics
        from core.agents.base import AgentRole, TaskPriority

        mock_metrics = TaskMetrics(
            lines_of_code_estimate=50,
            file_count_estimate=3,
            component_count=2,
            integration_points=1,
            external_dependencies=0
        )

        mock_instance.analyze_task.return_value = (
            mock_metrics,
            [AgentRole.BACKEND_PRIME],
            TaskPriority.MEDIUM
        )
        mock_instance._calculate_complexity_score.return_value = 5
        mock_class.return_value = mock_instance
        yield mock_instance


@pytest.fixture
def mock_agent_coordinator():
    """Create a mock agent coordinator for testing."""
    with patch('core.orchestrator.coordinator.AgentCoordinator') as mock_class:
        mock_instance = AsyncMock()
        mock_instance.start = AsyncMock()
        mock_instance.stop = AsyncMock()
        mock_instance.submit_task.return_value = "test-task-id"
        mock_instance.get_coordinator_stats.return_value = {
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
        mock_instance.get_results.return_value = []
        mock_class.return_value = mock_instance
        yield mock_instance


@pytest.fixture
def mock_terminal_session():
    """Create a mock terminal session for testing."""
    from datetime import datetime

    class MockTerminalSession:
        def __init__(self, session_id: str = "test-session"):
            self.session_id = session_id
            self.websocket = Mock()
            self.user_id = "test-user"
            self.pty_session_id = "test-pty-session"
            self.created_at = datetime.now()
            self.last_activity = datetime.now()
            self.is_active = True
            self.command_history = []

        async def send_message(self, message_type: str, data: Dict[str, Any]):
            pass

        async def send_error(self, error_type: str, message: str, details: Optional[Dict] = None):
            pass

        def update_activity(self):
            self.last_activity = datetime.now()

    return MockTerminalSession()


@pytest.fixture
def terminal_test_data():
    """Provide test data for terminal operations."""
    return {
        "safe_commands": [
            "ls -la",
            "pwd",
            "whoami",
            "echo 'Hello World'",
            "cat README.md",
            "grep -r 'pattern' .",
            "find . -name '*.py'",
            "python --version",
            "git status",
            "docker ps",
            "kubectl get pods",
        ],
        "dangerous_commands": [
            "rm -rf /",
            "sudo rm -rf /",
            "dd if=/dev/zero of=/dev/sda",
            "mkfs.ext4 /dev/sda",
            "chmod -R 777 /",
            ":(){ :|:& };:",  # Fork bomb
            "shutdown -h now",
            "init 0",
            "halt",
            "reboot",
        ],
        "casper_commands": [
            ("task", ["Create a new API endpoint"]),
            ("status", []),
            ("analyze", ["Implement authentication"]),
            ("help", []),
            ("list", ["10"]),
            ("init", []),
        ],
        "websocket_messages": [
            {"type": "command", "command": "ls -la"},
            {"type": "input", "data": "echo test\n"},
            {"type": "resize", "rows": 24, "cols": 80},
            {"type": "ping"},
            {"type": "casper_command", "command": "status", "args": []},
        ],
        "performance_test_sizes": {
            "small": 10,
            "medium": 50,
            "large": 100,
            "stress": 500,
        }
    }


@pytest.fixture
def performance_monitor():
    """Monitor performance metrics during tests."""
    import time
    import psutil
    import os

    class PerformanceMonitor:
        def __init__(self):
            self.process = psutil.Process(os.getpid())
            self.start_time = None
            self.start_memory = None
            self.metrics = {}

        def start(self, test_name: str = "test"):
            self.start_time = time.perf_counter()
            self.start_memory = self.process.memory_info().rss
            self.test_name = test_name

        def stop(self):
            if self.start_time is None:
                return None

            end_time = time.perf_counter()
            end_memory = self.process.memory_info().rss

            return {
                "test_name": self.test_name,
                "execution_time": end_time - self.start_time,
                "memory_used": end_memory - self.start_memory,
                "final_memory_mb": end_memory / (1024 * 1024),
                "cpu_percent": self.process.cpu_percent()
            }

        def assert_performance(self, max_time: float = None, max_memory_mb: float = None):
            """Assert performance metrics are within bounds."""
            metrics = self.stop()
            if not metrics:
                return

            if max_time and metrics["execution_time"] > max_time:
                pytest.fail(f"Test too slow: {metrics['execution_time']:.3f}s > {max_time}s")

            if max_memory_mb and metrics["memory_used"] / (1024 * 1024) > max_memory_mb:
                memory_mb = metrics["memory_used"] / (1024 * 1024)
                pytest.fail(f"Memory usage too high: {memory_mb:.1f}MB > {max_memory_mb}MB")

    return PerformanceMonitor()


@pytest.fixture(scope="session")
def test_database():
    """Create a test database for integration tests."""
    # This would set up a test database if needed
    # For now, we'll just return a mock
    return {
        "url": "sqlite:///:memory:",
        "tables_created": True
    }


@pytest.fixture(autouse=True)
def cleanup_temp_files():
    """Automatically cleanup temporary files after each test."""
    temp_files = []
    temp_dirs = []

    yield {"files": temp_files, "dirs": temp_dirs}

    # Cleanup
    for file_path in temp_files:
        try:
            Path(file_path).unlink(missing_ok=True)
        except Exception:
            pass

    for dir_path in temp_dirs:
        try:
            shutil.rmtree(dir_path, ignore_errors=True)
        except Exception:
            pass


# Test environment configuration
@pytest.fixture(scope="session", autouse=True)
def configure_test_environment():
    """Configure test environment variables and settings."""
    import os

    # Set test environment variables
    test_env = {
        "CASPER_TEST_MODE": "true",
        "CASPER_LOG_LEVEL": "DEBUG",
        "CASPER_DISABLE_TELEMETRY": "true",
        "PYTEST_RUNNING": "true",
    }

    # Store original values
    original_env = {}
    for key, value in test_env.items():
        original_env[key] = os.environ.get(key)
        os.environ[key] = value

    yield

    # Restore original environment
    for key, original_value in original_env.items():
        if original_value is None:
            os.environ.pop(key, None)
        else:
            os.environ[key] = original_value


# Async test helpers
@pytest.fixture
def async_timeout():
    """Provide timeout for async operations."""
    return 10.0  # 10 seconds timeout


@pytest.fixture
async def mock_server():
    """Create a mock server for testing WebSocket connections."""
    import aiohttp
    from aiohttp import web

    app = web.Application()

    async def websocket_handler(request):
        ws = web.WebSocketResponse()
        await ws.prepare(request)

        async for msg in ws:
            if msg.type == aiohttp.WSMsgType.TEXT:
                # Echo back the message
                await ws.send_str(f"Echo: {msg.data}")
            elif msg.type == aiohttp.WSMsgType.ERROR:
                break

        return ws

    app.router.add_get('/ws/terminal', websocket_handler)

    # This would start a test server
    # For now, just return the app
    return app


# Helper functions for test data generation
def generate_test_commands(count: int = 10, command_type: str = "safe") -> List[str]:
    """Generate test commands for testing."""
    if command_type == "safe":
        base_commands = ["ls", "pwd", "echo", "cat", "grep"]
    elif command_type == "dangerous":
        base_commands = ["rm -rf", "dd if=", "chmod 777", "sudo rm", "mkfs"]
    else:
        base_commands = ["ls", "pwd", "echo"]

    commands = []
    for i in range(count):
        base = base_commands[i % len(base_commands)]
        commands.append(f"{base} test-{i}")

    return commands


def create_mock_audit_events(count: int = 10) -> List[Dict[str, Any]]:
    """Create mock audit events for testing."""
    from datetime import datetime
    import random

    events = []
    risk_levels = ["low", "medium", "high", "critical"]
    event_types = ["COMMAND_EXECUTED", "COMMAND_BLOCKED", "SESSION_CREATED", "SECURITY_VIOLATION"]

    for i in range(count):
        events.append({
            "event_type": random.choice(event_types),
            "command": f"test command {i}",
            "session_id": f"session-{i % 5}",
            "user_id": f"user-{i % 3}",
            "risk_level": random.choice(risk_levels),
            "allowed": random.choice([True, False]),
            "reason": f"Test reason {i}",
            "timestamp": datetime.now().isoformat()
        })

    return events


# Pytest hooks for terminal testing
def pytest_runtest_setup(item):
    """Setup for each test run."""
    # Mark slow tests for conditional execution
    if "slow" in item.keywords and not item.config.getoption("--run-slow", False):
        pytest.skip("slow test skipped (use --run-slow to run)")


def pytest_addoption(parser):
    """Add custom command line options."""
    parser.addoption(
        "--run-slow", action="store_true", default=False,
        help="run slow tests including performance and E2E tests"
    )
    parser.addoption(
        "--run-integration", action="store_true", default=False,
        help="run integration tests"
    )
    parser.addoption(
        "--coverage-threshold", type=int, default=85,
        help="minimum coverage percentage required"
    )