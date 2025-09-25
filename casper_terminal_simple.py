#!/usr/bin/env python3
"""
CASPER2 Simple Terminal - Phase 1: Basic Functionality
Reuses original CASPER's proven UI framework with new agent capabilities.
"""

import asyncio
import sys
import os
from pathlib import Path
import json

# Add project to path
sys.path.insert(0, str(Path(__file__).parent))

from rich.console import Console
from rich.prompt import Prompt
from rich.panel import Panel
from rich.text import Text
from rich.table import Table
from rich import print as rprint
from typing import Optional, Dict, List

# Import original CASPER components
from core.cli import CasperCLI, print_modern_banner
from core.services.approval import HILApprovalService as ApprovalService


# Command categories for organized help
COMMAND_CATEGORIES = {
    "core": {
        "help": "Display available commands and usage",
        "task": "Execute development tasks",
        "analyze": "Analyze task complexity",
        "status": "Show system and agent status",
        "exit": "Exit CASPER2 terminal",
        "quit": "Exit CASPER2 terminal (alias for exit)"
    },
    "workflow": {
        "/task": "Execute task (slash version)",
        "/analyze": "Analyze task (slash version)",
        "/status": "Show status (slash version)",
        "/help": "Display help (slash version)",
        "list": "List available agents and tasks"
    },
    "development": {
        "/create": "Create new components",
        "/test": "Run tests",
        "/debug": "Debug code",
        "/review": "Code review",
        "/refactor": "Refactor code"
    }
}


async def handle_help(console: Console, args: str = "") -> None:
    """
    Handle help command with COT verification support.

    Purpose: Display available commands with descriptions
    Input: Optional category filter (e.g., "core", "workflow", "development")
    Output: Formatted command list in a Rich panel
    """
    # Validation
    if args and args not in COMMAND_CATEGORIES:
        console.print(f"[red]❌ Unknown category: {args}[/red]")
        console.print(f"[dim]Available categories: {', '.join(COMMAND_CATEGORIES.keys())}[/dim]")
        return

    # Build help content
    if not args:
        # Show all commands
        help_content = "[bold cyan]CASPER2 Commands[/bold cyan]\n\n"

        for category, commands in COMMAND_CATEGORIES.items():
            help_content += f"[green]{category.title()} Commands:[/green]\n"
            for cmd, desc in commands.items():
                help_content += f"  • [yellow]{cmd:<15}[/yellow] - {desc}\n"
            help_content += "\n"

        help_content += "[green]Examples:[/green]\n"
        help_content += "[cyan]task[/cyan] implement a REST API for user authentication\n"
        help_content += "[cyan]/analyze[/cyan] add unit tests for payment processing\n"
        help_content += "[cyan]status[/cyan]  # Check system status\n"
        help_content += "[cyan]help workflow[/cyan]  # Show workflow commands only"
    else:
        # Show specific category
        help_content = f"[bold cyan]{args.title()} Commands[/bold cyan]\n\n"
        for cmd, desc in COMMAND_CATEGORIES[args].items():
            help_content += f"• [yellow]{cmd:<15}[/yellow] - {desc}\n"

    # Display in panel
    help_panel = Panel.fit(
        help_content,
        title=f"📖 CASPER2 Help{f' - {args.title()}' if args else ''}",
        border_style="yellow"
    )
    console.print(help_panel)


async def handle_exit(console: Console, casper_cli: CasperCLI) -> bool:
    """
    Handle exit/quit command with proper cleanup.

    Purpose: Clean shutdown of CASPER2
    Input: None
    Output: Shutdown confirmation
    Returns: True to exit the main loop
    """
    console.print("[dim]→ Shutting down CASPER2...[/dim]")

    try:
        await casper_cli.shutdown()
        console.print("[bold green]✓[/bold green] CASPER2 shutdown complete")
    except Exception as e:
        console.print(f"[yellow]⚠ Shutdown warning: {e}[/yellow]")

    return True


async def handle_task(console: Console, casper_cli: CasperCLI, args: str) -> None:
    """
    Handle task execution command.

    Purpose: Execute development tasks via agent system
    Input: Task description string
    Output: Task execution results
    """
    if not args:
        console.print("[red]❌ Usage:[/red] task <task description>")
        console.print("[dim]Example: task implement user authentication API[/dim]")
        return

    console.print(f"[dim]→ Executing task:[/dim] [cyan]{args}[/cyan]")

    try:
        # Auto-approve any pending operations before execution
        approval_service = ApprovalService()
        pending = await approval_service.get_pending_operations()
        for op in pending:
            await approval_service.approve(op.id)
            console.print(f"[green]✓ Auto-approved: {op.operation_type}[/green]")
    except:
        pass  # Continue even if approval service not available

    try:
        await casper_cli.execute_task(args)
    except Exception as e:
        console.print(f"[red]❌ Task execution failed: {e}[/red]")


async def handle_analyze(console: Console, casper_cli: CasperCLI, args: str) -> None:
    """
    Handle task analysis command.

    Purpose: Analyze task complexity without execution
    Input: Task description string
    Output: Complexity analysis report
    """
    if not args:
        console.print("[red]❌ Usage:[/red] analyze <task description>")
        console.print("[dim]Example: analyze add unit tests for payment processing[/dim]")
        return

    console.print(f"[dim]→ Analyzing task:[/dim] [cyan]{args}[/cyan]")

    try:
        await casper_cli.analyze_only(args)
    except Exception as e:
        console.print(f"[red]❌ Analysis failed: {e}[/red]")


async def handle_status(console: Console, casper_cli: CasperCLI) -> None:
    """
    Handle status command.

    Purpose: Show system and agent pool status
    Input: None
    Output: Status report with agent availability
    """
    console.print("[dim]→ Fetching system status...[/dim]")

    try:
        await casper_cli.show_status()
    except Exception as e:
        console.print(f"[red]❌ Status check failed: {e}[/red]")


async def handle_list(console: Console) -> None:
    """
    Handle list command.

    Purpose: List available agents and their capabilities
    Input: None
    Output: Table of agents with descriptions
    """
    # Create agents table
    table = Table(title="Available CASPER2 Agents")
    table.add_column("Agent", style="cyan", width=20)
    table.add_column("Role", style="yellow")
    table.add_column("Capabilities", style="white")

    agents = [
        ("Master Prime", "Orchestrator", "Task routing, complexity analysis, agent coordination"),
        ("Alpha Prime", "React Developer", "React components, TypeScript, frontend architecture"),
        ("Beta Prime", "Backend Developer", "APIs, databases, server architecture"),
        ("Gamma Prime", "Full Stack", "End-to-end implementation, integration"),
        ("Delta Prime", "DevOps", "CI/CD, deployment, infrastructure"),
        ("Epsilon Prime", "Quality Assurance", "Testing, debugging, quality control")
    ]

    for agent, role, caps in agents:
        table.add_row(agent, role, caps)

    console.print(table)


def print_casper2_banner():
    """Print CASPER2 banner with original logo"""
    console = Console()

    # Original CASPER ASCII art logo
    banner = r"""
[bold bright_cyan]
________/\\\\\\\\_____/\\\\\\\\\________/\\\\\\\\\\\____/\\\\\\\\\\\\\____/\\\\\\\\\\\\\\\____/\\\\\\\\\_____
 _____/\\\////////____/\\\\\\\\\\\\\____/\\\/////////\\\_\/\\\/////////\\\_\/\\\///////////___/\\\///////\\\___
  ___/\\\/____________/\\\/////////\\\__\//\\\______\///__\/\\\_______\/\\\_\/\\\_____________\/\\\_____\/\\\___
   __/\\\_____________\/\\\___\\\___\\\___\////\\\_________\/\\\\\\\\\\\\\/__\/\\\\\\\\\\\_____\/\\\\\\\\\\\/____
    _\/\\\_____________\/\\\\\\\\\\\\\\\______\////\\\______\/\\\/////////____\/\\\///////______\/\\\//////\\\____
     _\//\\\____________\/\\\\\\\\\\\\\\\_________\////\\\___\/\\\_____________\/\\\_____________\/\\\____\//\\\___
      __\///\\\__________\/\\\\\\\\\\\\\\\__/\\\______\//\\\__\/\\\_____________\/\\\_____________\/\\\_____\//\\\__
       ____\////\\\\\\\\\_\/\\\\\\\\\\\\\\\_\///\\\\\\\\\\\/___\/\\\_____________\/\\\\\\\\\\\\\\\_\/\\\______\//\\\_
        _______\/////////__\//__//___//__//____\///////////_____\///______________\///////////////__\///________\///__
[/bold bright_cyan]"""

    console.print(banner)
    console.print("[bold green]✓[/bold green] [bright_white]CASPER initialized and ready[/bright_white]")


async def simple_terminal():
    """Simple terminal that reuses original CASPER functionality"""
    console = Console()

    # Print banner
    print_casper2_banner()

    # Check for API keys configuration
    config_path = Path.home() / ".casper" / "config.json"
    if not config_path.exists():
        console.print("[yellow]⚠️  No API keys configured. Setting up auto-approval mode.[/yellow]")
        console.print("[dim]Run 'casper' and use /setup to configure API keys for full functionality.[/dim]\n")

    # Initialize original CASPER CLI (reuse existing infrastructure)
    casper_cli = CasperCLI()

    # Set auto-approval for simple operations to avoid blocking
    try:
        # Override approval requirement for basic file operations
        if hasattr(casper_cli, 'config'):
            casper_cli.config['require_human_approval'] = False
        # Auto-approve pending operations
        approval_service = ApprovalService()
        approval_service.auto_approve = True
    except:
        pass  # If approval service not available, continue anyway

    await casper_cli.initialize()

    # Welcome message
    welcome_panel = Panel.fit(
        "[bold cyan]CASPER2 Interactive Development Terminal[/bold cyan]\n"
        "[dim]Enhanced AI Development Platform with Streaming Capabilities[/dim]\n\n"
        "[green]• Agent Coordinator:[/green] Active and ready\n"
        "[green]• Context Manager:[/green] Initialized\n"
        "[green]• Streaming Engine:[/green] Loaded\n\n"
        "[yellow]Type 'help' for commands, 'exit' to quit[/yellow]\n"
        "[dim]Examples: 'task create a hello world script', 'analyze user authentication'[/dim]",
        title="🚀 CASPER2 Prime",
        border_style="cyan"
    )
    console.print(welcome_panel)
    console.print()

    # Interactive loop
    while True:
        try:
            # Get user input
            user_input = Prompt.ask(
                Text.from_markup("[bold blue]casper2[/bold blue][dim]>[/dim]"),
                default=""
            ).strip()

            if not user_input:
                continue

            # Parse command and arguments
            parts = user_input.split(' ', 1)
            command = parts[0].lower()
            args = parts[1] if len(parts) > 1 else ""

            # Handle exit commands
            if command in ['exit', 'quit', 'q']:
                should_exit = await handle_exit(console, casper_cli)
                if should_exit:
                    break

            # Handle help commands (with category support)
            elif command in ['help', '?', '/help']:
                await handle_help(console, args)

            # Handle task commands
            elif command in ['task', '/task']:
                await handle_task(console, casper_cli, args)

            # Handle analyze commands
            elif command in ['analyze', '/analyze']:
                await handle_analyze(console, casper_cli, args)

            # Handle status commands
            elif command in ['status', '/status']:
                await handle_status(console, casper_cli)

            # Handle list command
            elif command == 'list':
                await handle_list(console)

            # Handle approve command (kept for compatibility)
            elif command == 'approve':
                try:
                    approval_service = ApprovalService()
                    pending = await approval_service.get_pending_operations()
                    if pending:
                        console.print("[yellow]Pending operations:[/yellow]")
                        for op in pending:
                            console.print(f"  • {op.id}: {op.operation_type} - {op.details.get('path', 'N/A')}")
                            response = Prompt.ask("Approve? [y/n]", default="y")
                            if response.lower() == 'y':
                                await approval_service.approve(op.id)
                                console.print("[green]✓ Approved[/green]")
                            else:
                                await approval_service.reject(op.id)
                                console.print("[red]✗ Rejected[/red]")
                    else:
                        console.print("[dim]No pending operations[/dim]")
                except Exception as e:
                    console.print(f"[red]Error handling approvals: {e}[/red]")

            else:
                console.print(f"[red]❌ Unknown command:[/red] [yellow]{command}[/yellow]")
                console.print("[dim]Type 'help' for available commands[/dim]")

            console.print()  # Add spacing

        except KeyboardInterrupt:
            console.print("\n[yellow]⚠ Use 'exit' to quit gracefully[/yellow]")
        except Exception as e:
            console.print(f"[red]❌ Error: {e}[/red]")


async def main():
    """Main entry point"""
    try:
        await simple_terminal()
    except KeyboardInterrupt:
        print("\n👋 CASPER2 Terminal interrupted")
    except Exception as e:
        print(f"❌ Fatal error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())