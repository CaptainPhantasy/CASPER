"""
WebSocket Integration for Streaming Orchestrator
Integrates the streaming orchestrator with the existing WebSocket handler
"""

import asyncio
import json
import logging
from typing import Dict, Any, Optional

from fastapi import WebSocket
from ..interfaces import CodingIntent, CodingAction, WSMessageType
from .streaming_orchestrator import get_streaming_orchestrator
from ..websocket_handler import TerminalWebSocketHandler

logger = logging.getLogger(__name__)


class StreamingWebSocketHandler:
    """Enhanced WebSocket handler with streaming capabilities"""

    def __init__(self, base_handler: TerminalWebSocketHandler):
        self.base_handler = base_handler
        self.streaming_orchestrator = get_streaming_orchestrator()

    async def handle_streaming_command(
        self, session_id: str, message: Dict[str, Any]
    ) -> None:
        """Handle streaming command execution request"""

        session = self.base_handler.sessions.get(session_id)
        if not session or not session.is_active:
            return

        try:
            # Parse the streaming request
            request_text = message.get("request", "")
            if not request_text:
                await session.send_error("invalid_request", "Empty request text")
                return

            # Create coding intent from natural language
            intent = await self._parse_coding_intent(request_text)

            # Prepare session context for streaming
            session_context = {
                "websocket": session.websocket,
                "session_id": session_id,
                "user_id": session.user_id,
                "working_directory": await self._get_working_directory(session),
                "project_context": await self._get_project_context(session),
            }

            # Send streaming start notification
            await session.send_message(
                "streaming_start",
                {
                    "intent": {
                        "action": intent.action.value,
                        "targets": intent.targets,
                        "scope": intent.scope,
                        "confidence": intent.confidence,
                    },
                    "message": "Starting streaming response...",
                },
            )

            # Stream the response
            chunk_count = 0
            async for chunk in self.streaming_orchestrator.stream_response(
                intent, session_context
            ):
                chunk_count += 1

                # Send chunk directly through WebSocket
                await session.websocket.send_json(
                    {
                        "type": "streaming_chunk",
                        "chunk_type": chunk.type,
                        "content": chunk.content,
                        "metadata": chunk.metadata,
                        "timestamp": chunk.timestamp.isoformat(),
                        "sequence": chunk.sequence_number,
                    }
                )

                # Update session activity
                session.update_activity()

            # Send streaming completion
            await session.send_message(
                "streaming_complete",
                {"chunks_sent": chunk_count, "message": "Streaming response completed"},
            )

        except Exception as e:
            logger.error(f"Streaming command error in session {session_id}: {e}")
            await session.send_error("streaming_error", f"Streaming failed: {str(e)}")

    async def _parse_coding_intent(self, request_text: str) -> CodingIntent:
        """Parse natural language request into coding intent"""

        # Simple intent parsing - in production, this would use NLP
        request_lower = request_text.lower()

        # Determine action
        action = CodingAction.IMPLEMENT  # Default
        if any(word in request_lower for word in ["fix", "debug", "solve"]):
            action = CodingAction.DEBUG
        elif any(word in request_lower for word in ["modify", "change", "update"]):
            action = CodingAction.MODIFY
        elif any(word in request_lower for word in ["test", "verify"]):
            action = CodingAction.TEST
        elif any(word in request_lower for word in ["explain", "understand"]):
            action = CodingAction.EXPLAIN
        elif any(word in request_lower for word in ["review", "audit"]):
            action = CodingAction.REVIEW
        elif any(word in request_lower for word in ["refactor", "restructure"]):
            action = CodingAction.REFACTOR
        elif any(word in request_lower for word in ["optimize", "improve"]):
            action = CodingAction.OPTIMIZE

        # Extract targets (files, functions, etc.)
        targets = []

        # Simple regex patterns for common targets
        import re

        # File extensions
        file_patterns = [
            r"\b\w+\.(py|js|ts|java|cpp|c|h|css|html|json|yaml|yml|md)\b",
            r"\b\w+/\w+\.(py|js|ts|java|cpp|c|h|css|html|json|yaml|yml|md)\b",
        ]

        for pattern in file_patterns:
            matches = re.findall(pattern, request_text, re.IGNORECASE)
            targets.extend(matches)

        # Function/class names
        function_patterns = [r"function\s+(\w+)", r"def\s+(\w+)", r"class\s+(\w+)"]

        for pattern in function_patterns:
            matches = re.findall(pattern, request_text, re.IGNORECASE)
            targets.extend(matches)

        if not targets:
            targets = ["unknown"]

        # Determine scope
        scope = "file"  # Default
        if any(word in request_lower for word in ["project", "codebase", "entire"]):
            scope = "project"
        elif any(word in request_lower for word in ["function", "method"]):
            scope = "function"
        elif any(word in request_lower for word in ["class"]):
            scope = "class"

        # Simple confidence scoring
        confidence = 0.8  # Default confidence
        if len(targets) > 1:
            confidence = 0.9
        if any(word in request_lower for word in ["please", "could", "might", "maybe"]):
            confidence = 0.7

        return CodingIntent(
            action=action,
            targets=targets,
            scope=scope,
            original_request=request_text,
            confidence=confidence,
            context_required=["project_structure", "dependencies"],
        )

    async def _get_working_directory(self, session) -> str:
        """Get the current working directory for the session"""
        try:
            if session.pty_session_id:
                # Try to get current directory from PTY
                # This is a simplified version
                return "/Volumes/Storage/Development/CASPER DEV"  # Default project root
        except Exception:
            pass

        return "/Volumes/Storage/Development/CASPER DEV"

    async def _get_project_context(self, session) -> Dict[str, Any]:
        """Get project context information"""
        return {
            "project_type": "python",
            "framework": "fastapi",
            "dependencies": ["fastapi", "uvicorn", "anthropic", "langchain"],
            "structure": {
                "backend": "core/",
                "frontend": "dashboard/",
                "tests": "tests/",
            },
        }

    async def handle_stream_cancel(
        self, session_id: str, message: Dict[str, Any]
    ) -> None:
        """Handle stream cancellation request"""

        stream_id = message.get("stream_id")
        if not stream_id:
            return

        session = self.base_handler.sessions.get(session_id)
        if not session:
            return

        try:
            success = await self.streaming_orchestrator.cancel_stream(stream_id)

            await session.send_message(
                "stream_cancelled",
                {
                    "stream_id": stream_id,
                    "success": success,
                    "message": "Stream cancellation requested",
                },
            )

        except Exception as e:
            logger.error(f"Stream cancellation error: {e}")
            await session.send_error(
                "cancel_error", f"Failed to cancel stream: {str(e)}"
            )

    async def get_streaming_status(self, session_id: str) -> Dict[str, Any]:
        """Get streaming status for session"""

        try:
            metrics = await self.streaming_orchestrator.get_stream_metrics()
            active_streams = self.streaming_orchestrator.get_active_stream_ids()

            return {
                "active_streams": len(active_streams),
                "stream_ids": active_streams,
                "metrics": metrics,
                "session_id": session_id,
            }

        except Exception as e:
            logger.error(f"Error getting streaming status: {e}")
            return {"error": str(e)}

    async def send_heartbeat_to_streams(self) -> None:
        """Send heartbeat to all active streams"""

        active_stream_ids = self.streaming_orchestrator.get_active_stream_ids()

        for stream_id in active_stream_ids:
            try:
                await self.streaming_orchestrator.send_heartbeat(stream_id)
            except Exception as e:
                logger.error(f"Failed to send heartbeat to stream {stream_id}: {e}")

    async def cleanup_old_streams(self, timeout_minutes: int = 30) -> int:
        """Cleanup old inactive streams"""

        try:
            return await self.streaming_orchestrator.cleanup_inactive_streams(
                timeout_minutes
            )
        except Exception as e:
            logger.error(f"Error cleaning up streams: {e}")
            return 0


# Enhanced message handler that includes streaming
async def enhanced_handle_message(
    handler: StreamingWebSocketHandler, session_id: str, message: Dict[str, Any]
):
    """Enhanced message handler with streaming support"""

    message_type = message.get("type", "unknown")

    # Handle streaming-specific messages
    if message_type == "streaming_request":
        await handler.handle_streaming_command(session_id, message)
    elif message_type == "stream_cancel":
        await handler.handle_stream_cancel(session_id, message)
    elif message_type == "streaming_status":
        status = await handler.get_streaming_status(session_id)
        session = handler.base_handler.sessions.get(session_id)
        if session:
            await session.send_message("streaming_status_response", status)
    else:
        # Delegate to base handler
        await handler.base_handler.handle_message(session_id, message)


# Integration helper function
def create_enhanced_websocket_handler(
    base_handler: TerminalWebSocketHandler,
) -> StreamingWebSocketHandler:
    """Create an enhanced WebSocket handler with streaming capabilities"""

    enhanced_handler = StreamingWebSocketHandler(base_handler)

    # Set up periodic cleanup
    async def periodic_cleanup():
        while True:
            try:
                await asyncio.sleep(300)  # Every 5 minutes
                await enhanced_handler.cleanup_old_streams(30)
                await enhanced_handler.send_heartbeat_to_streams()
            except Exception as e:
                logger.error(f"Periodic cleanup error: {e}")

    # Start cleanup task (should be done at application startup)
    asyncio.create_task(periodic_cleanup())

    return enhanced_handler


# Export for integration
__all__ = [
    "StreamingWebSocketHandler",
    "enhanced_handle_message",
    "create_enhanced_websocket_handler",
]
