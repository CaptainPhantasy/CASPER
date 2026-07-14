#!/usr/bin/env python3
"""
CASPER Prime CLI - Command-line interface for the autonomous AI development platform.
"""

import argparse
import asyncio
import json
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional
from uuid import UUID

from rich.console import Console
from rich.table import Table
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TaskProgressColumn, TimeRemainingColumn
from rich.live import Live
from rich.layout import Layout
from rich.panel import Panel
from rich.syntax import Syntax
from rich.spinner import Spinner
from rich.align import Align
from rich.columns import Columns
from rich.status import Status
from dotenv import load_dotenv

from core.orchestrator.coordinator import AgentCoordinator
from core.orchestrator.task_analyzer import TaskAnalyzer
from core.context.manager import ContextManager
from core.agents.base import AgentStatus, TaskPriority, ProgressUpdate
from core.reasoning.react_engine import get_react_engine


load_dotenv()

console = Console(force_terminal=True)


class CasperCLI:
    """
    Command-line interface for CASPER Prime.
    """

    def __init__(self):
        self.context_manager = ContextManager()
        self.coordinator = AgentCoordinator(self.context_manager)
        self.task_analyzer = TaskAnalyzer()
        self.active_task_id: Optional[UUID] = None

    async def initialize(self):
        """Initialize the coordinator with modern loading animation."""
        with Status("[bold bright_cyan]Initializing CASPER...", spinner="dots12", console=console) as status:
            await asyncio.sleep(0.5)  # Brief pause for visual effect
            status.update("[bold bright_cyan]Starting agent coordinator...")
            await self.coordinator.start()
            await asyncio.sleep(0.3)
            status.update("[bold bright_cyan]Loading agent pool...")
            await asyncio.sleep(0.2)
        
        console.print("[bold green]✓[/bold green] [bright_white]CASPER initialized and ready[/bright_white]")

    async def shutdown(self):
        """Shutdown the coordinator."""
        await self.coordinator.stop()
        console.print("[dim bright_white]→ CASPER shutting down gracefully[/dim bright_white]")

    async def execute_task(self, task: str, priority: str = "medium"):
        """
        Execute a task through the CASPER Prime system.
        """
        # Convert priority string to enum
        priority_map = {
            "high": TaskPriority.HIGH,
            "medium": TaskPriority.MEDIUM,
            "low": TaskPriority.LOW
        }
        task_priority = priority_map.get(priority.lower(), TaskPriority.MEDIUM)

        if "CASPER_PROJECT_ROOT" not in os.environ:
            os.environ["CASPER_PROJECT_ROOT"] = str(Path.cwd())

        # Modern task header
        console.print()
        console.print(Panel(
            f"[bright_white]{task}[/bright_white]",
            title="[bold bright_cyan]◆ Task Submission[/bold bright_cyan]",
            border_style="bright_cyan",
            padding=(0, 1)
        ))

        # Analyze task with animation
        with Status("[bold bright_cyan]Analyzing task complexity...", spinner="dots12", console=console):
            await asyncio.sleep(0.8)  # Simulate analysis time
            metrics, required_agents, suggested_priority = self.task_analyzer.analyze_task(task)

        # Display analysis
        self._display_task_analysis(task, metrics, required_agents, suggested_priority)

        # Submit task with modern progress
        with Status("[bold bright_green]Submitting to agent coordinator...", spinner="line", console=console) as status:
            task_id = await self.coordinator.submit_task(task, task_priority)
            self.active_task_id = task_id
            await asyncio.sleep(0.3)

        console.print(f"\n[bold bright_green]✓[/bold bright_green] [bright_white]Task queued successfully[/bright_white]")
        console.print(f"[dim]Task ID: {task_id}[/dim]\n")

        # Monitor progress with modern display
        console.print("[bold bright_cyan]◆ Execution Progress[/bold bright_cyan]")
        await self._monitor_task_progress(task_id)

    async def _monitor_task_progress(self, task_id: UUID):
        """
        Monitor and display task progress.
        """
        console.print("\n[cyan]Task Execution Progress:[/cyan]")

        # Register progress callback
        progress_updates = []

        async def progress_callback(update: ProgressUpdate):
            progress_updates.append(update)
            self._display_progress_update(update)

        self.coordinator.register_progress_callback(progress_callback)

        # Wait for completion
        completed = False
        while not completed:
            await asyncio.sleep(1)

            # Check for results
            results = await self.coordinator.get_results(1)
            if results:
                for result in results:
                    if result.task_id == task_id:
                        self._display_result(result)
                        if result.status == AgentStatus.COMPLETED:
                            completed = True
                        elif result.status == AgentStatus.FAILED:
                            console.print(f"[red]✗[/red] Task failed: {result.errors}")
                            completed = True

    def _display_task_analysis(self, task, metrics, required_agents, priority):
        """Display modern task analysis with clean styling."""
        # Create a sleek panel for task analysis
        table = Table(
            title="[bold bright_cyan]◆ Task Analysis[/bold bright_cyan]", 
            show_header=True, 
            border_style="bright_cyan",
            header_style="bold bright_white",
            title_style="bold bright_cyan"
        )
        table.add_column("Metric", style="bright_cyan", width=20)
        table.add_column("Value", style="bright_white", width=30)

        # Add rows with modern formatting
        table.add_row("Lines of Code", f"[bright_white]~{metrics.lines_of_code_estimate:,}[/bright_white]")
        table.add_row("Files Affected", f"[bright_white]{metrics.file_count_estimate}[/bright_white]")
        table.add_row("Components", f"[bright_white]{metrics.component_count}[/bright_white]")
        table.add_row("Integration Points", f"[bright_white]{metrics.integration_points}[/bright_white]")
        table.add_row("Dependencies", f"[bright_white]{metrics.external_dependencies}[/bright_white]")
        
        # Format agents with colors
        agent_list = [f"[bright_yellow]{a.value}[/bright_yellow]" for a in required_agents]
        table.add_row("Required Agents", ", ".join(agent_list))
        
        # Priority with color coding
        priority_colors = {"high": "bright_red", "medium": "bright_yellow", "low": "bright_green"}
        priority_color = priority_colors.get(priority.value, "white")
        table.add_row("Priority", f"[{priority_color}]{priority.value.upper()}[/{priority_color}]")
        
        # Estimated time
        est_time = TaskAnalyzer.estimate_completion_time(metrics)
        table.add_row("Est. Duration", f"[bright_white]{est_time} min[/bright_white]")

        console.print(table)

    def _display_progress_update(self, update: ProgressUpdate):
        """Display a modern progress update with animated indicators."""
        status_config = {
            AgentStatus.IDLE: {"symbol": "○", "color": "dim white", "spinner": None},
            AgentStatus.PLANNING: {"symbol": "◐", "color": "bright_yellow", "spinner": "dots"},
            AgentStatus.BUILDING: {"symbol": "●", "color": "bright_blue", "spinner": "line"},
            AgentStatus.REVIEWING: {"symbol": "◑", "color": "bright_magenta", "spinner": "arc"},
            AgentStatus.COMPLETED: {"symbol": "✓", "color": "bright_green", "spinner": None},
            AgentStatus.FAILED: {"symbol": "✗", "color": "bright_red", "spinner": None},
            AgentStatus.BLOCKED: {"symbol": "■", "color": "red", "spinner": None}
        }

        config = status_config.get(update.status, {"symbol": "?", "color": "white", "spinner": None})
        
        # Create progress bar for active tasks
        if update.progress > 0 and update.progress < 100:
            progress_bar = "█" * (update.progress // 5) + "░" * (20 - (update.progress // 5))
            progress_display = f"[{config['color']}]{progress_bar}[/{config['color']}] {update.progress}%"
        else:
            progress_display = f"[{config['color']}]{config['symbol']}[/{config['color']}]"

        # Format message with modern styling
        agent_name = f"[bold {config['color']}]{update.status.value.upper()}[/bold {config['color']}]"
        message = f"[bright_white]{update.message}[/bright_white]"
        tokens = f"[dim]({update.token_usage.get('total', 0)} tokens)[/dim]"
        
        console.print(f"  {progress_display} {agent_name} {message} {tokens}")

    def _display_result(self, result):
        """Display agent result."""
        panel = Panel(
            f"Agent: {result.agent_role.value}\n"
            f"Status: {result.status.value}\n"
            f"Output: {result.output[:200]}...\n"
            f"Tokens Used: {result.token_usage.get('total', 0)}",
            title=f"Result from {result.agent_role.value}",
            border_style="green" if result.status == AgentStatus.COMPLETED else "red"
        )
        console.print(panel)

    async def show_status(self):
        """Show current system status."""
        stats = self.coordinator.get_coordinator_stats()

        # Create status table
        table = Table(
            title="[bold bright_green]◆ System Status[/bold bright_green]", 
            show_header=True, 
            border_style="bright_green",
            header_style="bold bright_white"
        )
        table.add_column("Metric", style="bright_green", width=18)
        table.add_column("Value", style="bright_white", width=15)

        table.add_row("Active Tasks", str(stats["active_tasks"]))
        table.add_row("Queued Tasks", str(stats["queued_tasks"]))
        table.add_row("Total Agents", str(stats["agent_pool"]["total_agents"]))
        table.add_row("Busy Agents", str(stats["agent_pool"]["busy_agents"]))
        table.add_row("Context Sessions", str(stats["context_sessions"]))

        console.print(table)

        # Show agent availability
        if stats["agent_pool"]["available_by_role"]:
            availability_table = Table(
                title="[bold bright_blue]◆ Agent Pool[/bold bright_blue]", 
                show_header=True, 
                border_style="bright_blue",
                header_style="bold bright_white"
            )
            availability_table.add_column("Agent Role", style="bright_blue", width=15)
            availability_table.add_column("Available", style="bright_green", width=10)

            for role, count in stats["agent_pool"]["available_by_role"].items():
                availability_table.add_row(role, str(count))

            console.print(availability_table)

    async def list_tasks(self):
        """List recent tasks."""
        # Get recent results
        results = await self.coordinator.get_results(10)

        if not results:
            console.print("[yellow]No recent tasks found[/yellow]")
            return

        table = Table(
            title="[bold bright_magenta]◆ Task History[/bold bright_magenta]", 
            show_header=True, 
            border_style="bright_magenta",
            header_style="bold bright_white"
        )
        table.add_column("Task ID", style="bright_cyan", width=12)
        table.add_column("Agent", style="bright_white", width=15)
        table.add_column("Status", style="bright_white", width=12)
        table.add_column("Tokens", style="bright_yellow", width=10)

        for result in results:
            status_color = "green" if result.status == AgentStatus.COMPLETED else "red"
            table.add_row(
                str(result.task_id)[:8],
                result.agent_role.value,
                f"[{status_color}]{result.status.value}[/{status_color}]",
                str(result.token_usage.get("total", 0))
            )

        console.print(table)

    def init_project(self, project_dir: Path) -> None:
        project_dir = project_dir.resolve()
        os.environ["CASPER_PROJECT_ROOT"] = str(project_dir)
        output_dir = project_dir / ".casper" / "output"

        directories = [
            ".casper/context",
            ".casper/knowledge",
            ".casper/logs/agent-decisions",
            ".casper/logs/code-changes",
            ".casper/checkpoints",
            ".casper/output",
            ".casper/config",
        ]
        for relative in directories:
            (project_dir / relative).mkdir(parents=True, exist_ok=True)

        config = {
            "version": "0.1.0",
            "project_root": str(project_dir),
            "output_dir": str(output_dir),
            "max_tokens_per_task": 100000,
            "agent_settings": {
                # "auto" → resolved dynamically at runtime by LLMService.
                "primary_model": "auto",
                "worker_model": "auto",
            },
        }
        config_path = project_dir / ".casper/config/casper.json"
        config_path.write_text(json.dumps(config, indent=2))

        console.print(f"[bold green]CASPER initialized at[/bold green] {project_dir}")
        console.print(f"Artifacts will be written to: {output_dir}")

    async def analyze_only(self, task: str):
        """
        Analyze a task without executing it.
        """
        console.print(f"\n[cyan]Analyzing task:[/cyan] {task}")

        metrics, required_agents, priority = self.task_analyzer.analyze_task(task)
        self._display_task_analysis(task, metrics, required_agents, priority)

        # Show execution strategy
        strategy = TaskAnalyzer.suggest_execution_strategy(task, metrics)
        console.print(f"\n[cyan]Suggested Strategy:[/cyan] {strategy}")

    async def execute_react_task(self, task: str):
        """
        Execute a task using the ReAct reasoning engine with streaming output.
        """
        console.print()
        console.print(Panel(
            f"[bright_white]{task}[/bright_white]",
            title="[bold bright_magenta]◆ ReAct Reasoning Task[/bold bright_magenta]",
            border_style="bright_magenta",
            padding=(0, 1)
        ))

        # Initialize ReAct engine
        with Status("[bold bright_magenta]Initializing ReAct engine...", spinner="dots12", console=console):
            project_root = os.environ.get("CASPER_PROJECT_ROOT", str(Path.cwd()))
            react_engine = get_react_engine(project_root)
            await asyncio.sleep(0.5)  # Visual pause

        console.print(f"[bold green]✓[/bold green] [bright_white]ReAct engine ready[/bright_white]")
        console.print(f"[dim]Model: {react_engine.get_capabilities()['model']}[/dim]")
        console.print(f"[dim]Tools: {len(react_engine.get_capabilities()['tools'])} available[/dim]\n")

        # Stream reasoning process
        console.print("[bold bright_magenta]◆ Reasoning Chain[/bold bright_magenta]\n")

        try:
            step_count = 0
            async for step_data in react_engine.stream_reasoning(task):
                if step_data["type"] == "thought":
                    step_count = step_data["step"]
                    console.print(f"[bold bright_blue]💭 Step {step_count} - Thought:[/bold bright_blue]")
                    console.print(f"[dim]{step_data['content']}[/dim]\n")

                elif step_data["type"] == "action":
                    console.print(f"[bold bright_green]🔧 Action:[/bold bright_green] {step_data['action']}")
                    console.print(f"[bright_white]Input:[/bright_white] {step_data['input']}")

                elif step_data["type"] == "observation":
                    console.print(f"[bold bright_yellow]👁  Observation:[/bold bright_yellow]")
                    # Format observation nicely
                    obs = step_data['content']
                    if len(obs) > 500:
                        obs = obs[:500] + "\n... (truncated)"
                    console.print(f"[dim]{obs}[/dim]")
                    console.print("-" * 60 + "\n")

                elif step_data["type"] == "final_answer":
                    console.print(f"[bold bright_green]🎯 Final Answer:[/bold bright_green]")
                    console.print(Panel(
                        step_data["content"],
                        border_style="bright_green",
                        padding=(1, 2)
                    ))

                elif step_data["type"] == "completion":
                    result = step_data["result"]
                    console.print(f"\n[bold bright_green]✅ Task completed successfully![/bold bright_green]")
                    console.print(f"[dim]Reasoning steps: {result['reasoning_steps']}[/dim]")
                    console.print(f"[dim]Reasoning log: {result['reasoning_log_path']}[/dim]")
                    return

                elif step_data["type"] == "error":
                    console.print(f"\n[bold red]❌ Error during execution:[/bold red]")
                    console.print(f"[red]{step_data['error']}[/red]")
                    return

        except KeyboardInterrupt:
            console.print("\n[yellow]❌ ReAct execution interrupted by user[/yellow]")
        except Exception as e:
            console.print(f"\n[bold red]❌ ReAct execution failed:[/bold red]")
            console.print(f"[red]{e}[/red]")

    async def run_setup(self):
        """
        Run the AI provider setup configuration.
        """
        from core.services.setup import SetupService

        setup_service = SetupService()
        setup_service.interactive_setup()


async def main_async():
    """Main async entry point for CLI."""
    parser = argparse.ArgumentParser(
        description="CASPER - Cognitive Agent System for Planning, Execution & Refinement"
    )

    subparsers = parser.add_subparsers(dest="command", help="Commands")

    # Task command
    task_parser = subparsers.add_parser("task", help="Execute a task")
    task_parser.add_argument("description", help="Task description")
    task_parser.add_argument(
        "--priority", "-p",
        choices=["high", "medium", "low"],
        default="medium",
        help="Task priority"
    )

    # Analyze command
    analyze_parser = subparsers.add_parser("analyze", help="Analyze a task without executing")
    analyze_parser.add_argument("description", help="Task description")

    # ReAct command
    react_parser = subparsers.add_parser("react", help="Execute task using ReAct reasoning engine")
    react_parser.add_argument("description", help="Task description")

    # Status command
    subparsers.add_parser("status", help="Show system status")

    # List command
    subparsers.add_parser("list", help="List recent tasks")

    # Init command
    init_parser = subparsers.add_parser("init", help="Initialize CASPER in the current project")
    init_parser.add_argument(
        "--project", "-d",
        type=str,
        help="Project directory (default: current directory)"
    )

    # Setup command
    subparsers.add_parser("setup", help="Configure AI provider API keys")

    args = parser.parse_args()

    # The globally installed `casper` command is the interactive application
    # when no subcommand is supplied.  Direct subcommands remain scriptable.
    if args.command is None:
        from casper_terminal_complete import CasperTerminalComplete

        await CasperTerminalComplete().run()
        return

    # Create CLI instance
    cli = CasperCLI()

    initialized = False

    try:
        if args.command == "init":
            target = Path(args.project).resolve() if getattr(args, 'project', None) else Path.cwd()
            cli.init_project(target)
            return
        elif args.command == "setup":
            await cli.run_setup()
            return

        console.print("[bold green]Initializing CASPER...[/bold green]")
        await cli.initialize()
        initialized = True

        if args.command == "task":
            await cli.execute_task(args.description, args.priority)
        elif args.command == "analyze":
            await cli.analyze_only(args.description)
        elif args.command == "react":
            await cli.execute_react_task(args.description)
        elif args.command == "status":
            await cli.show_status()
        elif args.command == "list":
            await cli.list_tasks()
        else:
            parser.print_help()

    except KeyboardInterrupt:
        console.print("\n[yellow]Interrupted by user[/yellow]")
    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
    finally:
        if initialized:
            await cli.shutdown()


def print_modern_banner():
    """Print the clean CASPER logo as specified."""
    # Clean CASPER logo - no framing, no additional text
    ascii_art = [
        r"________/\\\\\\\\_____/\\\\\\\\\________/\\\\\\\\\\\____/\\\\\\\\\\\\\____/\\\\\\\\\\\\\\\____/\\\\\\\\\_____",
        r" _____/\\\////////____/\\\\\\\\\\\\\____/\\\/////////\\\_\/\\\/////////\\\_\/\\\///////////___/\\\///////\\\___",
        r"  ___/\\\/____________/\\\/////////\\\__\//\\\______\///__\/\\\\_______\/\\\_\/\\\_____________\/\\\_____\/\\\___",
        r"   __/\\\_____________\/\\\___\\\___\\\___\////\\\_________\/\\\\\\\\\\\\\/__\/\\\\\\\\\\\_____\/\\\\\\\\\\\/____",
        r"    _\/\\\_____________\/\\\\\\\\\\\\\\\______\////\\\______\/\\\/////////____\/\\\///////______\/\\\//////\\\____",
        r"     _\//\\\____________\/\\\\\\\\\\\\\\\_________\////\\\___\/\\\_____________\/\\\_____________\/\\\____\//\\\___",
        r"      __\///\\\__________\/\\\\\\\\\\\\\\\__/\\\______\//\\\__\/\\\_____________\/\\\_____________\/\\\_____\//\\\__",
        r"       ____\////\\\\\\\\\_\/\\\\\\\\\\\\\\\_\///\\\\\\\\\\\/___\/\\\_____________\/\\\\\\\\\\\\\\\_\/\\\______\//\\\_",
        r"        _______\/////////__\//__//___//__//____\///////////_____\///______________\///////////////__\///________\///__"
    ]

    console.print()
    for line in ascii_art:
        console.print(line)
    console.print()


if __name__ == "__main__":
    print_modern_banner()

    # Run async main
    asyncio.run(main_async())


def main():
    """Synchronous entry point for console_scripts (pipx/pip)."""
    print_modern_banner()
    asyncio.run(main_async())
