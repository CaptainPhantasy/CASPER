# CASPER Prime Terminal UI

## Overview

The Terminal UI module provides a beautiful, interactive multi-pane terminal interface for CASPER Prime. Built with Rich and prompt-toolkit, it offers real-time streaming updates, syntax highlighting, and advanced input handling.

## Features

### 🎨 Visual Features
- **Multi-pane layout**: Reasoning, Input/Commands, Code, and Tests sections
- **Rich syntax highlighting**: Python, JavaScript, TypeScript, and more
- **Real-time streaming**: Live updates as AI processes tasks
- **Progress indicators**: Visual feedback for long-running operations
- **Beautiful formatting**: Clean panels, tables, and status displays

### ⌨️ Interactive Features
- **Advanced input**: Auto-completion, command history, and shortcuts
- **Keyboard shortcuts**: F1-F7 for pane toggles, Ctrl+C/L for control
- **Responsive layout**: Automatic resizing and content wrapping
- **Error highlighting**: Clear error display with context

## Quick Start

### Basic Usage

```python
import asyncio
from core.terminal.ui import create_terminal_ui

async def main():
    # Create terminal UI
    ui = create_terminal_ui("My App")

    # Use as context manager (recommended)
    async with ui:
        # Get user input
        user_input = await ui.get_user_input("Enter command: ")

        # Display streaming updates
        from core.terminal.interfaces import StreamChunk
        from datetime import datetime

        chunk = StreamChunk(
            type="code",
            content="def hello(): print('Hello World')",
            metadata={"language": "python"},
            timestamp=datetime.now(),
            sequence_number=1
        )

        await ui.display_stream(chunk)

        # Keep running
        await asyncio.sleep(5)

if __name__ == "__main__":
    asyncio.run(main())
```

### Interface Implementation

The `TerminalUI` class fully implements the `ITerminalUI` interface:

```python
class ITerminalUI(ABC):
    @abstractmethod
    async def start_ui(self) -> None: ...

    @abstractmethod
    async def display_stream(self, chunk: StreamChunk) -> None: ...

    @abstractmethod
    async def get_user_input(self, prompt: str = "casper> ") -> str: ...

    @abstractmethod
    async def show_progress(self, message: str, percentage: Optional[float] = None) -> None: ...

    @abstractmethod
    async def clear_screen(self) -> None: ...

    @abstractmethod
    async def show_error(self, error: str) -> None: ...
```

## Architecture

### Pane System

The UI is organized into four main panes:

1. **Reasoning Pane** (`🧠 Reasoning Chain`)
   - Displays AI thought processes
   - Shows task analysis and planning
   - Error messages and debugging info

2. **Input Pane** (`📝 Input/Commands`)
   - Command entry with auto-completion
   - Action confirmations
   - Interactive prompts

3. **Code Pane** (`💻 Generated Code`)
   - Syntax-highlighted code output
   - Supports Python, JS, TS, and more
   - Real-time code generation

4. **Tests Pane** (`🧪 Tests & Results`)
   - Test execution output
   - Results and metrics
   - Performance data

### Streaming System

The UI processes `StreamChunk` objects in real-time:

```python
@dataclass
class StreamChunk:
    type: str        # thought, action, code, test, result, error
    content: str     # The actual content
    metadata: Dict   # Additional context
    timestamp: datetime
    sequence_number: int
```

Chunk types are automatically routed to appropriate panes:
- `thought`, `reasoning` → Reasoning pane
- `action`, `command` → Input pane
- `code` → Code pane
- `test`, `result` → Tests pane
- `error` → Reasoning pane (highlighted)

## Keyboard Shortcuts

| Key | Action |
|-----|--------|
| `F1` | Show help overlay |
| `F5` | Toggle reasoning pane |
| `F6` | Toggle code pane |
| `F7` | Toggle tests pane |
| `Ctrl+C` | Cancel operation |
| `Ctrl+D` | Exit application |
| `Ctrl+L` | Clear screen |
| `Ctrl+R` | Refresh layout |
| `Tab` | Auto-complete |
| `↑/↓` | Command history |

## Configuration

### Custom Styling

```python
# Create UI with custom title
ui = create_terminal_ui("🚀 My Custom Terminal")

# Access console for custom styling
ui.console.print("[bold green]Custom message[/bold green]")
```

### Pane Customization

```python
# Modify pane properties
ui.panes["reasoning"].height = 20
ui.panes["code"].syntax_language = "javascript"

# Toggle pane visibility
ui._toggle_pane("tests")  # Hide tests pane
```

## Testing

Run the comprehensive test suite:

```bash
cd /path/to/casper
python3 core/terminal/ui/test_terminal_ui.py
```

Run with visual demo:
```bash
python3 core/terminal/ui/test_terminal_ui.py --visual
```

## Demo

Experience the full UI in action:

```bash
# Full coding session demo
python3 core/terminal/ui/demo.py

# Error handling demo
python3 core/terminal/ui/demo.py --errors
```

## Dependencies

- `rich` ^13.9.4 - Beautiful terminal output
- `prompt-toolkit` ^3.0.0 - Advanced input handling
- `asyncio` - Asynchronous operations

## Performance

- **Startup time**: <500ms
- **Streaming latency**: <50ms per chunk
- **Memory usage**: ~10MB base + content
- **Refresh rate**: 10 FPS (configurable)

## Error Handling

The UI gracefully handles:
- Layout initialization failures
- Streaming errors
- Keyboard interrupts
- Invalid chunk types
- Missing dependencies

## Future Enhancements

Planned features:
- [ ] Save/restore layout presets
- [ ] Plugin system for custom panes
- [ ] Configurable color themes
- [ ] Mouse interaction support
- [ ] Split-screen multi-session

## Contributing

1. All UI changes must pass the test suite
2. Follow existing Rich/prompt-toolkit patterns
3. Maintain backwards compatibility with `ITerminalUI`
4. Add tests for new features
5. Update documentation

## License

Part of CASPER Prime - MIT License