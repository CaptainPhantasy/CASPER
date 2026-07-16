"""Current-contract tests for the secure terminal WebSocket handler."""

from unittest.mock import AsyncMock, Mock, patch

import pytest
from fastapi import WebSocketDisconnect

from core.terminal.websocket_handler import TerminalWebSocketHandler


class FakeWebSocket:
    def __init__(self, incoming=None):
        self.accepted = False
        self.closed = False
        self.incoming = list(incoming or [])
        self.sent = []

    async def accept(self):
        self.accepted = True

    async def send_json(self, data):
        self.sent.append(data)

    async def receive_json(self):
        if self.incoming:
            return self.incoming.pop(0)
        raise WebSocketDisconnect()

    async def close(self):
        self.closed = True


@pytest.fixture
def dependencies():
    with (
        patch("core.terminal.websocket_handler.PTYManager") as pty_class,
        patch("core.terminal.websocket_handler.CommandProxy") as proxy_class,
        patch("core.terminal.websocket_handler.SecurityMiddleware") as security_class,
    ):
        pty = Mock()
        pty.start = AsyncMock()
        pty.stop = AsyncMock()
        pty.create_session = AsyncMock(return_value="pty-1")
        pty.close_session = AsyncMock(return_value=True)
        pty.write_to_session = AsyncMock(return_value=True)
        pty.resize_session = AsyncMock(return_value=True)
        pty_class.return_value = pty

        proxy = Mock()
        proxy.initialize = AsyncMock()
        proxy.shutdown = AsyncMock()
        proxy.is_valid_command.return_value = True
        proxy.execute_casper_command = AsyncMock(return_value={"success": True})
        proxy_class.return_value = proxy

        security = Mock()
        security.create_sandbox = AsyncMock(
            return_value={"sandbox_dir": "/tmp", "env_vars": {}}
        )
        security.cleanup_sandbox = AsyncMock()
        security.validate_command = AsyncMock()
        security.audit_log = []
        security.session_contexts = {}
        security_class.return_value = security

        yield pty, proxy, security


@pytest.mark.asyncio
async def test_lifecycle_starts_and_stops_dependencies(dependencies):
    pty, proxy, _ = dependencies
    handler = TerminalWebSocketHandler()

    await handler.start()
    await handler.stop()

    pty.start.assert_awaited_once()
    proxy.initialize.assert_awaited_once()
    pty.stop.assert_awaited_once()
    proxy.shutdown.assert_awaited_once()


@pytest.mark.asyncio
async def test_connect_creates_secure_pty_session(dependencies):
    pty, _, security = dependencies
    handler = TerminalWebSocketHandler()
    websocket = FakeWebSocket()

    session_id = await handler.connect(websocket)

    assert websocket.accepted is True
    assert session_id in handler.sessions
    assert handler.sessions[session_id].pty_session_id == "pty-1"
    security.create_sandbox.assert_awaited_once_with(session_id)
    pty.create_session.assert_awaited_once_with(working_dir="/tmp", env={})
    pty.set_output_callback.assert_called_once()
    assert any(message["type"] == "connection" for message in websocket.sent)
    assert any(message["type"] == "pty_ready" for message in websocket.sent)


@pytest.mark.asyncio
async def test_messages_reach_security_pty_and_casper(dependencies):
    pty, proxy, security = dependencies
    handler = TerminalWebSocketHandler()
    websocket = FakeWebSocket()
    session_id = await handler.connect(websocket)

    await handler.handle_message(session_id, {"type": "command", "command": "pwd"})
    await handler.handle_message(session_id, {"type": "input", "data": "x"})
    await handler.handle_message(session_id, {"type": "resize", "rows": 40, "cols": 120})
    await handler.handle_message(
        session_id, {"type": "casper_command", "command": "status", "args": []}
    )

    security.validate_command.assert_awaited_once_with("pwd", session_id, None)
    assert pty.write_to_session.await_args_list[0].args == ("pty-1", "pwd\n")
    assert pty.write_to_session.await_args_list[1].args == ("pty-1", "x")
    pty.resize_session.assert_awaited_once_with("pty-1", 40, 120)
    proxy.execute_casper_command.assert_awaited_once_with("status", [])
    assert any(message["type"] == "casper_command_result" for message in websocket.sent)


@pytest.mark.asyncio
async def test_disconnect_cleans_all_session_state(dependencies):
    pty, _, security = dependencies
    handler = TerminalWebSocketHandler()
    websocket = FakeWebSocket()
    session_id = await handler.connect(websocket)

    await handler.disconnect(session_id)

    assert session_id not in handler.sessions
    assert websocket not in handler.active_connections
    pty.close_session.assert_awaited_once_with("pty-1")
    security.cleanup_sandbox.assert_awaited_once_with(session_id)


@pytest.mark.asyncio
async def test_failed_authentication_does_not_crash_cleanup(dependencies):
    handler = TerminalWebSocketHandler(jwt_secret="test-secret")
    websocket = FakeWebSocket()

    result = await handler.handle_connection(websocket, token="invalid-token")

    assert result == ""
    assert websocket.closed is True
    assert websocket.sent[0]["type"] == "auth_error"
