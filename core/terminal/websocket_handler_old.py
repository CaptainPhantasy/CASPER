"""
WebSocket Security Handler for CASPER Terminal Infrastructure.
Provides secure WebSocket communication with authentication and command validation.
"""

import asyncio
import json
import logging
from datetime import datetime, timedelta
from typing import Dict, Optional, Any, Callable, List, Set
from uuid import uuid4, UUID
import jwt
from fastapi import WebSocket, WebSocketDisconnect
from pathlib import Path

from .pty_manager import PTYManager
from .command_proxy import CommandProxy
from .security import SecurityMiddleware, SecurityViolation, CommandRisk
from core.security_config import JWT_SECRET

logger = logging.getLogger(__name__)


class TerminalSession:
    """Represents a secure terminal session with WebSocket connection."""

    def __init__(
        self, session_id: str, websocket: WebSocket, user_id: Optional[str] = None
    ):
        self.session_id = session_id
        self.websocket = websocket
        self.user_id = user_id
        self.pty_session_id: Optional[str] = None
        self.created_at = datetime.now()
        self.last_activity = datetime.now()
        self.is_active = True
        self.command_history: List[str] = []

    def update_activity(self):
        """Update last activity timestamp."""
        self.last_activity = datetime.now()

    async def send_message(self, message_type: str, data: Dict[str, Any]):
        """Send a message to the WebSocket client."""
        try:
            message = {
                "type": message_type,
                "timestamp": datetime.now().isoformat(),
                "session_id": self.session_id,
                **data,
            }
            await self.websocket.send_json(message)
        except Exception as e:
            logger.error(f"Failed to send message to session {self.session_id}: {e}")
            self.is_active = False

    async def send_error(
        self, error_type: str, message: str, details: Optional[Dict] = None
    ):
        """Send an error message to the client."""
        await self.send_message(
            "error",
            {"error_type": error_type, "message": message, "details": details or {}},
        )


class TerminalWebSocketHandler:
    """Handles secure WebSocket connections for terminal functionality."""

    def __init__(self, jwt_secret: Optional[str] = None):
        self.pty_manager = PTYManager()
        self.command_proxy = CommandProxy()
        self.security = SecurityMiddleware()
        self.jwt_secret = jwt_secret or JWT_SECRET
        self.sessions: Dict[str, TerminalSession] = {}
        self.active_connections: List[WebSocket] = []

        # Register security audit callback
        # self.security.audit_callback = self._on_security_event  # Disabled for now

    async def start(self):
        """Start the terminal handler and its dependencies."""
        await self.pty_manager.start()
        await self.command_proxy.initialize()
        logger.info("Terminal WebSocket Handler started")

    async def stop(self):
        """Stop the terminal handler and cleanup connections."""
        # Close all active sessions
        for session_id in list(self.sessions.keys()):
            await self.disconnect(session_id)

        await self.pty_manager.stop()
        await self.command_proxy.shutdown()
        logger.info("Terminal WebSocket Handler stopped")

    async def handle_connection(
        self, websocket: WebSocket, token: Optional[str] = None
    ) -> str:
        """
        Handle a new secure WebSocket connection.

        Args:
            websocket: WebSocket connection
            token: Optional JWT token for authentication

        Returns:
            str: Session ID

        Raises:
            Exception: If authentication fails
        """
        try:
            session_id = await self.connect(websocket, token)

            # Message handling loop
            while True:
                try:
                    data = await websocket.receive_json()
                    await self.handle_message(session_id, data)
                except json.JSONDecodeError:
                    await self.sessions[session_id].send_error(
                        "invalid_json", "Invalid JSON message"
                    )
                except WebSocketDisconnect:
                    logger.info(f"WebSocket disconnected: {session_id}")
                    break

        except Exception as e:
            logger.error(f"WebSocket connection error: {e}")
        finally:
            await self.disconnect(session_id)

        return session_id

    async def connect(self, websocket: WebSocket, token: Optional[str] = None) -> str:
        """
        Establish a secure WebSocket connection and create terminal session.
        """
        await websocket.accept()
        self.active_connections.append(websocket)

        # Authenticate user if token provided
        user_id = None
        if token:
            try:
                user_id = await self._authenticate_token(token)
            except Exception as e:
                await websocket.send_json(
                    {
                        "type": "auth_error",
                        "message": "Authentication failed",
                        "details": str(e),
                    }
                )
                await websocket.close()
                raise

        # Create terminal session
        session_id = str(uuid4())
        session = TerminalSession(session_id, websocket, user_id)
        self.sessions[session_id] = session

        logger.info(
            f"Created terminal session {session_id} for user {user_id or 'anonymous'}"
        )

        # Send connection confirmation
        await session.send_message(
            "connection",
            {
                "message": "Connected to CASPER Terminal",
                "user_id": user_id,
                "features": {
                    "security_enabled": True,
                    "audit_logging": True,
                    "command_validation": True,
                    "process_sandboxing": True,
                },
            },
        )

        # Create PTY session
        try:
            # Create sandbox for this session
            sandbox_context = await self.security.create_sandbox(session_id)

            # Create PTY with sandbox environment
            pty_session_id = await self.pty_manager.create_session(
                working_dir=sandbox_context["sandbox_dir"],
                env=sandbox_context["env_vars"],
            )
            session.pty_session_id = pty_session_id

            # Set up output callback
            self.pty_manager.set_output_callback(
                pty_session_id,
                lambda data: asyncio.create_task(
                    session.send_message("output", {"data": data})
                ),
            )

            await session.send_message(
                "pty_ready", {"pty_session_id": pty_session_id, "sandbox_enabled": True}
            )

        except Exception as e:
            logger.error(f"Failed to create PTY session for {session_id}: {e}")
            await session.send_error(
                "pty_error", "Failed to create terminal session", {"error": str(e)}
            )

        return session_id

    async def disconnect(self, session_id: str):
        """Disconnect and cleanup terminal session."""
        session = self.sessions.get(session_id)
        if not session:
            return

        try:
            # Close PTY session
            if session.pty_session_id:
                await self.pty_manager.close_session(session.pty_session_id)

            # Cleanup sandbox
            await self.security.cleanup_sandbox(session_id)

            # Remove WebSocket connection
            if session.websocket in self.active_connections:
                self.active_connections.remove(session.websocket)

            # Remove session
            del self.sessions[session_id]

            logger.info(f"Disconnected terminal session {session_id}")

        except Exception as e:
            logger.error(f"Error disconnecting session {session_id}: {e}")

    async def handle_message(self, session_id: str, message: Dict[str, Any]):
        """Handle incoming WebSocket message."""
        session = self.sessions.get(session_id)
        if not session or not session.is_active:
            return

        session.update_activity()
        message_type = message.get("type", "unknown")

        try:
            if message_type == "command":
                await self._handle_command(session, message)
            elif message_type == "input":
                await self._handle_input(session, message)
            elif message_type == "resize":
                await self._handle_resize(session, message)
            elif message_type == "ping":
                await session.send_message("pong", {})
            elif message_type == "get_history":
                await self._handle_get_history(session)
            elif message_type == "security_status":
                await self._handle_security_status(session)
            elif message_type == "casper_command":
                await self._handle_casper_command(session, message)
            else:
                await session.send_error(
                    "invalid_message", f"Unknown message type: {message_type}"
                )

        except SecurityViolation as e:
            await session.send_error(
                "security_violation",
                str(e),
                {"command": e.command, "risk_level": e.risk_level.value},
            )
        except Exception as e:
            logger.error(f"Error handling message in session {session_id}: {e}")
            await session.send_error(
                "handler_error", "Internal error processing message", {"error": str(e)}
            )

    async def _handle_create_session(
        self, connection_id: str, websocket: WebSocket, message: Dict[str, Any]
    ):
        """Handle session creation request."""
        working_dir = message.get("working_dir")
        env = message.get("env", {})

        try:
            # Create new PTY session
            session_id = await self.pty_manager.create_session(working_dir, env)

            # Link connection to session
            self.session_connections[session_id] = connection_id
            self.connection_sessions[connection_id] = session_id

            # Set up output callback to send data to WebSocket
            def output_callback(data: str):
                asyncio.create_task(self._send_output(websocket, session_id, data))

            self.pty_manager.set_output_callback(session_id, output_callback)

            # Send success response
            await self._send_message(
                websocket,
                {
                    "type": "session_created",
                    "session_id": session_id,
                    "working_dir": working_dir,
                    "timestamp": datetime.now().isoformat(),
                },
            )

            logger.info(
                f"Created terminal session {session_id} for connection {connection_id}"
            )

        except Exception as e:
            logger.error(f"Failed to create session for {connection_id}: {e}")
            await self._send_error(websocket, f"Failed to create session: {str(e)}")

    async def _handle_input(
        self, connection_id: str, websocket: WebSocket, message: Dict[str, Any]
    ):
        """Handle terminal input from client."""
        session_id = self.connection_sessions.get(connection_id)
        if not session_id:
            await self._send_error(websocket, "No active session")
            return

        data = message.get("data", "")

        # Apply security filtering
        if not await self.security.validate_input(data, session_id):
            await self._send_error(websocket, "Input blocked by security policy")
            return

        # Send input to PTY
        success = await self.pty_manager.write_to_session(session_id, data)
        if not success:
            await self._send_error(websocket, "Failed to send input to session")

    async def _handle_resize(
        self, connection_id: str, websocket: WebSocket, message: Dict[str, Any]
    ):
        """Handle terminal resize request."""
        session_id = self.connection_sessions.get(connection_id)
        if not session_id:
            await self._send_error(websocket, "No active session")
            return

        rows = message.get("rows", 24)
        cols = message.get("cols", 80)

        success = await self.pty_manager.resize_session(session_id, rows, cols)
        if not success:
            await self._send_error(websocket, "Failed to resize session")

    async def _handle_close_session(
        self, connection_id: str, websocket: WebSocket, message: Dict[str, Any]
    ):
        """Handle session close request."""
        session_id = self.connection_sessions.get(connection_id)
        if not session_id:
            await self._send_error(websocket, "No active session")
            return

        success = await self.pty_manager.close_session(session_id)
        if success:
            # Clean up connection mappings
            del self.session_connections[session_id]
            del self.connection_sessions[connection_id]

            await self._send_message(
                websocket,
                {
                    "type": "session_closed",
                    "session_id": session_id,
                    "timestamp": datetime.now().isoformat(),
                },
            )

    async def _handle_casper_command(
        self, connection_id: str, websocket: WebSocket, message: Dict[str, Any]
    ):
        """Handle CASPER CLI command execution."""
        command = message.get("command", "")
        args = message.get("args", [])

        # Validate command through security middleware
        if not await self.security.validate_casper_command(command, args):
            await self._send_error(websocket, "Command blocked by security policy")
            return

        try:
            # Execute command through proxy
            result = await self.command_proxy.execute_casper_command(command, args)

            await self._send_message(
                websocket,
                {
                    "type": "casper_command_result",
                    "command": command,
                    "result": result,
                    "timestamp": datetime.now().isoformat(),
                },
            )

        except Exception as e:
            logger.error(f"Error executing CASPER command '{command}': {e}")
            await self._send_error(websocket, f"Command execution failed: {str(e)}")

    async def _send_output(self, websocket: WebSocket, session_id: str, data: str):
        """Send terminal output to WebSocket client."""
        try:
            await self._send_message(
                websocket,
                {
                    "type": "output",
                    "session_id": session_id,
                    "data": data,
                    "timestamp": datetime.now().isoformat(),
                },
            )
        except Exception as e:
            logger.error(f"Failed to send output for session {session_id}: {e}")

    async def _send_message(self, websocket: WebSocket, message: Dict[str, Any]):
        """Send a message to WebSocket client."""
        try:
            await websocket.send_text(json.dumps(message))
        except Exception as e:
            logger.error(f"Failed to send WebSocket message: {e}")

    async def _send_error(self, websocket: WebSocket, error_message: str):
        """Send error message to WebSocket client."""
        await self._send_message(
            websocket,
            {
                "type": "error",
                "message": error_message,
                "timestamp": datetime.now().isoformat(),
            },
        )

    async def _cleanup_connection(self, connection_id: str):
        """Clean up a connection and its associated session."""
        try:
            # Close associated session if exists
            session_id = self.connection_sessions.get(connection_id)
            if session_id:
                await self.pty_manager.close_session(session_id)
                if session_id in self.session_connections:
                    del self.session_connections[session_id]
                if connection_id in self.connection_sessions:
                    del self.connection_sessions[connection_id]

            # Remove connection
            if connection_id in self.connections:
                del self.connections[connection_id]

            if connection_id in self.active_connections:
                self.active_connections.remove(connection_id)

            logger.info(f"Cleaned up terminal connection: {connection_id}")

        except Exception as e:
            logger.error(f"Error cleaning up connection {connection_id}: {e}")

    def get_connection_stats(self) -> Dict[str, Any]:
        """Get statistics about active connections and sessions."""
        return {
            "active_connections": len(self.active_connections),
            "active_sessions": len(self.session_connections),
            "connections": list(self.active_connections),
            "sessions": list(self.session_connections.keys()),
        }
