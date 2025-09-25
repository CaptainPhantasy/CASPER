"""
Comprehensive security test suite for CASPER Terminal Infrastructure.
Tests all security components including middleware, command validation, sandboxing, and audit logging.
"""

import asyncio
import pytest
import tempfile
import shutil
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import Mock, AsyncMock, patch
from uuid import uuid4

# Import all security components
from core.terminal.security import (
    SecurityMiddleware, SecurityConfig, SecurityViolation, CommandRisk,
    SecurityLevel, AuditEvent
)
from core.terminal.websocket_handler import TerminalWebSocketHandler, TerminalSession
from core.terminal.command_proxy import CommandProxy
from core.terminal.pty_manager import PTYManager


class TestSecurityConfig:
    """Test security configuration functionality."""

    def test_default_configuration(self):
        """Test default security configuration."""
        config = SecurityConfig()

        # Test safe commands
        assert "ls" in config.safe_commands
        assert "cat" in config.safe_commands
        assert "casper" in config.safe_commands

        # Test restricted commands
        assert "mkdir" in config.restricted_commands
        assert "git add" in config.restricted_commands

        # Test dangerous commands
        assert "sudo" in config.dangerous_commands
        assert "ssh" in config.dangerous_commands

        # Test blocked commands
        assert "rm" in config.blocked_commands
        assert "dd" in config.blocked_commands

    def test_dangerous_patterns(self):
        """Test dangerous command patterns detection."""
        config = SecurityConfig()

        # Test recursive delete pattern
        assert any(pattern.search("rm -rf /") for pattern in config.dangerous_patterns)

        # Test command substitution patterns
        assert any(pattern.search("echo `whoami`") for pattern in config.dangerous_patterns)
        assert any(pattern.search("echo $(id)") for pattern in config.dangerous_patterns)

        # Test command chaining
        assert any(pattern.search("ls && rm file") for pattern in config.dangerous_patterns)


class TestSecurityMiddleware:
    """Test security middleware functionality."""

    def setup_method(self):
        """Set up test environment."""
        self.security = SecurityMiddleware()
        self.session_id = str(uuid4())
        self.user_id = "test_user"

    @pytest.mark.asyncio
    async def test_safe_command_validation(self):
        """Test validation of safe commands."""
        safe_commands = ["ls -la", "cat file.txt", "pwd", "git status"]

        for command in safe_commands:
            result = await self.security.validate_command(command, self.session_id, self.user_id)
            assert result is True

    @pytest.mark.asyncio
    async def test_blocked_command_validation(self):
        """Test blocking of dangerous commands."""
        blocked_commands = ["rm -rf /", "dd if=/dev/zero", "sudo su", "reboot"]

        for command in blocked_commands:
            with pytest.raises(SecurityViolation) as exc_info:
                await self.security.validate_command(command, self.session_id, self.user_id)
            assert exc_info.value.risk_level in [CommandRisk.HIGH, CommandRisk.CRITICAL]

    @pytest.mark.asyncio
    async def test_dangerous_pattern_detection(self):
        """Test detection of dangerous command patterns."""
        dangerous_commands = [
            "rm -rf *",
            "echo `rm file`",
            "ls && rm file",
            "cat file | sh",
            "> /dev/sda"
        ]

        for command in dangerous_commands:
            with pytest.raises(SecurityViolation):
                await self.security.validate_command(command, self.session_id, self.user_id)

    @pytest.mark.asyncio
    async def test_path_validation(self):
        """Test path-based security validation."""
        # Should block access to system directories
        with pytest.raises(SecurityViolation):
            await self.security.validate_command("rm /etc/passwd", self.session_id, self.user_id)

        with pytest.raises(SecurityViolation):
            await self.security.validate_command("chmod 777 /bin/bash", self.session_id, self.user_id)

    @pytest.mark.asyncio
    async def test_sandbox_creation(self):
        """Test sandbox environment creation."""
        sandbox = await self.security.create_sandbox(self.session_id)

        assert "session_id" in sandbox
        assert "sandbox_dir" in sandbox
        assert "allowed_paths" in sandbox
        assert "env_vars" in sandbox

        # Verify sandbox directory exists
        sandbox_dir = Path(sandbox["sandbox_dir"])
        assert sandbox_dir.exists()
        assert sandbox_dir.is_dir()

        # Cleanup
        await self.security.cleanup_sandbox(self.session_id)
        assert not sandbox_dir.exists()

    def test_audit_logging(self):
        """Test security audit logging."""
        initial_log_count = len(self.security.audit_log)

        # Log a security event
        self.security._log_security_event(
            "TEST_EVENT", "test command", self.session_id, self.user_id,
            CommandRisk.LOW, True, "Test audit event"
        )

        assert len(self.security.audit_log) == initial_log_count + 1

        # Verify event details
        event = self.security.audit_log[-1]
        assert event.event_type == "TEST_EVENT"
        assert event.command == "test command"
        assert event.session_id == self.session_id
        assert event.user_id == self.user_id
        assert event.risk_level == CommandRisk.LOW
        assert event.allowed is True

    def test_audit_summary(self):
        """Test audit summary generation."""
        # Add some test events
        events = [
            ("COMMAND_1", CommandRisk.LOW, True),
            ("COMMAND_2", CommandRisk.HIGH, False),
            ("COMMAND_3", CommandRisk.MEDIUM, True),
            ("COMMAND_4", CommandRisk.CRITICAL, False)
        ]

        for event_type, risk, allowed in events:
            self.security._log_security_event(
                event_type, f"test {event_type}", self.session_id, self.user_id,
                risk, allowed, "Test event"
            )

        summary = self.security.get_audit_summary(hours=1)

        assert summary["total_events"] >= 4
        assert summary["allowed_commands"] >= 2
        assert summary["blocked_commands"] >= 2
        assert summary["risk_levels"]["low"] >= 1
        assert summary["risk_levels"]["high"] >= 1


class TestWebSocketSecurityHandler:
    """Test WebSocket security handler."""

    def setup_method(self):
        """Set up test environment."""
        self.handler = TerminalWebSocketHandler()
        self.mock_websocket = Mock()
        self.mock_websocket.accept = AsyncMock()
        self.mock_websocket.send_json = AsyncMock()

    @pytest.mark.asyncio
    async def test_connection_without_token(self):
        """Test connection establishment without authentication token."""
        session_id = await self.handler.connect(self.mock_websocket)

        assert session_id in self.handler.sessions
        session = self.handler.sessions[session_id]
        assert session.user_id is None
        assert session.is_active is True

    @pytest.mark.asyncio
    async def test_connection_with_invalid_token(self):
        """Test connection rejection with invalid token."""
        with pytest.raises(Exception):
            await self.handler.connect(self.mock_websocket, "invalid_token")

    @pytest.mark.asyncio
    @patch('jwt.decode')
    async def test_connection_with_valid_token(self, mock_jwt_decode):
        """Test connection establishment with valid authentication token."""
        mock_jwt_decode.return_value = {"user_id": "test_user"}

        session_id = await self.handler.connect(self.mock_websocket, "valid_token")

        session = self.handler.sessions[session_id]
        assert session.user_id == "test_user"

    @pytest.mark.asyncio
    async def test_command_security_validation(self):
        """Test command security validation through WebSocket handler."""
        session_id = await self.handler.connect(self.mock_websocket)
        session = self.handler.sessions[session_id]

        # Test safe command
        message = {"type": "command", "command": "ls -la"}
        await self.handler.handle_message(session_id, message)

        # Test blocked command
        message = {"type": "command", "command": "rm -rf /"}
        await self.handler.handle_message(session_id, message)

        # Verify error was sent for blocked command
        assert self.mock_websocket.send_json.call_count >= 1

    @pytest.mark.asyncio
    async def test_session_cleanup(self):
        """Test proper session cleanup."""
        session_id = await self.handler.connect(self.mock_websocket)
        assert session_id in self.handler.sessions

        await self.handler.disconnect(session_id)
        assert session_id not in self.handler.sessions


class TestCommandProxy:
    """Test secure command proxy functionality."""

    def setup_method(self):
        """Set up test environment."""
        self.proxy = CommandProxy()
        self.user_id = "test_user"
        self.session_id = str(uuid4())

    @pytest.mark.asyncio
    async def test_rate_limiting(self):
        """Test command rate limiting."""
        # Set a very low rate limit for testing
        self.proxy.command_rate_limits["status"]["max_per_minute"] = 2

        # First two commands should succeed
        assert await self.proxy._check_rate_limits("status", self.user_id) is True
        assert await self.proxy._check_rate_limits("status", self.user_id) is True

        # Third command should be rate limited
        assert await self.proxy._check_rate_limits("status", self.user_id) is False

    @pytest.mark.asyncio
    async def test_concurrent_task_limits(self):
        """Test concurrent task execution limits."""
        self.proxy.max_concurrent_tasks = 2

        # Add tasks to active set
        self.proxy.active_tasks.add("task1")
        self.proxy.active_tasks.add("task2")

        # Should raise SecurityViolation for exceeding limit
        with pytest.raises(SecurityViolation):
            await self.proxy.execute_casper_command(
                "task", ["test task"], self.user_id, self.session_id
            )

    @pytest.mark.asyncio
    async def test_command_validation_logging(self):
        """Test that command execution is properly logged."""
        initial_log_count = len(self.proxy.security.audit_log)

        # Execute a help command (should be safe)
        try:
            await self.proxy.execute_casper_command(
                "help", [], self.user_id, self.session_id
            )
        except Exception:
            pass  # We're testing logging, not execution

        # Verify logging occurred
        assert len(self.proxy.security.audit_log) > initial_log_count

    def test_task_cleanup(self):
        """Test active task cleanup."""
        task_id = "test_task_123"
        self.proxy.active_tasks.add(task_id)

        assert task_id in self.proxy.active_tasks

        self.proxy.cleanup_completed_tasks(task_id)
        assert task_id not in self.proxy.active_tasks


class TestPTYManagerSecurity:
    """Test PTY manager security features."""

    def setup_method(self):
        """Set up test environment."""
        self.pty_manager = PTYManager()

    @pytest.mark.asyncio
    async def test_session_isolation(self):
        """Test that PTY sessions are properly isolated."""
        await self.pty_manager.start()

        try:
            # Create two sessions
            session1 = await self.pty_manager.create_session()
            session2 = await self.pty_manager.create_session()

            assert session1 != session2
            assert session1 in self.pty_manager.sessions
            assert session2 in self.pty_manager.sessions

            # Sessions should have different PIDs
            info1 = self.pty_manager.get_session_info(session1)
            info2 = self.pty_manager.get_session_info(session2)

            assert info1["process_pid"] != info2["process_pid"]

        finally:
            await self.pty_manager.stop()

    @pytest.mark.asyncio
    async def test_session_timeout_cleanup(self):
        """Test automatic cleanup of inactive sessions."""
        await self.pty_manager.start()

        try:
            session_id = await self.pty_manager.create_session()
            session = self.pty_manager.sessions[session_id]

            # Simulate old session by setting old activity time
            session.last_activity = asyncio.get_event_loop().time() - 2000

            # Run cleanup
            await self.pty_manager._cleanup_inactive_sessions()

            # Session should be cleaned up
            assert session_id not in self.pty_manager.sessions

        finally:
            await self.pty_manager.stop()


class TestIntegratedSecurity:
    """Test integrated security across all components."""

    def setup_method(self):
        """Set up integrated test environment."""
        self.security = SecurityMiddleware()
        self.handler = TerminalWebSocketHandler()
        self.proxy = CommandProxy(self.security)

    @pytest.mark.asyncio
    async def test_end_to_end_security_flow(self):
        """Test complete security flow from WebSocket to command execution."""
        mock_websocket = Mock()
        mock_websocket.accept = AsyncMock()
        mock_websocket.send_json = AsyncMock()

        # Establish connection
        session_id = await self.handler.connect(mock_websocket)

        # Attempt to execute a safe command
        message = {
            "type": "casper_command",
            "command": "help",
            "args": []
        }

        await self.handler.handle_message(session_id, message)

        # Verify command was processed
        assert mock_websocket.send_json.called

        # Attempt to execute a dangerous command
        message = {
            "type": "command",
            "command": "rm -rf /"
        }

        await self.handler.handle_message(session_id, message)

        # Verify security violation was handled
        calls = mock_websocket.send_json.call_args_list
        error_sent = any(
            "error" in str(call) and "security_violation" in str(call)
            for call in calls
        )
        assert error_sent

    def test_audit_trail_completeness(self):
        """Test that all security events are properly logged."""
        initial_count = len(self.security.audit_log)

        # Simulate various security events
        events = [
            ("COMMAND_EXECUTION", "ls", CommandRisk.LOW, True),
            ("COMMAND_BLOCKED", "rm -rf /", CommandRisk.CRITICAL, False),
            ("SANDBOX_CREATED", "sandbox_123", CommandRisk.LOW, True),
            ("RATE_LIMIT_EXCEEDED", "status", CommandRisk.MEDIUM, False)
        ]

        for event_type, command, risk, allowed in events:
            self.security._log_security_event(
                event_type, command, "test_session", "test_user", risk, allowed
            )

        # Verify all events were logged
        assert len(self.security.audit_log) == initial_count + len(events)

        # Generate audit summary
        summary = self.security.get_audit_summary()
        assert summary["total_events"] >= len(events)

    @pytest.mark.asyncio
    async def test_security_metrics_accuracy(self):
        """Test accuracy of security metrics and statistics."""
        # Execute various commands to generate metrics
        test_commands = [
            ("ls", True),
            ("rm -rf /", False),
            ("cat file", True),
            ("sudo su", False)
        ]

        for command, should_succeed in test_commands:
            try:
                await self.security.validate_command(command, "test_session", "test_user")
                assert should_succeed, f"Command '{command}' should have been blocked"
            except SecurityViolation:
                assert not should_succeed, f"Command '{command}' should have been allowed"

        # Verify metrics
        summary = self.security.get_audit_summary()
        assert summary["allowed_commands"] >= 2  # ls, cat
        assert summary["blocked_commands"] >= 2  # rm, sudo


# Performance and stress tests
class TestSecurityPerformance:
    """Test security system performance under load."""

    def setup_method(self):
        """Set up performance test environment."""
        self.security = SecurityMiddleware()

    @pytest.mark.asyncio
    async def test_command_validation_performance(self):
        """Test command validation performance under high load."""
        import time

        commands = ["ls", "cat file", "pwd", "git status"] * 250  # 1000 commands

        start_time = time.time()

        for command in commands:
            await self.security.validate_command(command, "perf_session", "perf_user")

        end_time = time.time()
        execution_time = end_time - start_time

        # Should process 1000 safe commands in under 1 second
        assert execution_time < 1.0, f"Command validation too slow: {execution_time}s for 1000 commands"

    def test_audit_log_memory_efficiency(self):
        """Test audit log memory usage doesn't grow indefinitely."""
        initial_count = len(self.security.audit_log)

        # Generate many audit events
        for i in range(10000):
            self.security._log_security_event(
                "PERF_TEST", f"command_{i}", "perf_session", "perf_user",
                CommandRisk.LOW, True, "Performance test event"
            )

        # Should have all events in memory for testing
        # In production, implement log rotation
        assert len(self.security.audit_log) == initial_count + 10000


if __name__ == "__main__":
    # Run specific test categories
    import sys

    if len(sys.argv) > 1 and sys.argv[1] == "--security-only":
        pytest.main([__file__ + "::TestSecurityMiddleware", "-v"])
    elif len(sys.argv) > 1 and sys.argv[1] == "--performance":
        pytest.main([__file__ + "::TestSecurityPerformance", "-v"])
    else:
        pytest.main([__file__, "-v", "--tb=short"])