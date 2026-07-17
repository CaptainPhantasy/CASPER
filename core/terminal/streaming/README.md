# Terminal Streaming Engine

Real-time streaming orchestrator for CASPER terminal with token-by-token code generation, syntax highlighting, and backpressure handling.

## Features

- **Token-by-token streaming**: Code is generated and sent character by character with realistic delays
- **Real-time syntax highlighting**: Python, JavaScript, TypeScript, Java, and Rust support
- **Backpressure handling**: Automatic flow control when clients can't keep up
- **WebSocket protocol**: Full integration with CASPER's WebSocket infrastructure
- **Performance metrics**: Real-time monitoring and statistics
- **Stream management**: Cancellation, heartbeat, and cleanup capabilities

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                 Streaming Orchestrator                       │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐      │
│  │   Syntax     │  │ Backpressure │  │    Stream    │      │
│  │ Highlighter  │  │   Handler    │  │   Manager    │      │
│  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘      │
│         │                  │                  │              │
│         └──────────────────┼──────────────────┘              │
│                            │                                 │
│  ┌─────────────────────────▼─────────────────────────┐      │
│  │            ReAct Engine Integration                │      │
│  └─────────────────────────┬─────────────────────────┘      │
│                            │                                 │
│  ┌─────────────────────────▼─────────────────────────┐      │
│  │          WebSocket Message Protocol                │      │
│  └─────────────────────────────────────────────────────      │
└─────────────────────────────────────────────────────────────┘
```

## Usage

### Basic Streaming

```python
from core.terminal.streaming import get_streaming_orchestrator
from core.terminal.interfaces import CodingIntent, CodingAction

# Create a coding intent
intent = CodingIntent(
    action=CodingAction.IMPLEMENT,
    targets=["calculator.py"],
    scope="file",
    original_request="create a calculator class with basic operations",
    confidence=0.9,
    context_required=["project_structure"]
)

# Session context with WebSocket
session_context = {
    "websocket": websocket,
    "session_id": "user-session-123"
}

# Stream the response
orchestrator = get_streaming_orchestrator()

async for chunk in orchestrator.stream_response(intent, session_context):
    print(f"[{chunk.type}] {chunk.content}")

    # Handle different chunk types
    if chunk.type == "code":
        # Code chunk with syntax highlighting
        syntax_type = chunk.metadata.get("syntax_type")
        color = chunk.metadata.get("color")
        # Apply to terminal display
    elif chunk.type == "thought":
        # AI reasoning step
        reasoning = chunk.content
    elif chunk.type == "result":
        # Execution result
        result = chunk.content
```

### WebSocket Integration

```python
from core.terminal.streaming.websocket_integration import create_enhanced_websocket_handler

# Enhance existing WebSocket handler
base_handler = TerminalWebSocketHandler()
enhanced_handler = create_enhanced_websocket_handler(base_handler)

# Handle streaming messages
async def handle_websocket_message(session_id: str, message: dict):
    if message["type"] == "streaming_request":
        await enhanced_handler.handle_streaming_command(session_id, message)
    elif message["type"] == "stream_cancel":
        await enhanced_handler.handle_stream_cancel(session_id, message)
    else:
        # Handle regular terminal messages
        await base_handler.handle_message(session_id, message)
```

### Client-Side WebSocket Protocol

```javascript
// Connect to streaming endpoint
const ws = new WebSocket('ws://localhost:8742/ws/terminal');

// Send streaming request
ws.send(JSON.stringify({
    type: "streaming_request",
    request: "implement a REST API for user authentication"
}));

// Handle streaming chunks
ws.onmessage = (event) => {
    const data = JSON.parse(event.data);

    if (data.type === "streaming_chunk") {
        const chunk = data;

        // Handle different chunk types
        switch (chunk.chunk_type) {
            case "thought":
                displayThought(chunk.content);
                break;
            case "code":
                displayCode(chunk.content, chunk.metadata);
                break;
            case "result":
                displayResult(chunk.content);
                break;
        }
    }
};

// Cancel stream
ws.send(JSON.stringify({
    type: "stream_cancel",
    stream_id: "stream-id-here"
}));
```

## Message Protocol

### Streaming Request
```json
{
    "type": "streaming_request",
    "request": "create a hello world function in Python"
}
```

### Streaming Chunk
```json
{
    "type": "streaming_chunk",
    "chunk_type": "code",
    "content": "def ",
    "metadata": {
        "syntax_type": "keyword",
        "color": "\033[38;5;33m",
        "position": 0,
        "line": 1,
        "column": 1,
        "language": "python"
    },
    "timestamp": "2025-09-25T06:00:00.000Z",
    "sequence": 1
}
```

### Stream Cancellation
```json
{
    "type": "stream_cancel",
    "stream_id": "uuid-stream-id"
}
```

### Streaming Status
```json
{
    "type": "streaming_status",
    "active_streams": 3,
    "stream_ids": ["uuid1", "uuid2", "uuid3"],
    "metrics": {
        "tokens_per_second": 45.2,
        "average_latency_ms": 12.5,
        "backpressure_events": 0
    }
}
```

## Syntax Highlighting

The streaming orchestrator supports real-time syntax highlighting for:

- **Python**: Keywords, strings, numbers, comments, functions, classes, decorators
- **JavaScript**: Keywords, strings, numbers, comments, functions
- **TypeScript**: Interfaces, type annotations, generics
- **Java**: Classes, methods, access modifiers
- **Rust**: Functions, structs, implementations

### Token Types

```python
class SyntaxType(Enum):
    KEYWORD = "keyword"        # Blue
    STRING = "string"          # Green
    NUMBER = "number"          # Orange
    COMMENT = "comment"        # Gray
    FUNCTION = "function"      # Yellow
    CLASS = "class"           # Red
    VARIABLE = "variable"     # White
    OPERATOR = "operator"     # Magenta
    PUNCTUATION = "punctuation" # Light Gray
```

## Backpressure Handling

The streaming orchestrator automatically handles client backpressure:

- **Buffer monitoring**: Tracks client buffer size
- **Threshold detection**: Applies backpressure at 80% buffer capacity
- **Exponential backoff**: Delays increase with repeated backpressure
- **Automatic recovery**: Resumes streaming when buffer clears

```python
# Configure backpressure settings
handler = BackpressureHandler(
    max_buffer_size=1024 * 1024  # 1MB buffer
)

# Check backpressure status
if await handler.check_backpressure(context):
    await handler.handle_backpressure(context)
```

## Performance Metrics

Real-time performance monitoring:

```python
metrics = await orchestrator.get_stream_metrics()

print(f"Active streams: {metrics['active_streams']}")
print(f"Tokens/sec: {metrics['tokens_per_second']}")
print(f"Avg latency: {metrics['average_latency_ms']}ms")
print(f"Backpressure events: {metrics['backpressure_events']}")
```

## Stream Management

### Heartbeat
```python
# Send heartbeat to keep stream alive
await orchestrator.send_heartbeat(stream_id)
```

### Cancellation
```python
# Cancel active stream
success = await orchestrator.cancel_stream(stream_id)
```

### Cleanup
```python
# Clean up inactive streams (older than 30 minutes)
cleaned = await orchestrator.cleanup_inactive_streams(30)
```

## Integration with ReAct Engine

The streaming orchestrator integrates seamlessly with CASPER's ReAct reasoning engine:

```python
# ReAct engine provides reasoning steps
async for reasoning_chunk in react_engine.stream_reasoning(task):
    # Convert to streaming chunk with syntax highlighting
    if reasoning_chunk.type == "final_answer":
        # Apply syntax highlighting to code
        async for highlighted_chunk in stream_highlighted_code(reasoning_chunk.content):
            yield highlighted_chunk
```

## Testing

Comprehensive test suite included:

```bash
# Run streaming orchestrator tests
python3 -m pytest tests/test_streaming_orchestrator.py -v

# Test syntax highlighting
python3 -m pytest tests/test_streaming_orchestrator.py::TestSyntaxHighlighter -v

# Test backpressure handling
python3 -m pytest tests/test_streaming_orchestrator.py::TestBackpressureHandler -v
```

## Error Handling

Robust error handling with proper cleanup:

```python
try:
    async for chunk in orchestrator.stream_response(intent, session_context):
        yield chunk
except StreamingError as e:
    # Handle streaming-specific errors
    logger.error(f"Streaming error: {e}")
except Exception as e:
    # Handle general errors
    logger.error(f"Unexpected error: {e}")
finally:
    # Automatic cleanup in finally block
    pass
```

## Production Considerations

- **Rate limiting**: Configure max concurrent streams per session
- **Memory management**: Set appropriate buffer sizes for your environment
- **Monitoring**: Use metrics for performance tuning
- **Security**: All streams inherit WebSocket security policies
- **Scalability**: Designed for production load with efficient memory usage

## Zero Tolerance Policy

This implementation has **ZERO TOLERANCE** for:
- ❌ Placeholders or mock implementations
- ❌ "Coming soon" or TODO comments
- ❌ Incomplete functionality
- ✅ Everything works in production immediately