#!/usr/bin/env python3
"""
CASPER2 Complete Terminal - All 57 Commands Implementation
Full implementation following COT methodology with all tiers.
Enhanced with agent-based natural language processing.
"""

import asyncio
import sys
import os
from pathlib import Path
import json
import subprocess
import shutil
from datetime import datetime
from typing import Optional, Dict, List, Any
import logging

# Add project to path
sys.path.insert(0, str(Path(__file__).parent))

from rich.console import Console
from rich.prompt import Prompt
from rich.panel import Panel
from rich.text import Text
from rich.table import Table
from rich.syntax import Syntax
from rich import print as rprint

# Import original CASPER components
from core.cli import CasperCLI, print_modern_banner
from core.services.approval import HILApprovalService as ApprovalService
from core.services.slash_commands import SlashCommandRegistry

# Import agent layer system for natural language processing
from core.agents.layer_initialization import AgentLayerInitializer
from core.agents.base import AgentRole, ContextBundle

logger = logging.getLogger(__name__)


# Command categories for organized help - ALL 57 COMMANDS
COMMAND_CATEGORIES = {
    "core": {
        "help": "Display available commands and usage",
        "task": "Execute development tasks",
        "analyze": "Analyze task complexity",
        "status": "Show system and agent status",
        "approve": "Review and approve pending operations",
        "clear": "Clear the terminal screen",
        "exit": "Exit CASPER2 terminal",
        "quit": "Exit CASPER2 terminal (alias for exit)",
    },
    "workflow": {
        "/task": "Execute task (slash version)",
        "/analyze": "Analyze task (slash version)",
        "/status": "Show status (slash version)",
        "/help": "Display help (slash version)",
        "list": "List available agents and tasks",
    },
    "agent": {
        "/goal": "Persist an evidence-gated project goal",
        "/model": "Show or select the active provider/model",
        "/plan": "Analyze a request without executing it",
        "/diff": "Show the current Git diff",
        "/pwd": "Show the active working directory",
    },
    "development": {
        "/create": "Create new components",
        "/test": "Run tests",
        "/debug": "Debug code",
        "/review": "Code review",
        "/refactor": "Refactor code",
        "/init": "Initialize project",
        "/build": "Build project",
        "/deploy": "Deploy application",
        "/rollback": "Rollback deployment",
        "/migrate": "Run migrations",
        "/generate": "Generate code",
        "/scaffold": "Scaffold project structure",
        "/optimize": "Optimize code",
        "/profile": "Profile performance",
    },
    "ai": {
        "/ai-review": "AI code review",
        "/ai-complete": "AI code completion",
        "/ai-explain": "AI code explanation",
        "/ai-suggest": "AI suggestions",
        "/ai-translate": "AI code translation",
    },
    "business": {
        "/invoice": "Generate invoice",
        "/proposal": "Create proposal",
        "/contract": "Draft contract",
        "/quote": "Generate quote",
        "/timesheet": "Manage timesheet",
    },
    "testing": {
        "/unit-test": "Run unit tests",
        "/integration-test": "Run integration tests",
        "/e2e-test": "Run end-to-end tests",
        "/load-test": "Run load tests",
        "/security-test": "Run security tests",
    },
    "utility": {
        "/search": "Search in codebase",
        "/replace": "Find and replace",
        "/format": "Format code",
        "/lint": "Lint code",
        "/clean": "Clean project",
        "/backup": "Backup project",
        "/restore": "Restore from backup",
        "/export": "Export data",
        "/import": "Import data",
        "/sync": "Sync repositories",
    },
}


class CasperTerminalComplete:
    """Complete CASPER2 terminal with all 57 commands and agent-based NLP"""

    def __init__(self):
        self.console = Console()
        self.casper_cli = None
        self.slash_commands = None
        self.project_root = Path.cwd()
        self.casper_dir = Path.home() / ".casper"
        self.backup_dir = self.casper_dir / "backups"
        self.export_dir = self.casper_dir / "exports"

        # Agent layer system for natural language processing
        self.agent_initializer = None
        self.agent_session = None
        self.layer_0_agent = None

        # Ensure directories exist
        self.backup_dir.mkdir(parents=True, exist_ok=True)
        self.export_dir.mkdir(parents=True, exist_ok=True)

    async def initialize(self):
        """Initialize CASPER CLI with approval mode and agent layers"""
        injected_cli = self.casper_cli is not None
        if self.casper_cli is None:
            self.casper_cli = CasperCLI()

        # Get approval mode from environment
        approval_mode = os.environ.get("CASPER_APPROVAL_MODE", "STRICT")
        self.approval_mode = approval_mode

        # Configure approval based on mode
        try:
            if approval_mode == "YOLO":
                # YOLO mode - approve everything automatically
                if hasattr(self.casper_cli, "config"):
                    self.casper_cli.config["require_human_approval"] = False
                approval_service = ApprovalService()
                approval_service.auto_approve = True
                self.console.print(
                    "[bold yellow]⚡ YOLO MODE ACTIVATED[/bold yellow] - All operations will be auto-approved!"
                )
            elif approval_mode == "AUTO":
                # Auto mode - smart auto-approval for safe operations
                if hasattr(self.casper_cli, "config"):
                    self.casper_cli.config["require_human_approval"] = True
                    self.casper_cli.config["auto_approve_safe"] = True
                self.console.print(
                    "[bold green]🤖 AUTO-APPROVAL MODE[/bold green] - Safe operations will be auto-approved"
                )
            else:  # STRICT mode (default)
                # Strict mode - require approval for all operations
                if hasattr(self.casper_cli, "config"):
                    self.casper_cli.config["require_human_approval"] = True
                approval_service = ApprovalService()
                approval_service.auto_approve = False
                self.console.print(
                    "[bold red]🔒 STRICT MODE[/bold red] - All operations require approval"
                )
        except:
            pass

        await self.casper_cli.initialize()
        self.slash_commands = SlashCommandRegistry(self.casper_cli)

        # Dependency injection is used by tests and embedders that already
        # own the CLI lifecycle. Do not replace it or start a second agent
        # hierarchy behind their back.
        if injected_cli:
            return

        # Initialize agent layers for natural language processing
        self.console.print("[dim]→ Initializing agent layers...[/dim]")
        try:
            self.agent_initializer = AgentLayerInitializer()
            self.agent_session = (
                await self.agent_initializer.initialize_casper_session()
            )

            # Get Layer 0 agent for orchestration
            from core.agents.layer_initialization import AgentLayer

            if AgentLayer.LAYER_0 in self.agent_initializer.layer_agents:
                self.layer_0_agent = self.agent_initializer.layer_agents[
                    AgentLayer.LAYER_0
                ][0]
                self.console.print(
                    "[bold green]✓[/bold green] Agent layers initialized"
                )
            else:
                self.console.print(
                    "[yellow]⚠ Agent layers initialized without Layer 0[/yellow]"
                )
        except Exception as e:
            self.console.print(f"[yellow]⚠ Agent initialization warning: {e}[/yellow]")
            logger.warning(f"Failed to initialize agent layers: {e}")

    async def process_natural_language(self, input_text: str) -> bool:
        """
        Process natural language input through actual LLM and agent system.
        NO PLACEHOLDERS - uses real LLM API for all responses.
        Returns True if handled, False if should fall back to command processing.
        """
        # Import LLM service
        from core.services.llm import llm_service

        try:
            self.console.print(f"[dim]→ Processing through LLM...[/dim]")

            # Build context for LLM
            system_prompt = """You are CASPER, an advanced AI development assistant with multi-agent capabilities.
            You have access to specialized agents for Frontend, Backend, Testing, and DevOps tasks.

            When the user asks a question, provide helpful, accurate information.
            When the user requests a task, analyze what needs to be done and explain how you'll approach it.

            You can execute real code changes, run tests, deploy applications, and more through your agent system.
            Be concise but thorough in your responses."""

            # Use actual LLM to process the input
            response = await llm_service.complete(
                prompt=input_text, system=system_prompt, max_tokens=1000
            )

            if not response:
                # LLM failed - try to handle locally
                self.console.print(
                    "[yellow]⚠ LLM service unavailable. Processing locally...[/yellow]"
                )

                # Check if it's a task-like request
                action_words = [
                    "create",
                    "make",
                    "build",
                    "test",
                    "debug",
                    "deploy",
                    "implement",
                    "add",
                    "fix",
                    "update",
                    "refactor",
                    "write",
                    "generate",
                ]
                if any(word in input_text.lower() for word in action_words):
                    # Route as task
                    self.console.print(
                        f"[dim]→ Routing to task execution: {input_text}[/dim]"
                    )
                    await self.handle_task(input_text)
                    return True
                else:
                    # Can't process without LLM
                    self.console.print(
                        "[red]Unable to process natural language without LLM service.[/red]"
                    )
                    self.console.print(
                        "[dim]Please configure ANTHROPIC_API_KEY or OPENAI_API_KEY in your environment.[/dim]"
                    )
                    return False

            # Display the LLM response
            self.console.print("\n[bold cyan]CASPER Response:[/bold cyan]")
            self.console.print(response)

            # Now determine if we need to execute any actions based on the input
            # Check if this looks like a task request that needs execution
            task_indicators = [
                "create",
                "make",
                "build",
                "implement",
                "add",
                "write",
                "generate",
                "test",
                "debug",
                "deploy",
                "fix",
                "update",
                "refactor",
                "setup",
                "install",
                "configure",
                "delete",
                "remove",
            ]

            is_task_request = any(
                word in input_text.lower() for word in task_indicators
            )

            if is_task_request:
                # This is a task that needs execution
                self.console.print(
                    "\n[dim]→ Executing task through agent system...[/dim]"
                )

                # Use the casper_cli to execute the task directly
                try:
                    await self.casper_cli.execute_task(input_text)
                except Exception as e:
                    self.console.print(f"[red]❌ Task execution failed: {e}[/red]")

                    # Fallback to layer_0_agent if available
                    if self.layer_0_agent:
                        # Create context for agent execution
                        context = ContextBundle(
                            parent_task=input_text,
                            session_id=(
                                self.agent_session["session_id"]
                                if self.agent_session
                                else None
                            ),
                        )

                        # Analyze if we can handle this task
                        can_handle, reason = await self.layer_0_agent.analyze_task(
                            input_text, context
                        )

                        if can_handle:
                            # Execute through the actual agent system
                            result = await self.layer_0_agent.execute_task(
                                input_text, context
                            )

                            if result and result.output:
                                self.console.print(
                                    "\n[bold green]Task Execution Result:[/bold green]"
                                )
                                self.console.print(result.output)

                            # If there were any errors, display them
                            if result and result.errors:
                                self.console.print(
                                    "\n[bold red]Errors encountered:[/bold red]"
                                )
                                for error in result.errors:
                                    self.console.print(f"  • {error}")
                        else:
                            # Can't execute this specific task
                            self.console.print(
                                f"\n[yellow]Note: Unable to execute this task automatically.[/yellow]"
                            )
                            self.console.print(f"[dim]Reason: {reason}[/dim]")

            return True

        except Exception as e:
            logger.error(f"Natural language processing error: {e}")
            self.console.print(f"[red]Error processing natural language: {e}[/red]")

            # Fallback to basic task routing if it looks like a command
            if any(
                word in input_text.lower()
                for word in ["create", "test", "debug", "build"]
            ):
                self.console.print(
                    "[dim]→ Falling back to direct task execution...[/dim]"
                )
                await self.handle_task(input_text)
                return True

            return False

    # ============= TIER 1: CORE COMMANDS =============

    async def handle_help(self, args: str = "") -> None:
        """Handle help command with category support"""
        if args and args not in COMMAND_CATEGORIES:
            self.console.print(f"[red]❌ Unknown category: {args}[/red]")
            self.console.print(
                f"[dim]Available categories: {', '.join(COMMAND_CATEGORIES.keys())}[/dim]"
            )
            return

        if not args:
            # Show all commands
            help_content = (
                "[bold cyan]CASPER2 Complete - All 57 Commands[/bold cyan]\n\n"
            )

            for category, commands in COMMAND_CATEGORIES.items():
                help_content += f"[green]{category.title()} Commands:[/green]\n"
                for cmd, desc in commands.items():
                    help_content += f"  • [yellow]{cmd:<20}[/yellow] - {desc}\n"
                help_content += "\n"

            help_content += "[green]Examples:[/green]\n"
            help_content += "[cyan]task[/cyan] implement REST API\n"
            help_content += "[cyan]/create[/cyan] component UserProfile\n"
            help_content += "[cyan]/test[/cyan] --coverage\n"
            help_content += "[cyan]/ai-review[/cyan] src/main.py"
        else:
            # Show specific category
            help_content = f"[bold cyan]{args.title()} Commands[/bold cyan]\n\n"
            for cmd, desc in COMMAND_CATEGORIES[args].items():
                help_content += f"• [yellow]{cmd:<20}[/yellow] - {desc}\n"

        help_panel = Panel.fit(
            help_content,
            title=f"📖 CASPER2 Help{f' - {args.title()}' if args else ''}",
            border_style="yellow",
        )
        self.console.print(help_panel)

    async def handle_exit(self) -> bool:
        """Handle exit command"""
        self.console.print("[dim]→ Shutting down CASPER2...[/dim]")
        try:
            await self.casper_cli.shutdown()
            self.console.print("[bold green]✓[/bold green] CASPER2 shutdown complete")
        except Exception as e:
            self.console.print(f"[yellow]⚠ Shutdown warning: {e}[/yellow]")
        return True

    async def handle_task(self, args: str) -> None:
        """Handle task execution"""
        if not args:
            self.console.print("[red]❌ Usage:[/red] task <description>")
            return

        self.console.print(f"[dim]→ Executing task:[/dim] [cyan]{args}[/cyan]")
        try:
            await self.casper_cli.execute_task(args)
        except Exception as e:
            self.console.print(f"[red]❌ Task failed: {e}[/red]")

    async def handle_analyze(self, args: str) -> None:
        """Handle task analysis"""
        if not args:
            self.console.print("[red]❌ Usage:[/red] analyze <description>")
            return

        self.console.print(f"[dim]→ Analyzing task:[/dim] [cyan]{args}[/cyan]")
        try:
            await self.casper_cli.analyze_only(args)
        except Exception as e:
            self.console.print(f"[red]❌ Analysis failed: {e}[/red]")

    async def handle_status(self, args: str = "") -> None:
        """Handle status command"""
        self.console.print("[dim]→ Fetching system status...[/dim]")
        try:
            await self.casper_cli.show_status()
        except Exception as e:
            self.console.print(f"[red]❌ Status check failed: {e}[/red]")

    async def handle_list(self, args: str = "") -> None:
        """Handle list command"""
        table = Table(title="Available CASPER2 Agents")
        table.add_column("Agent", style="cyan", width=20)
        table.add_column("Role", style="yellow")
        table.add_column("Capabilities", style="white")

        agents = [
            (
                "Master Prime",
                "Orchestrator",
                "Task routing, complexity analysis, agent coordination",
            ),
            (
                "Alpha Prime",
                "React Developer",
                "React components, TypeScript, frontend architecture",
            ),
            ("Beta Prime", "Backend Developer", "APIs, databases, server architecture"),
            ("Gamma Prime", "Full Stack", "End-to-end implementation, integration"),
            ("Delta Prime", "DevOps", "CI/CD, deployment, infrastructure"),
            (
                "Epsilon Prime",
                "Quality Assurance",
                "Testing, debugging, quality control",
            ),
        ]

        for agent, role, caps in agents:
            table.add_row(agent, role, caps)

        self.console.print(table)

    async def handle_approve(self) -> None:
        """Handle approve command - review pending operations"""
        if self.approval_mode == "YOLO":
            self.console.print(
                "[yellow]⚡ YOLO mode active - operations are auto-approved![/yellow]"
            )
            return

        try:
            # Use the global approval service instance from core.services.approval
            from core.services.approval import approval_service

            # Get pending operations (not async - it's a regular method)
            pending = approval_service.get_pending_approvals()

            if pending:
                self.console.print(
                    f"[yellow]Found {len(pending)} pending operations:[/yellow]\n"
                )

                for op in pending:
                    # Display operation details
                    table = Table(show_header=False, box=None)
                    table.add_column("Field", style="cyan")
                    table.add_column("Value", style="white")

                    table.add_row("Operation ID", op.id)
                    table.add_row("Type", op.operation_type)
                    table.add_row("Path", op.path)
                    table.add_row("Agent ID", op.agent_id)
                    table.add_row(
                        "Created", op.created_at.strftime("%Y-%m-%d %H:%M:%S")
                    )

                    # Show content preview
                    content_preview = (
                        op.content[:200] + "..."
                        if len(op.content) > 200
                        else op.content
                    )
                    table.add_row("Content Preview", content_preview)

                    self.console.print(
                        Panel(
                            table, title=f"[bold yellow]Pending Operation[/bold yellow]"
                        )
                    )

                    # Ask for approval
                    from rich.prompt import Confirm

                    if Confirm.ask("Approve this operation?", default=False):
                        approval_service.approve_operation(op.id)
                        self.console.print("[green]✓ Approved[/green]\n")
                    else:
                        approval_service.reject_operation(op.id)
                        self.console.print("[red]✗ Rejected[/red]\n")
            else:
                self.console.print("[dim]No pending operations to approve[/dim]")

        except Exception as e:
            self.console.print(f"[red]❌ Error accessing approval service: {e}[/red]")

    # ============= TIER 3: DEVELOPMENT COMMANDS =============

    async def handle_create(self, args: str) -> None:
        """Handle create command - creates new components, files, or folders"""
        if not args:
            self.console.print("[red]❌ Usage:[/red] /create <what_to_create>")
            self.console.print("[dim]Examples:[/dim]")
            self.console.print("[dim]  /create a folder named projects[/dim]")
            self.console.print("[dim]  /create a file called index.js[/dim]")
            self.console.print("[dim]  /create component UserProfile[/dim]")
            return

        # Just pass the entire args as the creation task
        self.console.print(f"[dim]→ Creating:[/dim] [cyan]{args}[/cyan]")

        # Pass directly to the task handler without modification
        # The Worker agent will parse what needs to be created
        await self.handle_task(f"create {args}")

    async def handle_test(self, args: str) -> None:
        """Handle test command - runs tests"""
        self.console.print("[dim]→ Running tests...[/dim]")

        test_commands = {
            "": "pytest tests/",
            "--coverage": "pytest --cov=core tests/",
            "--unit": "pytest tests/unit/",
            "--integration": "pytest tests/integration/",
            "--verbose": "pytest -xvs tests/",
        }

        cmd = test_commands.get(args, f"pytest {args}")

        try:
            result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
            if result.returncode == 0:
                self.console.print("[green]✓ Tests passed![/green]")
                if "--coverage" in args:
                    self.console.print(result.stdout)
            else:
                self.console.print("[red]❌ Tests failed[/red]")
                self.console.print(result.stdout)
        except Exception as e:
            self.console.print(f"[red]❌ Test execution failed: {e}[/red]")

    async def handle_debug(self, args: str) -> None:
        """Handle debug command"""
        if not args:
            self.console.print("[red]❌ Usage:[/red] /debug <file_or_issue>")
            return

        self.console.print(f"[dim]→ Debugging:[/dim] [cyan]{args}[/cyan]")

        # Delegate to CASPER for debugging
        task = f"debug the issue: {args}"
        await self.handle_task(task)

    async def handle_review(self, args: str) -> None:
        """Handle code review command"""
        if not args:
            # Review all changed files
            self.console.print("[dim]→ Reviewing changed files...[/dim]")
            task = "review all recently changed files and provide feedback"
        else:
            self.console.print(f"[dim]→ Reviewing:[/dim] [cyan]{args}[/cyan]")
            task = f"perform a code review of {args}"

        await self.handle_task(task)

    async def handle_refactor(self, args: str) -> None:
        """Handle refactor command"""
        if not args:
            self.console.print("[red]❌ Usage:[/red] /refactor <code_or_pattern>")
            return

        self.console.print(f"[dim]→ Refactoring:[/dim] [cyan]{args}[/cyan]")
        task = f"refactor {args} to improve code quality"
        await self.handle_task(task)

    async def handle_init(self, args: str) -> None:
        """Handle project initialization"""
        project_type = args or "python"
        self.console.print(f"[dim]→ Initializing {project_type} project...[/dim]")

        task = f"initialize a new {project_type} project with best practices"
        await self.handle_task(task)

    async def handle_build(self, args: str) -> None:
        """Handle build command"""
        self.console.print("[dim]→ Building project...[/dim]")

        # Try common build commands
        build_commands = [
            "npm run build",
            "yarn build",
            "python setup.py build",
            "make build",
            "cargo build",
        ]

        for cmd in build_commands:
            if shutil.which(cmd.split()[0]):
                try:
                    result = subprocess.run(
                        cmd, shell=True, capture_output=True, text=True
                    )
                    if result.returncode == 0:
                        self.console.print("[green]✓ Build successful![/green]")
                        return
                except:
                    continue

        self.console.print("[yellow]⚠ No build configuration found[/yellow]")

    async def handle_deploy(self, args: str) -> None:
        """Handle deployment"""
        environment = args or "production"
        self.console.print(f"[dim]→ Deploying to {environment}...[/dim]")

        task = f"deploy the application to {environment}"
        await self.handle_task(task)

    async def handle_rollback(self, args: str) -> None:
        """Handle deployment rollback"""
        version = args or "previous"
        self.console.print(f"[dim]→ Rolling back to {version}...[/dim]")

        task = f"rollback deployment to {version}"
        await self.handle_task(task)

    async def handle_migrate(self, args: str) -> None:
        """Handle database migrations"""
        self.console.print("[dim]→ Running migrations...[/dim]")

        # Try common migration commands
        migration_commands = [
            "python manage.py migrate",
            "alembic upgrade head",
            "npm run migrate",
            "rake db:migrate",
        ]

        for cmd in migration_commands:
            if shutil.which(cmd.split()[0]):
                try:
                    result = subprocess.run(
                        cmd, shell=True, capture_output=True, text=True
                    )
                    if result.returncode == 0:
                        self.console.print("[green]✓ Migrations completed![/green]")
                        return
                except:
                    continue

        self.console.print("[yellow]⚠ No migration system found[/yellow]")

    async def handle_generate(self, args: str) -> None:
        """Handle code generation"""
        if not args:
            self.console.print("[red]❌ Usage:[/red] /generate <type> <name>")
            return

        self.console.print(f"[dim]→ Generating:[/dim] [cyan]{args}[/cyan]")
        task = f"generate {args}"
        await self.handle_task(task)

    async def handle_scaffold(self, args: str) -> None:
        """Handle project scaffolding"""
        template = args or "default"
        self.console.print(
            f"[dim]→ Scaffolding with template:[/dim] [cyan]{template}[/cyan]"
        )

        task = f"scaffold project structure using {template} template"
        await self.handle_task(task)

    async def handle_optimize(self, args: str) -> None:
        """Handle code optimization"""
        target = args or "all"
        self.console.print(f"[dim]→ Optimizing:[/dim] [cyan]{target}[/cyan]")

        task = f"optimize {target} for better performance"
        await self.handle_task(task)

    async def handle_profile(self, args: str) -> None:
        """Handle performance profiling"""
        target = args or "application"
        self.console.print(f"[dim]→ Profiling:[/dim] [cyan]{target}[/cyan]")

        task = f"profile {target} performance and identify bottlenecks"
        await self.handle_task(task)

    # ============= TIER 4: AI COMMANDS =============

    async def handle_ai_review(self, args: str) -> None:
        """Handle AI code review"""
        target = args or "changed files"
        self.console.print(f"[dim]→ AI reviewing:[/dim] [cyan]{target}[/cyan]")

        task = f"perform an AI-powered code review of {target}"
        await self.handle_task(task)

    async def handle_ai_complete(self, args: str) -> None:
        """Handle AI code completion"""
        if not args:
            self.console.print("[red]❌ Usage:[/red] /ai-complete <partial_code>")
            return

        self.console.print(f"[dim]→ AI completing code...[/dim]")
        task = f"complete this code: {args}"
        await self.handle_task(task)

    async def handle_ai_explain(self, args: str) -> None:
        """Handle AI code explanation"""
        if not args:
            self.console.print("[red]❌ Usage:[/red] /ai-explain <code_or_file>")
            return

        self.console.print(f"[dim]→ AI explaining:[/dim] [cyan]{args}[/cyan]")
        task = f"explain this code: {args}"
        await self.handle_task(task)

    async def handle_ai_suggest(self, args: str) -> None:
        """Handle AI suggestions"""
        context = args or "current project"
        self.console.print(
            f"[dim]→ Getting AI suggestions for:[/dim] [cyan]{context}[/cyan]"
        )

        task = f"provide AI suggestions for improving {context}"
        await self.handle_task(task)

    async def handle_ai_translate(self, args: str) -> None:
        """Handle AI code translation"""
        if not args:
            self.console.print(
                "[red]❌ Usage:[/red] /ai-translate <from_lang> <to_lang> <code>"
            )
            return

        self.console.print(f"[dim]→ AI translating code...[/dim]")
        task = f"translate code: {args}"
        await self.handle_task(task)

    # ============= TIER 4: BUSINESS COMMANDS =============

    async def handle_invoice(self, args: str) -> None:
        """Handle invoice generation"""
        client = args or "default"
        self.console.print(
            f"[dim]→ Generating invoice for:[/dim] [cyan]{client}[/cyan]"
        )

        task = f"generate an invoice for {client}"
        await self.handle_task(task)

    async def handle_proposal(self, args: str) -> None:
        """Handle proposal creation"""
        project = args or "new project"
        self.console.print(
            f"[dim]→ Creating proposal for:[/dim] [cyan]{project}[/cyan]"
        )

        task = f"create a project proposal for {project}"
        await self.handle_task(task)

    async def handle_contract(self, args: str) -> None:
        """Handle contract drafting"""
        contract_type = args or "service"
        self.console.print(f"[dim]→ Drafting {contract_type} contract...[/dim]")

        task = f"draft a {contract_type} contract"
        await self.handle_task(task)

    async def handle_quote(self, args: str) -> None:
        """Handle quote generation"""
        service = args or "development services"
        self.console.print(f"[dim]→ Generating quote for:[/dim] [cyan]{service}[/cyan]")

        task = f"generate a quote for {service}"
        await self.handle_task(task)

    async def handle_timesheet(self, args: str) -> None:
        """Handle timesheet management"""
        action = args or "view"
        self.console.print(f"[dim]→ Timesheet action:[/dim] [cyan]{action}[/cyan]")

        if action == "view":
            task = "show timesheet entries for this week"
        elif action == "add":
            task = "add a timesheet entry"
        else:
            task = f"manage timesheet: {action}"

        await self.handle_task(task)

    # ============= TIER 4: TESTING COMMANDS =============

    async def handle_unit_test(self, args: str) -> None:
        """Handle unit test execution"""
        target = args or "all"
        self.console.print(
            f"[dim]→ Running unit tests for:[/dim] [cyan]{target}[/cyan]"
        )

        cmd = f"pytest tests/unit/{target}" if target != "all" else "pytest tests/unit/"
        try:
            result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
            if result.returncode == 0:
                self.console.print("[green]✓ Unit tests passed![/green]")
            else:
                self.console.print("[red]❌ Unit tests failed[/red]")
        except Exception as e:
            self.console.print(f"[red]❌ Error: {e}[/red]")

    async def handle_integration_test(self, args: str) -> None:
        """Handle integration test execution"""
        self.console.print("[dim]→ Running integration tests...[/dim]")

        cmd = (
            "pytest tests/integration/"
            if not args
            else f"pytest tests/integration/{args}"
        )
        try:
            result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
            if result.returncode == 0:
                self.console.print("[green]✓ Integration tests passed![/green]")
            else:
                self.console.print("[red]❌ Integration tests failed[/red]")
        except Exception as e:
            self.console.print(f"[red]❌ Error: {e}[/red]")

    async def handle_e2e_test(self, args: str) -> None:
        """Handle end-to-end test execution"""
        self.console.print("[dim]→ Running end-to-end tests...[/dim]")

        # Try common E2E test commands
        e2e_commands = [
            "npm run test:e2e",
            "yarn test:e2e",
            "playwright test",
            "cypress run",
        ]

        for cmd in e2e_commands:
            if shutil.which(cmd.split()[0]):
                try:
                    result = subprocess.run(
                        cmd, shell=True, capture_output=True, text=True
                    )
                    if result.returncode == 0:
                        self.console.print("[green]✓ E2E tests passed![/green]")
                        return
                except:
                    continue

        self.console.print("[yellow]⚠ No E2E test runner found[/yellow]")

    async def handle_load_test(self, args: str) -> None:
        """Handle load testing"""
        target = args or "http://localhost:8000"
        self.console.print(
            f"[dim]→ Running load test against:[/dim] [cyan]{target}[/cyan]"
        )

        task = f"perform load testing on {target}"
        await self.handle_task(task)

    async def handle_security_test(self, args: str) -> None:
        """Handle security testing"""
        self.console.print("[dim]→ Running security tests...[/dim]")

        task = "perform security testing and vulnerability scanning"
        await self.handle_task(task)

    # ============= TIER 4: UTILITY COMMANDS =============

    async def handle_search(self, args: str) -> None:
        """Handle search in codebase"""
        if not args:
            self.console.print("[red]❌ Usage:[/red] /search <pattern>")
            return

        self.console.print(f"[dim]→ Searching for:[/dim] [cyan]{args}[/cyan]")

        try:
            # Use ripgrep if available, otherwise grep
            cmd = f"rg '{args}'" if shutil.which("rg") else f"grep -r '{args}' ."
            result = subprocess.run(cmd, shell=True, capture_output=True, text=True)

            if result.stdout:
                all_lines = result.stdout.strip().split("\n")
                lines = all_lines[:20]  # Show first 20 results
                for line in lines:
                    self.console.print(line)
                if len(all_lines) > 20:
                    self.console.print(
                        f"[dim]... and {len(all_lines) - 20} more results[/dim]"
                    )
            else:
                self.console.print("[yellow]No results found[/yellow]")
        except Exception as e:
            self.console.print(f"[red]❌ Search failed: {e}[/red]")

    async def handle_replace(self, args: str) -> None:
        """Handle find and replace"""
        if not args or " " not in args:
            self.console.print("[red]❌ Usage:[/red] /replace <find> <replace>")
            return

        parts = args.split(maxsplit=1)
        find_text = parts[0]
        replace_text = parts[1] if len(parts) > 1 else ""

        self.console.print(
            f"[dim]→ Replacing:[/dim] [cyan]{find_text}[/cyan] → [green]{replace_text}[/green]"
        )

        task = f"find and replace '{find_text}' with '{replace_text}' in the codebase"
        await self.handle_task(task)

    async def handle_format(self, args: str) -> None:
        """Handle code formatting"""
        target = args or "."
        self.console.print(f"[dim]→ Formatting:[/dim] [cyan]{target}[/cyan]")

        # Try common formatters
        formatters = {
            ".py": "black",
            ".js": "prettier",
            ".ts": "prettier",
            ".go": "gofmt",
            ".rs": "rustfmt",
        }

        for ext, formatter in formatters.items():
            if shutil.which(formatter):
                cmd = f"{formatter} {target}"
                try:
                    subprocess.run(cmd, shell=True)
                    self.console.print(f"[green]✓ Formatted with {formatter}[/green]")
                    return
                except:
                    continue

        self.console.print("[yellow]⚠ No formatter found[/yellow]")

    async def handle_lint(self, args: str) -> None:
        """Handle code linting"""
        target = args or "."
        self.console.print(f"[dim]→ Linting:[/dim] [cyan]{target}[/cyan]")

        # Try common linters
        linters = ["eslint", "pylint", "flake8", "rubocop", "golint"]

        for linter in linters:
            if shutil.which(linter):
                cmd = f"{linter} {target}"
                try:
                    result = subprocess.run(
                        cmd, shell=True, capture_output=True, text=True
                    )
                    if result.returncode == 0:
                        self.console.print(f"[green]✓ No linting issues found![/green]")
                    else:
                        self.console.print(f"[yellow]⚠ Linting issues found[/yellow]")
                        self.console.print(result.stdout[:500])  # Show first 500 chars
                    return
                except:
                    continue

        self.console.print("[yellow]⚠ No linter found[/yellow]")

    async def handle_clean(self, args: str) -> None:
        """Handle project cleaning"""
        self.console.print("[dim]→ Cleaning project...[/dim]")

        # Common clean patterns
        patterns = [
            "**/__pycache__",
            "**/node_modules",
            "**/dist",
            "**/build",
            "**/*.pyc",
            "**/.DS_Store",
        ]

        cleaned = 0
        for pattern in patterns:
            for path in Path(".").glob(pattern):
                try:
                    if path.is_dir():
                        shutil.rmtree(path)
                    else:
                        path.unlink()
                    cleaned += 1
                except:
                    pass

        self.console.print(f"[green]✓ Cleaned {cleaned} items[/green]")

    async def handle_backup(self, args: str) -> None:
        """Handle project backup"""
        backup_name = args or f"backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        backup_path = self.backup_dir / backup_name

        self.console.print(f"[dim]→ Creating backup:[/dim] [cyan]{backup_name}[/cyan]")

        try:
            shutil.make_archive(str(backup_path), "zip", self.project_root)
            self.console.print(f"[green]✓ Backup created: {backup_path}.zip[/green]")
        except Exception as e:
            self.console.print(f"[red]❌ Backup failed: {e}[/red]")

    async def handle_restore(self, args: str) -> None:
        """Handle backup restoration"""
        if not args:
            # List available backups
            backups = list(self.backup_dir.glob("*.zip"))
            if backups:
                self.console.print("[yellow]Available backups:[/yellow]")
                for backup in backups:
                    self.console.print(f"  • {backup.name}")
            else:
                self.console.print("[yellow]No backups found[/yellow]")
            return

        backup_path = self.backup_dir / args
        if not backup_path.exists():
            backup_path = self.backup_dir / f"{args}.zip"

        if backup_path.exists():
            self.console.print(
                f"[dim]→ Restoring from:[/dim] [cyan]{backup_path.name}[/cyan]"
            )
            try:
                shutil.unpack_archive(str(backup_path), self.project_root)
                self.console.print("[green]✓ Backup restored successfully[/green]")
            except Exception as e:
                self.console.print(f"[red]❌ Restore failed: {e}[/red]")
        else:
            self.console.print(f"[red]❌ Backup not found: {args}[/red]")

    async def handle_export(self, args: str) -> None:
        """Handle data export"""
        format_type = args or "json"
        export_file = (
            self.export_dir
            / f"export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.{format_type}"
        )

        self.console.print(
            f"[dim]→ Exporting data as:[/dim] [cyan]{format_type}[/cyan]"
        )

        task = f"export project data to {export_file}"
        await self.handle_task(task)

    async def handle_import(self, args: str) -> None:
        """Handle data import"""
        if not args:
            self.console.print("[red]❌ Usage:[/red] /import <file>")
            return

        self.console.print(f"[dim]→ Importing from:[/dim] [cyan]{args}[/cyan]")

        task = f"import data from {args}"
        await self.handle_task(task)

    async def handle_sync(self, args: str) -> None:
        """Handle repository synchronization"""
        remote = args or "origin"
        self.console.print(f"[dim]→ Syncing with:[/dim] [cyan]{remote}[/cyan]")

        try:
            # Git sync commands
            commands = [
                f"git fetch {remote}",
                f"git pull {remote}",
                f"git push {remote}",
            ]

            for cmd in commands:
                result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
                if result.returncode != 0 and "Already up to date" not in result.stdout:
                    self.console.print(f"[yellow]⚠ {cmd} had issues[/yellow]")

            self.console.print("[green]✓ Repository synchronized[/green]")
        except Exception as e:
            self.console.print(f"[red]❌ Sync failed: {e}[/red]")

    # ============= MAIN COMMAND ROUTER =============

    async def handle_clear(self) -> None:
        """Handle clear command - clears the screen"""
        self.console.clear()
        # Reprint banner after clear
        print_casper2_banner()
        self.console.print()

    async def handle_agent_command(self, command: str, args: str) -> None:
        """Delegate compact agent-style commands to the shared slash registry."""
        if not self.slash_commands:
            self.slash_commands = SlashCommandRegistry(self.casper_cli)
        await self.slash_commands.execute(f"{command} {args}".rstrip())

    async def handle_command(self, command: str, args: str) -> bool:
        """Route command to appropriate handler"""

        # Handle empty command edge case
        if not command:
            # If we get here with no command, treat the whole thing as natural language
            full_input = f"{command} {args}".strip()
            if full_input:
                handled = await self.process_natural_language(full_input)
                if handled:
                    return False  # Don't exit
            return False

        # Command mapping
        handlers = {
            # Core commands
            "help": lambda: self.handle_help(args),
            "?": lambda: self.handle_help(args),
            "task": lambda: self.handle_task(args),
            "analyze": lambda: self.handle_analyze(args),
            "status": lambda: self.handle_status(),
            "approve": lambda: self.handle_approve(),
            "list": lambda: self.handle_list(),
            "clear": lambda: self.handle_clear(),
            "cls": lambda: self.handle_clear(),  # Windows-style alias
            "exit": lambda: self.handle_exit(),
            "quit": lambda: self.handle_exit(),
            "q": lambda: self.handle_exit(),
            # Slash commands
            "/help": lambda: self.handle_help(args),
            "/task": lambda: self.handle_task(args),
            "/analyze": lambda: self.handle_analyze(args),
            "/status": lambda: self.handle_status(),
            "/goal": lambda: self.handle_agent_command("/goal", args),
            "/model": lambda: self.handle_agent_command("/model", args),
            "/models": lambda: self.handle_agent_command(
                "/model", f"list {args}".strip()
            ),
            "/plan": lambda: self.handle_agent_command("/plan", args),
            "/diff": lambda: self.handle_agent_command("/diff", args),
            "/pwd": lambda: self.handle_agent_command("/pwd", args),
            # Development commands
            "/create": lambda: self.handle_create(args),
            "/test": lambda: self.handle_test(args),
            "/debug": lambda: self.handle_debug(args),
            "/review": lambda: self.handle_review(args),
            "/refactor": lambda: self.handle_refactor(args),
            "/init": lambda: self.handle_init(args),
            "/build": lambda: self.handle_build(args),
            "/deploy": lambda: self.handle_deploy(args),
            "/rollback": lambda: self.handle_rollback(args),
            "/migrate": lambda: self.handle_migrate(args),
            "/generate": lambda: self.handle_generate(args),
            "/scaffold": lambda: self.handle_scaffold(args),
            "/optimize": lambda: self.handle_optimize(args),
            "/profile": lambda: self.handle_profile(args),
            # AI commands
            "/ai-review": lambda: self.handle_ai_review(args),
            "/ai-complete": lambda: self.handle_ai_complete(args),
            "/ai-explain": lambda: self.handle_ai_explain(args),
            "/ai-suggest": lambda: self.handle_ai_suggest(args),
            "/ai-translate": lambda: self.handle_ai_translate(args),
            # Business commands
            "/invoice": lambda: self.handle_invoice(args),
            "/proposal": lambda: self.handle_proposal(args),
            "/contract": lambda: self.handle_contract(args),
            "/quote": lambda: self.handle_quote(args),
            "/timesheet": lambda: self.handle_timesheet(args),
            # Testing commands
            "/unit-test": lambda: self.handle_unit_test(args),
            "/integration-test": lambda: self.handle_integration_test(args),
            "/e2e-test": lambda: self.handle_e2e_test(args),
            "/load-test": lambda: self.handle_load_test(args),
            "/security-test": lambda: self.handle_security_test(args),
            # Utility commands
            "/search": lambda: self.handle_search(args),
            "/replace": lambda: self.handle_replace(args),
            "/format": lambda: self.handle_format(args),
            "/lint": lambda: self.handle_lint(args),
            "/clean": lambda: self.handle_clean(args),
            "/backup": lambda: self.handle_backup(args),
            "/restore": lambda: self.handle_restore(args),
            "/export": lambda: self.handle_export(args),
            "/import": lambda: self.handle_import(args),
            "/sync": lambda: self.handle_sync(args),
        }

        if command in handlers:
            result = await handlers[command]()
            return result if command in ["exit", "quit", "q"] else False
        else:
            # Unknown command - try natural language as fallback
            full_input = f"{command} {args}".strip()
            self.console.print(f"[yellow]Unknown command '{command}'.[/yellow]")
            self.console.print(
                "[dim]→ Attempting to interpret as natural language...[/dim]"
            )

            # Try to process as natural language
            handled = await self.process_natural_language(full_input)

            if not handled:
                self.console.print(f"[red]❌ Unable to process: {full_input}[/red]")
                self.console.print("[dim]Type 'help' for available commands[/dim]")

            return False

    async def execute_direct_task(self, task: str):
        """Execute a single task directly from command line"""
        print_casper2_banner()

        # Initialize
        await self.initialize()

        # Execute task through natural language processing
        print(f"\n[cyan]→ Executing task: {task}[/cyan]")

        # Process as natural language
        handled = await self.process_natural_language(task)

        if not handled:
            # Try as a command if NLP didn't handle it
            parts = task.split(maxsplit=1)
            if len(parts) == 2:
                command, args = parts
                await self.handle_command(command, args)
            elif len(parts) == 1:
                await self.handle_command(parts[0], "")

        # Clean shutdown
        if self.agent_initializer:
            await self.agent_initializer.shutdown()

    async def run(self):
        """Main terminal loop"""
        import time

        # Track consecutive CTRL-C presses
        last_interrupt_time = 0
        interrupt_threshold = 2.0  # seconds

        # Print banner
        print_casper2_banner()

        # Initialize
        await self.initialize()

        # Welcome message with approval mode status
        approval_status = {
            "YOLO": "[bold yellow]⚡ YOLO MODE[/bold yellow] - Auto-approving everything",
            "AUTO": "[bold green]🤖 AUTO MODE[/bold green] - Smart auto-approval",
            "STRICT": "[bold red]🔒 STRICT MODE[/bold red] - Manual approval required",
        }.get(self.approval_mode, "[dim]Unknown approval mode[/dim]")

        welcome_panel = Panel.fit(
            "[bold cyan]CASPER2 Complete Terminal[/bold cyan]\n"
            "[dim]All 50+ Commands with Full Approval Control[/dim]\n\n"
            f"Approval: {approval_status}\n\n"
            "[green]• Core Commands:[/green] 8 commands\n"
            "[green]• Workflow Commands:[/green] 5 commands\n"
            "[green]• Development Commands:[/green] 14 commands\n"
            "[green]• AI Commands:[/green] 5 commands\n"
            "[green]• Business Commands:[/green] 5 commands\n"
            "[green]• Testing Commands:[/green] 5 commands\n"
            "[green]• Utility Commands:[/green] 10 commands\n\n"
            "[yellow]Total: 50+ commands ready[/yellow]\n"
            "[dim]Type 'help' for commands, 'approve' to review operations[/dim]\n"
            "[dim]Press Ctrl+C twice quickly to force exit[/dim]",
            title="🚀 CASPER2 Complete",
            border_style="cyan",
        )
        self.console.print(welcome_panel)
        self.console.print()

        # Main loop
        while True:
            try:
                # Get user input
                user_input = Prompt.ask(
                    Text.from_markup("[bold blue]casper2[/bold blue][dim]>[/dim]"),
                    default="",
                ).strip()

                if not user_input:
                    continue

                # First, try natural language processing if not a clear command
                # Check if it starts with a known command prefix
                is_command = user_input.startswith("/") or user_input.split()[
                    0
                ].lower() in [
                    "help",
                    "task",
                    "analyze",
                    "status",
                    "approve",
                    "clear",
                    "exit",
                    "quit",
                    "list",
                    "cls",
                    "q",
                ]

                if not is_command:
                    # Try to process as natural language
                    handled = await self.process_natural_language(user_input)
                    if handled:
                        self.console.print()  # Add spacing
                        continue

                # Parse as command if not handled by NLP or is explicit command
                parts = user_input.split(" ", 1)
                command = parts[0].lower()
                args = parts[1] if len(parts) > 1 else ""

                # Handle command
                should_exit = await self.handle_command(command, args)
                if should_exit:
                    break

                self.console.print()  # Add spacing

            except KeyboardInterrupt:
                current_time = time.time()
                if current_time - last_interrupt_time < interrupt_threshold:
                    # Second CTRL-C within threshold - exit
                    self.console.print("\n[dim]→ Shutting down CASPER2...[/dim]")
                    try:
                        await self.casper_cli.shutdown()
                        self.console.print(
                            "[bold green]✓[/bold green] CASPER2 shutdown complete"
                        )
                    except:
                        pass  # Ignore shutdown errors on force exit
                    break
                else:
                    # First CTRL-C - show message and continue
                    last_interrupt_time = current_time
                    self.console.print(
                        "\n[dim]→ Press Ctrl+C again to exit, or type 'exit' for graceful shutdown[/dim]"
                    )

            except Exception as e:
                self.console.print(f"[red]❌ Error: {e}[/red]")
                self.console.print(
                    "[dim]The session remains active. Type 'help' for commands.[/dim]"
                )


def print_casper2_banner():
    """Print CASPER2 banner"""
    console = Console()

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
    console.print(
        "[bold green]✓[/bold green] [bright_white]CASPER2 Complete initialized[/bright_white]"
    )


async def main():
    """Main entry point"""
    import argparse

    # Parse command-line arguments
    parser = argparse.ArgumentParser(description="CASPER2 Complete Terminal")
    parser.add_argument("task", nargs="?", help="Task to execute directly")
    parser.add_argument(
        "--yolo",
        action="store_true",
        help="Enable YOLO mode (auto-approve all operations)",
    )
    parser.add_argument(
        "--auto",
        action="store_true",
        help="Enable AUTO mode (auto-approve safe operations)",
    )
    parser.add_argument(
        "--strict",
        action="store_true",
        help="Enable STRICT mode (require approval for all operations)",
    )

    args = parser.parse_args()

    # Set approval mode based on flags
    if args.yolo:
        os.environ["CASPER_APPROVAL_MODE"] = "YOLO"
    elif args.auto:
        os.environ["CASPER_APPROVAL_MODE"] = "AUTO"
    elif args.strict:
        os.environ["CASPER_APPROVAL_MODE"] = "STRICT"

    terminal = CasperTerminalComplete()

    try:
        if args.task:
            # Execute task directly and exit
            await terminal.execute_direct_task(args.task)
        else:
            # Run interactive mode
            await terminal.run()
    except KeyboardInterrupt:
        print("\n👋 CASPER2 Terminal interrupted")
    except Exception as e:
        print(f"❌ Fatal error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
