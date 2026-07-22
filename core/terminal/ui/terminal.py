"""
CASPER Prime Terminal UI - OMEGA Agent Component
Rich terminal user interface for interactive coding sessions.
PRODUCTION GRADE - Full implementation of ITerminalUI interface.
"""

import asyncio
import sys
import os
from typing import Optional, Dict, Any, List
from datetime import datetime
import logging

# Rich terminal library imports
try:
    from rich.console import Console
    from rich.panel import Panel
    from rich.progress import Progress, TaskID, SpinnerColumn, TextColumn, BarColumn, TimeElapsedColumn
    from rich.syntax import Syntax
    from rich.markdown import Markdown
    from rich.table import Table
    from rich.layout import Layout
    from rich.live import Live
    from rich.text import Text
    from rich.prompt import Prompt
    RICH_AVAILABLE = True
except ImportError:
    RICH_AVAILABLE = False
    logging.warning("Rich library not available, falling back to basic terminal UI")

from ..interfaces import ITerminalUI, StreamChunk, WSMessageType

logger = logging.getLogger(__name__)


class TerminalUI(ITerminalUI):
    """
    Production-grade terminal UI for CASPER Prime Terminal.
    Provides rich interactive interface with streaming support.
    """

    def __init__(self):
        """Initialize the terminal UI with rich components."""
        if RICH_AVAILABLE:
            self.console = Console()
            self.progress: Optional[Progress] = None
            self.current_task: Optional[TaskID] = None
            self.live_display: Optional[Live] = None
        else:
            self.console = None

        self.ui_state = {
            "started": False,
            "current_prompt": "casper> ",
            "streaming": False,
            "last_chunk_type": None
        }

        # UI Layout components
        self.layout = None
        self.content_area = ""
        self.status_area = ""

        # Color scheme
        self.colors = {
            "primary": "cyan",
            "secondary": "blue",
            "success": "green",
            "warning": "yellow",
            "error": "red",
            "info": "white",
            "code": "bright_black"
        }

    async def start_ui(self) -> None:
        """Start the rich terminal UI with layout and components."""
        try:
            if RICH_AVAILABLE:
                await self._start_rich_ui()
            else:
                await self._start_basic_ui()

            self.ui_state["started"] = True
            logger.info("Terminal UI started successfully")

        except Exception as e:
            logger.error(f"Failed to start terminal UI: {e}")
            # Fall back to basic UI
            await self._start_basic_ui()
            self.ui_state["started"] = True

    async def _start_rich_ui(self) -> None:
        """Start the rich terminal interface."""
        # Clear screen and show welcome
        self.console.clear()

        welcome_panel = Panel.fit(
            "[bold cyan]CASPER Prime Terminal[/bold cyan]\n"
            "[dim]AI-Powered Coding Assistant[/dim]\n\n"
            "Type your coding requests in natural language\n"
            "Examples:\n"
            "• [green]implement a user authentication class[/green]\n"
            "• [green]debug the login function[/green]\n"
            "• [green]explain how this algorithm works[/green]\n"
            "• [green]review my code for security issues[/green]\n\n"
            "[dim]Type 'help' for more commands or 'exit' to quit[/dim]",
            title="Welcome",
            border_style="cyan"
        )

        self.console.print(welcome_panel)
        self.console.print()  # Empty line

        # Initialize progress display
        self.progress = Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
            TimeElapsedColumn(),
            console=self.console,
            transient=True
        )

    async def _start_basic_ui(self) -> None:
        """Start basic terminal interface without rich."""
        os.system('clear' if os.name == 'posix' else 'cls')
        print("=" * 60)
        print("CASPER Prime Terminal - AI-Powered Coding Assistant")
        print("=" * 60)
        print("\nType your coding requests in natural language")
        print("Examples:")
        print("  • implement a user authentication class")
        print("  • debug the login function")
        print("  • explain how this algorithm works")
        print("  • review my code for security issues")
        print("\nType 'help' for more commands or 'exit' to quit\n")

    async def display_stream(self, chunk: StreamChunk) -> None:
        """Display a streaming chunk in the terminal UI."""
        try:
            if RICH_AVAILABLE:
                await self._display_rich_stream(chunk)
            else:
                await self._display_basic_stream(chunk)

            self.ui_state["last_chunk_type"] = chunk.type

        except Exception as e:
            logger.error(f"Failed to display stream chunk: {e}")
            await self._display_fallback_chunk(chunk)

    async def _display_rich_stream(self, chunk: StreamChunk) -> None:
        """Display streaming chunk with rich formatting."""
        timestamp = chunk.timestamp.strftime("%H:%M:%S")

        if chunk.type == "thought":
            # Display thinking process
            panel = Panel(
                f"[dim]{chunk.content}[/dim]",
                title=f"[cyan]💭 Thinking[/cyan] [{timestamp}]",
                border_style="dim cyan",
                padding=(0, 1)
            )
            self.console.print(panel)

        elif chunk.type == "action":
            # Display action being taken
            self.console.print(f"[bold yellow]🔧 {chunk.content}[/bold yellow]")

        elif chunk.type == "code":
            # Display code with syntax highlighting
            language = chunk.metadata.get("language", "python")
            try:
                syntax = Syntax(
                    chunk.content,
                    language,
                    theme="monokai",
                    line_numbers=True,
                    background_color="default"
                )
                panel = Panel(
                    syntax,
                    title=f"[green]💻 Code[/green] [{timestamp}]",
                    border_style="green",
                    padding=(0, 1)
                )
                self.console.print(panel)
            except Exception:
                # Fallback to plain code display
                self.console.print(f"[green]Code:[/green]\n{chunk.content}")

        elif chunk.type == "test":
            # Display test code
            syntax = Syntax(
                chunk.content,
                "python",  # Assume Python tests
                theme="monokai",
                line_numbers=True
            )
            panel = Panel(
                syntax,
                title=f"[blue]🧪 Test[/blue] [{timestamp}]",
                border_style="blue",
                padding=(0, 1)
            )
            self.console.print(panel)

        elif chunk.type == "result":
            # Display final result
            panel = Panel(
                f"[bold green]✅ {chunk.content}[/bold green]",
                title=f"[green]Result[/green] [{timestamp}]",
                border_style="green",
                padding=(0, 1)
            )
            self.console.print(panel)

        elif chunk.type == "error":
            # Display error
            panel = Panel(
                f"[bold red]❌ {chunk.content}[/bold red]",
                title=f"[red]Error[/red] [{timestamp}]",
                border_style="red",
                padding=(0, 1)
            )
            self.console.print(panel)

        else:
            # Generic display
            self.console.print(f"[dim][{timestamp}] {chunk.content}[/dim]")

        # Small delay for smooth streaming effect
        await asyncio.sleep(0.05)

    async def _display_basic_stream(self, chunk: StreamChunk) -> None:
        """Display streaming chunk in basic terminal."""
        timestamp = chunk.timestamp.strftime("%H:%M:%S")

        type_prefixes = {
            "thought": "💭 THINKING: ",
            "action": "🔧 ACTION: ",
            "code": "💻 CODE:\n",
            "test": "🧪 TEST:\n",
            "result": "✅ RESULT: ",
            "error": "❌ ERROR: "
        }

        prefix = type_prefixes.get(chunk.type, f"[{chunk.type.upper()}] ")

        if chunk.type in ["code", "test"]:
            print(f"\n{prefix}")
            # Basic code formatting
            lines = chunk.content.split('\n')
            for i, line in enumerate(lines, 1):
                print(f"{i:2d} | {line}")
            print()
        else:
            print(f"[{timestamp}] {prefix}{chunk.content}")

        # Small delay for streaming effect
        await asyncio.sleep(0.1)

    async def _display_fallback_chunk(self, chunk: StreamChunk) -> None:
        """Fallback display method for chunks."""
        timestamp = chunk.timestamp.strftime("%H:%M:%S")
        print(f"[{timestamp}] [{chunk.type}] {chunk.content}")

    async def get_user_input(self, prompt: str = "casper> ") -> str:
        """Get input from user with rich prompt interface."""
        try:
            if RICH_AVAILABLE and self.console:
                # Use rich prompt
                user_input = await self._get_rich_input(prompt)
            else:
                # Use standard input
                user_input = await self._get_basic_input(prompt)

            self.ui_state["current_prompt"] = prompt
            return user_input

        except EOFError:
            return "exit"
        except KeyboardInterrupt:
            return "exit"
        except Exception as e:
            logger.error(f"Error getting user input: {e}")
            return ""

    async def _get_rich_input(self, prompt: str) -> str:
        """Get input using rich prompt interface."""
        # Run in thread to avoid blocking
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            None,
            lambda: Prompt.ask(f"[cyan]{prompt}[/cyan]", default="", show_default=False)
        )

    async def _get_basic_input(self, prompt: str) -> str:
        """Get input using basic prompt interface."""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, input, prompt)

    async def show_progress(self, message: str, percentage: Optional[float] = None) -> None:
        """Show progress indicator with optional percentage."""
        try:
            if RICH_AVAILABLE and self.progress:
                await self._show_rich_progress(message, percentage)
            else:
                await self._show_basic_progress(message, percentage)

        except Exception as e:
            logger.error(f"Error showing progress: {e}")
            print(f"Progress: {message}" + (f" ({percentage}%)" if percentage else ""))

    async def _show_rich_progress(self, message: str, percentage: Optional[float]) -> None:
        """Show progress using rich progress display."""
        if not self.progress:
            return

        with self.progress:
            if self.current_task:
                self.progress.remove_task(self.current_task)

            self.current_task = self.progress.add_task(
                message,
                total=100 if percentage is not None else None
            )

            if percentage is not None:
                self.progress.update(self.current_task, completed=percentage)

            # Brief display
            await asyncio.sleep(0.5)

    async def _show_basic_progress(self, message: str, percentage: Optional[float]) -> None:
        """Show progress using basic text display."""
        if percentage is not None:
            progress_bar = "█" * int(percentage / 5) + "░" * (20 - int(percentage / 5))
            print(f"\rProgress: [{progress_bar}] {percentage:.1f}% - {message}", end="", flush=True)
        else:
            print(f"Progress: {message}")

    async def clear_screen(self) -> None:
        """Clear the terminal screen."""
        try:
            if RICH_AVAILABLE and self.console:
                self.console.clear()
            else:
                os.system('clear' if os.name == 'posix' else 'cls')

        except Exception as e:
            logger.error(f"Error clearing screen: {e}")

    async def show_error(self, error: str) -> None:
        """Display error message with appropriate formatting."""
        try:
            if RICH_AVAILABLE and self.console:
                error_panel = Panel(
                    f"[bold red]{error}[/bold red]",
                    title="[red]Error[/red]",
                    border_style="red",
                    padding=(0, 1)
                )
                self.console.print(error_panel)
            else:
                print(f"\n❌ ERROR: {error}\n")

        except Exception as e:
            logger.error(f"Error displaying error: {e}")
            print(f"ERROR: {error}")

    async def show_help(self) -> None:
        """Display help information."""
        help_content = """
[bold cyan]CASPER Prime Terminal Help[/bold cyan]

[bold yellow]Basic Commands:[/bold yellow]
• help - Show this help message
• exit, quit, bye - Exit the terminal
• clear - Clear the screen
• status - Show terminal status

[bold yellow]Coding Commands (Natural Language):[/bold yellow]
• implement [description] - Create new code
• modify [target] - Change existing code
• debug [issue] - Fix problems
• test [target] - Create or run tests
• explain [target] - Get explanations
• review [target] - Code review
• refactor [target] - Improve code structure
• optimize [target] - Improve performance

[bold yellow]Examples:[/bold yellow]
• "implement a user authentication function"
• "debug the login method in user.py"
• "explain how the sorting algorithm works"
• "review my code for security issues"
• "test the payment processing module"

[bold yellow]Tips:[/bold yellow]
• Be specific about what you want to work on
• Mention file names, function names, or features
• Ask follow-up questions for clarification
• Use natural language - no special syntax required
"""

        if RICH_AVAILABLE and self.console:
            help_panel = Panel(
                help_content,
                title="Help",
                border_style="cyan",
                padding=(1, 2)
            )
            self.console.print(help_panel)
        else:
            print(help_content)

    async def show_status(self, status_info: Dict[str, Any]) -> None:
        """Display terminal status information."""
        try:
            if RICH_AVAILABLE and self.console:
                await self._show_rich_status(status_info)
            else:
                await self._show_basic_status(status_info)

        except Exception as e:
            logger.error(f"Error showing status: {e}")

    async def _show_rich_status(self, status_info: Dict[str, Any]) -> None:
        """Display status using rich formatting."""
        table = Table(title="Terminal Status")
        table.add_column("Property", style="cyan", no_wrap=True)
        table.add_column("Value", style="white")

        for key, value in status_info.items():
            table.add_row(str(key).replace('_', ' ').title(), str(value))

        self.console.print(table)

    async def _show_basic_status(self, status_info: Dict[str, Any]) -> None:
        """Display status using basic formatting."""
        print("\n" + "=" * 40)
        print("TERMINAL STATUS")
        print("=" * 40)

        for key, value in status_info.items():
            print(f"{key.replace('_', ' ').title()}: {value}")

        print("=" * 40 + "\n")

    def is_started(self) -> bool:
        """Check if UI has been started."""
        return self.ui_state["started"]

    async def shutdown(self) -> None:
        """Shutdown the terminal UI gracefully."""
        try:
            if self.progress and RICH_AVAILABLE:
                self.progress.stop()

            if self.live_display and RICH_AVAILABLE:
                self.live_display.stop()

            # Clear any remaining progress displays
            if RICH_AVAILABLE and self.console:
                self.console.clear()
                goodbye_panel = Panel(
                    "[bold cyan]Thank you for using CASPER Prime Terminal![/bold cyan]\n"
                    "[dim]Session ended at " + datetime.now().strftime("%Y-%m-%d %H:%M:%S") + "[/dim]",
                    title="Goodbye",
                    border_style="cyan"
                )
                self.console.print(goodbye_panel)
            else:
                print("\nThank you for using CASPER Prime Terminal!")
                print(f"Session ended at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

            self.ui_state["started"] = False
            logger.info("Terminal UI shutdown complete")

        except Exception as e:
            logger.error(f"Error during UI shutdown: {e}")


# Alternative basic UI implementation for fallback
class BasicTerminalUI(ITerminalUI):
    """Basic fallback terminal UI implementation."""

    def __init__(self):
        self.started = False

    async def start_ui(self) -> None:
        os.system('clear' if os.name == 'posix' else 'cls')
        print("CASPER Prime Terminal (Basic Mode)")
        print("=" * 50)
        self.started = True

    async def display_stream(self, chunk: StreamChunk) -> None:
        timestamp = chunk.timestamp.strftime("%H:%M:%S")
        print(f"[{timestamp}] [{chunk.type.upper()}] {chunk.content}")

    async def get_user_input(self, prompt: str = "casper> ") -> str:
        return input(prompt)

    async def show_progress(self, message: str, percentage: Optional[float] = None) -> None:
        if percentage:
            print(f"Progress: {message} ({percentage:.1f}%)")
        else:
            print(f"Progress: {message}")

    async def clear_screen(self) -> None:
        os.system('clear' if os.name == 'posix' else 'cls')

    async def show_error(self, error: str) -> None:
        print(f"ERROR: {error}")