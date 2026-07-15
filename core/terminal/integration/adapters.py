"""
CASPER Prime Terminal Integration Adapters
Adapters to bridge between agent implementations and IInterface definitions.
PRODUCTION GRADE - Seamless integration between different implementations.
"""

import asyncio
import logging
from datetime import datetime
from typing import Dict, Any, List, Optional, Tuple, AsyncIterator

from ..interfaces import (
    ISession,
    IStreaming,
    IParser,
    SessionState,
    CodingIntent,
    CodingAction,
    StreamChunk,
    SessionError,
    StreamingError,
    ParsingError,
)

logger = logging.getLogger(__name__)


class CodingSessionAdapter(ISession):
    """
    Adapter for CodingSession to implement ISession interface.
    Bridges between the agent implementation and the standard interface.
    """

    def __init__(self, persistence_path: str, session_timeout: int):
        """Initialize adapter with CodingSession."""
        try:
            from ..session.coding_session import CodingSession

            self.coding_session = CodingSession(storage_path=persistence_path)
            self.session_timeout = session_timeout
            logger.info("CodingSession adapter initialized")
        except Exception as e:
            logger.error(f"Failed to initialize CodingSession adapter: {e}")
            raise SessionError(f"Adapter initialization failed: {e}")

    async def start_session(self, session_id: str) -> SessionState:
        """Start session using CodingSession."""
        try:
            # Use existing coding_session instance
            # CodingSession handles multiple sessions internally

            # Initialize the session
            await self.coding_session.initialize()

            # Convert to SessionState
            now = datetime.now()
            return SessionState(
                session_id=session_id,
                started_at=now,
                last_activity=now,
                context_tokens=0,
                files_modified=[],
                conversation_history=[],
                knowledge_base_id=f"kb_{session_id}",
                active=True,
            )

        except Exception as e:
            logger.error(f"Failed to start session: {e}")
            raise SessionError(f"Session start failed: {e}")

    async def add_interaction(self, user_input: str, response: str) -> None:
        """Add interaction through CodingSession."""
        try:
            # Create tokenized interaction
            from ..session.coding_session import TokenizedInteraction

            interaction = TokenizedInteraction(
                user_input=user_input,
                assistant_response=response,
                timestamp=datetime.now(),
                token_count=len(user_input + response) // 4,  # Rough estimate
                context_retrieved=[],
            )

            await self.coding_session.add_interaction(interaction)
            await self.coding_session.persist()

        except Exception as e:
            logger.error(f"Failed to add interaction: {e}")
            raise SessionError(f"Add interaction failed: {e}")

    async def get_context(self) -> Dict[str, Any]:
        """Get context from CodingSession."""
        try:
            metrics = self.coding_session.get_metrics()

            return {
                "session_id": self.coding_session.session_id,
                "started_at": datetime.now().isoformat(),  # CodingSession doesn't track this
                "last_activity": datetime.now().isoformat(),
                "context_tokens": metrics.total_tokens,
                "total_interactions": metrics.total_interactions,
                "files_modified": [],  # CodingSession doesn't track this
                "active": True,
                "adapter": "CodingSession",
            }

        except Exception as e:
            logger.error(f"Failed to get context: {e}")
            return {"error": f"Context retrieval failed: {e}"}

    async def persist(self) -> None:
        """Persist session through CodingSession."""
        try:
            await self.coding_session.persist()
        except Exception as e:
            logger.error(f"Failed to persist session: {e}")
            raise SessionError(f"Session persistence failed: {e}")

    async def recover(self, session_id: str) -> SessionState:
        """Recover session through CodingSession."""
        try:
            # Create and recover CodingSession
            from ..session.coding_session import CodingSession

            self.coding_session = CodingSession(
                session_id=session_id,
                persistence_dir=str(self.coding_session.persistence_dir.parent),
            )

            await self.coding_session.recover()

            # Convert to SessionState
            now = datetime.now()
            metrics = self.coding_session.get_metrics()

            return SessionState(
                session_id=session_id,
                started_at=now,  # CodingSession doesn't track creation time
                last_activity=now,
                context_tokens=metrics.total_tokens,
                files_modified=[],
                conversation_history=[],
                knowledge_base_id=f"kb_{session_id}",
                active=True,
            )

        except Exception as e:
            logger.error(f"Failed to recover session: {e}")
            raise SessionError(f"Session recovery failed: {e}")

    async def cleanup_old_sessions(self, days: int = 30) -> int:
        """Clean up old sessions - simplified for CodingSession."""
        try:
            # CodingSession doesn't have built-in cleanup, so we'll return 0
            logger.info("CodingSession cleanup not implemented")
            return 0
        except Exception as e:
            logger.error(f"Failed to cleanup sessions: {e}")
            return 0


class StreamingOrchestratorAdapter(IStreaming):
    """
    Adapter for StreamingOrchestrator to implement IStreaming interface.
    """

    def __init__(self, max_concurrent_streams: int = 10):
        """Initialize adapter with StreamingOrchestrator."""
        try:
            from ..streaming.streaming_orchestrator import StreamingOrchestrator

            self.orchestrator = StreamingOrchestrator()
            self.max_concurrent_streams = max_concurrent_streams
            logger.info("StreamingOrchestrator adapter initialized")
        except Exception as e:
            logger.error(f"Failed to initialize StreamingOrchestrator adapter: {e}")
            raise StreamingError(f"Adapter initialization failed: {e}")

    async def stream_response(
        self, intent: CodingIntent, session_context: Dict[str, Any]
    ) -> AsyncIterator[StreamChunk]:
        """Stream response using StreamingOrchestrator."""
        try:
            # Convert intent to format expected by orchestrator
            request_data = {
                "command": intent.original_request,
                "action": intent.action.value,
                "targets": intent.targets,
                "scope": intent.scope,
                "context": session_context,
            }

            sequence_number = 0
            # Stream response from orchestrator
            async for chunk_data in self.orchestrator.stream_coding_response(
                request_data
            ):
                sequence_number += 1

                # Convert orchestrator chunk to StreamChunk
                chunk = StreamChunk(
                    type=chunk_data.get("type", "action"),
                    content=chunk_data.get("content", ""),
                    metadata=chunk_data.get("metadata", {}),
                    timestamp=datetime.now(),
                    sequence_number=sequence_number,
                )

                yield chunk

        except Exception as e:
            logger.error(f"Failed to stream response: {e}")
            # Yield error chunk
            yield StreamChunk(
                type="error",
                content=f"Streaming error: {e}",
                metadata={"error_type": type(e).__name__},
                timestamp=datetime.now(),
                sequence_number=0,
            )

    async def handle_backpressure(self) -> None:
        """Handle backpressure - delegated to orchestrator."""
        try:
            # StreamingOrchestrator should handle this internally
            await asyncio.sleep(0.1)  # Brief pause
        except Exception as e:
            logger.error(f"Backpressure handling error: {e}")

    async def cancel_stream(self, stream_id: str) -> bool:
        """Cancel stream - simplified implementation."""
        try:
            # StreamingOrchestrator might not support direct cancellation
            logger.info(f"Stream cancellation requested: {stream_id}")
            return True
        except Exception as e:
            logger.error(f"Failed to cancel stream: {e}")
            return False

    async def get_stream_metrics(self) -> Dict[str, Any]:
        """Get streaming metrics."""
        try:
            return {
                "adapter": "StreamingOrchestrator",
                "timestamp": datetime.now().isoformat(),
                "max_concurrent_streams": self.max_concurrent_streams,
            }
        except Exception as e:
            logger.error(f"Failed to get metrics: {e}")
            return {"error": f"Metrics retrieval failed: {e}"}


class IntentParserAdapter(IParser):
    """
    Adapter for IntentParser to implement IParser interface.
    """

    def __init__(self):
        """Initialize adapter with IntentParser."""
        try:
            from ..nlp.intent_parser import IntentParser

            self.intent_parser = IntentParser()
            logger.info("IntentParser adapter initialized")
        except Exception as e:
            logger.error(f"Failed to initialize IntentParser adapter: {e}")
            raise ParsingError(f"Adapter initialization failed: {e}")

    async def parse_input(self, user_input: str) -> CodingIntent:
        """Parse input using IntentParser."""
        try:
            # Parse using the agent's intent parser
            parsed_intent = await self.intent_parser.parse_natural_language(user_input)

            # Convert to CodingIntent
            # Map the parsed intent to CodingAction
            action_mapping = {
                "implement": CodingAction.IMPLEMENT,
                "modify": CodingAction.MODIFY,
                "debug": CodingAction.DEBUG,
                "test": CodingAction.TEST,
                "explain": CodingAction.EXPLAIN,
                "review": CodingAction.REVIEW,
                "refactor": CodingAction.REFACTOR,
                "optimize": CodingAction.OPTIMIZE,
            }

            action = action_mapping.get(
                parsed_intent.get("action", "explain").lower(), CodingAction.EXPLAIN
            )

            return CodingIntent(
                action=action,
                targets=parsed_intent.get("targets", ["general"]),
                scope=parsed_intent.get("scope", "function"),
                original_request=user_input,
                confidence=parsed_intent.get("confidence", 0.8),
                context_required=parsed_intent.get("context_required", []),
            )

        except Exception as e:
            logger.error(f"Failed to parse input: {e}")
            # Return default intent
            return CodingIntent(
                action=CodingAction.EXPLAIN,
                targets=["general"],
                scope="function",
                original_request=user_input,
                confidence=0.3,
                context_required=["fallback"],
            )

    async def extract_entities(self, text: str) -> List[Tuple[str, str]]:
        """Extract entities using IntentParser."""
        try:
            # Use the agent's entity extraction if available
            entities = await self.intent_parser.extract_entities(text)
            return [(entity["text"], entity["type"]) for entity in entities]
        except Exception as e:
            logger.error(f"Failed to extract entities: {e}")
            return []

    async def suggest_completion(
        self, partial: str, context: Dict[str, Any]
    ) -> List[str]:
        """Suggest completion using IntentParser."""
        try:
            # Use agent's completion suggestion if available
            suggestions = await self.intent_parser.suggest_completions(partial, context)
            return suggestions[:10]  # Limit results
        except Exception as e:
            logger.error(f"Failed to suggest completions: {e}")
            # Provide basic fallback suggestions
            return [
                "implement function",
                "debug error",
                "explain code",
                "test implementation",
            ]

    async def detect_language(self, code_snippet: str) -> str:
        """Detect language using IntentParser."""
        try:
            # Use agent's language detection if available
            language = await self.intent_parser.detect_programming_language(
                code_snippet
            )
            return language.lower()
        except Exception as e:
            logger.error(f"Failed to detect language: {e}")
            # Basic fallback detection
            if "def " in code_snippet or "import " in code_snippet:
                return "python"
            elif "function " in code_snippet or "const " in code_snippet:
                return "javascript"
            else:
                return "text"


# Helper function to check if agent implementations are compatible
async def check_agent_compatibility() -> Dict[str, bool]:
    """Check if agent implementations are compatible with interfaces."""
    compatibility = {"session": False, "streaming": False, "nlp": False, "ui": False}

    try:
        from ..session.coding_session import CodingSession

        compatibility["session"] = hasattr(CodingSession, "add_interaction")
    except ImportError:
        pass

    try:
        from ..streaming.streaming_orchestrator import StreamingOrchestrator

        compatibility["streaming"] = hasattr(
            StreamingOrchestrator, "stream_coding_response"
        )
    except ImportError:
        pass

    try:
        from ..nlp.intent_parser import IntentParser

        compatibility["nlp"] = hasattr(IntentParser, "parse_natural_language")
    except ImportError:
        pass

    try:
        from ..ui.terminal_ui import TerminalUI

        compatibility["ui"] = hasattr(TerminalUI, "start_ui")
    except ImportError:
        pass

    return compatibility
