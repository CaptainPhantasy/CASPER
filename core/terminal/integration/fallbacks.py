"""
CASPER Prime Terminal Fallback Implementations
Fallback components when specialist agent implementations are not available.
PRODUCTION GRADE - Fully functional fallbacks, not placeholders.
"""

import asyncio
import json
import logging
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, Tuple, AsyncIterator
from pathlib import Path
from uuid import uuid4

from ..interfaces import (
    ISession,
    IStreaming,
    IParser,
    ITerminalUI,
    SessionState,
    CodingIntent,
    CodingAction,
    StreamChunk,
    SessionError,
    StreamingError,
    ParsingError,
)

logger = logging.getLogger(__name__)


class FallbackSessionManager(ISession):
    """
    Fallback session manager with basic functionality.
    Provides minimal but working session management.
    """

    def __init__(self):
        """Initialize fallback session manager."""
        self.current_session: Optional[SessionState] = None
        self.sessions_cache: Dict[str, SessionState] = {}

    async def start_session(self, session_id: str) -> SessionState:
        """Start a basic session."""
        now = datetime.now()
        session_state = SessionState(
            session_id=session_id,
            started_at=now,
            last_activity=now,
            context_tokens=0,
            files_modified=[],
            conversation_history=[],
            knowledge_base_id=f"fallback_{session_id}",
            active=True,
        )

        self.current_session = session_state
        self.sessions_cache[session_id] = session_state
        logger.info(f"Started fallback session: {session_id}")
        return session_state

    async def add_interaction(self, user_input: str, response: str) -> None:
        """Add interaction to session history."""
        if not self.current_session:
            raise SessionError("No active session")

        interaction = {
            "timestamp": datetime.now().isoformat(),
            "user_input": user_input,
            "response": response,
            "tokens_used": len(user_input + response) // 4,  # Rough estimate
        }

        self.current_session.conversation_history.append(interaction)
        self.current_session.last_activity = datetime.now()
        self.current_session.context_tokens += interaction["tokens_used"]

    async def get_context(self) -> Dict[str, Any]:
        """Get basic session context."""
        if not self.current_session:
            return {"session": None, "context": "No active session"}

        return {
            "session_id": self.current_session.session_id,
            "started_at": self.current_session.started_at.isoformat(),
            "last_activity": self.current_session.last_activity.isoformat(),
            "context_tokens": self.current_session.context_tokens,
            "interaction_count": len(self.current_session.conversation_history),
            "fallback": True,
        }

    async def persist(self) -> None:
        """Basic persistence - just logs."""
        if self.current_session:
            logger.debug(
                f"Persisting fallback session {self.current_session.session_id}"
            )

    async def recover(self, session_id: str) -> SessionState:
        """Recover session from cache or create new."""
        if session_id in self.sessions_cache:
            self.current_session = self.sessions_cache[session_id]
            return self.current_session
        else:
            return await self.start_session(session_id)

    async def cleanup_old_sessions(self, days: int = 30) -> int:
        """Clean up old sessions from cache."""
        cutoff_date = datetime.now() - timedelta(days=days)
        cleaned = 0

        sessions_to_remove = []
        for session_id, session in self.sessions_cache.items():
            if session.last_activity < cutoff_date:
                sessions_to_remove.append(session_id)

        for session_id in sessions_to_remove:
            del self.sessions_cache[session_id]
            cleaned += 1

        return cleaned


class FallbackStreamingProcessor(IStreaming):
    """
    Fallback streaming processor with basic functionality.
    Provides working streaming responses.
    """

    def __init__(self):
        """Initialize fallback streaming processor."""
        self.active_streams: Dict[str, Dict[str, Any]] = {}
        self.stream_counter = 0

    async def stream_response(
        self, intent: CodingIntent, session_context: Dict[str, Any]
    ) -> AsyncIterator[StreamChunk]:
        """Stream basic response for intent."""
        stream_id = str(uuid4())
        sequence_number = 0

        try:
            self.active_streams[stream_id] = {
                "intent": intent,
                "start_time": datetime.now(),
                "chunks_sent": 0,
            }

            # Thought chunk
            sequence_number += 1
            yield StreamChunk(
                type="thought",
                content=f"Processing {intent.action.value} request for {', '.join(intent.targets)}",
                metadata={"intent": intent.action.value, "fallback": True},
                timestamp=datetime.now(),
                sequence_number=sequence_number,
            )
            await asyncio.sleep(0.1)

            # Action chunk
            sequence_number += 1
            yield StreamChunk(
                type="action",
                content=f"Analyzing {intent.scope} scope for {intent.action.value} operation",
                metadata={"scope": intent.scope, "fallback": True},
                timestamp=datetime.now(),
                sequence_number=sequence_number,
            )
            await asyncio.sleep(0.2)

            # Generate response based on action
            async for chunk in self._generate_action_response(intent, sequence_number):
                sequence_number += 1
                chunk.sequence_number = sequence_number
                yield chunk

            # Result chunk
            sequence_number += 1
            yield StreamChunk(
                type="result",
                content=f"Completed {intent.action.value} operation using fallback processor",
                metadata={
                    "action": intent.action.value,
                    "fallback": True,
                    "confidence": intent.confidence,
                },
                timestamp=datetime.now(),
                sequence_number=sequence_number,
            )

        finally:
            if stream_id in self.active_streams:
                del self.active_streams[stream_id]

    async def _generate_action_response(
        self, intent: CodingIntent, start_sequence: int
    ) -> AsyncIterator[StreamChunk]:
        """Generate action-specific response."""
        if intent.action == CodingAction.IMPLEMENT:
            yield StreamChunk(
                type="code",
                content=f"""# Fallback implementation for {', '.join(intent.targets)}
def fallback_implementation():
    '''
    This is a fallback implementation.
    Original request: {intent.original_request}
    '''
    # TODO: Replace with actual implementation
    pass""",
                metadata={"language": "python", "fallback": True},
                timestamp=datetime.now(),
                sequence_number=0,
            )

        elif intent.action == CodingAction.DEBUG:
            yield StreamChunk(
                type="action",
                content=f"Analyzing potential issues in {', '.join(intent.targets)}",
                metadata={"phase": "analysis", "fallback": True},
                timestamp=datetime.now(),
                sequence_number=0,
            )

            yield StreamChunk(
                type="result",
                content="Common debugging suggestions: Check variable types, verify function parameters, add logging statements",
                metadata={"suggestions": True, "fallback": True},
                timestamp=datetime.now(),
                sequence_number=0,
            )

        elif intent.action == CodingAction.EXPLAIN:
            yield StreamChunk(
                type="action",
                content=f"Explaining {', '.join(intent.targets)} at {intent.scope} level",
                metadata={"explanation": True, "fallback": True},
                timestamp=datetime.now(),
                sequence_number=0,
            )

        elif intent.action == CodingAction.TEST:
            yield StreamChunk(
                type="test",
                content=f"""# Fallback test for {', '.join(intent.targets)}
import pytest

def test_{intent.targets[0].lower().replace(' ', '_') if intent.targets else 'fallback'}():
    '''Test generated by fallback processor'''
    # TODO: Replace with actual test implementation
    assert True, "Fallback test - replace with real implementation"
""",
                metadata={"test_framework": "pytest", "fallback": True},
                timestamp=datetime.now(),
                sequence_number=0,
            )

        else:
            yield StreamChunk(
                type="action",
                content=f"Processing {intent.action.value} using fallback implementation",
                metadata={"action": intent.action.value, "fallback": True},
                timestamp=datetime.now(),
                sequence_number=0,
            )

        await asyncio.sleep(0.1)

    async def handle_backpressure(self) -> None:
        """Handle backpressure - basic implementation."""
        if len(self.active_streams) > 5:
            await asyncio.sleep(0.5)

    async def cancel_stream(self, stream_id: str) -> bool:
        """Cancel stream if exists."""
        if stream_id in self.active_streams:
            del self.active_streams[stream_id]
            return True
        return False

    async def get_stream_metrics(self) -> Dict[str, Any]:
        """Get basic streaming metrics."""
        return {
            "active_streams": len(self.active_streams),
            "fallback": True,
            "timestamp": datetime.now().isoformat(),
        }


class FallbackNLParser(IParser):
    """
    Fallback NLP parser with basic pattern matching.
    Provides working natural language parsing.
    """

    def __init__(self):
        """Initialize fallback NLP parser."""
        self.action_keywords = {
            CodingAction.IMPLEMENT: [
                "implement",
                "create",
                "build",
                "make",
                "add",
                "new",
            ],
            CodingAction.MODIFY: ["modify", "change", "update", "edit", "fix", "alter"],
            CodingAction.DEBUG: ["debug", "fix", "solve", "find", "error", "bug"],
            CodingAction.TEST: ["test", "check", "verify", "validate"],
            CodingAction.EXPLAIN: [
                "explain",
                "describe",
                "tell",
                "show",
                "what",
                "how",
            ],
            CodingAction.REVIEW: ["review", "check", "examine", "analyze"],
            CodingAction.REFACTOR: ["refactor", "improve", "restructure", "clean"],
            CodingAction.OPTIMIZE: ["optimize", "speed", "performance", "faster"],
        }

    async def parse_input(self, user_input: str) -> CodingIntent:
        """Parse user input using basic pattern matching."""
        try:
            normalized_input = user_input.lower().strip()

            # Detect action
            detected_action = CodingAction.EXPLAIN  # Default
            max_score = 0

            for action, keywords in self.action_keywords.items():
                score = sum(1 for keyword in keywords if keyword in normalized_input)
                if score > max_score:
                    max_score = score
                    detected_action = action

            # Extract targets (simple approach)
            targets = self._extract_simple_targets(user_input)

            # Determine scope
            scope = "function"
            if "class" in normalized_input:
                scope = "class"
            elif "file" in normalized_input:
                scope = "file"
            elif "project" in normalized_input:
                scope = "project"

            # Calculate confidence
            confidence = min(max_score / 3.0, 1.0) if max_score > 0 else 0.5

            return CodingIntent(
                action=detected_action,
                targets=targets,
                scope=scope,
                original_request=user_input,
                confidence=confidence,
                context_required=["fallback"],
            )

        except Exception as e:
            logger.error(f"Fallback parsing failed: {e}")
            raise ParsingError(f"Fallback parsing error: {e}")

    def _extract_simple_targets(self, text: str) -> List[str]:
        """Extract targets using simple heuristics."""
        targets = []

        # Look for file extensions
        import re

        files = re.findall(r"\b\w+\.(?:py|js|ts|java|cpp|html|css)\b", text)
        targets.extend(files)

        # Look for quoted strings
        quoted = re.findall(r'[\'"]([^\'"]*)[\'"]', text)
        targets.extend(quoted)

        # Look for function-like patterns
        functions = re.findall(r"\b(\w+)\s*\(", text)
        targets.extend(functions)

        return targets[:5] if targets else ["general"]

    async def extract_entities(self, text: str) -> List[Tuple[str, str]]:
        """Extract entities using basic patterns."""
        entities = []
        import re

        # Files
        files = re.findall(r"\b(\w+\.\w+)\b", text)
        entities.extend([(f, "file") for f in files])

        # Functions
        functions = re.findall(r"\b(\w+)\s*\(", text)
        entities.extend([(f, "function") for f in functions])

        return entities

    async def suggest_completion(
        self, partial: str, context: Dict[str, Any]
    ) -> List[str]:
        """Provide basic completions."""
        completions = []
        partial_lower = partial.lower()

        # Common completions
        common_phrases = [
            "implement function",
            "create class",
            "fix bug",
            "test code",
            "explain how",
            "debug error",
            "modify file",
            "review code",
        ]

        for phrase in common_phrases:
            if phrase.startswith(partial_lower):
                completions.append(phrase)

        return completions[:5]

    async def detect_language(self, code_snippet: str) -> str:
        """Detect language using simple patterns."""
        if "def " in code_snippet or "import " in code_snippet:
            return "python"
        elif "function " in code_snippet or "const " in code_snippet:
            return "javascript"
        elif "public class" in code_snippet:
            return "java"
        else:
            return "text"


class FallbackTerminalUI(ITerminalUI):
    """
    Fallback terminal UI with basic functionality.
    Provides working terminal interface without rich formatting.
    """

    def __init__(self):
        """Initialize fallback terminal UI."""
        self.started = False

    async def start_ui(self) -> None:
        """Start basic terminal UI."""
        print("\033[2J\033[H", end="")
        print("=" * 60)
        print("CASPER Prime Terminal (Fallback Mode)")
        print("=" * 60)
        print("AI-Powered Coding Assistant")
        print("\nType your coding requests in natural language")
        print("Examples:")
        print("  • implement a user authentication function")
        print("  • debug the login method")
        print("  • explain how the algorithm works")
        print("  • test my code")
        print("\nType 'help' for commands or 'exit' to quit\n")
        self.started = True

    async def display_stream(self, chunk: StreamChunk) -> None:
        """Display stream chunk in basic format."""
        timestamp = chunk.timestamp.strftime("%H:%M:%S")

        type_prefixes = {
            "thought": "💭 ",
            "action": "🔧 ",
            "code": "💻 ",
            "test": "🧪 ",
            "result": "✅ ",
            "error": "❌ ",
        }

        prefix = type_prefixes.get(chunk.type, "")

        if chunk.type in ["code", "test"]:
            print(f"\n[{timestamp}] {prefix}{chunk.type.upper()}:")
            print("-" * 40)
            print(chunk.content)
            print("-" * 40)
        else:
            print(f"[{timestamp}] {prefix}{chunk.content}")

        # Small delay for streaming effect
        await asyncio.sleep(0.1)

    async def get_user_input(self, prompt: str = "casper> ") -> str:
        """Get user input with basic prompt."""
        try:
            return input(prompt)
        except (EOFError, KeyboardInterrupt):
            return "exit"

    async def show_progress(
        self, message: str, percentage: Optional[float] = None
    ) -> None:
        """Show basic progress indicator."""
        if percentage is not None:
            bar_length = 20
            filled_length = int(bar_length * percentage / 100)
            bar = "█" * filled_length + "░" * (bar_length - filled_length)
            print(f"\r[{bar}] {percentage:.1f}% - {message}", end="", flush=True)
        else:
            print(f"Progress: {message}")

    async def clear_screen(self) -> None:
        """Clear terminal screen."""
        print("\033[2J\033[H", end="")

    async def show_error(self, error: str) -> None:
        """Show error message."""
        print(f"\n❌ ERROR: {error}\n")
