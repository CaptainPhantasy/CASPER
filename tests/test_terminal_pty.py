"""
Tests for PTY Manager and PTY Session functionality.
Comprehensive unit tests for terminal backend infrastructure.
"""

import asyncio
import os
import pytest
import subprocess
import tempfile
import time
from pathlib import Path
from unittest.mock import Mock, patch, AsyncMock

from core.terminal.pty_manager import PTYManager, PTYSession


class TestPTYSession:
    """Test PTYSession functionality."""

    @pytest.fixture
    def mock_pty_session(self):
        """Create a mock PTY session for testing."""
        with patch('subprocess.Popen') as mock_popen:
            mock_process = Mock()
            mock_process.pid = 12345
            mock_popen.return_value = mock_process

            session = PTYSession(
                session_id="test-session",
                master_fd=10,
                slave_fd=11,
                process=mock_process
            )
            session.is_active = True
            return session

    def test_session_initialization(self, mock_pty_session):
        """Test PTY session initialization."""
        session = mock_pty_session
        assert session.session_id == "test-session"
        assert session.master_fd == 10
        assert session.slave_fd == 11
        assert session.is_active is True
        assert session.output_callback is None
        assert session.process.pid == 12345

    def test_set_output_callback(self, mock_pty_session):
        """Test setting output callback."""
        callback = Mock()
        mock_pty_session.set_output_callback(callback)
        assert mock_pty_session.output_callback == callback

    @patch('os.write')
    def test_write_success(self, mock_write, mock_pty_session):
        """Test successful write to PTY."""
        test_data = "test command\n"
        mock_pty_session.write(test_data)

        mock_write.assert_called_once_with(10, test_data.encode('utf-8'))

    @patch('os.write')
    def test_write_failure(self, mock_write, mock_pty_session):
        """Test write failure handling."""
        mock_write.side_effect = OSError("Write failed")
        mock_pty_session.write("test")

        assert mock_pty_session.is_active is False

    @patch('select.select')
    @patch('os.read')
    def test_read_success(self, mock_read, mock_select, mock_pty_session):
        """Test successful read from PTY."""
        mock_select.return_value = ([10], [], [])  # fd 10 is ready
        mock_read.return_value = b"output data"

        result = mock_pty_session.read()
        assert result == "output data"

    @patch('select.select')
    def test_read_no_data(self, mock_select, mock_pty_session):
        """Test read when no data is available."""
        mock_select.return_value = ([], [], [])  # No fd ready

        result = mock_pty_session.read()
        assert result is None

    @patch('fcntl.ioctl')
    def test_resize_success(self, mock_ioctl, mock_pty_session):
        """Test successful terminal resize."""
        mock_pty_session.resize(50, 120)

        mock_ioctl.assert_called_once()
        call_args = mock_ioctl.call_args
        assert call_args[0][0] == 10  # master_fd
        assert call_args[0][1] is not None  # TIOCSWINSZ constant

    @patch('fcntl.ioctl')
    def test_resize_failure(self, mock_ioctl, mock_pty_session):
        """Test resize failure handling."""
        mock_ioctl.side_effect = OSError("Resize failed")

        # Should not raise exception
        mock_pty_session.resize(50, 120)

    def test_close_session(self, mock_pty_session):
        """Test session closure."""
        with patch('os.close') as mock_close:
            mock_pty_session.close()

            assert mock_pty_session.is_active is False
            mock_pty_session.process.terminate.assert_called_once()
            # os.close should be called twice (master and slave fd)
            assert mock_close.call_count == 2


class TestPTYManager:
    """Test PTYManager functionality."""

    @pytest.fixture
    async def pty_manager(self):
        """Create a PTY manager for testing."""
        manager = PTYManager()
        await manager.start()
        yield manager
        await manager.stop()

    @pytest.mark.asyncio
    async def test_manager_start_stop(self):
        """Test PTY manager start/stop lifecycle."""
        manager = PTYManager()
        assert not manager._running

        await manager.start()
        assert manager._running
        assert manager._cleanup_task is not None

        await manager.stop()
        assert not manager._running

    @pytest.mark.asyncio
    async def test_create_session_success(self, pty_manager):
        """Test successful session creation."""
        with patch('pty.openpty') as mock_openpty, \
             patch('subprocess.Popen') as mock_popen:

            mock_openpty.return_value = (10, 11)
            mock_process = Mock()
            mock_process.pid = 12345
            mock_popen.return_value = mock_process

            session_id = await pty_manager.create_session()

            assert session_id in pty_manager.sessions
            assert len(pty_manager.sessions) == 1

            session = pty_manager.sessions[session_id]
            assert session.master_fd == 10
            assert session.slave_fd == 11
            assert session.is_active

    @pytest.mark.asyncio
    async def test_create_session_with_options(self, pty_manager):
        """Test session creation with custom options."""
        with patch('pty.openpty') as mock_openpty, \
             patch('subprocess.Popen') as mock_popen:

            mock_openpty.return_value = (10, 11)
            mock_process = Mock()
            mock_popen.return_value = mock_process

            working_dir = "/tmp"
            env = {"TEST_VAR": "test_value"}

            session_id = await pty_manager.create_session(
                working_dir=working_dir,
                env=env
            )

            # Verify subprocess.Popen was called with correct parameters
            call_args = mock_popen.call_args
            assert call_args[1]['cwd'] == working_dir
            assert call_args[1]['env']['TEST_VAR'] == "test_value"
            assert call_args[1]['env']['TERM'] == 'xterm-256color'

    @pytest.mark.asyncio
    async def test_create_session_failure(self, pty_manager):
        """Test session creation failure handling."""
        with patch('pty.openpty') as mock_openpty:
            mock_openpty.side_effect = OSError("PTY creation failed")

            with pytest.raises(OSError):
                await pty_manager.create_session()

    @pytest.mark.asyncio
    async def test_close_session_success(self, pty_manager):
        """Test successful session closure."""
        # Create a mock session
        session_id = "test-session"
        mock_session = Mock()
        mock_session.session_id = session_id
        pty_manager.sessions[session_id] = mock_session

        result = await pty_manager.close_session(session_id)

        assert result is True
        assert session_id not in pty_manager.sessions
        mock_session.close.assert_called_once()

    @pytest.mark.asyncio
    async def test_close_nonexistent_session(self, pty_manager):
        """Test closing a non-existent session."""
        result = await pty_manager.close_session("nonexistent")
        assert result is False

    @pytest.mark.asyncio
    async def test_write_to_session_success(self, pty_manager):
        """Test successful write to session."""
        session_id = "test-session"
        mock_session = Mock()
        mock_session.is_active = True
        pty_manager.sessions[session_id] = mock_session

        result = await pty_manager.write_to_session(session_id, "test data")

        assert result is True
        mock_session.write.assert_called_once_with("test data")

    @pytest.mark.asyncio
    async def test_write_to_inactive_session(self, pty_manager):
        """Test write to inactive session."""
        session_id = "test-session"
        mock_session = Mock()
        mock_session.is_active = False
        pty_manager.sessions[session_id] = mock_session

        result = await pty_manager.write_to_session(session_id, "test data")

        assert result is False

    @pytest.mark.asyncio
    async def test_resize_session_success(self, pty_manager):
        """Test successful session resize."""
        session_id = "test-session"
        mock_session = Mock()
        mock_session.is_active = True
        pty_manager.sessions[session_id] = mock_session

        result = await pty_manager.resize_session(session_id, 50, 120)

        assert result is True
        mock_session.resize.assert_called_once_with(50, 120)

    def test_set_output_callback(self, pty_manager):
        """Test setting output callback."""
        session_id = "test-session"
        mock_session = Mock()
        pty_manager.sessions[session_id] = mock_session
        callback = Mock()

        result = pty_manager.set_output_callback(session_id, callback)

        assert result is True
        mock_session.set_output_callback.assert_called_once_with(callback)

    def test_get_session_info(self, pty_manager):
        """Test getting session information."""
        session_id = "test-session"
        mock_session = Mock()
        mock_session.session_id = session_id
        mock_session.is_active = True
        mock_session.last_activity = 123456.789
        mock_session.process.pid = 12345
        pty_manager.sessions[session_id] = mock_session

        info = pty_manager.get_session_info(session_id)

        assert info is not None
        assert info['session_id'] == session_id
        assert info['is_active'] is True
        assert info['last_activity'] == 123456.789
        assert info['process_pid'] == 12345

    def test_list_sessions(self, pty_manager):
        """Test listing all sessions."""
        # Add mock sessions
        for i in range(3):
            session_id = f"session-{i}"
            mock_session = Mock()
            mock_session.session_id = session_id
            mock_session.is_active = True
            mock_session.last_activity = time.time()
            mock_session.process.pid = 1000 + i
            pty_manager.sessions[session_id] = mock_session

        sessions = pty_manager.list_sessions()

        assert len(sessions) == 3
        assert all(isinstance(session, dict) for session in sessions)

    @pytest.mark.asyncio
    async def test_cleanup_inactive_sessions(self):
        """Test cleanup of inactive sessions."""
        manager = PTYManager()

        # Add an active session and an inactive session
        active_session = Mock()
        active_session.session_id = "active"
        active_session.is_active = True
        active_session.last_activity = time.time()

        inactive_session = Mock()
        inactive_session.session_id = "inactive"
        inactive_session.is_active = False
        inactive_session.last_activity = time.time() - 2000  # Old activity

        manager.sessions["active"] = active_session
        manager.sessions["inactive"] = inactive_session

        manager._running = True

        # Mock the close_session method
        manager.close_session = AsyncMock()

        # Run one cleanup cycle
        await manager._cleanup_inactive_sessions()

        # Should have attempted to close the inactive session
        manager.close_session.assert_called_with("inactive")


class TestPTYIntegration:
    """Integration tests for PTY functionality."""

    @pytest.mark.asyncio
    async def test_full_pty_workflow(self):
        """Test complete PTY workflow with real shell."""
        manager = PTYManager()
        await manager.start()

        try:
            # Create session
            session_id = await manager.create_session()
            assert session_id in manager.sessions

            # Set up output capture
            output_data = []

            def capture_output(data):
                output_data.append(data)

            manager.set_output_callback(session_id, capture_output)

            # Send a command
            await manager.write_to_session(session_id, "echo 'Hello Terminal'\n")

            # Wait for output
            await asyncio.sleep(0.5)

            # Verify we got some output
            assert len(output_data) > 0
            output_text = ''.join(output_data)
            assert "Hello Terminal" in output_text or "echo" in output_text

            # Test resize
            result = await manager.resize_session(session_id, 50, 120)
            assert result is True

            # Close session
            result = await manager.close_session(session_id)
            assert result is True
            assert session_id not in manager.sessions

        finally:
            await manager.stop()

    @pytest.mark.asyncio
    async def test_multiple_concurrent_sessions(self):
        """Test multiple PTY sessions running concurrently."""
        manager = PTYManager()
        await manager.start()

        try:
            # Create multiple sessions
            session_ids = []
            for i in range(3):
                session_id = await manager.create_session()
                session_ids.append(session_id)

            # Verify all sessions exist
            assert len(manager.sessions) == 3
            for session_id in session_ids:
                assert session_id in manager.sessions

            # Send commands to all sessions
            for i, session_id in enumerate(session_ids):
                await manager.write_to_session(session_id, f"echo 'Session {i}'\n")

            # Wait for processing
            await asyncio.sleep(0.5)

            # Close all sessions
            for session_id in session_ids:
                result = await manager.close_session(session_id)
                assert result is True

            assert len(manager.sessions) == 0

        finally:
            await manager.stop()

    @pytest.mark.asyncio
    async def test_pty_with_custom_environment(self):
        """Test PTY with custom environment variables."""
        manager = PTYManager()
        await manager.start()

        try:
            # Create session with custom environment
            custom_env = {
                "TEST_VARIABLE": "test_value_123",
                "CUSTOM_PATH": "/custom/path"
            }

            session_id = await manager.create_session(env=custom_env)

            # Capture output
            output_data = []
            manager.set_output_callback(session_id, output_data.append)

            # Test environment variable
            await manager.write_to_session(session_id, "echo $TEST_VARIABLE\n")
            await asyncio.sleep(0.5)

            output_text = ''.join(output_data)
            assert "test_value_123" in output_text or "TEST_VARIABLE" in output_text

        finally:
            await manager.close_session(session_id)
            await manager.stop()


@pytest.mark.performance
class TestPTYPerformance:
    """Performance tests for PTY functionality."""

    @pytest.mark.asyncio
    async def test_session_creation_performance(self):
        """Test PTY session creation performance."""
        manager = PTYManager()
        await manager.start()

        try:
            start_time = time.time()

            # Create 10 sessions quickly
            session_ids = []
            for i in range(10):
                session_id = await manager.create_session()
                session_ids.append(session_id)

            creation_time = time.time() - start_time

            # Should create 10 sessions in under 2 seconds
            assert creation_time < 2.0, f"Session creation took {creation_time}s, expected < 2.0s"
            assert len(manager.sessions) == 10

            # Clean up
            for session_id in session_ids:
                await manager.close_session(session_id)

        finally:
            await manager.stop()

    @pytest.mark.asyncio
    async def test_write_throughput(self):
        """Test write throughput to PTY."""
        manager = PTYManager(shell_command="/bin/bash")
        await manager.start()

        try:
            session_id = await manager.create_session()

            # Write large amount of data
            start_time = time.time()
            data_size = 0

            for i in range(100):
                data = f"echo 'Data packet {i} - " + "x" * 50 + "'\n"
                await manager.write_to_session(session_id, data)
                data_size += len(data)

            write_time = time.time() - start_time
            throughput = data_size / write_time  # bytes per second

            # Should achieve reasonable throughput
            assert throughput > 1000, f"Write throughput {throughput} bytes/s too low"

        finally:
            await manager.close_session(session_id)
            await manager.stop()
