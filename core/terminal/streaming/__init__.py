"""
Terminal Streaming Module
Real-time code generation with syntax highlighting and backpressure handling
"""

from .streaming_orchestrator import (
    StreamingOrchestrator,
    SyntaxHighlighter,
    BackpressureHandler,
    SyntaxToken,
    SyntaxType,
    get_streaming_orchestrator,
)

from .processor import StreamingProcessor

from .websocket_integration import (
    StreamingWebSocketHandler,
    enhanced_handle_message,
    create_enhanced_websocket_handler,
)

__all__ = [
    "StreamingOrchestrator",
    "SyntaxHighlighter",
    "BackpressureHandler",
    "SyntaxToken",
    "SyntaxType",
    "get_streaming_orchestrator",
    "StreamingProcessor",
    "StreamingWebSocketHandler",
    "enhanced_handle_message",
    "create_enhanced_websocket_handler",
]
