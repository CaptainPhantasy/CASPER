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
        self.security.audit_callback = self._on_security_event

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
                    if session_id in self.sessions:
                        await self.sessions[session_id].send_error(
                            "invalid_json", "Invalid JSON message"
                        )
                except WebSocketDisconnect:
                    logger.info(f"WebSocket disconnected: {session_id}")
                    break

        except Exception as e:
            logger.error(f"WebSocket connection error: {e}")
        finally:
            if session_id:
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

            # Send welcome banner with CASPER logo
            await self._send_welcome_banner(session)

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

    async def _handle_command(self, session: TerminalSession, message: Dict[str, Any]):
        """Handle command execution request."""
        command = message.get("command", "").strip()
        if not command:
            return

        # Validate command security
        try:
            await self.security.validate_command(
                command, session.session_id, session.user_id
            )
        except SecurityViolation as e:
            # Security violation already logged by middleware
            raise e

        # Add to command history
        session.command_history.append(command)
        if len(session.command_history) > 1000:  # Limit history size
            session.command_history = session.command_history[-1000:]

        # Execute command in PTY
        if session.pty_session_id:
            command_with_newline = command + "\n"
            success = await self.pty_manager.write_to_session(
                session.pty_session_id, command_with_newline
            )

            if not success:
                await session.send_error("execution_error", "Failed to execute command")
        else:
            await session.send_error("no_pty", "No PTY session available")

    async def _handle_input(self, session: TerminalSession, message: Dict[str, Any]):
        """Handle raw terminal input."""
        data = message.get("data", "")
        if not data:
            return

        session.update_activity()

        if session.pty_session_id:
            await self.pty_manager.write_to_session(session.pty_session_id, data)

    async def _handle_resize(self, session: TerminalSession, message: Dict[str, Any]):
        """Handle terminal resize request."""
        rows = message.get("rows", 24)
        cols = message.get("cols", 80)

        if session.pty_session_id:
            success = await self.pty_manager.resize_session(
                session.pty_session_id, rows, cols
            )
            if success:
                await session.send_message("resized", {"rows": rows, "cols": cols})

    async def _handle_get_history(self, session: TerminalSession):
        """Send command history to client."""
        await session.send_message(
            "history",
            {
                "commands": session.command_history[-100:],  # Last 100 commands
                "total_count": len(session.command_history),
            },
        )

    async def _handle_security_status(self, session: TerminalSession):
        """Send security status information."""
        audit_summary = self.security.get_audit_summary(hours=1)  # Last hour
        session_audit = [
            event
            for event in self.security.audit_log
            if event.session_id == session.session_id
        ]

        await session.send_message(
            "security_status",
            {
                "session_events": len(session_audit),
                "blocked_commands": len([e for e in session_audit if not e.allowed]),
                "risk_summary": audit_summary.get("risk_levels", {}),
                "sandbox_active": session.session_id in self.security.session_contexts,
            },
        )

    async def _handle_casper_command(
        self, session: TerminalSession, message: Dict[str, Any]
    ):
        """Handle CASPER CLI command execution."""
        command = message.get("command", "")
        args = message.get("args", [])

        # Validate command through security middleware
        if not self.command_proxy.is_valid_command(command):
            await session.send_error(
                "invalid_casper_command", f"Unknown CASPER command: {command}"
            )
            return

        try:
            # Execute command through proxy
            result = await self.command_proxy.execute_casper_command(command, args)

            await session.send_message(
                "casper_command_result", {"command": command, "result": result}
            )

        except Exception as e:
            logger.error(f"Error executing CASPER command '{command}': {e}")
            await session.send_error(
                "casper_command_error", f"Command execution failed: {str(e)}"
            )

    async def _authenticate_token(self, token: str) -> str:
        """
        Authenticate JWT token and return user ID.

        Args:
            token: JWT token string

        Returns:
            str: User ID from token

        Raises:
            Exception: If token is invalid
        """
        try:
            payload = jwt.decode(token, self.jwt_secret, algorithms=["HS256"])
            user_id = payload.get("user_id")
            if not user_id:
                raise ValueError("No user_id in token")
            return user_id
        except jwt.InvalidTokenError as e:
            raise Exception(f"Invalid JWT token: {e}")

    def _on_security_event(self, event):
        """Handle security audit events."""
        # Broadcast security events to relevant sessions
        for session in self.sessions.values():
            if session.session_id == event.session_id and session.is_active:
                asyncio.create_task(
                    session.send_message(
                        "security_event",
                        {
                            "event_type": event.event_type,
                            "risk_level": event.risk_level.value,
                            "allowed": event.allowed,
                            "reason": event.reason,
                        },
                    )
                )

    async def handle_websocket_disconnect(self, session_id: str):
        """Handle WebSocket disconnection."""
        await self.disconnect(session_id)

    async def broadcast_message(
        self,
        message_type: str,
        data: Dict[str, Any],
        exclude_session: Optional[str] = None,
    ):
        """Broadcast message to all active sessions."""
        for session_id, session in list(self.sessions.items()):
            if session_id != exclude_session and session.is_active:
                try:
                    await session.send_message(message_type, data)
                except Exception:
                    # Remove inactive session
                    await self.disconnect(session_id)

    def get_active_sessions(self) -> List[Dict[str, Any]]:
        """Get information about active sessions."""
        sessions_info = []
        for session in self.sessions.values():
            if session.is_active:
                sessions_info.append(
                    {
                        "session_id": session.session_id,
                        "user_id": session.user_id,
                        "created_at": session.created_at.isoformat(),
                        "last_activity": session.last_activity.isoformat(),
                        "command_count": len(session.command_history),
                        "has_pty": session.pty_session_id is not None,
                    }
                )
        return sessions_info

    async def cleanup_inactive_sessions(self, timeout_minutes: int = 30):
        """Clean up inactive sessions."""
        cutoff_time = datetime.now().timestamp() - (timeout_minutes * 60)
        inactive_sessions = []

        for session_id, session in self.sessions.items():
            if session.last_activity.timestamp() < cutoff_time:
                inactive_sessions.append(session_id)

        for session_id in inactive_sessions:
            logger.info(f"Cleaning up inactive session {session_id}")
            await self.disconnect(session_id)

        return len(inactive_sessions)

    def get_connection_stats(self) -> Dict[str, Any]:
        """Get statistics about active connections and sessions."""
        return {
            "active_connections": len(self.active_connections),
            "active_sessions": len(self.sessions),
            "sessions": list(self.sessions.keys()),
            "security_events": len(self.security.audit_log),
            "sandboxed_sessions": len(self.security.session_contexts),
        }

    async def _send_welcome_banner(self, session: "TerminalSession"):
        """Send the CASPER welcome banner to a new terminal session."""
        # Clean CASPER ASCII logo - no framing, no additional text
        logo_lines = [
            r"________/\\\\\\\\_____/\\\\\\\\\________/\\\\\\\\\\\____/\\\\\\\\\\\\\____/\\\\\\\\\\\\\\\____/\\\\\\\\\_____",
            r" _____/\\\////////____/\\\\\\\\\\\\\____/\\\/////////\\\_\/\\\/////////\\\_\/\\\///////////___/\\\///////\\\___",
            r"  ___/\\\/____________/\\\/////////\\\__\//\\\______\///__\/\\\\_______\/\\\_\/\\\_____________\/\\\_____\/\\\___",
            r"   __/\\\_____________\/\\\___\\\___\\\___\////\\\_________\/\\\\\\\\\\\\\/__\/\\\\\\\\\\\_____\/\\\\\\\\\\\/____",
            r"    _\/\\\_____________\/\\\\\\\\\\\\\\\______\////\\\______\/\\\/////////____\/\\\///////______\/\\\//////\\\____",
            r"     _\//\\\____________\/\\\\\\\\\\\\\\\_________\////\\\___\/\\\_____________\/\\\_____________\/\\\____\//\\\___",
            r"      __\///\\\__________\/\\\\\\\\\\\\\\\__/\\\______\//\\\__\/\\\_____________\/\\\_____________\/\\\_____\//\\\__",
            r"       ____\////\\\\\\\\\_\/\\\\\\\\\\\\\\\_\///\\\\\\\\\\\/___\/\\\_____________\/\\\\\\\\\\\\\\\_\/\\\______\//\\\_",
            r"        _______\/////////__\//__//___//__//____\///////////_____\///______________\///////////////__\///________\///__",
        ]

        # Send each line of the logo as terminal output
        try:
            # Send a newline first
            await session.send_message("output", {"data": "\n"})

            # Send each logo line
            for line in logo_lines:
                await session.send_message("output", {"data": line + "\n"})

            # Send a final newline
            await session.send_message("output", {"data": "\n"})

        except Exception as e:
            logger.error(
                f"Failed to send welcome banner to session {session.session_id}: {e}"
            )
