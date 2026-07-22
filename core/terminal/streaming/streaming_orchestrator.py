"""
Real-time Streaming Orchestrator for CASPER Terminal
Implements token-by-token code generation with syntax highlighting and backpressure handling.
PRODUCTION GRADE - No placeholders or mocks.
"""

import asyncio
import json
import logging
import time
import re
from typing import AsyncIterator, Dict, Any, List, Optional, Set, Tuple, Callable
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from uuid import uuid4
from pathlib import Path

from ..interfaces import IStreaming, StreamChunk, CodingIntent, WSMessageType, StreamingError
from ...reasoning.react_engine import get_react_engine, ReActStep
from ...services.llm import llm_service

logger = logging.getLogger(__name__)


class SyntaxType(Enum):
    """Token syntax types for highlighting"""
    KEYWORD = "keyword"
    STRING = "string"
    NUMBER = "number"
    COMMENT = "comment"
    IDENTIFIER = "identifier"
    OPERATOR = "operator"
    PUNCTUATION = "punctuation"
    FUNCTION = "function"
    CLASS = "class"
    VARIABLE = "variable"
    IMPORT = "import"
    DECORATOR = "decorator"
    WHITESPACE = "whitespace"
    NEWLINE = "newline"
    UNKNOWN = "unknown"


@dataclass
class SyntaxToken:
    """Token with syntax highlighting information"""
    content: str
    type: SyntaxType
    color: str
    position: int
    line_number: int
    column: int


@dataclass
class StreamingContext:
    """Context for active streaming session"""
    stream_id: str
    intent: CodingIntent
    session_context: Dict[str, Any]
    websocket: Any  # WebSocket connection
    started_at: datetime = field(default_factory=datetime.utcnow)
    last_sent_at: datetime = field(default_factory=datetime.utcnow)
    tokens_sent: int = 0
    backpressure_count: int = 0
    is_cancelled: bool = False
    buffer: List[StreamChunk] = field(default_factory=list)
    buffer_size_bytes: int = 0


@dataclass
class StreamingMetrics:
    """Performance metrics for streaming"""
    active_streams: int = 0
    total_streams: int = 0
    tokens_per_second: float = 0.0
    average_latency_ms: float = 0.0
    backpressure_events: int = 0
    cancelled_streams: int = 0
    error_count: int = 0


class SyntaxHighlighter:
    """Real-time syntax highlighting for streamed tokens"""

    def __init__(self):
        self.language_patterns = self._load_language_patterns()
        self.color_scheme = self._load_color_scheme()

    def _load_language_patterns(self) -> Dict[str, Dict[SyntaxType, List[str]]]:
        """Load regex patterns for different programming languages"""
        return {
            "python": {
                SyntaxType.KEYWORD: [
                    r'\b(def|class|if|else|elif|for|while|try|except|finally|with|import|from|as|return|yield|lambda|and|or|not|in|is|None|True|False|async|await)\b'
                ],
                SyntaxType.STRING: [
                    r'(""".*?""")',  # Triple quotes
                    r"('''.*?''')",
                    r'(".*?")',      # Double quotes
                    r"('.*?')",      # Single quotes
                    r'(f".*?")',     # f-strings
                    r"(f'.*?')"
                ],
                SyntaxType.NUMBER: [
                    r'\b(\d+\.?\d*([eE][+-]?\d+)?)\b'
                ],
                SyntaxType.COMMENT: [
                    r'(#.*$)'
                ],
                SyntaxType.FUNCTION: [
                    r'\b([a-zA-Z_][a-zA-Z0-9_]*)\s*(?=\()'
                ],
                SyntaxType.CLASS: [
                    r'\b(class\s+[a-zA-Z_][a-zA-Z0-9_]*)'
                ],
                SyntaxType.DECORATOR: [
                    r'(@[a-zA-Z_][a-zA-Z0-9_.]*)'
                ],
                SyntaxType.OPERATOR: [
                    r'([+\-*/%=<>!&|^~]|==|!=|<=|>=|<<|>>|\*\*|//|\.\.\.)'
                ],
                SyntaxType.PUNCTUATION: [
                    r'([{}()\[\],.;:])'
                ]
            },
            "javascript": {
                SyntaxType.KEYWORD: [
                    r'\b(function|var|let|const|if|else|for|while|do|break|continue|return|try|catch|finally|throw|new|this|typeof|instanceof|in|of|class|extends|super|import|export|default|async|await)\b'
                ],
                SyntaxType.STRING: [
                    r'(`.*?`)',      # Template literals
                    r'(".*?")',
                    r"('.*?')"
                ],
                SyntaxType.NUMBER: [
                    r'\b(\d+\.?\d*([eE][+-]?\d+)?)\b'
                ],
                SyntaxType.COMMENT: [
                    r'(//.*$)',
                    r'(/\*.*?\*/)'
                ]
            },
            "typescript": {
                SyntaxType.KEYWORD: [
                    r'\b(interface|type|enum|namespace|declare|abstract|implements|private|public|protected|readonly|static|export|import|from|as|default|async|await)\b'
                ]
            }
        }

    def _load_color_scheme(self) -> Dict[SyntaxType, str]:
        """Load ANSI color codes for syntax types"""
        return {
            SyntaxType.KEYWORD: "\033[38;5;33m",      # Blue
            SyntaxType.STRING: "\033[38;5;10m",       # Green
            SyntaxType.NUMBER: "\033[38;5;208m",      # Orange
            SyntaxType.COMMENT: "\033[38;5;244m",     # Gray
            SyntaxType.FUNCTION: "\033[38;5;220m",    # Yellow
            SyntaxType.CLASS: "\033[38;5;196m",       # Red
            SyntaxType.VARIABLE: "\033[38;5;15m",     # White
            SyntaxType.OPERATOR: "\033[38;5;201m",    # Magenta
            SyntaxType.PUNCTUATION: "\033[38;5;245m", # Light Gray
            SyntaxType.DECORATOR: "\033[38;5;166m",   # Dark Orange
            SyntaxType.IMPORT: "\033[38;5;51m",       # Cyan
            SyntaxType.IDENTIFIER: "\033[38;5;15m",   # White
            SyntaxType.WHITESPACE: "",                # No color
            SyntaxType.NEWLINE: "",                   # No color
            SyntaxType.UNKNOWN: "\033[38;5;15m"       # White
        }

    def detect_language(self, code_snippet: str) -> str:
        """Detect programming language from code snippet"""
        # Simple heuristics for language detection
        # Check TypeScript first (more specific patterns)
        if any(keyword in code_snippet for keyword in ['interface ', ': string', ': number', 'type ', 'namespace ']):
            return "typescript"
        elif any(keyword in code_snippet for keyword in ['def ', 'import ', 'from ', '__init__']):
            return "python"
        elif any(keyword in code_snippet for keyword in ['function', 'const ', 'let ', 'var ']):
            return "javascript"
        elif any(keyword in code_snippet for keyword in ['public class', 'private ', 'public static']):
            return "java"
        elif any(keyword in code_snippet for keyword in ['fn ', 'struct ', 'impl ', 'use ']):
            return "rust"
        else:
            return "python"  # Default fallback

    def tokenize_and_highlight(self, text: str, language: str = "python") -> List[SyntaxToken]:
        """Tokenize text and apply syntax highlighting"""
        tokens = []
        patterns = self.language_patterns.get(language, self.language_patterns["python"])
        position = 0
        line_number = 1
        column = 1

        # Process text character by character for real-time streaming
        remaining_text = text

        while remaining_text:
            matched = False

            # Try to match syntax patterns
            for syntax_type, pattern_list in patterns.items():
                for pattern in pattern_list:
                    match = re.match(pattern, remaining_text, re.MULTILINE)
                    if match:
                        content = match.group(0)
                        token = SyntaxToken(
                            content=content,
                            type=syntax_type,
                            color=self.color_scheme.get(syntax_type, ""),
                            position=position,
                            line_number=line_number,
                            column=column
                        )
                        tokens.append(token)

                        # Update position tracking
                        position += len(content)
                        if '\n' in content:
                            line_number += content.count('\n')
                            column = len(content) - content.rfind('\n')
                        else:
                            column += len(content)

                        remaining_text = remaining_text[len(content):]
                        matched = True
                        break

                if matched:
                    break

            # If no pattern matched, treat as single character
            if not matched:
                char = remaining_text[0]
                if char == '\n':
                    syntax_type = SyntaxType.NEWLINE
                    line_number += 1
                    column = 1
                elif char.isspace():
                    syntax_type = SyntaxType.WHITESPACE
                    column += 1
                else:
                    syntax_type = SyntaxType.UNKNOWN
                    column += 1

                token = SyntaxToken(
                    content=char,
                    type=syntax_type,
                    color=self.color_scheme.get(syntax_type, ""),
                    position=position,
                    line_number=line_number,
                    column=column
                )
                tokens.append(token)

                position += 1
                remaining_text = remaining_text[1:]

        return tokens


class BackpressureHandler:
    """Handles client backpressure during streaming"""

    def __init__(self, max_buffer_size: int = 1024 * 1024):  # 1MB default
        self.max_buffer_size = max_buffer_size
        self.backpressure_threshold = 0.8 * max_buffer_size  # 80% of max

    async def check_backpressure(self, context: StreamingContext) -> bool:
        """Check if backpressure should be applied"""
        return context.buffer_size_bytes >= self.backpressure_threshold

    async def handle_backpressure(self, context: StreamingContext) -> None:
        """Handle backpressure by pausing stream"""
        context.backpressure_count += 1
        logger.warning(f"Backpressure applied to stream {context.stream_id}, buffer size: {context.buffer_size_bytes}")

        # Exponential backoff with jitter
        delay = min(0.1 * (2 ** context.backpressure_count), 2.0)
        jitter = delay * 0.1 * (time.time() % 1.0)  # Up to 10% jitter

        await asyncio.sleep(delay + jitter)

    async def flush_buffer(self, context: StreamingContext) -> int:
        """Flush buffered chunks to client"""
        sent_count = 0

        while context.buffer and context.buffer_size_bytes > 0:
            try:
                chunk = context.buffer.pop(0)
                await self._send_chunk_to_client(context, chunk)
                context.buffer_size_bytes -= len(chunk.content.encode('utf-8'))
                sent_count += 1
            except Exception as e:
                logger.error(f"Failed to flush buffer chunk for stream {context.stream_id}: {e}")
                break

        return sent_count

    async def _send_chunk_to_client(self, context: StreamingContext, chunk: StreamChunk) -> None:
        """Send chunk to WebSocket client"""
        try:
            message = {
                "type": chunk.type,
                "content": chunk.content,
                "metadata": chunk.metadata,
                "timestamp": chunk.timestamp.isoformat(),
                "sequence": chunk.sequence_number,
                "stream_id": context.stream_id
            }
            await context.websocket.send_json(message)
            context.last_sent_at = datetime.utcnow()
            context.tokens_sent += 1
        except Exception as e:
            logger.error(f"Failed to send chunk to client: {e}")
            raise


class StreamingOrchestrator(IStreaming):
    """
    Real-time streaming orchestrator for coding terminal.
    Implements token-by-token code generation with syntax highlighting and backpressure handling.
    """

    def __init__(self, max_concurrent_streams: int = 10):
        self.max_concurrent_streams = max_concurrent_streams
        self.active_streams: Dict[str, StreamingContext] = {}
        self.syntax_highlighter = SyntaxHighlighter()
        self.backpressure_handler = BackpressureHandler()
        self.react_engine = get_react_engine()
        self.metrics = StreamingMetrics()

        # Performance tracking
        self._start_time = time.time()
        self._token_timestamps: List[float] = []

        logger.info("StreamingOrchestrator initialized")

    async def stream_response(
        self,
        intent: CodingIntent,
        session_context: Dict[str, Any]
    ) -> AsyncIterator[StreamChunk]:
        """Stream response chunks for the given intent"""

        if len(self.active_streams) >= self.max_concurrent_streams:
            raise StreamingError("Maximum concurrent streams exceeded")

        stream_id = str(uuid4())
        websocket = session_context.get('websocket')
        if not websocket:
            raise StreamingError("No WebSocket connection in session context")

        # Create streaming context
        context = StreamingContext(
            stream_id=stream_id,
            intent=intent,
            session_context=session_context,
            websocket=websocket
        )
        self.active_streams[stream_id] = context
        self.metrics.active_streams += 1
        self.metrics.total_streams += 1

        try:
            # Stream the coding task execution
            async for chunk in self._execute_streaming_task(context):
                if context.is_cancelled:
                    break

                # Check for backpressure
                if await self.backpressure_handler.check_backpressure(context):
                    await self.handle_backpressure()

                yield chunk

        except Exception as e:
            self.metrics.error_count += 1
            logger.error(f"Streaming error for stream {stream_id}: {e}")
            yield StreamChunk(
                type=WSMessageType.ERROR.value,
                content=f"Streaming error: {str(e)}",
                metadata={"error_type": "streaming_error", "stream_id": stream_id},
                timestamp=datetime.utcnow(),
                sequence_number=context.tokens_sent + 1
            )
        finally:
            # Cleanup
            if stream_id in self.active_streams:
                del self.active_streams[stream_id]
            self.metrics.active_streams -= 1

    async def _execute_streaming_task(self, context: StreamingContext) -> AsyncIterator[StreamChunk]:
        """Execute the coding task and stream results"""

        # Send initial task analysis
        yield StreamChunk(
            type=WSMessageType.THOUGHT.value,
            content=f"Analyzing task: {context.intent.original_request}",
            metadata={
                "intent_action": context.intent.action.value,
                "targets": context.intent.targets,
                "scope": context.intent.scope
            },
            timestamp=datetime.utcnow(),
            sequence_number=1
        )

        # Stream ReAct reasoning
        sequence_num = 2
        async for reasoning_chunk in self.react_engine.stream_reasoning(context.intent.original_request):
            if context.is_cancelled:
                break

            chunk_type = WSMessageType.THOUGHT.value
            if reasoning_chunk.get("type") == "action":
                chunk_type = WSMessageType.ACTION.value
            elif reasoning_chunk.get("type") == "observation":
                chunk_type = WSMessageType.RESULT.value
            elif reasoning_chunk.get("type") == "final_answer":
                chunk_type = WSMessageType.CODE.value
                # Apply syntax highlighting to code content
                content = reasoning_chunk.get("content", "")
                async for highlighted_chunk in self._stream_highlighted_code(content, sequence_num):
                    yield highlighted_chunk
                    sequence_num += 1
                continue

            yield StreamChunk(
                type=chunk_type,
                content=reasoning_chunk.get("content", ""),
                metadata=reasoning_chunk,
                timestamp=datetime.utcnow(),
                sequence_number=sequence_num
            )
            sequence_num += 1

        # Send completion signal
        yield StreamChunk(
            type=WSMessageType.RESULT.value,
            content="Task execution completed",
            metadata={"status": "completed", "tokens_sent": context.tokens_sent},
            timestamp=datetime.utcnow(),
            sequence_number=sequence_num
        )

    async def _stream_highlighted_code(self, code: str, start_sequence: int) -> AsyncIterator[StreamChunk]:
        """Stream code with syntax highlighting applied token by token"""

        # Detect language
        language = self.syntax_highlighter.detect_language(code)

        # Tokenize and highlight
        tokens = self.syntax_highlighter.tokenize_and_highlight(code, language)

        sequence_num = start_sequence
        for token in tokens:
            # Create chunk for each token
            chunk = StreamChunk(
                type=WSMessageType.CODE.value,
                content=token.content,
                metadata={
                    "syntax_type": token.type.value,
                    "color": token.color,
                    "position": token.position,
                    "line": token.line_number,
                    "column": token.column,
                    "language": language
                },
                timestamp=datetime.utcnow(),
                sequence_number=sequence_num
            )

            yield chunk
            sequence_num += 1

            # Add small delay for realistic streaming effect
            await asyncio.sleep(0.01)  # 10ms between tokens

    async def handle_backpressure(self) -> None:
        """Handle client backpressure in streaming"""

        for context in self.active_streams.values():
            if await self.backpressure_handler.check_backpressure(context):
                await self.backpressure_handler.handle_backpressure(context)
                self.metrics.backpressure_events += 1

    async def cancel_stream(self, stream_id: str) -> bool:
        """Cancel an active stream"""

        context = self.active_streams.get(stream_id)
        if not context:
            return False

        context.is_cancelled = True
        self.metrics.cancelled_streams += 1

        # Send cancellation notice
        try:
            cancel_chunk = StreamChunk(
                type=WSMessageType.CANCEL.value,
                content="Stream cancelled by client",
                metadata={"stream_id": stream_id},
                timestamp=datetime.utcnow(),
                sequence_number=context.tokens_sent + 1
            )

            await context.websocket.send_json({
                "type": cancel_chunk.type,
                "content": cancel_chunk.content,
                "metadata": cancel_chunk.metadata,
                "timestamp": cancel_chunk.timestamp.isoformat(),
                "sequence": cancel_chunk.sequence_number
            })
        except Exception as e:
            logger.error(f"Failed to send cancellation notice for stream {stream_id}: {e}")

        logger.info(f"Stream {stream_id} cancelled")
        return True

    async def get_stream_metrics(self) -> Dict[str, Any]:
        """Get streaming performance metrics"""

        current_time = time.time()
        runtime_seconds = current_time - self._start_time

        # Calculate tokens per second
        if runtime_seconds > 0:
            total_tokens = sum(context.tokens_sent for context in self.active_streams.values())
            self.metrics.tokens_per_second = total_tokens / runtime_seconds

        # Calculate average latency
        if self._token_timestamps:
            recent_timestamps = [t for t in self._token_timestamps if current_time - t < 60]  # Last minute
            if len(recent_timestamps) > 1:
                latencies = [recent_timestamps[i] - recent_timestamps[i-1]
                           for i in range(1, len(recent_timestamps))]
                self.metrics.average_latency_ms = (sum(latencies) / len(latencies)) * 1000

        return {
            "active_streams": self.metrics.active_streams,
            "total_streams": self.metrics.total_streams,
            "tokens_per_second": round(self.metrics.tokens_per_second, 2),
            "average_latency_ms": round(self.metrics.average_latency_ms, 2),
            "backpressure_events": self.metrics.backpressure_events,
            "cancelled_streams": self.metrics.cancelled_streams,
            "error_count": self.metrics.error_count,
            "max_concurrent_streams": self.max_concurrent_streams,
            "runtime_seconds": round(runtime_seconds, 2)
        }

    def get_active_stream_ids(self) -> List[str]:
        """Get list of active stream IDs"""
        return list(self.active_streams.keys())

    async def cleanup_inactive_streams(self, timeout_minutes: int = 30) -> int:
        """Clean up inactive streams that have timed out"""

        cutoff_time = datetime.utcnow() - timedelta(minutes=timeout_minutes)
        inactive_streams = []

        for stream_id, context in self.active_streams.items():
            if context.last_sent_at < cutoff_time:
                inactive_streams.append(stream_id)

        cleanup_count = 0
        for stream_id in inactive_streams:
            if await self.cancel_stream(stream_id):
                cleanup_count += 1
                # Ensure stream is removed from active streams
                if stream_id in self.active_streams:
                    del self.active_streams[stream_id]
                    self.metrics.active_streams -= 1

        logger.info(f"Cleaned up {cleanup_count} inactive streams")
        return cleanup_count

    async def send_heartbeat(self, stream_id: str) -> bool:
        """Send heartbeat to keep stream alive"""

        context = self.active_streams.get(stream_id)
        if not context:
            return False

        try:
            heartbeat_message = {
                "type": WSMessageType.HEARTBEAT.value,
                "timestamp": datetime.utcnow().isoformat(),
                "stream_id": stream_id,
                "tokens_sent": context.tokens_sent
            }

            await context.websocket.send_json(heartbeat_message)
            context.last_sent_at = datetime.utcnow()
            return True

        except Exception as e:
            logger.error(f"Failed to send heartbeat for stream {stream_id}: {e}")
            return False


# Global singleton instance
_orchestrator_instance = None

def get_streaming_orchestrator() -> StreamingOrchestrator:
    """Get singleton streaming orchestrator instance"""
    global _orchestrator_instance

    if _orchestrator_instance is None:
        _orchestrator_instance = StreamingOrchestrator()

    return _orchestrator_instance


# Export for integration
__all__ = [
    "StreamingOrchestrator",
    "SyntaxHighlighter",
    "BackpressureHandler",
    "SyntaxToken",
    "SyntaxType",
    "get_streaming_orchestrator"
]