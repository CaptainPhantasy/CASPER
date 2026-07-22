"""
Shared interfaces for Terminal Squad agents.
PRODUCTION GRADE - No modifications without consensus.
"""

from abc import ABC, abstractmethod
from typing import AsyncIterator, Dict, Any, List, Optional, Tuple
from dataclasses import dataclass
from datetime import datetime
from enum import Enum


class CodingAction(Enum):
    """Supported coding actions"""
    IMPLEMENT = "implement"
    MODIFY = "modify"
    DEBUG = "debug"
    TEST = "test"
    EXPLAIN = "explain"
    REVIEW = "review"
    REFACTOR = "refactor"
    OPTIMIZE = "optimize"


@dataclass
class CodingIntent:
    """Parsed user intent for coding action"""
    action: CodingAction
    targets: List[str]  # files, functions, classes, etc
    scope: str  # file, function, class, project
    original_request: str
    confidence: float  # 0.0 to 1.0
    context_required: List[str]  # what context is needed


@dataclass
class StreamChunk:
    """Single chunk in streaming response"""
    type: str  # thought, action, code, test, result, error
    content: str
    metadata: Dict[str, Any]
    timestamp: datetime
    sequence_number: int  # for ordering


@dataclass
class SessionState:
    """Complete session state for persistence"""
    session_id: str
    started_at: datetime
    last_activity: datetime
    context_tokens: int
    files_modified: List[str]
    conversation_history: List[Dict[str, str]]
    knowledge_base_id: str
    active: bool


class ISession(ABC):
    """Session management interface"""

    @abstractmethod
    async def start_session(self, session_id: str) -> SessionState:
        """Initialize a new coding session"""
        pass

    @abstractmethod
    async def add_interaction(self, user_input: str, response: str) -> None:
        """Add an interaction to session history"""
        pass

    @abstractmethod
    async def get_context(self) -> Dict[str, Any]:
        """Get current session context"""
        pass

    @abstractmethod
    async def persist(self) -> None:
        """Save session to persistent storage"""
        pass

    @abstractmethod
    async def recover(self, session_id: str) -> SessionState:
        """Recover session from storage"""
        pass

    @abstractmethod
    async def cleanup_old_sessions(self, days: int = 30) -> int:
        """Clean up sessions older than specified days"""
        pass


class IStreaming(ABC):
    """Streaming response interface"""

    @abstractmethod
    async def stream_response(
        self,
        intent: CodingIntent,
        session_context: Dict[str, Any]
    ) -> AsyncIterator[StreamChunk]:
        """Stream response chunks for the given intent"""
        pass

    @abstractmethod
    async def handle_backpressure(self) -> None:
        """Handle client backpressure in streaming"""
        pass

    @abstractmethod
    async def cancel_stream(self, stream_id: str) -> bool:
        """Cancel an active stream"""
        pass

    @abstractmethod
    async def get_stream_metrics(self) -> Dict[str, Any]:
        """Get streaming performance metrics"""
        pass


class IParser(ABC):
    """Natural language parsing interface"""

    @abstractmethod
    async def parse_input(self, user_input: str) -> CodingIntent:
        """Parse natural language into coding intent"""
        pass

    @abstractmethod
    async def extract_entities(self, text: str) -> List[Tuple[str, str]]:
        """Extract entities (name, type) from text"""
        pass

    @abstractmethod
    async def suggest_completion(
        self,
        partial: str,
        context: Dict[str, Any]
    ) -> List[str]:
        """Suggest completions for partial input"""
        pass

    @abstractmethod
    async def detect_language(self, code_snippet: str) -> str:
        """Detect programming language from snippet"""
        pass


class ITerminalUI(ABC):
    """Terminal user interface"""

    @abstractmethod
    async def start_ui(self) -> None:
        """Start the terminal UI"""
        pass

    @abstractmethod
    async def display_stream(self, chunk: StreamChunk) -> None:
        """Display a streaming chunk in the UI"""
        pass

    @abstractmethod
    async def get_user_input(self, prompt: str = "casper> ") -> str:
        """Get input from user with prompt"""
        pass

    @abstractmethod
    async def show_progress(
        self,
        message: str,
        percentage: Optional[float] = None
    ) -> None:
        """Show progress indicator"""
        pass

    @abstractmethod
    async def clear_screen(self) -> None:
        """Clear the terminal screen"""
        pass

    @abstractmethod
    async def show_error(self, error: str) -> None:
        """Display error message"""
        pass


class IIntegration(ABC):
    """Main integration interface"""

    @abstractmethod
    async def initialize_terminal(self) -> None:
        """Initialize all terminal components"""
        pass

    @abstractmethod
    async def start_interactive_session(self) -> None:
        """Start interactive coding session"""
        pass

    @abstractmethod
    async def handle_mcp_connection(self, websocket) -> None:
        """Handle Model Context Protocol connection from IDE"""
        pass

    @abstractmethod
    async def shutdown(self) -> None:
        """Gracefully shutdown terminal"""
        pass


# Shared constants for all agents
MAX_CONTEXT_TOKENS = 200000
SESSION_TIMEOUT_MINUTES = 30
STREAMING_CHUNK_SIZE = 100  # characters
MAX_COMPLETIONS = 10
DEFAULT_TEMPERATURE = 0.1

# WebSocket message types
class WSMessageType(Enum):
    """WebSocket message types for streaming"""
    THOUGHT = "thought"
    ACTION = "action"
    CODE = "code"
    TEST = "test"
    RESULT = "result"
    ERROR = "error"
    HEARTBEAT = "heartbeat"
    CANCEL = "cancel"


# Shared error types
class TerminalError(Exception):
    """Base exception for terminal errors"""
    pass


class SessionError(TerminalError):
    """Session-related errors"""
    pass


class StreamingError(TerminalError):
    """Streaming-related errors"""
    pass


class ParsingError(TerminalError):
    """Parsing-related errors"""
    pass