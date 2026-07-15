"""
Tests for StreamingOrchestrator implementation
Production-grade testing with real WebSocket mocking
"""

import asyncio
import pytest
import json
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch
from typing import List, Dict, Any

from core.terminal.streaming.streaming_orchestrator import (
    StreamingOrchestrator,
    SyntaxHighlighter,
    BackpressureHandler,
    SyntaxType,
    StreamingContext,
)
from core.terminal.interfaces import (
    CodingIntent,
    CodingAction,
    StreamChunk,
    WSMessageType,
)


class MockWebSocket:
    """Mock WebSocket for testing"""

    def __init__(self):
        self.sent_messages = []
        self.closed = False

    async def send_json(self, data: Dict[str, Any]):
        """Mock send_json method"""
        self.sent_messages.append(data)

    async def close(self):
        """Mock close method"""
        self.closed = True

    def get_sent_messages(self) -> List[Dict[str, Any]]:
        """Get all sent messages"""
        return self.sent_messages


class TestSyntaxHighlighter:
    """Test syntax highlighting functionality"""

    def setup_method(self):
        """Setup test fixtures"""
        self.highlighter = SyntaxHighlighter()

    def test_language_detection(self):
        """Test programming language detection"""
        # Python detection
        python_code = "def hello():\n    print('world')\n    import os"
        assert self.highlighter.detect_language(python_code) == "python"

        # JavaScript detection
        js_code = "function hello() { const x = 'world'; }"
        assert self.highlighter.detect_language(js_code) == "javascript"

        # TypeScript detection
        ts_code = "interface User { name: string; age: number; }"
        assert self.highlighter.detect_language(ts_code) == "typescript"

    def test_python_tokenization(self):
        """Test Python code tokenization"""
        code = "def hello():\n    return 'world'"
        tokens = self.highlighter.tokenize_and_highlight(code, "python")

        assert len(tokens) > 0

        # Find keyword tokens
        keyword_tokens = [t for t in tokens if t.type == SyntaxType.KEYWORD]
        assert len(keyword_tokens) >= 2  # 'def' and 'return'

        # Find string tokens
        string_tokens = [t for t in tokens if t.type == SyntaxType.STRING]
        assert len(string_tokens) >= 1  # 'world'

    def test_javascript_tokenization(self):
        """Test JavaScript code tokenization"""
        code = "function test() { const x = 42; return x; }"
        tokens = self.highlighter.tokenize_and_highlight(code, "javascript")

        assert len(tokens) > 0

        # Should find keywords
        keyword_tokens = [t for t in tokens if t.type == SyntaxType.KEYWORD]
        assert len(keyword_tokens) >= 3  # 'function', 'const', 'return'

    def test_position_tracking(self):
        """Test position and line tracking"""
        code = "line1\nline2\nline3"
        tokens = self.highlighter.tokenize_and_highlight(code)

        # Check line numbers are tracked correctly
        line_nums = [t.line_number for t in tokens if t.type != SyntaxType.WHITESPACE]
        assert max(line_nums) == 3

        # Check positions increase
        positions = [t.position for t in tokens]
        assert positions == sorted(positions)

    def test_color_assignment(self):
        """Test color assignment for syntax types"""
        code = "def test(): pass  # comment"
        tokens = self.highlighter.tokenize_and_highlight(code, "python")

        # Keywords should have blue color
        keyword_tokens = [t for t in tokens if t.type == SyntaxType.KEYWORD]
        for token in keyword_tokens:
            assert token.color == "\033[38;5;33m"

        # Comments should have gray color
        comment_tokens = [t for t in tokens if t.type == SyntaxType.COMMENT]
        for token in comment_tokens:
            assert token.color == "\033[38;5;244m"


class TestBackpressureHandler:
    """Test backpressure handling functionality"""

    def setup_method(self):
        """Setup test fixtures"""
        self.handler = BackpressureHandler(max_buffer_size=1000)
        self.mock_websocket = MockWebSocket()

        self.context = StreamingContext(
            stream_id="test-stream",
            intent=CodingIntent(
                action=CodingAction.IMPLEMENT,
                targets=["test.py"],
                scope="file",
                original_request="test request",
                confidence=0.9,
                context_required=[],
            ),
            session_context={"test": "context"},
            websocket=self.mock_websocket,
        )

    async def test_backpressure_detection(self):
        """Test backpressure detection"""
        # No backpressure initially
        assert not await self.handler.check_backpressure(self.context)

        # Add buffer content to trigger backpressure
        self.context.buffer_size_bytes = 900  # Above threshold (80% of 1000)
        assert await self.handler.check_backpressure(self.context)

    async def test_backpressure_handling(self):
        """Test backpressure handling with exponential backoff"""
        initial_count = self.context.backpressure_count

        start_time = asyncio.get_event_loop().time()
        await self.handler.handle_backpressure(self.context)
        end_time = asyncio.get_event_loop().time()

        # Should increment backpressure count
        assert self.context.backpressure_count == initial_count + 1

        # Should have some delay (at least 0.1 seconds for first backpressure)
        assert end_time - start_time >= 0.1

    async def test_buffer_flushing(self):
        """Test buffer flushing functionality"""
        # Add test chunks to buffer
        test_chunks = [
            StreamChunk(
                type=WSMessageType.CODE.value,
                content=f"chunk_{i}",
                metadata={},
                timestamp=datetime.utcnow(),
                sequence_number=i,
            )
            for i in range(3)
        ]

        self.context.buffer = test_chunks
        self.context.buffer_size_bytes = sum(
            len(chunk.content.encode("utf-8")) for chunk in test_chunks
        )

        # Flush buffer
        sent_count = await self.handler.flush_buffer(self.context)

        # Should have sent all chunks
        assert sent_count == 3
        assert len(self.context.buffer) == 0
        assert self.context.buffer_size_bytes == 0

        # Should have sent messages to websocket
        assert len(self.mock_websocket.sent_messages) == 3


class TestStreamingOrchestrator:
    """Test main StreamingOrchestrator functionality"""

    def setup_method(self):
        """Setup test fixtures"""
        self.orchestrator = StreamingOrchestrator(max_concurrent_streams=2)
        self.mock_websocket = MockWebSocket()

    async def test_stream_response_basic(self):
        """Test basic streaming response"""
        intent = CodingIntent(
            action=CodingAction.IMPLEMENT,
            targets=["hello.py"],
            scope="file",
            original_request="create a hello world function",
            confidence=0.9,
            context_required=[],
        )

        session_context = {
            "websocket": self.mock_websocket,
            "session_id": "test-session",
        }

        # Mock the ReAct engine
        with patch(
            "core.terminal.streaming.streaming_orchestrator.get_react_engine"
        ) as mock_engine:
            mock_engine.return_value.stream_reasoning = AsyncMock(
                return_value=self._mock_react_stream()
            )

            chunks = []
            async for chunk in self.orchestrator.stream_response(
                intent, session_context
            ):
                chunks.append(chunk)

            # Should receive multiple chunks
            assert len(chunks) > 0

            # Should have thought, action, and result chunks
            chunk_types = [chunk.type for chunk in chunks]
            assert WSMessageType.THOUGHT.value in chunk_types

    async def _mock_react_stream(self):
        """Mock ReAct streaming responses"""
        yield {"type": "thought", "content": "I need to create a hello world function"}
        yield {"type": "action", "content": "write_file", "input": "hello.py"}
        yield {"type": "observation", "content": "File created successfully"}
        yield {
            "type": "final_answer",
            "content": "def hello():\n    print('Hello, World!')",
        }

    async def test_concurrent_stream_limit(self):
        """Test concurrent stream limit enforcement"""
        intent = CodingIntent(
            action=CodingAction.IMPLEMENT,
            targets=["test.py"],
            scope="file",
            original_request="test request",
            confidence=0.9,
            context_required=[],
        )

        session_context = {"websocket": MockWebSocket()}

        # Fill up to max concurrent streams
        active_streams = []

        # Mock ReAct engine to return infinite stream
        async def infinite_stream():
            while True:
                yield {"type": "thought", "content": "thinking..."}
                await asyncio.sleep(0.1)

        with patch(
            "core.terminal.streaming.streaming_orchestrator.get_react_engine"
        ) as mock_engine:
            mock_engine.return_value.stream_reasoning = AsyncMock(
                return_value=infinite_stream()
            )

            # Start max_concurrent_streams
            for i in range(self.orchestrator.max_concurrent_streams):
                stream = self.orchestrator.stream_response(intent, session_context)
                active_streams.append(stream)
                # Start but don't consume
                await stream.__anext__()

            # Next stream should raise error
            with pytest.raises(Exception) as exc_info:
                extra_stream = self.orchestrator.stream_response(
                    intent, session_context
                )
                await extra_stream.__anext__()

            assert "Maximum concurrent streams exceeded" in str(exc_info.value)

    async def test_stream_cancellation(self):
        """Test stream cancellation"""
        intent = CodingIntent(
            action=CodingAction.IMPLEMENT,
            targets=["test.py"],
            scope="file",
            original_request="test request",
            confidence=0.9,
            context_required=[],
        )

        session_context = {"websocket": self.mock_websocket}

        # Start a stream
        with patch(
            "core.terminal.streaming.streaming_orchestrator.get_react_engine"
        ) as mock_engine:
            mock_engine.return_value.stream_reasoning = AsyncMock(
                return_value=self._mock_react_stream()
            )

            stream = self.orchestrator.stream_response(intent, session_context)
            first_chunk = await stream.__anext__()

            # Get stream ID from active streams
            stream_ids = self.orchestrator.get_active_stream_ids()
            assert len(stream_ids) == 1

            stream_id = stream_ids[0]

            # Cancel the stream
            result = await self.orchestrator.cancel_stream(stream_id)
            assert result is True

            # Should have sent cancellation message
            assert len(self.mock_websocket.sent_messages) > 0
            cancel_message = self.mock_websocket.sent_messages[-1]
            assert cancel_message["type"] == WSMessageType.CANCEL.value

    async def test_metrics_collection(self):
        """Test streaming metrics collection"""
        initial_metrics = await self.orchestrator.get_stream_metrics()

        # Should have initial state
        assert initial_metrics["active_streams"] == 0
        assert initial_metrics["total_streams"] >= 0
        assert "runtime_seconds" in initial_metrics
        assert "tokens_per_second" in initial_metrics

    async def test_heartbeat_functionality(self):
        """Test heartbeat sending"""
        # Create a mock context
        context = StreamingContext(
            stream_id="test-stream",
            intent=CodingIntent(
                action=CodingAction.IMPLEMENT,
                targets=["test.py"],
                scope="file",
                original_request="test",
                confidence=0.9,
                context_required=[],
            ),
            session_context={},
            websocket=self.mock_websocket,
        )

        self.orchestrator.active_streams["test-stream"] = context

        # Send heartbeat
        result = await self.orchestrator.send_heartbeat("test-stream")
        assert result is True

        # Should have sent heartbeat message
        assert len(self.mock_websocket.sent_messages) == 1
        heartbeat_msg = self.mock_websocket.sent_messages[0]
        assert heartbeat_msg["type"] == WSMessageType.HEARTBEAT.value

    async def test_cleanup_inactive_streams(self):
        """Test cleanup of inactive streams"""
        # Create old context
        old_context = StreamingContext(
            stream_id="old-stream",
            intent=CodingIntent(
                action=CodingAction.IMPLEMENT,
                targets=["test.py"],
                scope="file",
                original_request="test",
                confidence=0.9,
                context_required=[],
            ),
            session_context={},
            websocket=MockWebSocket(),
        )

        # Make it appear old
        old_context.last_sent_at = datetime.utcnow().replace(hour=0)  # Very old
        self.orchestrator.active_streams["old-stream"] = old_context

        # Cleanup with 0 minute timeout (should cleanup immediately)
        cleanup_count = await self.orchestrator.cleanup_inactive_streams(
            timeout_minutes=0
        )

        assert cleanup_count == 1
        assert "old-stream" not in self.orchestrator.active_streams


class TestIntegration:
    """Integration tests for streaming orchestrator"""

    async def test_full_streaming_workflow(self):
        """Test complete streaming workflow from start to finish"""
        orchestrator = StreamingOrchestrator()
        mock_websocket = MockWebSocket()

        intent = CodingIntent(
            action=CodingAction.IMPLEMENT,
            targets=["calculator.py"],
            scope="file",
            original_request="create a simple calculator class",
            confidence=0.9,
            context_required=[],
        )

        session_context = {
            "websocket": mock_websocket,
            "session_id": "integration-test",
        }

        # Mock ReAct engine with realistic response
        def mock_calculator_stream():
            async def _stream():
                yield {
                    "type": "thought",
                    "content": "I'll create a simple calculator class with basic operations",
                }
                yield {
                    "type": "action",
                    "content": "write_file",
                    "input": "calculator.py",
                }
                yield {"type": "observation", "content": "Creating calculator.py file"}
                yield {
                    "type": "final_answer",
                    "content": """class Calculator:
    def __init__(self):
        pass

    def add(self, a, b):
        return a + b

    def subtract(self, a, b):
        return a - b

    def multiply(self, a, b):
        return a * b

    def divide(self, a, b):
        if b == 0:
            raise ValueError("Cannot divide by zero")
        return a / b""",
                }

            return _stream()

        with patch(
            "core.terminal.streaming.streaming_orchestrator.get_react_engine"
        ) as mock_engine:
            mock_engine.return_value.stream_reasoning = AsyncMock(
                return_value=mock_calculator_stream()
            )

            # Collect all chunks
            chunks = []
            async for chunk in orchestrator.stream_response(intent, session_context):
                chunks.append(chunk)

            # Verify streaming workflow
            assert len(chunks) > 0

            # Should have different chunk types
            chunk_types = set(chunk.type for chunk in chunks)
            assert len(chunk_types) > 1

            # Should have code chunks with syntax highlighting
            code_chunks = [
                chunk for chunk in chunks if chunk.type == WSMessageType.CODE.value
            ]
            assert len(code_chunks) > 0

            # Code chunks should have syntax metadata
            for chunk in code_chunks[:5]:  # Check first few code chunks
                assert "syntax_type" in chunk.metadata
                assert "language" in chunk.metadata
                assert chunk.metadata["language"] == "python"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
