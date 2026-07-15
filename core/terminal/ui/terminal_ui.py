"""
Interactive Terminal UI for CASPER Prime - Production Grade Implementation
Implements ITerminalUI interface with multi-pane layout and advanced features.
"""

import asyncio
import logging
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, Any, List
from dataclasses import dataclass

# Rich imports for beautiful terminal output
from rich.console import Console, RenderableType
from rich.layout import Layout
from rich.panel import Panel
from rich.live import Live
from rich.progress import (
    Progress,
    TaskID,
    SpinnerColumn,
    TextColumn,
    BarColumn,
    TimeRemainingColumn,
)
from rich.syntax import Syntax
from rich.text import Text

# Prompt-toolkit imports for advanced input
from prompt_toolkit import Application
from prompt_toolkit.key_binding import KeyBindings
from prompt_toolkit.styles import Style as PTStyle
from prompt_toolkit.patch_stdout import patch_stdout

from ..interfaces import ITerminalUI, StreamChunk
from .coding_commands import CodingCommandDispatcher
from .feature_manager import COMMAND_HELP, LocalCommandResult, TerminalFeatureManager

logger = logging.getLogger(__name__)


@dataclass
class PaneState:
    """State for individual UI panes"""

    title: str
    content: str
    visible: bool = True
    height: int = 10
    syntax_language: Optional[str] = None


class TerminalUI(ITerminalUI):
    """
    Production-grade terminal UI with multi-pane layout and streaming support.
    Implements the ITerminalUI interface completely with beautiful Rich output.
    """

    def __init__(
        self,
        title: str = "CASPER Prime Terminal",
        state_root: Optional[Path | str] = None,
        project_root: Optional[Path | str] = None,
        console: Optional[Console] = None,
    ):
        self.features = TerminalFeatureManager(state_root)
        self.project_root = Path(project_root or Path.cwd()).expanduser().resolve()
        self.coding_commands = CodingCommandDispatcher(
            self.project_root,
            self.features,
        )
        COMMAND_HELP.update(self.coding_commands.help_entries())
        self.console = console or Console(
            force_terminal=None,
            no_color=self.features.no_color,
            record=True,
        )
        self.layout = Layout(name="root")
        self.live: Optional[Live] = None
        self.running = False
        self.title = title
        self._runner_task: Optional[asyncio.Task] = None

        # Multi-pane state
        self.panes: Dict[str, PaneState] = {
            "reasoning": PaneState(
                title="🧠 Reasoning Chain",
                content="Ready to process your request...",
                height=15,
                syntax_language="text",
            ),
            "input": PaneState(
                title="📝 Input/Commands",
                content="casper> ",
                height=5,
                syntax_language="bash",
            ),
            "code": PaneState(
                title="💻 Generated Code",
                content="# Code output will appear here",
                height=20,
                syntax_language="python",
            ),
            "tests": PaneState(
                title="🧪 Tests & Results",
                content="# Test results and logs",
                height=10,
                syntax_language="text",
            ),
        }

        # Progress tracking
        self.progress_tasks: Dict[str, TaskID] = {}
        self.progress: Optional[Progress] = None

        # Keyboard bindings
        self.kb = KeyBindings()
        self._setup_key_bindings()

        # Application state
        self.app: Optional[Application] = None
        self.input_buffer = ""
        self.history: List[str] = self.features.history()
        self.history_index = 0

        # Streaming state
        self.stream_active = False
        self.chunk_queue = asyncio.Queue()

    def _setup_key_bindings(self):
        """Setup keyboard shortcuts for terminal interaction"""

        @self.kb.add("c-c")  # Ctrl+C
        def _(event):
            """Cancel current operation"""
            event.app.exit(exception=KeyboardInterrupt)

        @self.kb.add("c-d")  # Ctrl+D
        def _(event):
            """Exit application"""
            event.app.exit()

        @self.kb.add("c-l")  # Ctrl+L
        def _(event):
            """Clear screen"""
            asyncio.create_task(self.clear_screen())

        @self.kb.add("c-r")  # Ctrl+R
        def _(event):
            """Refresh layout"""
            self._refresh_layout()

        @self.kb.add("f1")  # F1
        def _(event):
            """Show help"""
            self._show_help_overlay()

        @self.kb.add("f5")  # F5
        def _(event):
            """Toggle reasoning pane"""
            self._toggle_pane("reasoning")

        @self.kb.add("f6")  # F6
        def _(event):
            """Toggle code pane"""
            self._toggle_pane("code")

        @self.kb.add("f7")  # F7
        def _(event):
            """Toggle tests pane"""
            self._toggle_pane("tests")

    async def start_ui(self) -> None:
        """Initialize the TUI and schedule its renderer without blocking input."""
        if self.running:
            return

        self.running = True

        # Initialize rich progress
        self.progress = Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(bar_width=None),
            "[progress.percentage]{task.percentage:>3.1f}%",
            TimeRemainingColumn(),
            console=self.console,
            transient=True,
        )

        # Setup layout
        self._setup_layout()

        # Start the live display in a background task so initialization can
        # continue into the interactive prompt loop.
        self.live = Live(self.layout, console=self.console, refresh_per_second=10)
        self._runner_task = asyncio.create_task(
            self._run_ui(), name="casper-tui-renderer"
        )
        await asyncio.sleep(0)

    async def _run_ui(self) -> None:
        """Own the Rich live context and streaming consumer."""
        if not self.live:
            return
        with self.live:
            await self._show_startup_banner()
            chunk_task = asyncio.create_task(self._process_chunks())
            try:
                while self.running:
                    await asyncio.sleep(0.1)
            finally:
                chunk_task.cancel()
                try:
                    await chunk_task
                except asyncio.CancelledError:
                    pass

    def refresh_console_capabilities(self) -> None:
        """Apply capability-aware color settings to the active console."""
        self.console.no_color = self.features.no_color
        self._refresh_layout()

    def refresh_layout(self) -> None:
        """Public refresh hook used by deterministic local commands."""
        self._refresh_layout()

    def rebuild_layout(self) -> None:
        """Public layout rebuild hook used by deterministic local commands."""
        self._setup_layout()

    def _setup_layout(self):
        """Setup the multi-pane layout structure"""
        self.layout.split(
            Layout(name="header", size=3),
            Layout(name="main", ratio=1),
            Layout(name="footer", size=2),
        )

        # Split main into panes based on current visibility
        main_panes = []

        if self.panes["reasoning"].visible:
            main_panes.append(
                Layout(name="reasoning", size=self.panes["reasoning"].height)
            )

        if self.panes["input"].visible:
            main_panes.append(Layout(name="input", size=self.panes["input"].height))

        if self.panes["code"].visible:
            main_panes.append(Layout(name="code", size=self.panes["code"].height))

        if self.panes["tests"].visible:
            main_panes.append(Layout(name="tests", size=self.panes["tests"].height))

        self.layout["main"].split(*main_panes)

        # Update content
        self._refresh_layout()

    def _refresh_layout(self):
        """Refresh all pane content"""
        if not self.running or not self.layout:
            return

        try:
            # Header
            if "header" in self.layout:
                self.layout["header"].update(
                    Panel(
                        Text(
                            f"{self.title} - Interactive Coding Terminal", style="bold"
                        ),
                        style=self.features.theme["border"],
                        padding=(0, 1),
                    )
                )

            # Update visible panes
            for pane_name, pane in self.panes.items():
                if pane.visible and pane_name in self.layout:
                    content = self._format_pane_content(pane)
                    self.layout[pane_name].update(
                        Panel(
                            content,
                            title=f"[bold]{pane.title}[/bold]",
                            border_style=(
                                self.features.theme["border"]
                                if pane_name == "input"
                                else "dim"
                            ),
                            padding=(0, 1),
                        )
                    )

            # Footer with shortcuts
            if "footer" in self.layout:
                bindings = self.features.settings.get("shortcuts", {})
                shortcuts = " ".join(
                    f"[{keys}] {action.title()}" for action, keys in bindings.items()
                )
                if self.features.notifications:
                    shortcuts += f" | {self.features.notifications[-1]}"
                self.layout["footer"].update(
                    Panel(Text(shortcuts, style="dim"), style="dim", padding=(0, 1))
                )
        except Exception as exc:
            logger.debug("TUI layout refresh failed: %s", exc)

    def _format_pane_content(self, pane: PaneState) -> RenderableType:
        """Format content for a pane with syntax highlighting"""
        if pane.syntax_language and pane.content.strip():
            try:
                return Syntax(
                    pane.content,
                    pane.syntax_language,
                    theme=self.features.theme["syntax"],
                    line_numbers=(
                        True
                        if pane.syntax_language
                        in ["python", "javascript", "typescript"]
                        else False
                    ),
                    word_wrap=True,
                )
            except Exception:
                # Fallback to plain text
                return Text(pane.content, style="white")
        else:
            return Text(pane.content, style="white")

    async def display_stream(self, chunk: StreamChunk) -> None:
        """Display a streaming chunk in the appropriate pane"""
        if not self.running:
            return

        await self.chunk_queue.put(chunk)

    async def _process_chunks(self):
        """Process streaming chunks and update UI"""
        while self.running:
            try:
                chunk = await asyncio.wait_for(self.chunk_queue.get(), timeout=0.1)
                await self._handle_chunk(chunk)
            except asyncio.TimeoutError:
                continue
            except asyncio.CancelledError:
                break
            except Exception as e:
                # Only print error if running to avoid test noise
                if self.running:
                    self.console.print(f"[red]Error processing chunk: {e}[/red]")

    async def _handle_chunk(self, chunk: StreamChunk):
        """Handle individual stream chunks"""
        chunk_type = chunk.type.lower()
        self.features.remember_edit(self.panes)
        target_pane = "reasoning"

        if chunk_type == "thought" or chunk_type == "reasoning":
            # Add to reasoning pane
            current = self.panes["reasoning"].content
            if current == "Ready to process your request...":
                current = ""

            timestamp = chunk.timestamp.strftime("%H:%M:%S")
            new_content = f"{current}\n[{timestamp}] 💭 {chunk.content}"
            self.panes["reasoning"].content = new_content.strip()

        elif chunk_type == "action" or chunk_type == "command":
            target_pane = "input"
            # Add to input pane
            current = self.panes["input"].content
            new_content = f"{current}\n🔧 Action: {chunk.content}"
            self.panes["input"].content = new_content.strip()

        elif chunk_type == "code":
            target_pane = "code"
            # Update code pane
            self.panes["code"].content = chunk.content
            # Try to detect language from metadata
            if "language" in chunk.metadata:
                self.panes["code"].syntax_language = chunk.metadata["language"]

        elif chunk_type == "test" or chunk_type == "result":
            target_pane = "tests"
            # Add to tests pane
            current = self.panes["tests"].content
            if current == "# Test results and logs":
                current = ""

            timestamp = chunk.timestamp.strftime("%H:%M:%S")
            symbol = "🧪" if chunk_type == "test" else "📊"
            new_content = f"{current}\n[{timestamp}] {symbol} {chunk.content}"
            self.panes["tests"].content = new_content.strip()

        elif chunk_type == "error":
            # Add error to reasoning pane with red styling
            current = self.panes["reasoning"].content
            timestamp = chunk.timestamp.strftime("%H:%M:%S")
            new_content = f"{current}\n[{timestamp}] ❌ ERROR: {chunk.content}"
            self.panes["reasoning"].content = new_content.strip()

        self.features.append_transcript(target_pane, chunk_type, chunk.content)
        self.features.autosave(self.panes)
        self._refresh_layout()

    async def get_user_input(self, prompt: str = "casper> ") -> str:
        """Get input from user with advanced prompt-toolkit features"""
        if not self.running:
            return ""

        # Update input pane prompt
        self.panes["input"].content = prompt
        self._refresh_layout()

        # Use prompt-toolkit for advanced input
        try:
            with patch_stdout():
                loop = asyncio.get_event_loop()
                result = await loop.run_in_executor(None, self._get_input_sync, prompt)
                return result or ""
        except (KeyboardInterrupt, EOFError):
            return ""

    def _get_input_sync(self, prompt: str) -> str:
        """Synchronous input handler for prompt-toolkit"""
        from prompt_toolkit import prompt
        from prompt_toolkit.completion import WordCompleter
        from prompt_toolkit.history import InMemoryHistory
        from prompt_toolkit.auto_suggest import AutoSuggestFromHistory

        # Setup completions
        casper_commands = sorted(COMMAND_HELP) + ["exit", "quit"]

        self.history = self.features.history()
        completer = WordCompleter(casper_commands, ignore_case=True, sentence=True)
        history = InMemoryHistory()

        # Add previous commands to history
        for cmd in self.history:
            history.append_string(cmd)

        try:
            result = prompt(
                prompt,
                completer=completer,
                history=history,
                auto_suggest=AutoSuggestFromHistory(),
                key_bindings=self.kb,
                style=PTStyle.from_dict(
                    {
                        "prompt": "#ansibrightcyan bold",
                        "input": "#ansiwhite",
                    }
                ),
            )

            self.features.record_history(result)
            self.history = self.features.history()

            return result
        except (KeyboardInterrupt, EOFError):
            return ""

    async def execute_command(self, command_line: str) -> LocalCommandResult:
        """Run a deterministic TUI command or return an unhandled result."""
        result = await self.coding_commands.execute(self, command_line)
        if not result.handled:
            result = await self.features.execute(self, command_line)
        if result.handled and result.message:
            self.features.remember_edit(self.panes)
            current = self.panes["reasoning"].content
            if current == "Ready to process your request...":
                current = ""
            self.panes["reasoning"].content = f"{current}\n{result.message}".strip()
            self.features.append_transcript(
                "reasoning", "local-command", result.message
            )
            self.features.autosave(self.panes)
            self._refresh_layout()
        return result

    def bind_integration(self, integration: Any) -> None:
        """Expose live MCP, agent, session, and pipeline state to commands."""
        self.coding_commands.bind_integration(integration)

    async def show_progress(
        self, message: str, percentage: Optional[float] = None
    ) -> None:
        """Show progress indicator with optional percentage"""
        if not self.progress:
            return

        # Update or create progress task
        if message not in self.progress_tasks:
            self.progress_tasks[message] = self.progress.add_task(message, total=100)

        task_id = self.progress_tasks[message]

        if percentage is not None:
            self.progress.update(task_id, completed=percentage)
        else:
            # Advance by small amount for indeterminate progress
            self.progress.advance(task_id, 0.5)

    async def clear_screen(self) -> None:
        """Clear the terminal screen and reset panes"""
        self.features.remember_edit(self.panes)
        # Clear all pane content
        self.panes["reasoning"].content = "Ready to process your request..."
        self.panes["input"].content = "casper> "
        self.panes["code"].content = "# Code output will appear here"
        self.panes["tests"].content = "# Test results and logs"

        # Clear progress tasks
        if self.progress:
            for task_id in self.progress_tasks.values():
                self.progress.remove_task(task_id)
            self.progress_tasks.clear()

        self.features.autosave(self.panes)
        self._refresh_layout()

    async def show_error(self, error: str) -> None:
        """Display error message prominently"""
        error_chunk = StreamChunk(
            type="error",
            content=error,
            metadata={"severity": "error"},
            timestamp=datetime.now(),
            sequence_number=0,
        )

        await self.display_stream(error_chunk)

        # Also show in console for immediate visibility
        self.console.print(f"[bold red]❌ Error:[/bold red] {error}")

    def _toggle_pane(self, pane_name: str):
        """Toggle visibility of a pane"""
        if pane_name in self.panes:
            self.panes[pane_name].visible = not self.panes[pane_name].visible
            self.features.autosave(self.panes)
            if self.running:
                self._setup_layout()  # Rebuild layout

    def _show_help_overlay(self):
        """Show help information overlay"""
        help_text = """
🎯 CASPER Prime Terminal UI - Keyboard Shortcuts

Navigation:
  F1        Show this help
  F5        Toggle reasoning pane
  F6        Toggle code pane
  F7        Toggle tests pane

Control:
  Ctrl+C    Cancel current operation
  Ctrl+D    Exit application
  Ctrl+L    Clear screen
  Ctrl+R    Refresh layout

Input:
  Tab       Auto-complete commands
  ↑/↓       Navigate command history
  Enter     Execute command
        """

        # Add to reasoning pane temporarily
        old_content = self.panes["reasoning"].content
        self.panes["reasoning"].content = help_text
        self._refresh_layout()

        # Restore after a delay
        async def restore_content():
            await asyncio.sleep(5)
            self.panes["reasoning"].content = old_content
            self._refresh_layout()

        asyncio.create_task(restore_content())

    async def _show_startup_banner(self):
        """Show beautiful startup banner"""
        if self.features.settings.get("plain"):
            banner = "CASPER Prime Terminal UI\nInteractive Coding Assistant\nReady."
        else:
            banner = """
╔══════════════════════════════════════════════════════════════════════╗
║                     🚀 CASPER Prime Terminal UI                     ║
║                      Interactive Coding Assistant                    ║
╚══════════════════════════════════════════════════════════════════════╝

Welcome to the advanced terminal interface for CASPER Prime!

💡 Features:
   • Multi-pane layout with reasoning, code, and test output
   • Real-time streaming of AI responses
   • Syntax highlighting and code formatting
   • Advanced input with auto-completion
   • Keyboard shortcuts for efficient navigation

🎯 Ready to help you build amazing software!
        """

        self.panes["reasoning"].content = banner
        self._refresh_layout()
        if not self.features.settings.get("reduced_motion"):
            await asyncio.sleep(0.15)

    async def shutdown(self):
        """Gracefully shutdown the terminal UI"""
        if self.panes:
            self.features.autosave(self.panes)
        self.running = False

        current = asyncio.current_task()
        if self._runner_task and self._runner_task is not current:
            self._runner_task.cancel()
            try:
                await self._runner_task
            except asyncio.CancelledError:
                pass
            self._runner_task = None

        if self.live:
            self.live.stop()

        if self.progress:
            self.progress.stop()

        self.progress_tasks.clear()

        self.console.print("[dim]Terminal UI shutdown complete.[/dim]")

    # Context manager support
    async def __aenter__(self):
        await self.start_ui()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.shutdown()


# Factory function for easy instantiation
def create_terminal_ui(
    title: str = "CASPER Prime Terminal",
    state_root: Optional[Path | str] = None,
    project_root: Optional[Path | str] = None,
) -> TerminalUI:
    """Factory function to create a configured TerminalUI instance"""
    return TerminalUI(
        title=title,
        state_root=state_root,
        project_root=project_root,
    )


# Example usage and testing
async def main():
    """Example usage of the TerminalUI"""
    ui = create_terminal_ui("CASPER Demo")

    async with ui:
        # Simulate streaming chunks
        test_chunks = [
            StreamChunk(
                type="thought",
                content="Analyzing the user request...",
                metadata={},
                timestamp=datetime.now(),
                sequence_number=1,
            ),
            StreamChunk(
                type="code",
                content="def hello_world():\n    print('Hello from CASPER!')\n    return True",
                metadata={"language": "python"},
                timestamp=datetime.now(),
                sequence_number=2,
            ),
            StreamChunk(
                type="test",
                content="Running tests... All passed! ✅",
                metadata={},
                timestamp=datetime.now(),
                sequence_number=3,
            ),
        ]

        # Stream the chunks
        for chunk in test_chunks:
            await ui.display_stream(chunk)
            await asyncio.sleep(1)

        # Get user input
        user_input = await ui.get_user_input("Enter a command: ")
        print(f"User entered: {user_input}")

        await asyncio.sleep(5)  # Keep running for demo


if __name__ == "__main__":
    asyncio.run(main())
