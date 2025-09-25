"""
Tests for Terminal WebSocket Handler.
Comprehensive unit and integration tests for WebSocket terminal functionality.
"""

import asyncio
import json
import pytest
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from fastapi import WebSocket, WebSocketDisconnect
from datetime import datetime

from core.terminal.websocket_handler import TerminalWebSocketHandler


class MockWebSocket:
    """Mock WebSocket for testing."""

    def __init__(self):
        self.messages = []
        self.received_messages = []
        self.closed = False
        self.accepted = False

    async def accept(self):
        self.accepted = True

    async def send_text(self, data: str):
        if self.closed:
            raise ConnectionError("WebSocket closed")
        self.messages.append(data)

    async def receive_text(self):
        if self.closed:
            raise WebSocketDisconnect()
        if self.received_messages:
            return self.received_messages.pop(0)
        # Simulate WebSocket disconnect after no messages
        raise WebSocketDisconnect()

    def add_received_message(self, message: dict):
        """Add a message to be received by the websocket."""
        self.received_messages.append(json.dumps(message))

    def close(self):
        self.closed = True

    def get_sent_messages(self):
        """Get all sent messages as parsed JSON."""
        return [json.loads(msg) for msg in self.messages]


class TestTerminalWebSocketHandler:
    """Test Terminal WebSocket Handler functionality."""

    @pytest.fixture
    def mock_dependencies(self):
        """Mock all dependencies for WebSocket handler."""
        with patch('core.terminal.websocket_handler.PTYManager') as mock_pty, \
             patch('core.terminal.websocket_handler.CommandProxy') as mock_proxy, \
             patch('core.terminal.websocket_handler.SecurityMiddleware') as mock_security:

            # Set up mocks
            mock_pty_instance = AsyncMock()
            mock_pty.return_value = mock_pty_instance

            mock_proxy_instance = AsyncMock()
            mock_proxy.return_value = mock_proxy_instance

            mock_security_instance = AsyncMock()
            mock_security_instance.validate_input.return_value = True
            mock_security_instance.validate_casper_command.return_value = True
            mock_security.return_value = mock_security_instance

            return {
                'pty_manager': mock_pty_instance,
                'command_proxy': mock_proxy_instance,
                'security': mock_security_instance
            }

    @pytest.fixture
    async def handler(self, mock_dependencies):
        """Create a terminal WebSocket handler for testing."""
        handler = TerminalWebSocketHandler()
        await handler.start()
        yield handler
        await handler.stop()

    @pytest.mark.asyncio
    async def test_handler_start_stop(self, mock_dependencies):
        """Test handler lifecycle management."""
        handler = TerminalWebSocketHandler()

        # Test start
        await handler.start()
        mock_dependencies['pty_manager'].start.assert_called_once()

        # Test stop
        await handler.stop()
        mock_dependencies['pty_manager'].stop.assert_called_once()

    @pytest.mark.asyncio
    async def test_handle_connection_establishment(self, handler):
        """Test WebSocket connection establishment."""
        websocket = MockWebSocket()

        # Start connection handling in background
        connection_task = asyncio.create_task(
            handler.handle_connection(websocket, "test-connection")
        )

        # Give it a moment to establish connection
        await asyncio.sleep(0.01)

        # Verify connection was accepted
        assert websocket.accepted
        assert "test-connection" in handler.active_connections
        assert "test-connection" in handler.connections

        # Check initial message
        messages = websocket.get_sent_messages()
        assert len(messages) >= 1
        assert messages[0]["type"] == "connection_established"
        assert messages[0]["connection_id"] == "test-connection"

        # Close connection to stop the task
        websocket.close()
        await connection_task

    @pytest.mark.asyncio
    async def test_create_session_success(self, handler, mock_dependencies):
        """Test successful session creation."""
        websocket = MockWebSocket()

        # Mock PTY manager to return a session ID
        mock_dependencies['pty_manager'].create_session.return_value = "test-session"

        # Add message to be received
        websocket.add_received_message({
            "type": "create_session",
            "working_dir": "/tmp",
            "env": {"TEST": "value"}
        })

        # Start connection handling
        connection_task = asyncio.create_task(
            handler.handle_connection(websocket, "test-connection")
        )

        await asyncio.sleep(0.01)
        websocket.close()
        await connection_task

        # Verify session creation was called
        mock_dependencies['pty_manager'].create_session.assert_called_with(
            "/tmp", {"TEST": "value"}
        )

        # Check connection mappings
        assert "test-session" in handler.session_connections
        assert handler.session_connections["test-session"] == "test-connection"
        assert handler.connection_sessions["test-connection"] == "test-session"

        # Verify response message
        messages = websocket.get_sent_messages()
        session_created_msg = next(
            (msg for msg in messages if msg["type"] == "session_created"), None
        )
        assert session_created_msg is not None
        assert session_created_msg["session_id"] == "test-session"

    @pytest.mark.asyncio
    async def test_create_session_failure(self, handler, mock_dependencies):
        """Test session creation failure handling."""
        websocket = MockWebSocket()

        # Mock PTY manager to raise exception
        mock_dependencies['pty_manager'].create_session.side_effect = Exception("Session creation failed")

        websocket.add_received_message({
            "type": "create_session"
        })

        connection_task = asyncio.create_task(
            handler.handle_connection(websocket, "test-connection")
        )

        await asyncio.sleep(0.01)
        websocket.close()
        await connection_task

        # Verify error message was sent
        messages = websocket.get_sent_messages()
        error_msg = next(
            (msg for msg in messages if msg["type"] == "error"), None
        )
        assert error_msg is not None
        assert "Failed to create session" in error_msg["message"]

    @pytest.mark.asyncio
    async def test_handle_input(self, handler, mock_dependencies):
        """Test terminal input handling."""
        websocket = MockWebSocket()

        # Set up session mapping
        handler.connection_sessions["test-connection"] = "test-session"
        mock_dependencies['pty_manager'].write_to_session.return_value = True

        websocket.add_received_message({
            "type": "input",
            "data": "echo hello\n"
        })

        connection_task = asyncio.create_task(
            handler.handle_connection(websocket, "test-connection")
        )

        await asyncio.sleep(0.01)
        websocket.close()
        await connection_task

        # Verify input was validated and sent
        mock_dependencies['security'].validate_input.assert_called_with(
            "echo hello\n", "test-session"
        )
        mock_dependencies['pty_manager'].write_to_session.assert_called_with(
            "test-session", "echo hello\n"
        )

    @pytest.mark.asyncio
    async def test_handle_input_blocked(self, handler, mock_dependencies):
        """Test input blocked by security."""
        websocket = MockWebSocket()

        handler.connection_sessions["test-connection"] = "test-session"
        mock_dependencies['security'].validate_input.return_value = False

        websocket.add_received_message({
            "type": "input",
            "data": "rm -rf /"
        })

        connection_task = asyncio.create_task(
            handler.handle_connection(websocket, "test-connection")
        )

        await asyncio.sleep(0.01)
        websocket.close()
        await connection_task

        # Verify input was not sent to PTY
        mock_dependencies['pty_manager'].write_to_session.assert_not_called()

        # Verify error message
        messages = websocket.get_sent_messages()
        error_msg = next(
            (msg for msg in messages if msg["type"] == "error"), None
        )
        assert error_msg is not None
        assert "blocked by security policy" in error_msg["message"]

    @pytest.mark.asyncio
    async def test_handle_resize(self, handler, mock_dependencies):
        """Test terminal resize handling."""
        websocket = MockWebSocket()

        handler.connection_sessions["test-connection"] = "test-session"
        mock_dependencies['pty_manager'].resize_session.return_value = True

        websocket.add_received_message({
            "type": "resize",
            "rows": 50,
            "cols": 120
        })

        connection_task = asyncio.create_task(
            handler.handle_connection(websocket, "test-connection")
        )

        await asyncio.sleep(0.01)
        websocket.close()
        await connection_task

        # Verify resize was called
        mock_dependencies['pty_manager'].resize_session.assert_called_with(
            "test-session", 50, 120
        )

    @pytest.mark.asyncio
    async def test_handle_casper_command(self, handler, mock_dependencies):
        """Test CASPER command execution."""
        websocket = MockWebSocket()

        mock_dependencies['command_proxy'].execute_casper_command.return_value = {
            "status": "success",
            "output": "Command executed successfully"
        }

        websocket.add_received_message({
            "type": "casper_command",
            "command": "task",
            "args": ["list"]
        })

        connection_task = asyncio.create_task(
            handler.handle_connection(websocket, "test-connection")
        )

        await asyncio.sleep(0.01)
        websocket.close()
        await connection_task

        # Verify command was validated and executed
        mock_dependencies['security'].validate_casper_command.assert_called_with(
            "task", ["list"]
        )
        mock_dependencies['command_proxy'].execute_casper_command.assert_called_with(
            "task", ["list"]
        )

        # Verify response
        messages = websocket.get_sent_messages()
        result_msg = next(
            (msg for msg in messages if msg["type"] == "casper_command_result"), None
        )
        assert result_msg is not None
        assert result_msg["command"] == "task"
        assert result_msg["result"]["status"] == "success"

    @pytest.mark.asyncio
    async def test_handle_casper_command_blocked(self, handler, mock_dependencies):
        """Test blocked CASPER command."""
        websocket = MockWebSocket()

        mock_dependencies['security'].validate_casper_command.return_value = False

        websocket.add_received_message({
            "type": "casper_command",
            "command": "dangerous-command",
            "args": []
        })

        connection_task = asyncio.create_task(
            handler.handle_connection(websocket, "test-connection")
        )

        await asyncio.sleep(0.01)
        websocket.close()
        await connection_task

        # Verify command was not executed
        mock_dependencies['command_proxy'].execute_casper_command.assert_not_called()

        # Verify error message
        messages = websocket.get_sent_messages()
        error_msg = next(
            (msg for msg in messages if msg["type"] == "error"), None
        )
        assert error_msg is not None
        assert "blocked by security policy" in error_msg["message"]

    @pytest.mark.asyncio
    async def test_handle_ping_pong(self, handler):
        """Test ping-pong mechanism."""
        websocket = MockWebSocket()

        websocket.add_received_message({
            "type": "ping"
        })

        connection_task = asyncio.create_task(
            handler.handle_connection(websocket, "test-connection")
        )

        await asyncio.sleep(0.01)
        websocket.close()
        await connection_task

        # Verify pong response
        messages = websocket.get_sent_messages()
        pong_msg = next(
            (msg for msg in messages if msg["type"] == "pong"), None
        )
        assert pong_msg is not None
        assert "timestamp" in pong_msg

    @pytest.mark.asyncio
    async def test_handle_unknown_message_type(self, handler):
        """Test handling of unknown message types."""
        websocket = MockWebSocket()

        websocket.add_received_message({
            "type": "unknown_type"
        })

        connection_task = asyncio.create_task(
            handler.handle_connection(websocket, "test-connection")
        )

        await asyncio.sleep(0.01)
        websocket.close()
        await connection_task

        # Verify error message
        messages = websocket.get_sent_messages()
        error_msg = next(
            (msg for msg in messages if msg["type"] == "error"), None
        )
        assert error_msg is not None
        assert "Unknown message type" in error_msg["message"]

    @pytest.mark.asyncio
    async def test_close_session(self, handler, mock_dependencies):
        """Test session closure."""
        websocket = MockWebSocket()

        # Set up session mapping
        handler.connection_sessions["test-connection"] = "test-session"
        handler.session_connections["test-session"] = "test-connection"
        mock_dependencies['pty_manager'].close_session.return_value = True

        websocket.add_received_message({
            "type": "close_session"
        })

        connection_task = asyncio.create_task(
            handler.handle_connection(websocket, "test-connection")
        )

        await asyncio.sleep(0.01)
        websocket.close()
        await connection_task

        # Verify session was closed
        mock_dependencies['pty_manager'].close_session.assert_called_with("test-session")

        # Verify mappings were cleaned up
        assert "test-session" not in handler.session_connections
        assert "test-connection" not in handler.connection_sessions

        # Verify response
        messages = websocket.get_sent_messages()
        closed_msg = next(
            (msg for msg in messages if msg["type"] == "session_closed"), None
        )
        assert closed_msg is not None
        assert closed_msg["session_id"] == "test-session"

    @pytest.mark.asyncio
    async def test_connection_cleanup(self, handler, mock_dependencies):
        """Test connection cleanup on disconnect."""
        websocket = MockWebSocket()

        # Set up session mapping
        handler.connection_sessions["test-connection"] = "test-session"
        handler.session_connections["test-session"] = "test-connection"

        # Start connection and immediately close
        connection_task = asyncio.create_task(
            handler.handle_connection(websocket, "test-connection")
        )

        await asyncio.sleep(0.01)
        websocket.close()
        await connection_task

        # Verify cleanup
        assert "test-connection" not in handler.active_connections
        assert "test-connection" not in handler.connections
        assert "test-connection" not in handler.connection_sessions
        assert "test-session" not in handler.session_connections
        mock_dependencies['pty_manager'].close_session.assert_called_with("test-session")

    def test_get_connection_stats(self, handler):
        """Test connection statistics."""
        # Add some mock connections and sessions
        handler.active_connections.add("conn1")
        handler.active_connections.add("conn2")
        handler.session_connections["session1"] = "conn1"
        handler.session_connections["session2"] = "conn2"

        stats = handler.get_connection_stats()

        assert stats["active_connections"] == 2
        assert stats["active_sessions"] == 2
        assert "conn1" in stats["connections"]
        assert "conn2" in stats["connections"]
        assert "session1" in stats["sessions"]
        assert "session2" in stats["sessions"]

    @pytest.mark.asyncio
    async def test_output_callback_integration(self, handler, mock_dependencies):
        """Test output callback integration with PTY manager."""
        websocket = MockWebSocket()

        # Mock session creation to capture the output callback
        captured_callback = None

        def mock_set_output_callback(session_id, callback):
            nonlocal captured_callback
            captured_callback = callback

        mock_dependencies['pty_manager'].set_output_callback = mock_set_output_callback
        mock_dependencies['pty_manager'].create_session.return_value = "test-session"

        websocket.add_received_message({
            "type": "create_session"
        })

        connection_task = asyncio.create_task(
            handler.handle_connection(websocket, "test-connection")
        )

        await asyncio.sleep(0.01)

        # Simulate output from PTY
        if captured_callback:
            captured_callback("test output data")
            await asyncio.sleep(0.01)  # Allow callback to process

        websocket.close()
        await connection_task

        # Verify output was sent to WebSocket
        messages = websocket.get_sent_messages()
        output_msg = next(
            (msg for msg in messages if msg["type"] == "output"), None
        )
        assert output_msg is not None
        assert output_msg["data"] == "test output data"
        assert output_msg["session_id"] == "test-session"


class TestWebSocketIntegration:
    """Integration tests for WebSocket terminal functionality."""

    @pytest.mark.asyncio
    async def test_full_session_workflow(self, mock_dependencies):
        """Test complete session workflow from creation to closure."""
        handler = TerminalWebSocketHandler()
        await handler.start()

        try:
            websocket = MockWebSocket()

            # Mock PTY responses
            mock_dependencies['pty_manager'].create_session.return_value = "session-123"
            mock_dependencies['pty_manager'].write_to_session.return_value = True
            mock_dependencies['pty_manager'].resize_session.return_value = True
            mock_dependencies['pty_manager'].close_session.return_value = True

            # Simulate full workflow
            messages = [
                {"type": "create_session", "working_dir": "/tmp"},
                {"type": "input", "data": "echo hello\n"},
                {"type": "resize", "rows": 50, "cols": 120},
                {"type": "input", "data": "ls -la\n"},
                {"type": "close_session"}
            ]

            for msg in messages:
                websocket.add_received_message(msg)

            # Run connection
            connection_task = asyncio.create_task(
                handler.handle_connection(websocket, "test-conn")
            )

            await asyncio.sleep(0.05)  # Allow all messages to process
            websocket.close()
            await connection_task

            # Verify all operations were called
            mock_dependencies['pty_manager'].create_session.assert_called_once()
            assert mock_dependencies['pty_manager'].write_to_session.call_count == 2
            mock_dependencies['pty_manager'].resize_session.assert_called_once()
            mock_dependencies['pty_manager'].close_session.assert_called_once()

            # Verify response messages
            sent_messages = websocket.get_sent_messages()
            message_types = [msg["type"] for msg in sent_messages]

            assert "connection_established" in message_types
            assert "session_created" in message_types
            assert "session_closed" in message_types

        finally:
            await handler.stop()

    @pytest.mark.asyncio
    async def test_multiple_concurrent_connections(self, mock_dependencies):
        """Test handling multiple concurrent WebSocket connections."""
        handler = TerminalWebSocketHandler()
        await handler.start()

        try:
            websockets = [MockWebSocket() for _ in range(3)]

            # Mock different session IDs for each connection
            mock_dependencies['pty_manager'].create_session.side_effect = [
                f"session-{i}" for i in range(3)
            ]
            mock_dependencies['pty_manager'].write_to_session.return_value = True

            # Start connections
            connection_tasks = []
            for i, ws in enumerate(websockets):
                ws.add_received_message({"type": "create_session"})
                ws.add_received_message({"type": "input", "data": f"echo {i}\n"})

                task = asyncio.create_task(
                    handler.handle_connection(ws, f"conn-{i}")
                )
                connection_tasks.append(task)

            await asyncio.sleep(0.05)

            # Verify multiple sessions were created
            assert len(handler.active_connections) == 3
            assert len(handler.session_connections) == 3

            # Close all connections
            for ws in websockets:
                ws.close()

            await asyncio.gather(*connection_tasks)

            # Verify cleanup
            assert len(handler.active_connections) == 0
            assert len(handler.session_connections) == 0

        finally:
            await handler.stop()

    @pytest.mark.asyncio
    async def test_error_recovery(self, mock_dependencies):
        """Test error handling and recovery."""
        handler = TerminalWebSocketHandler()
        await handler.start()

        try:
            websocket = MockWebSocket()

            # Simulate various error conditions
            mock_dependencies['pty_manager'].create_session.side_effect = [
                Exception("First failure"),  # First attempt fails
                "recovery-session"  # Second attempt succeeds
            ]

            # Send two create session requests
            websocket.add_received_message({"type": "create_session"})
            websocket.add_received_message({"type": "create_session"})

            connection_task = asyncio.create_task(
                handler.handle_connection(websocket, "test-conn")
            )

            await asyncio.sleep(0.05)
            websocket.close()
            await connection_task

            # Verify error handling
            sent_messages = websocket.get_sent_messages()
            error_msgs = [msg for msg in sent_messages if msg["type"] == "error"]
            success_msgs = [msg for msg in sent_messages if msg["type"] == "session_created"]

            assert len(error_msgs) >= 1  # Should have error from first failure
            assert len(success_msgs) >= 1  # Should have success from recovery

        finally:
            await handler.stop()


@pytest.mark.performance
class TestWebSocketPerformance:
    """Performance tests for WebSocket terminal functionality."""

    @pytest.mark.asyncio
    async def test_connection_throughput(self, mock_dependencies):
        """Test WebSocket connection establishment throughput."""
        handler = TerminalWebSocketHandler()
        await handler.start()

        try:
            import time

            # Create many connections quickly
            num_connections = 50
            start_time = time.time()

            websockets = []
            tasks = []

            mock_dependencies['pty_manager'].create_session.side_effect = [
                f"session-{i}" for i in range(num_connections)
            ]

            for i in range(num_connections):
                ws = MockWebSocket()
                ws.add_received_message({"type": "create_session"})
                websockets.append(ws)

                task = asyncio.create_task(
                    handler.handle_connection(ws, f"perf-conn-{i}")
                )
                tasks.append(task)

            # Wait for all connections to establish
            await asyncio.sleep(0.1)

            establishment_time = time.time() - start_time

            # Verify all connections were established
            assert len(handler.active_connections) == num_connections
            assert len(handler.session_connections) == num_connections

            # Performance assertion - should establish 50 connections in under 1 second
            assert establishment_time < 1.0, f"Connection establishment took {establishment_time}s"

            # Cleanup
            for ws in websockets:
                ws.close()
            await asyncio.gather(*tasks, return_exceptions=True)

        finally:
            await handler.stop()

    @pytest.mark.asyncio
    async def test_message_processing_performance(self, mock_dependencies):
        """Test message processing throughput."""
        handler = TerminalWebSocketHandler()
        await handler.start()

        try:
            websocket = MockWebSocket()

            mock_dependencies['pty_manager'].create_session.return_value = "perf-session"
            mock_dependencies['pty_manager'].write_to_session.return_value = True

            # Add session creation first
            websocket.add_received_message({"type": "create_session"})

            # Add many input messages
            num_messages = 100
            for i in range(num_messages):
                websocket.add_received_message({
                    "type": "input",
                    "data": f"echo message-{i}\n"
                })

            import time
            start_time = time.time()

            connection_task = asyncio.create_task(
                handler.handle_connection(websocket, "perf-conn")
            )

            await asyncio.sleep(0.5)  # Allow processing time
            processing_time = time.time() - start_time

            websocket.close()
            await connection_task

            # Verify all messages were processed
            assert mock_dependencies['pty_manager'].write_to_session.call_count == num_messages

            # Performance assertion - should process 100 messages in under 1 second
            throughput = num_messages / processing_time
            assert throughput > 50, f"Message throughput {throughput} msg/s too low"

        finally:
            await handler.stop()