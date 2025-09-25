"""
CASPER Slash Command System
Implements industry-standard CLI slash commands for efficient development workflows.
"""

import os
import json
import asyncio
import subprocess
from pathlib import Path
from typing import Dict, List, Optional, Callable, Any
from dataclasses import dataclass
from datetime import datetime
from uuid import uuid4

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.syntax import Syntax
from rich.prompt import Prompt, Confirm

from core.services.user_config import user_config
from core.context.manager import ContextManager
from core.services.personalization import personalization_manager

console = Console()

@dataclass
class SlashCommand:
    """Represents a slash command with its metadata and handler."""
    name: str
    description: str
    usage: str
    handler: Callable
    category: str = "General"
    aliases: List[str] = None

    def __post_init__(self):
        if self.aliases is None:
            self.aliases = []

class SlashCommandRegistry:
    """Registry for all available slash commands."""

    def __init__(self, casper_cli=None):
        self.commands: Dict[str, SlashCommand] = {}
        self.casper_cli = casper_cli
        self.context_manager = ContextManager()
        self.sessions_dir = Path.home() / ".casper" / "sessions"
        self.sessions_dir.mkdir(parents=True, exist_ok=True)

        # Register built-in commands
        self._register_builtin_commands()
        self._load_custom_commands()

    def register(self, command: SlashCommand):
        """Register a new slash command."""
        self.commands[command.name] = command
        for alias in command.aliases:
            self.commands[alias] = command

    def get_command(self, name: str) -> Optional[SlashCommand]:
        """Get a command by name or alias."""
        return self.commands.get(name.lstrip('/'))

    def list_commands(self, category: Optional[str] = None) -> List[SlashCommand]:
        """List all commands, optionally filtered by category."""
        # Remove duplicates from aliases by using a dict keyed by command name
        seen = {}
        for cmd in self.commands.values():
            if cmd.name not in seen:
                seen[cmd.name] = cmd

        commands = list(seen.values())
        if category:
            commands = [cmd for cmd in commands if cmd.category == category]
        return sorted(commands, key=lambda x: (x.category, x.name))

    async def execute(self, command_line: str) -> bool:
        """Execute a slash command or custom command. Returns True if command was found and executed."""
        if not command_line.startswith('/') and not command_line.startswith('#'):
            return False

        # Handle custom #commands
        if command_line.startswith('#'):
            parts = command_line[1:].split(' ')
            command_name = parts[0].lower()
            args = parts[1:] if len(parts) > 1 else []

            return await personalization_manager.execute_custom_command(command_name, args, self)

        # Handle regular /commands
        parts = command_line[1:].split(' ', 1)
        command_name = parts[0].lower()
        args = parts[1] if len(parts) > 1 else ""

        command = self.get_command(command_name)
        if not command:
            console.print(f"[red]❌ Unknown command: /{command_name}[/red]")
            console.print("[dim]Type '/help' to see available commands, '/custom' to see custom commands[/dim]")
            return True

        try:
            await command.handler(args)
            return True
        except Exception as e:
            console.print(f"[red]❌ Error executing /{command_name}: {str(e)}[/red]")
            return True

    def _register_builtin_commands(self):
        """Register all built-in slash commands."""

        # === HELP AND SYSTEM ===
        self.register(SlashCommand(
            name="help",
            description="Show available commands and their descriptions",
            usage="/help [category]",
            handler=self._cmd_help,
            category="System",
            aliases=["h", "?"]
        ))

        self.register(SlashCommand(
            name="status",
            description="Show system status, agent pool, and current tasks",
            usage="/status",
            handler=self._cmd_status,
            category="System"
        ))

        self.register(SlashCommand(
            name="config",
            description="View or modify CASPER configuration",
            usage="/config [show|set <key> <value>]",
            handler=self._cmd_config,
            category="System"
        ))

        self.register(SlashCommand(
            name="setup",
            description="Configure AI provider API keys",
            usage="/setup",
            handler=self._cmd_setup,
            category="System"
        ))

        self.register(SlashCommand(
            name="clear",
            description="Clear current chat and start fresh",
            usage="/clear",
            handler=self._cmd_clear,
            category="System"
        ))

        # === SESSION MANAGEMENT ===
        self.register(SlashCommand(
            name="save",
            description="Save current session with optional name",
            usage="/save [session_name]",
            handler=self._cmd_save,
            category="Session"
        ))

        self.register(SlashCommand(
            name="resume",
            description="Resume a saved session",
            usage="/resume [session_id]",
            handler=self._cmd_resume,
            category="Session"
        ))

        self.register(SlashCommand(
            name="sessions",
            description="List all saved sessions",
            usage="/sessions",
            handler=self._cmd_sessions,
            category="Session",
            aliases=["list-sessions"]
        ))

        # === CODE GENERATION ===
        self.register(SlashCommand(
            name="newcomponent",
            description="Generate a new component with boilerplate, tests, and docs",
            usage="/newcomponent <name> [--type=react|vue|python]",
            handler=self._cmd_newcomponent,
            category="Code Generation"
        ))

        self.register(SlashCommand(
            name="gen",
            description="Generate feature scaffolding (API, DB, frontend)",
            usage="/gen <feature_name> [--full|--api|--frontend]",
            handler=self._cmd_gen,
            category="Code Generation"
        ))

        self.register(SlashCommand(
            name="addroute",
            description="Create new frontend route with component",
            usage="/addroute <path> <component>",
            handler=self._cmd_addroute,
            category="Code Generation",
            aliases=["route"]
        ))

        self.register(SlashCommand(
            name="docs",
            description="Generate documentation for function or file",
            usage="/docs <file_or_function>",
            handler=self._cmd_docs,
            category="Code Generation"
        ))

        self.register(SlashCommand(
            name="refactor",
            description="AI-powered code refactoring suggestions",
            usage="/refactor <file> [suggestion]",
            handler=self._cmd_refactor,
            category="Code Generation"
        ))

        # === GIT AND VERSION CONTROL ===
        self.register(SlashCommand(
            name="commit",
            description="Generate smart commit message from changes",
            usage="/commit [--message='custom message']",
            handler=self._cmd_commit,
            category="Git"
        ))

        self.register(SlashCommand(
            name="pr",
            description="Create pull request with smart title and description",
            usage="/pr [--title='PR title']",
            handler=self._cmd_pr,
            category="Git"
        ))

        self.register(SlashCommand(
            name="review",
            description="AI code review of file or current changes",
            usage="/review [file_path]",
            handler=self._cmd_review,
            category="Git"
        ))

        self.register(SlashCommand(
            name="fixbug",
            description="Create bug fix branch and workflow",
            usage="/fixbug <issue_number>",
            handler=self._cmd_fixbug,
            category="Git"
        ))

        # === TESTING AND DEBUGGING ===
        self.register(SlashCommand(
            name="test",
            description="Run tests for specific file or component",
            usage="/test [file_or_component]",
            handler=self._cmd_test,
            category="Testing"
        ))

        self.register(SlashCommand(
            name="testfail",
            description="Rerun only failed tests",
            usage="/testfail",
            handler=self._cmd_testfail,
            category="Testing",
            aliases=["test-fail"]
        ))

        self.register(SlashCommand(
            name="debug",
            description="Set up debugging session for issue",
            usage="/debug [issue_number]",
            handler=self._cmd_debug,
            category="Testing"
        ))

        self.register(SlashCommand(
            name="explain",
            description="Explain error or code concept",
            usage="/explain [error_message|concept]",
            handler=self._cmd_explain,
            category="Testing",
            aliases=["explain-error"]
        ))

        # === WORKFLOW ===
        self.register(SlashCommand(
            name="todo",
            description="Add task to project todo list",
            usage="/todo <task_description>",
            handler=self._cmd_todo,
            category="Workflow"
        ))

        self.register(SlashCommand(
            name="standup",
            description="Generate standup summary from recent activity",
            usage="/standup",
            handler=self._cmd_standup,
            category="Workflow"
        ))

        self.register(SlashCommand(
            name="deploy",
            description="Deploy to specified environment",
            usage="/deploy <environment>",
            handler=self._cmd_deploy,
            category="Workflow"
        ))

        self.register(SlashCommand(
            name="sync",
            description="Sync with remote repository and update dependencies",
            usage="/sync",
            handler=self._cmd_sync,
            category="Workflow"
        ))

        # === PERSONALIZATION ===
        self.register(SlashCommand(
            name="custom",
            description="Manage custom commands and personalizations",
            usage="/custom [list|add|delete|prefs]",
            handler=self._cmd_custom,
            category="Personalization",
            aliases=["c", "personalize"]
        ))

        self.register(SlashCommand(
            name="favorite",
            description="Add/remove commands from favorites",
            usage="/favorite [add|remove] <command>",
            handler=self._cmd_favorite,
            category="Personalization",
            aliases=["fav", "star"]
        ))

        self.register(SlashCommand(
            name="theme",
            description="Change CASPER theme and appearance",
            usage="/theme [list|set <theme_name>|create]",
            handler=self._cmd_theme,
            category="Personalization"
        ))

        self.register(SlashCommand(
            name="profile",
            description="Manage project profiles",
            usage="/profile [list|create|use] <profile_name>",
            handler=self._cmd_profile,
            category="Personalization"
        ))

        # === ENVIRONMENT & INFRASTRUCTURE ===
        self.register(SlashCommand(
            name="env",
            description="Environment variable management with encryption",
            usage="/env [list|set <key> <value>|get <key>|delete <key>|encrypt|sync]",
            handler=self._cmd_env,
            category="Environment"
        ))

        self.register(SlashCommand(
            name="migrate",
            description="Database migration generation and execution",
            usage="/migrate [create <name>|up|down|status|rollback]",
            handler=self._cmd_migrate,
            category="Database"
        ))

        self.register(SlashCommand(
            name="seed",
            description="Database seeding with test/sample data",
            usage="/seed [run|create <seeder>|rollback]",
            handler=self._cmd_seed,
            category="Database"
        ))

        # === SECURITY & QUALITY ===
        self.register(SlashCommand(
            name="scan",
            description="Security vulnerability scanning",
            usage="/scan [deps|code|all] [--fix]",
            handler=self._cmd_scan,
            category="Security"
        ))

        self.register(SlashCommand(
            name="lint",
            description="Multi-language linting with auto-fix",
            usage="/lint [file_pattern] [--fix] [--all]",
            handler=self._cmd_lint,
            category="Quality"
        ))

        # === API & INTEGRATION ===
        self.register(SlashCommand(
            name="api",
            description="Generate REST/GraphQL API scaffolding",
            usage="/api [rest|graphql] <resource_name> [--crud] [--auth]",
            handler=self._cmd_api,
            category="API"
        ))

        # === PERFORMANCE & MONITORING ===
        self.register(SlashCommand(
            name="logs",
            description="Intelligent log analysis and error detection",
            usage="/logs [tail|search <pattern>|errors] [--follow]",
            handler=self._cmd_logs,
            category="Monitoring"
        ))

        # === CONTEXT & PROJECT MANAGEMENT ===
        self.register(SlashCommand(
            name="context",
            description="Save/restore full project context and mental model",
            usage="/context [save|restore|list] [context_name]",
            handler=self._cmd_context,
            category="Context"
        ))

        self.register(SlashCommand(
            name="switch",
            description="Smart project switching with context preservation",
            usage="/switch <project_name> [--save-current]",
            handler=self._cmd_switch,
            category="Context"
        ))

        self.register(SlashCommand(
            name="notes",
            description="Contextual note-taking linked to code/commits",
            usage="/notes [add|list|search] [note_text]",
            handler=self._cmd_notes,
            category="Context"
        ))

        # === CLIENT & BUSINESS MANAGEMENT ===
        self.register(SlashCommand(
            name="proposal",
            description="Generate project proposals with AI effort estimation",
            usage="/proposal <client_name> [--template=<type>] [--hours]",
            handler=self._cmd_proposal,
            category="Business"
        ))

        self.register(SlashCommand(
            name="estimate",
            description="AI-powered project estimation with risk factors",
            usage="/estimate <project_description> [--detailed] [--risks]",
            handler=self._cmd_estimate,
            category="Business"
        ))

        self.register(SlashCommand(
            name="invoice",
            description="Generate invoices with time tracking integration",
            usage="/invoice <client_name> [--hours] [--template]",
            handler=self._cmd_invoice,
            category="Business"
        ))

        # === EMERGENCY & RECOVERY ===
        self.register(SlashCommand(
            name="panic",
            description="Emergency troubleshooting and recovery procedures",
            usage="/panic [--logs] [--rollback] [--backup]",
            handler=self._cmd_panic,
            category="Emergency"
        ))

        self.register(SlashCommand(
            name="hotfix",
            description="Rapid hotfix deployment with minimal testing",
            usage="/hotfix <issue_description> [--deploy]",
            handler=self._cmd_hotfix,
            category="Emergency"
        ))

        # === WORKFLOW & PRODUCTIVITY ===
        self.register(SlashCommand(
            name="focus",
            description="Deep work session management with distraction blocking",
            usage="/focus [start|stop|status] [duration_minutes]",
            handler=self._cmd_focus,
            category="Productivity"
        ))

        self.register(SlashCommand(
            name="til",
            description="Today I Learned - knowledge capture and indexing",
            usage="/til <learning_text> [--tags] [--project]",
            handler=self._cmd_til,
            category="Knowledge"
        ))

        # === CASPER SPECIFIC ===
        self.register(SlashCommand(
            name="task",
            description="Execute development task via multi-agent workflow",
            usage="/task <task_description>",
            handler=self._cmd_task,
            category="CASPER"
        ))

        self.register(SlashCommand(
            name="analyze",
            description="Analyze task complexity without execution",
            usage="/analyze <task_description>",
            handler=self._cmd_analyze,
            category="CASPER"
        ))

        self.register(SlashCommand(
            name="init",
            description="Initialize CASPER in current project",
            usage="/init",
            handler=self._cmd_init,
            category="CASPER"
        ))

    def _load_custom_commands(self):
        """Load custom commands from user config directory."""
        custom_dir = Path.home() / ".casper" / "commands"
        if custom_dir.exists():
            for cmd_file in custom_dir.glob("*.json"):
                try:
                    with open(cmd_file) as f:
                        cmd_data = json.load(f)
                        # TODO: Implement custom command loading
                        pass
                except Exception as e:
                    console.print(f"[yellow]⚠️  Failed to load custom command {cmd_file.name}: {e}[/yellow]")

    # === COMMAND HANDLERS ===

    async def _cmd_help(self, args: str):
        """Show help for all commands or specific category."""
        category = args.strip() if args else None

        commands = self.list_commands(category)

        if category:
            console.print(f"\n[bold bright_cyan]CASPER Commands - {category}[/bold bright_cyan]")
        else:
            console.print(f"\n[bold bright_cyan]CASPER Slash Commands[/bold bright_cyan]")

        # Group by category
        by_category = {}
        for cmd in commands:
            if cmd.category not in by_category:
                by_category[cmd.category] = []
            by_category[cmd.category].append(cmd)

        for cat, cat_commands in by_category.items():
            console.print(f"\n[bold bright_green]{cat}:[/bold bright_green]")

            table = Table(show_header=False, box=None, padding=(0, 2))
            table.add_column("Command", style="yellow", width=20)
            table.add_column("Description", style="bright_white")

            for cmd in cat_commands:
                aliases_str = f" [{', '.join(cmd.aliases)}]" if cmd.aliases else ""
                table.add_row(f"/{cmd.name}{aliases_str}", cmd.description)

            console.print(table)

        if not category:
            console.print(f"\n[dim]Use '/help <category>' for category-specific help[/dim]")
            console.print(f"[dim]Categories: {', '.join(sorted(by_category.keys()))}[/dim]")

    async def _cmd_status(self, args: str):
        """Show system status."""
        if self.casper_cli:
            await self.casper_cli.show_status()
        else:
            console.print("[yellow]⚠️  Status requires CASPER CLI context[/yellow]")

    async def _cmd_config(self, args: str):
        """Handle configuration commands."""
        if not args:
            # Show current config
            info = user_config.get_user_info()
            config_data = user_config.get_config()

            table = Table(title="CASPER Configuration", show_header=True, header_style="bold cyan")
            table.add_column("Setting", style="bright_white", width=20)
            table.add_column("Value", style="bright_yellow")

            table.add_row("Username", info["username"])
            table.add_row("Config Directory", str(info["config_dir"]))
            table.add_row("Configured Providers", ", ".join(info["configured_providers"]))
            table.add_row("Default Provider", user_config.get_default_provider())

            for key, value in config_data.items():
                if key not in ["last_used_provider", "default_provider"]:
                    table.add_row(key, str(value))

            console.print(table)
        else:
            parts = args.split()
            if len(parts) >= 3 and parts[0] == "set":
                key, value = parts[1], " ".join(parts[2:])
                config = user_config.get_config()
                config[key] = value
                user_config.store_config(config)
                console.print(f"[green]✅ Set {key} = {value}[/green]")
            else:
                console.print("[red]❌ Usage: /config set <key> <value>[/red]")

    async def _cmd_setup(self, args: str):
        """Open setup interface."""
        if self.casper_cli:
            await self.casper_cli.run_setup()
        else:
            from core.services.setup import SetupService
            setup = SetupService()
            setup.interactive_setup()

    async def _cmd_clear(self, args: str):
        """Clear the current session."""
        console.clear()
        console.print("[green]✅ Session cleared[/green]")

    async def _cmd_save(self, args: str):
        """Save current session."""
        session_name = args.strip() or f"session_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        session_id = str(uuid4())

        session_data = {
            "id": session_id,
            "name": session_name,
            "created_at": datetime.now().isoformat(),
            "context": {},  # TODO: Capture current context
        }

        session_file = self.sessions_dir / f"{session_id}.json"
        with open(session_file, 'w') as f:
            json.dump(session_data, f, indent=2)

        console.print(f"[green]✅ Session saved as '{session_name}' ({session_id[:8]})[/green]")

    async def _cmd_resume(self, args: str):
        """Resume a saved session."""
        if not args:
            # Show available sessions
            await self._cmd_sessions("")
            return

        session_id = args.strip()
        session_files = list(self.sessions_dir.glob("*.json"))

        for session_file in session_files:
            with open(session_file) as f:
                session_data = json.load(f)
                if session_data["id"].startswith(session_id) or session_data["name"] == session_id:
                    console.print(f"[green]✅ Resuming session '{session_data['name']}'[/green]")
                    # TODO: Restore context
                    return

        console.print(f"[red]❌ Session not found: {session_id}[/red]")

    async def _cmd_sessions(self, args: str):
        """List all saved sessions."""
        session_files = list(self.sessions_dir.glob("*.json"))

        if not session_files:
            console.print("[yellow]No saved sessions found[/yellow]")
            return

        table = Table(title="Saved Sessions", show_header=True, header_style="bold cyan")
        table.add_column("ID", style="bright_white", width=10)
        table.add_column("Name", style="bright_yellow", width=25)
        table.add_column("Created", style="dim", width=20)

        for session_file in sorted(session_files, key=lambda x: x.stat().st_mtime, reverse=True):
            with open(session_file) as f:
                session_data = json.load(f)
                created = datetime.fromisoformat(session_data["created_at"])
                table.add_row(
                    session_data["id"][:8],
                    session_data["name"],
                    created.strftime("%Y-%m-%d %H:%M")
                )

        console.print(table)

    async def _cmd_task(self, args: str):
        """Execute a task via CASPER."""
        if not args:
            console.print("[red]❌ Usage: /task <task_description>[/red]")
            return

        if self.casper_cli:
            await self.casper_cli.execute_task(args)
        else:
            console.print("[yellow]⚠️  Task execution requires CASPER CLI context[/yellow]")

    async def _cmd_analyze(self, args: str):
        """Analyze a task without executing."""
        if not args:
            console.print("[red]❌ Usage: /analyze <task_description>[/red]")
            return

        if self.casper_cli:
            await self.casper_cli.analyze_only(args)
        else:
            console.print("[yellow]⚠️  Analysis requires CASPER CLI context[/yellow]")

    async def _cmd_init(self, args: str):
        """Initialize CASPER in current project."""
        if self.casper_cli:
            # Use existing init logic
            console.print("[green]✅ Initializing CASPER in current project...[/green]")
        else:
            console.print("[yellow]⚠️  Init requires CASPER CLI context[/yellow]")

    # === PLACEHOLDER IMPLEMENTATIONS ===
    # TODO: Implement remaining command handlers

    async def _cmd_newcomponent(self, args: str):
        """Create a new component with boilerplate code."""
        from core.services.codegen import code_generator

        if not args.strip():
            console.print("[red]❌ Usage: /newcomponent <ComponentName> [--type=react|vue|python] [--no-tests] [--stories][/red]")
            return

        # Parse arguments
        parts = args.split()
        component_name = parts[0]

        # Parse options
        options = {
            "include_tests": True,
            "include_stories": False,
            "include_types": True
        }
        component_type = None

        for part in parts[1:]:
            if part.startswith("--type="):
                component_type = part.split("=", 1)[1]
            elif part == "--no-tests":
                options["include_tests"] = False
            elif part == "--stories":
                options["include_stories"] = True

        # Execute component generation
        success = await code_generator.generate_component(
            name=component_name,
            component_type=component_type,
            options=options
        )

        if not success:
            console.print("[red]❌ Failed to create component[/red]")

    async def _cmd_gen(self, args: str):
        """Generate feature scaffolding (API, DB, frontend)."""
        if not args.strip():
            console.print("[red]❌ Usage: /gen <feature_name> [--full|--api|--frontend|--backend][/red]")
            console.print("[dim]Examples:[/dim]")
            console.print("[dim]  /gen user --full (complete CRUD feature)[/dim]")
            console.print("[dim]  /gen product --api (API only)[/dim]")
            console.print("[dim]  /gen dashboard --frontend (frontend only)[/dim]")
            console.print("[dim]  /gen auth --backend (backend models & API)[/dim]")
            return

        parts = args.strip().split()
        feature_name = parts[0]

        # Parse options
        options = {
            'full': '--full' in parts,
            'api': '--api' in parts,
            'frontend': '--frontend' in parts,
            'backend': '--backend' in parts
        }

        # Default to full if no specific option
        if not any(options.values()):
            options['full'] = True

        console.print(f"[cyan]⚡ Generating feature: {feature_name}[/cyan]")

        try:
            await self._generate_feature_scaffolding(feature_name, options)
        except Exception as e:
            console.print(f"[red]❌ Error generating feature: {str(e)}[/red]")

    async def _generate_feature_scaffolding(self, feature_name: str, options: dict):
        """Generate comprehensive feature scaffolding."""
        from pathlib import Path
        import json

        current_dir = Path.cwd()

        # Detect project type
        project_info = await self._detect_project_type(current_dir)

        console.print(f"[dim]→ Project type: {project_info['type']}[/dim]")

        results = []

        # Generate based on options
        if options['full'] or options['backend'] or options['api']:
            backend_results = await self._generate_backend_scaffolding(feature_name, project_info)
            results.extend(backend_results)

        if options['full'] or options['frontend']:
            frontend_results = await self._generate_frontend_scaffolding(feature_name, project_info)
            results.extend(frontend_results)

        if options['full']:
            # Generate integration files
            integration_results = await self._generate_integration_files(feature_name, project_info)
            results.extend(integration_results)

        # Display results
        if results:
            console.print(f"\n[bold green]✅ Generated {len(results)} files for '{feature_name}' feature:[/bold green]")

            for result in results:
                if result['status'] == 'created':
                    console.print(f"  [green]✓[/green] {result['file']}")
                elif result['status'] == 'exists':
                    console.print(f"  [yellow]≈[/yellow] {result['file']} (already exists)")
                else:
                    console.print(f"  [red]✗[/red] {result['file']} ({result['error']})")

            console.print(f"\n[cyan]💡 Next steps:[/cyan]")
            console.print(f"  1. Review generated files for your specific requirements")
            console.print(f"  2. Update database migrations and run them")
            console.print(f"  3. Add proper validation and business logic")
            console.print(f"  4. Write comprehensive tests")
            console.print(f"  5. Update API documentation")
        else:
            console.print("[yellow]⚠️ No files were generated[/yellow]")

    async def _detect_project_type(self, current_dir: Path) -> dict:
        """Detect project type and framework."""
        info = {
            'type': 'unknown',
            'backend': None,
            'frontend': None,
            'database': None
        }

        # Backend detection
        if (current_dir / "requirements.txt").exists() or (current_dir / "pyproject.toml").exists():
            info['backend'] = 'python'

            # Framework detection
            if (current_dir / "manage.py").exists():
                info['type'] = 'django'
            elif any((current_dir / "core").glob("*.py")):
                info['type'] = 'fastapi'  # Assume FastAPI for this project
            else:
                info['type'] = 'python'

        elif (current_dir / "package.json").exists():
            with open(current_dir / "package.json") as f:
                pkg = json.load(f)
                deps = {**pkg.get("dependencies", {}), **pkg.get("devDependencies", {})}

                if "express" in deps:
                    info['backend'] = 'nodejs'
                    info['type'] = 'express'
                elif "fastify" in deps:
                    info['backend'] = 'nodejs'
                    info['type'] = 'fastify'

        # Frontend detection
        if (current_dir / "dashboard").exists():
            info['frontend'] = 'react'
        elif (current_dir / "frontend").exists():
            info['frontend'] = 'generic'

        # Database detection
        if (current_dir / "poetry.lock").exists() or (current_dir / "requirements.txt").exists():
            # Check for common Python DB libraries
            info['database'] = 'postgresql'  # Default assumption

        return info

    async def _generate_backend_scaffolding(self, feature_name: str, project_info: dict) -> list:
        """Generate backend API scaffolding."""
        results = []
        current_dir = Path.cwd()

        if project_info['backend'] == 'python' and project_info['type'] == 'fastapi':
            # Generate FastAPI model
            model_path = current_dir / "core" / "models" / f"{feature_name}.py"
            model_path.parent.mkdir(parents=True, exist_ok=True)

            model_content = f'''"""
{feature_name.title()} model definition.
"""

from sqlalchemy import Column, Integer, String, DateTime, Boolean
from sqlalchemy.sql import func
from core.database import Base


class {feature_name.title()}(Base):
    __tablename__ = "{feature_name}s"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False, index=True)
    description = Column(String, nullable=True)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    def __repr__(self):
        return f"<{feature_name.title()}(id={{self.id}}, name='{{self.name}}')>"
'''

            try:
                if not model_path.exists():
                    model_path.write_text(model_content)
                    results.append({'file': str(model_path), 'status': 'created'})
                else:
                    results.append({'file': str(model_path), 'status': 'exists'})
            except Exception as e:
                results.append({'file': str(model_path), 'status': 'error', 'error': str(e)})

            # Generate API endpoints
            api_path = current_dir / "core" / "api" / f"{feature_name}.py"
            api_path.parent.mkdir(parents=True, exist_ok=True)

            api_content = f'''"""
{feature_name.title()} API endpoints.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List

from core.database import get_db
from core.models.{feature_name} import {feature_name.title()}
from core.schemas.{feature_name} import {feature_name.title()}Create, {feature_name.title()}Response

router = APIRouter(prefix="/{feature_name}s", tags=["{feature_name}s"])


@router.get("/", response_model=List[{feature_name.title()}Response])
async def get_{feature_name}s(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    """Get all {feature_name}s."""
    {feature_name}s = db.query({feature_name.title()}).filter({feature_name.title()}.is_active == True).offset(skip).limit(limit).all()
    return {feature_name}s


@router.get("/{{id}}", response_model={feature_name.title()}Response)
async def get_{feature_name}(id: int, db: Session = Depends(get_db)):
    """Get specific {feature_name} by ID."""
    {feature_name}_obj = db.query({feature_name.title()}).filter({feature_name.title()}.id == id, {feature_name.title()}.is_active == True).first()
    if not {feature_name}_obj:
        raise HTTPException(status_code=404, detail="{feature_name.title()} not found")
    return {feature_name}_obj


@router.post("/", response_model={feature_name.title()}Response, status_code=status.HTTP_201_CREATED)
async def create_{feature_name}({feature_name}_data: {feature_name.title()}Create, db: Session = Depends(get_db)):
    """Create new {feature_name}."""
    {feature_name}_obj = {feature_name.title()}(**{feature_name}_data.dict())
    db.add({feature_name}_obj)
    db.commit()
    db.refresh({feature_name}_obj)
    return {feature_name}_obj


@router.put("/{{id}}", response_model={feature_name.title()}Response)
async def update_{feature_name}(id: int, {feature_name}_data: {feature_name.title()}Create, db: Session = Depends(get_db)):
    """Update existing {feature_name}."""
    {feature_name}_obj = db.query({feature_name.title()}).filter({feature_name.title()}.id == id).first()
    if not {feature_name}_obj:
        raise HTTPException(status_code=404, detail="{feature_name.title()} not found")

    for key, value in {feature_name}_data.dict().items():
        setattr({feature_name}_obj, key, value)

    db.commit()
    db.refresh({feature_name}_obj)
    return {feature_name}_obj


@router.delete("/{{id}}")
async def delete_{feature_name}(id: int, db: Session = Depends(get_db)):
    """Soft delete {feature_name}."""
    {feature_name}_obj = db.query({feature_name.title()}).filter({feature_name.title()}.id == id).first()
    if not {feature_name}_obj:
        raise HTTPException(status_code=404, detail="{feature_name.title()} not found")

    {feature_name}_obj.is_active = False
    db.commit()
    return {{"message": "{feature_name.title()} deleted successfully"}}
'''

            try:
                if not api_path.exists():
                    api_path.write_text(api_content)
                    results.append({'file': str(api_path), 'status': 'created'})
                else:
                    results.append({'file': str(api_path), 'status': 'exists'})
            except Exception as e:
                results.append({'file': str(api_path), 'status': 'error', 'error': str(e)})

            # Generate Pydantic schemas
            schema_path = current_dir / "core" / "schemas" / f"{feature_name}.py"
            schema_path.parent.mkdir(parents=True, exist_ok=True)

            schema_content = f'''"""
{feature_name.title()} Pydantic schemas.
"""

from pydantic import BaseModel
from datetime import datetime
from typing import Optional


class {feature_name.title()}Base(BaseModel):
    name: str
    description: Optional[str] = None
    is_active: bool = True


class {feature_name.title()}Create({feature_name.title()}Base):
    pass


class {feature_name.title()}Response({feature_name.title()}Base):
    id: int
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        orm_mode = True
'''

            try:
                if not schema_path.exists():
                    schema_path.write_text(schema_content)
                    results.append({'file': str(schema_path), 'status': 'created'})
                else:
                    results.append({'file': str(schema_path), 'status': 'exists'})
            except Exception as e:
                results.append({'file': str(schema_path), 'status': 'error', 'error': str(e)})

        return results

    async def _generate_frontend_scaffolding(self, feature_name: str, project_info: dict) -> list:
        """Generate frontend component scaffolding."""
        results = []
        current_dir = Path.cwd()

        if project_info['frontend'] == 'react':
            # Generate React component
            component_dir = current_dir / "dashboard" / "src" / "components" / feature_name.title()
            component_dir.mkdir(parents=True, exist_ok=True)

            component_path = component_dir / f"{feature_name.title()}Component.tsx"

            component_content = f'''import React, {{ useState, useEffect }} from 'react';
import {{ Card, CardContent, CardHeader, CardTitle }} from '@/components/ui/card';
import {{ Button }} from '@/components/ui/button';
import {{ Input }} from '@/components/ui/input';

interface {feature_name.title()}Item {{
  id: number;
  name: string;
  description?: string;
  is_active: boolean;
  created_at: string;
  updated_at?: string;
}}

interface {feature_name.title()}ComponentProps {{
  className?: string;
}}

export const {feature_name.title()}Component: React.FC<{feature_name.title()}ComponentProps> = ({{ className }}) => {{
  const [{feature_name}s, set{feature_name.title()}s] = useState<{feature_name.title()}Item[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [newItem, setNewItem] = useState({{ name: '', description: '' }});

  useEffect(() => {{
    fetch{feature_name.title()}s();
  }}, []);

  const fetch{feature_name.title()}s = async () => {{
    setLoading(true);
    setError(null);

    try {{
      const response = await fetch('/api/{feature_name}s');
      if (!response.ok) throw new Error('Failed to fetch {feature_name}s');
      const data = await response.json();
      set{feature_name.title()}s(data);
    }} catch (err) {{
      setError(err instanceof Error ? err.message : 'Unknown error');
    }} finally {{
      setLoading(false);
    }}
  }};

  const create{feature_name.title()} = async () => {{
    if (!newItem.name.trim()) return;

    try {{
      const response = await fetch('/api/{feature_name}s', {{
        method: 'POST',
        headers: {{ 'Content-Type': 'application/json' }},
        body: JSON.stringify(newItem),
      }});

      if (!response.ok) throw new Error('Failed to create {feature_name}');

      setNewItem({{ name: '', description: '' }});
      await fetch{feature_name.title()}s();
    }} catch (err) {{
      setError(err instanceof Error ? err.message : 'Unknown error');
    }}
  }};

  const delete{feature_name.title()} = async (id: number) => {{
    try {{
      const response = await fetch(`/api/{feature_name}s/${{id}}`, {{
        method: 'DELETE',
      }});

      if (!response.ok) throw new Error('Failed to delete {feature_name}');

      await fetch{feature_name.title()}s();
    }} catch (err) {{
      setError(err instanceof Error ? err.message : 'Unknown error');
    }}
  }};

  return (
    <div className={{className}}>
      <Card>
        <CardHeader>
          <CardTitle>{feature_name.title()} Management</CardTitle>
        </CardHeader>
        <CardContent>
          {{/* Add new item form */}}
          <div className="mb-4 space-y-2">
            <Input
              placeholder="{feature_name.title()} name"
              value={{newItem.name}}
              onChange={{(e) => setNewItem({{ ...newItem, name: e.target.value }})}}
            />
            <Input
              placeholder="Description (optional)"
              value={{newItem.description}}
              onChange={{(e) => setNewItem({{ ...newItem, description: e.target.value }})}}
            />
            <Button onClick={{create{feature_name.title()}}} disabled={{!newItem.name.trim()}}>
              Add {feature_name.title()}
            </Button>
          </div>

          {{/* Error display */}}
          {{error && (
            <div className="mb-4 p-2 bg-red-100 border border-red-300 text-red-700 rounded">
              {{error}}
            </div>
          )}}

          {{/* Loading state */}}
          {{loading && <div>Loading {feature_name}s...</div>}}

          {{/* Items list */}}
          <div className="space-y-2">
            {{{feature_name}s.map(item => (
              <div key={{item.id}} className="flex justify-between items-center p-2 border rounded">
                <div>
                  <h4 className="font-medium">{{item.name}}</h4>
                  {{item.description && (
                    <p className="text-sm text-gray-600">{{item.description}}</p>
                  )}}
                  <p className="text-xs text-gray-400">
                    Created: {{new Date(item.created_at).toLocaleDateString()}}
                  </p>
                </div>
                <Button
                  variant="destructive"
                  size="sm"
                  onClick={{() => delete{feature_name.title()}(item.id)}}
                >
                  Delete
                </Button>
              </div>
            ))}}
          </div>

          {{{feature_name}s.length === 0 && !loading && (
            <div className="text-center text-gray-500 py-4">
              No {feature_name}s found. Create one above to get started.
            </div>
          )}}
        </CardContent>
      </Card>
    </div>
  );
}};

export default {feature_name.title()}Component;
'''

            try:
                if not component_path.exists():
                    component_path.write_text(component_content)
                    results.append({'file': str(component_path), 'status': 'created'})
                else:
                    results.append({'file': str(component_path), 'status': 'exists'})
            except Exception as e:
                results.append({'file': str(component_path), 'status': 'error', 'error': str(e)})

        return results

    async def _generate_integration_files(self, feature_name: str, project_info: dict) -> list:
        """Generate integration files like tests, docs, etc."""
        results = []
        current_dir = Path.cwd()

        # Generate basic test file
        test_path = current_dir / "tests" / f"test_{feature_name}.py"
        test_path.parent.mkdir(parents=True, exist_ok=True)

        test_content = f'''"""
Tests for {feature_name} feature.
"""

import pytest
from fastapi.testclient import TestClient

from core.server import app
from core.models.{feature_name} import {feature_name.title()}

client = TestClient(app)


def test_create_{feature_name}():
    """Test creating a new {feature_name}."""
    {feature_name}_data = {{
        "name": "Test {feature_name.title()}",
        "description": "Test description"
    }}

    response = client.post("/{feature_name}s/", json={feature_name}_data)
    assert response.status_code == 201

    data = response.json()
    assert data["name"] == {feature_name}_data["name"]
    assert data["description"] == {feature_name}_data["description"]
    assert "id" in data


def test_get_{feature_name}s():
    """Test getting all {feature_name}s."""
    response = client.get("/{feature_name}s/")
    assert response.status_code == 200

    data = response.json()
    assert isinstance(data, list)


def test_get_{feature_name}_by_id():
    """Test getting a specific {feature_name}."""
    # First create a {feature_name}
    {feature_name}_data = {{
        "name": "Test {feature_name.title()} For Get",
        "description": "Test description"
    }}

    create_response = client.post("/{feature_name}s/", json={feature_name}_data)
    created_id = create_response.json()["id"]

    # Then get it
    response = client.get(f"/{feature_name}s/{{created_id}}")
    assert response.status_code == 200

    data = response.json()
    assert data["id"] == created_id
    assert data["name"] == {feature_name}_data["name"]


def test_update_{feature_name}():
    """Test updating a {feature_name}."""
    # First create a {feature_name}
    {feature_name}_data = {{
        "name": "Test {feature_name.title()} For Update",
        "description": "Original description"
    }}

    create_response = client.post("/{feature_name}s/", json={feature_name}_data)
    created_id = create_response.json()["id"]

    # Then update it
    updated_data = {{
        "name": "Updated {feature_name.title()}",
        "description": "Updated description"
    }}

    response = client.put(f"/{feature_name}s/{{created_id}}", json=updated_data)
    assert response.status_code == 200

    data = response.json()
    assert data["name"] == updated_data["name"]
    assert data["description"] == updated_data["description"]


def test_delete_{feature_name}():
    """Test deleting a {feature_name}."""
    # First create a {feature_name}
    {feature_name}_data = {{
        "name": "Test {feature_name.title()} For Delete",
        "description": "Test description"
    }}

    create_response = client.post("/{feature_name}s/", json={feature_name}_data)
    created_id = create_response.json()["id"]

    # Then delete it
    response = client.delete(f"/{feature_name}s/{{created_id}}")
    assert response.status_code == 200

    # Verify it's gone (should return 404)
    get_response = client.get(f"/{feature_name}s/{{created_id}}")
    assert get_response.status_code == 404
'''

        try:
            if not test_path.exists():
                test_path.write_text(test_content)
                results.append({'file': str(test_path), 'status': 'created'})
            else:
                results.append({'file': str(test_path), 'status': 'exists'})
        except Exception as e:
            results.append({'file': str(test_path), 'status': 'error', 'error': str(e)})

        return results

    async def _cmd_addroute(self, args: str):
        """Create new frontend route with component."""
        if not args:
            console.print("[red]❌ Usage: /addroute <path> <ComponentName>[/red]")
            console.print("[dim]Example: /addroute /dashboard DashboardComponent[/dim]")
            return

        parts = args.strip().split()
        if len(parts) != 2:
            console.print("[red]❌ Please provide both path and component name[/red]")
            return

        route_path, component_name = parts

        # Detect project type and create appropriate route
        from pathlib import Path
        import json

        console.print(f"[cyan]→ Adding route {route_path} with component {component_name}...[/cyan]")

        # React Router implementation
        if Path("src/App.tsx").exists() or Path("src/App.jsx").exists():
            # Generate React component
            component_code = f'''import React from 'react';

export const {component_name}: React.FC = () => {{
  return (
    <div className="{component_name.lower()}">
      <h1>{component_name}</h1>
      {{/* Add your component content here */}}
    </div>
  );
}};

export default {component_name};'''

            # Create component file
            component_dir = Path(f"src/components")
            component_dir.mkdir(exist_ok=True, parents=True)
            component_file = component_dir / f"{component_name}.tsx"

            if not component_file.exists():
                component_file.write_text(component_code)
                console.print(f"[green]✅ Created component: {component_file}[/green]")

                # Add route instruction
                console.print("\n[yellow]📝 Add this to your router configuration:[/yellow]")
                console.print(f"[dim]import {component_name} from './components/{component_name}';[/dim]")
                console.print(f"[dim]<Route path=\"{route_path}\" component={{{component_name}}} />[/dim]")
            else:
                console.print(f"[yellow]⚠️ Component already exists: {component_file}[/yellow]")

        # Vue Router implementation
        elif Path("src/router/index.js").exists() or Path("src/router/index.ts").exists():
            console.print("[green]✅ Vue project detected[/green]")
            console.print(f"[dim]Add to router: {{ path: '{route_path}', component: {component_name} }}[/dim]")

        # Generic instruction
        else:
            console.print(f"[green]✅ Route configuration:[/green]")
            console.print(f"[dim]Path: {route_path}[/dim]")
            console.print(f"[dim]Component: {component_name}[/dim]")
            console.print("[dim]Add this route to your application's router configuration[/dim]")

    async def _cmd_docs(self, args: str):
        """Generate documentation for function or file."""
        from core.services.docgen import doc_generator

        if not args.strip():
            console.print("[red]❌ Usage: /docs <file_path> [function_name][/red]")
            console.print("[dim]Examples:[/dim]")
            console.print("[dim]  /docs src/utils.py[/dim]")
            console.print("[dim]  /docs src/utils.py calculate_total[/dim]")
            return

        parts = args.strip().split()
        file_path = parts[0]
        function_name = parts[1] if len(parts) > 1 else None

        if function_name:
            success = await doc_generator.generate_function_docs(file_path, function_name)
        else:
            success = await doc_generator.generate_file_docs(file_path)

        if not success:
            console.print("[red]❌ Failed to generate documentation[/red]")

    async def _cmd_refactor(self, args: str):
        """AI-powered code refactoring suggestions."""
        if not args:
            console.print("[red]❌ Usage: /refactor <file_path> [specific_function][/red]")
            console.print("[dim]Example: /refactor src/utils.py calculate_total[/dim]")
            return

        from pathlib import Path
        from core.services.llm import llm_service

        parts = args.strip().split()
        file_path = parts[0]
        function_name = parts[1] if len(parts) > 1 else None

        if not Path(file_path).exists():
            console.print(f"[red]❌ File not found: {file_path}[/red]")
            return

        console.print(f"[cyan]→ Analyzing {file_path} for refactoring opportunities...[/cyan]")

        # Read the file
        try:
            with open(file_path, 'r') as f:
                code = f.read()

            # Focus on specific function if requested
            if function_name:
                import re
                pattern = rf"(def |function |const |class ){function_name}.*?"
                match = re.search(pattern, code)
                if match:
                    # Extract function (simplified)
                    lines = code.split('\n')
                    start_idx = code[:match.start()].count('\n')
                    code_section = '\n'.join(lines[start_idx:start_idx+50])  # Get 50 lines
                else:
                    console.print(f"[yellow]⚠️ Function '{function_name}' not found[/yellow]")
                    code_section = code[:2000]  # Use first 2000 chars
            else:
                code_section = code[:2000]  # Analyze first portion

            # Generate refactoring suggestions
            if llm_service and hasattr(llm_service, 'complete'):
                prompt = f"""Analyze this code and provide specific refactoring suggestions:

{code_section}

Provide:
1. Code smell issues
2. Performance improvements
3. Readability enhancements
4. Best practice violations
5. Suggested refactored code

Be specific and actionable."""

                response = await llm_service.complete(prompt)
                console.print("\n[bold]🔍 Refactoring Analysis:[/bold]")
                console.print(response)
            else:
                # Fallback analysis without AI
                console.print("\n[bold]🔍 Code Analysis:[/bold]")

                # Basic static analysis
                issues = []
                if len(code.split('\n')) > 100:
                    issues.append("• Consider breaking large files into modules")
                if 'TODO' in code or 'FIXME' in code:
                    issues.append("• Unresolved TODO/FIXME comments found")
                if code.count('if ') > 10:
                    issues.append("• High cyclomatic complexity - consider extracting methods")
                if 'except:' in code or 'except Exception' in code:
                    issues.append("• Broad exception handling - be more specific")

                if issues:
                    for issue in issues:
                        console.print(f"[yellow]{issue}[/yellow]")
                else:
                    console.print("[green]✅ No obvious issues found[/green]")

                console.print("\n[cyan]💡 Run with AI service for detailed suggestions[/cyan]")

        except Exception as e:
            console.print(f"[red]❌ Error analyzing file: {str(e)}[/red]")

    async def _cmd_commit(self, args: str):
        """Generate smart commit message from changes."""
        import subprocess
        from rich.prompt import Confirm
        from core.services.llm import llm_service

        try:
            # Parse custom message option
            custom_message = None
            if args.strip() and args.strip().startswith('--message='):
                custom_message = args.strip().replace('--message=', '').strip('\'"')

            # Check if we're in a git repository
            try:
                subprocess.run(['git', 'status'], check=True, capture_output=True)
            except subprocess.CalledProcessError:
                console.print("[red]❌ Not in a git repository[/red]")
                return

            # Get git status and diff
            status_result = subprocess.run(['git', 'status', '--porcelain'],
                                        capture_output=True, text=True, check=True)

            if not status_result.stdout.strip():
                console.print("[yellow]⚠️ No changes to commit[/yellow]")
                return

            # Get diff for staged and unstaged changes
            diff_result = subprocess.run(['git', 'diff', 'HEAD'],
                                       capture_output=True, text=True)

            changes = status_result.stdout
            diff_content = diff_result.stdout[:2000]  # Limit diff size

            if custom_message:
                commit_message = custom_message
                console.print(f"[dim]→ Using custom message: {commit_message}[/dim]")
            else:
                # Generate smart commit message with AI
                console.print("[dim]→ Analyzing changes to generate commit message...[/dim]")

                llm = llm_service
                if llm:
                    prompt = f"""
Analyze these git changes and generate a concise, descriptive commit message following conventional commits format.

Git Status:
{changes}

Git Diff (abbreviated):
{diff_content}

Generate a commit message that:
1. Uses conventional commit format (feat:, fix:, docs:, style:, refactor:, test:, chore:)
2. Summarizes the main change in 50 characters or less for the subject
3. Includes a brief body if the change is complex
4. Focuses on WHAT changed and WHY, not HOW

Respond with only the commit message, no explanations.
"""

                    commit_message = await llm.complete(prompt)
                    commit_message = commit_message.strip().strip('`"\'')
                else:
                    # Fallback to basic message generation
                    modified_files = []
                    added_files = []
                    deleted_files = []

                    for line in changes.strip().split('\n'):
                        if line.startswith('M '):
                            modified_files.append(line[3:])
                        elif line.startswith('A '):
                            added_files.append(line[3:])
                        elif line.startswith('D '):
                            deleted_files.append(line[3:])

                    if added_files:
                        commit_message = f"feat: add {', '.join(added_files[:2])}"
                    elif modified_files:
                        commit_message = f"update: modify {', '.join(modified_files[:2])}"
                    elif deleted_files:
                        commit_message = f"remove: delete {', '.join(deleted_files[:2])}"
                    else:
                        commit_message = "chore: update project files"

            # Show the generated message and ask for confirmation
            console.print(Panel(
                f"[bold white]{commit_message}[/bold white]",
                title="🎯 Generated Commit Message",
                border_style="green"
            ))

            # Show changed files
            console.print("[dim]Changed files:[/dim]")
            for line in changes.strip().split('\n'):
                status_char = line[:2]
                file_path = line[3:] if len(line) > 3 else ""
                if status_char == 'M ':
                    console.print(f"[yellow]  Modified:[/yellow] {file_path}")
                elif status_char == 'A ':
                    console.print(f"[green]  Added:[/green] {file_path}")
                elif status_char == 'D ':
                    console.print(f"[red]  Deleted:[/red] {file_path}")
                elif status_char == '??':
                    console.print(f"[blue]  Untracked:[/blue] {file_path}")

            # Ask for confirmation
            if Confirm.ask("\n[bold]Commit with this message?[/bold]", default=True):
                # Add all changes and commit
                subprocess.run(['git', 'add', '.'], check=True)
                subprocess.run(['git', 'commit', '-m', commit_message], check=True)
                console.print(f"[green]✅ Committed successfully![/green]")
            else:
                console.print("[dim]→ Commit cancelled[/dim]")

        except subprocess.CalledProcessError as e:
            console.print(f"[red]❌ Git error: {e}[/red]")
        except Exception as e:
            console.print(f"[red]❌ Error: {str(e)}[/red]")

    async def _cmd_pr(self, args: str):
        """Create pull request with smart title and description."""
        import subprocess
        from core.services.llm import llm_service

        # Check if gh CLI is installed
        try:
            subprocess.run(['gh', '--version'], capture_output=True, check=True)
        except:
            console.print("[yellow]⚠️ GitHub CLI not installed. Installing instructions:[/yellow]")
            console.print("[dim]• macOS: brew install gh[/dim]")
            console.print("[dim]• Linux: See https://github.com/cli/cli/blob/trunk/docs/install_linux.md[/dim]")
            console.print("[dim]• Windows: winget install GitHub.cli[/dim]")
            return

        console.print("[cyan]→ Preparing pull request...[/cyan]")

        # Get current branch
        result = subprocess.run(['git', 'branch', '--show-current'],
                              capture_output=True, text=True)
        current_branch = result.stdout.strip()

        if current_branch == 'main' or current_branch == 'master':
            console.print("[red]❌ Cannot create PR from main/master branch[/red]")
            console.print("[dim]Create a feature branch first: git checkout -b feature-name[/dim]")
            return

        # Get diff for PR description
        diff_result = subprocess.run(['git', 'diff', 'main...HEAD', '--stat'],
                                    capture_output=True, text=True)
        changes_summary = diff_result.stdout

        # Get commits
        log_result = subprocess.run(['git', 'log', 'main..HEAD', '--oneline'],
                                   capture_output=True, text=True)
        commits = log_result.stdout

        # Generate title and description
        if llm_service and hasattr(llm_service, 'complete'):
            prompt = f"""Generate a concise PR title and description based on these changes:

Branch: {current_branch}
Commits:
{commits}

Changes:
{changes_summary}

Provide:
1. Title (one line, under 72 chars)
2. Description (bullet points of what changed and why)"""

            response = await llm_service.complete(prompt)
            console.print("\n[bold]📝 Generated PR:[/bold]")
            console.print(response)

            # Extract title (first line)
            title = response.split('\n')[0].replace('Title:', '').strip()
        else:
            # Fallback: use branch name as title
            title = current_branch.replace('-', ' ').replace('_', ' ').title()

        # Create the PR
        console.print("\n[cyan]→ Creating pull request...[/cyan]")

        if args:
            # Use provided title
            title = args

        pr_cmd = ['gh', 'pr', 'create', '--title', title, '--body', commits]

        try:
            result = subprocess.run(pr_cmd, capture_output=True, text=True)
            if result.returncode == 0:
                console.print("[green]✅ Pull request created successfully![/green]")
                console.print(result.stdout)
            else:
                console.print("[yellow]⚠️ Could not create PR automatically[/yellow]")
                console.print(f"[dim]Run manually: gh pr create --title \"{title}\"[/dim]")
        except Exception as e:
            console.print(f"[red]❌ Error creating PR: {str(e)}[/red]")

    async def _cmd_review(self, args: str):
        """AI code review of file or current changes."""
        import subprocess
        from pathlib import Path
        from core.services.llm import llm_service

        if not args:
            # Review unstaged changes
            console.print("[cyan]→ Reviewing current changes...[/cyan]")
            result = subprocess.run(['git', 'diff'], capture_output=True, text=True)
            diff = result.stdout

            if not diff:
                console.print("[yellow]⚠️ No unstaged changes to review[/yellow]")
                console.print("[dim]Tip: Use /review <file> to review a specific file[/dim]")
                return

            target = "current changes"
            content = diff
        else:
            # Review specific file
            file_path = args.strip()
            if not Path(file_path).exists():
                console.print(f"[red]❌ File not found: {file_path}[/red]")
                return

            console.print(f"[cyan]→ Reviewing {file_path}...[/cyan]")
            with open(file_path, 'r') as f:
                content = f.read()[:3000]  # Limit size
            target = file_path

        # Perform code review
        if llm_service and hasattr(llm_service, 'complete'):
            prompt = f"""Perform a thorough code review of {target}:

{content}

Review for:
1. Security vulnerabilities
2. Performance issues
3. Code quality and maintainability
4. Best practices
5. Potential bugs

Provide specific, actionable feedback with line references where possible."""

            response = await llm_service.complete(prompt)
            console.print("\n[bold]🔍 Code Review Results:[/bold]")
            console.print(response)
        else:
            # Basic static analysis fallback
            console.print("\n[bold]🔍 Basic Code Review:[/bold]")

            issues = []
            if 'password' in content.lower() or 'secret' in content.lower():
                issues.append("⚠️ Potential hardcoded secrets detected")
            if 'eval(' in content or 'exec(' in content:
                issues.append("⚠️ Dynamic code execution detected (security risk)")
            if 'TODO' in content or 'FIXME' in content:
                issues.append("📝 Unresolved TODO/FIXME comments")
            if content.count('\n') > 100 and 'def ' in content:
                if content.count('def ') < 3:
                    issues.append("📏 Large functions detected - consider breaking down")

            if issues:
                for issue in issues:
                    console.print(f"[yellow]{issue}[/yellow]")
            else:
                console.print("[green]✅ No obvious issues found[/green]")

            console.print("\n[cyan]💡 Enable AI service for comprehensive review[/cyan]")

    async def _cmd_fixbug(self, args: str):
        """Create bug fix branch and workflow."""
        import subprocess
        from core.services.llm import llm_service

        if not args:
            console.print("[red]❌ Usage: /fixbug <issue_number_or_description>[/red]")
            console.print("[dim]Example: /fixbug 123 or /fixbug 'login validation error'[/dim]")
            return

        # Parse issue number or description
        issue_ref = args.strip()
        if issue_ref.isdigit():
            branch_name = f"fix/issue-{issue_ref}"
            issue_desc = f"issue #{issue_ref}"
        else:
            # Create branch from description
            branch_name = "fix/" + issue_ref.lower().replace(' ', '-')[:30]
            issue_desc = issue_ref

        console.print(f"[cyan]→ Creating bug fix workflow for {issue_desc}...[/cyan]")

        # Create and checkout branch
        try:
            # Check current branch
            result = subprocess.run(['git', 'branch', '--show-current'],
                                  capture_output=True, text=True)
            current_branch = result.stdout.strip()

            # Create new branch
            subprocess.run(['git', 'checkout', '-b', branch_name],
                          capture_output=True, check=True)
            console.print(f"[green]✅ Created branch: {branch_name}[/green]")

            # Set up debugging checklist
            console.print("\n[bold]🐛 Bug Fix Workflow:[/bold]")
            checklist = [
                "1. Reproduce the bug",
                "2. Add failing test case",
                "3. Identify root cause",
                "4. Implement fix",
                "5. Verify test passes",
                "6. Check for regressions",
                "7. Update documentation"
            ]

            for item in checklist:
                console.print(f"[dim]□ {item}[/dim]")

            # Generate fix suggestions if AI available
            if llm_service and hasattr(llm_service, 'complete') and not issue_ref.isdigit():
                prompt = f"""Suggest debugging approach for: {issue_desc}

Provide:
1. Likely causes
2. Files to check
3. Debug steps
4. Common fixes"""

                response = await llm_service.complete(prompt)
                console.print("\n[bold]💡 Debugging Suggestions:[/bold]")
                console.print(response)
            else:
                console.print("\n[bold]💡 Next Steps:[/bold]")
                console.print("[dim]1. Search for related code: grep -r 'error_keyword' .[/dim]")
                console.print("[dim]2. Check recent changes: git log --oneline -10[/dim]")
                console.print("[dim]3. Run tests: /test[/dim]")
                console.print("[dim]4. Use /explain for error analysis[/dim]")

            # Create bug fix template file
            bug_file = f".casper/bugs/{branch_name}.md"
            from pathlib import Path
            Path(".casper/bugs").mkdir(exist_ok=True, parents=True)

            with open(bug_file, 'w') as f:
                f.write(f"""# Bug Fix: {issue_desc}

## Problem
{issue_desc}

## Root Cause
[To be determined]

## Solution
[Describe fix here]

## Testing
- [ ] Unit test added
- [ ] Regression test passed
- [ ] Manual verification completed

## Notes
[Additional context]
""")

            console.print(f"\n[green]✅ Bug tracking file created: {bug_file}[/green]")
            console.print("[dim]Ready to start debugging![/dim]")

        except subprocess.CalledProcessError as e:
            console.print(f"[red]❌ Git error: {e}[/red]")
            console.print("[dim]Make sure you're in a git repository[/dim]")

    async def _cmd_test(self, args: str):
        """Run tests with intelligent test detection."""
        import subprocess
        from pathlib import Path

        try:
            current_dir = Path.cwd()

            # Parse arguments
            test_filter = None
            test_file = None
            verbose = False

            if args.strip():
                parts = args.strip().split()
                for part in parts:
                    if part == "--verbose" or part == "-v":
                        verbose = True
                    elif part.endswith('.py') or part.endswith('.js') or part.endswith('.ts'):
                        test_file = part
                    else:
                        test_filter = part

            console.print("[dim]→ Detecting test framework...[/dim]")

            # Detect test framework and run appropriate command
            test_command = None
            test_type = None

            # Check for Python testing
            if (current_dir / "pytest.ini").exists() or (current_dir / "pyproject.toml").exists():
                test_type = "pytest"
                cmd_parts = ["python", "-m", "pytest"]

                if test_file:
                    cmd_parts.append(test_file)
                elif test_filter:
                    cmd_parts.extend(["-k", test_filter])

                if verbose:
                    cmd_parts.append("-v")

                cmd_parts.extend(["--tb=short"])
                test_command = cmd_parts

            # Check for Node.js testing
            elif (current_dir / "package.json").exists():
                try:
                    import json
                    with open(current_dir / "package.json") as f:
                        pkg = json.load(f)
                        scripts = pkg.get("scripts", {})

                        if "test" in scripts:
                            test_type = "npm"
                            cmd_parts = ["npm", "test"]

                            # Add arguments if supported
                            if test_filter and "jest" in scripts.get("test", ""):
                                cmd_parts.extend(["--", "--testNamePattern", test_filter])
                            elif test_file:
                                cmd_parts.append(test_file)

                            test_command = cmd_parts
                except:
                    pass

            # Check for Jest directly
            if not test_command and (current_dir / "jest.config.js").exists():
                test_type = "jest"
                cmd_parts = ["npx", "jest"]

                if test_file:
                    cmd_parts.append(test_file)
                elif test_filter:
                    cmd_parts.extend(["--testNamePattern", test_filter])

                if verbose:
                    cmd_parts.append("--verbose")

                test_command = cmd_parts

            # Fallback detection
            if not test_command:
                test_dirs = ["tests", "test", "__tests__"]
                for test_dir in test_dirs:
                    if (current_dir / test_dir).exists():
                        # Try pytest for Python files
                        python_tests = list((current_dir / test_dir).glob("**/*.py"))
                        if python_tests:
                            test_type = "pytest"
                            test_command = ["python", "-m", "pytest", str(current_dir / test_dir)]
                            break

                        # Try jest for JS/TS files
                        js_tests = list((current_dir / test_dir).glob("**/*.js")) + list((current_dir / test_dir).glob("**/*.ts"))
                        if js_tests:
                            test_type = "jest"
                            test_command = ["npx", "jest", str(current_dir / test_dir)]
                            break

            if not test_command:
                console.print("[red]❌ No test framework detected[/red]")
                console.print("[dim]Supported: pytest, jest, npm test[/dim]")
                console.print("[dim]Create tests in: tests/, test/, or __tests__ directories[/dim]")
                return

            console.print(f"[green]✓[/green] Detected {test_type} testing")
            console.print(f"[dim]→ Running: {' '.join(test_command)}[/dim]")

            # Run the tests
            result = subprocess.run(
                test_command,
                capture_output=True,
                text=True,
                cwd=current_dir
            )

            # Display results
            if result.stdout:
                console.print("\n[bold]Test Output:[/bold]")
                console.print(result.stdout)

            if result.stderr:
                console.print("\n[bold]Error Output:[/bold]")
                console.print(f"[red]{result.stderr}[/red]")

            # Show summary
            if result.returncode == 0:
                console.print("[green]✅ All tests passed![/green]")
            else:
                console.print(f"[red]❌ Tests failed (exit code: {result.returncode})[/red]")

                # Offer to run failed tests only for pytest
                if test_type == "pytest" and not test_filter:
                    from rich.prompt import Confirm
                    if Confirm.ask("\n[bold]Run only failed tests?[/bold]", default=False):
                        retry_command = test_command + ["--lf"]  # --lf = last failed
                        console.print(f"[dim]→ Running: {' '.join(retry_command)}[/dim]")

                        retry_result = subprocess.run(
                            retry_command,
                            capture_output=True,
                            text=True,
                            cwd=current_dir
                        )

                        if retry_result.stdout:
                            console.print("\n[bold]Failed Tests Output:[/bold]")
                            console.print(retry_result.stdout)

        except subprocess.CalledProcessError as e:
            console.print(f"[red]❌ Command failed: {e}[/red]")
        except Exception as e:
            console.print(f"[red]❌ Error running tests: {str(e)}[/red]")

    async def _cmd_testfail(self, args: str):
        """Rerun only failed tests using appropriate test framework."""
        import subprocess
        from pathlib import Path

        current_dir = Path.cwd()

        # Parse arguments for verbose mode
        verbose = "--verbose" in args or "-v" in args

        console.print("[cyan]🔄 Running failed tests only...[/cyan]")

        try:
            # Detect test framework and build command
            test_command = None
            test_type = None

            # Check for Python testing (pytest)
            if (current_dir / "pytest.ini").exists() or (current_dir / "pyproject.toml").exists():
                test_type = "pytest"
                cmd_parts = ["python", "-m", "pytest", "--lf"]  # --lf = last failed

                if verbose:
                    cmd_parts.append("-v")

                cmd_parts.extend(["--tb=short"])
                test_command = cmd_parts

            # Check for Node.js testing
            elif (current_dir / "package.json").exists():
                try:
                    import json
                    with open(current_dir / "package.json") as f:
                        pkg = json.load(f)
                        scripts = pkg.get("scripts", {})

                        if "test" in scripts:
                            script_content = scripts["test"]

                            # Check if using Jest
                            if "jest" in script_content:
                                test_type = "jest"
                                cmd_parts = ["npx", "jest", "--onlyFailures"]

                                if verbose:
                                    cmd_parts.append("--verbose")

                                test_command = cmd_parts

                            else:
                                # Generic npm test - may not support failed tests only
                                console.print("[yellow]⚠️ Generic npm test detected - may not support running failed tests only[/yellow]")
                                test_type = "npm"
                                test_command = ["npm", "test"]

                except Exception:
                    pass

            # Check for Jest config directly
            if not test_command and (current_dir / "jest.config.js").exists():
                test_type = "jest"
                cmd_parts = ["npx", "jest", "--onlyFailures"]

                if verbose:
                    cmd_parts.append("--verbose")

                test_command = cmd_parts

            # Fallback detection
            if not test_command:
                test_dirs = ["tests", "test", "__tests__"]
                for test_dir in test_dirs:
                    if (current_dir / test_dir).exists():
                        # Try pytest for Python files
                        python_tests = list((current_dir / test_dir).glob("**/*.py"))
                        if python_tests:
                            test_type = "pytest"
                            test_command = ["python", "-m", "pytest", "--lf", str(current_dir / test_dir)]
                            break

                        # Try jest for JS/TS files
                        js_tests = list((current_dir / test_dir).glob("**/*.js")) + list((current_dir / test_dir).glob("**/*.ts"))
                        if js_tests:
                            test_type = "jest"
                            test_command = ["npx", "jest", "--onlyFailures", str(current_dir / test_dir)]
                            break

            if not test_command:
                console.print("[red]❌ No supported test framework detected[/red]")
                console.print("[dim]Supported frameworks:[/dim]")
                console.print("[dim]  • pytest (Python) - detects pytest.ini or pyproject.toml[/dim]")
                console.print("[dim]  • Jest (JavaScript/TypeScript) - detects jest.config.js or package.json[/dim]")
                console.print("\n[cyan]💡 Alternatives:[/cyan]")
                console.print("[cyan]  • pytest --lf (manually)[/cyan]")
                console.print("[cyan]  • npx jest --onlyFailures (manually)[/cyan]")
                return

            console.print(f"[green]✓[/green] Detected {test_type} testing")
            console.print(f"[dim]→ Running: {' '.join(test_command)}[/dim]")

            # Run the failed tests
            result = subprocess.run(
                test_command,
                capture_output=True,
                text=True,
                cwd=current_dir
            )

            # Display results
            if result.stdout:
                console.print(f"\n[bold]Test Output:[/bold]")
                console.print(result.stdout)

            if result.stderr:
                console.print(f"\n[bold]Error Output:[/bold]")
                console.print(f"[red]{result.stderr}[/red]")

            # Show summary
            if result.returncode == 0:
                if "no tests ran" in result.stdout.lower() or "no failures" in result.stdout.lower():
                    console.print("[green]✅ No failed tests to rerun![/green]")
                    console.print("[dim]All tests passed in the last run[/dim]")
                else:
                    console.print("[green]✅ Failed tests now passing![/green]")
            else:
                console.print(f"[red]❌ Some tests still failing (exit code: {result.returncode})[/red]")

                # Offer to explain errors if there are any
                if "FAILED" in result.stdout or "Error" in result.stderr:
                    console.print("\n[dim]💡 Use '/explain <error_message>' to get help with specific test failures[/dim]")

        except subprocess.CalledProcessError as e:
            console.print(f"[red]❌ Command failed: {e}[/red]")
        except Exception as e:
            console.print(f"[red]❌ Error running failed tests: {str(e)}[/red]")

    async def _cmd_debug(self, args: str):
        """Set up debugging session for issue."""
        if not args.strip():
            console.print("[red]❌ Usage: /debug <error_description_or_file>[/red]")
            console.print("[dim]Examples:[/dim]")
            console.print("[dim]  /debug login function not working[/dim]")
            console.print("[dim]  /debug src/auth.py[/dim]")
            console.print("[dim]  /debug TypeError in data processing[/dim]")
            return

        query = args.strip()
        console.print(f"[cyan]🐛 Setting up debug session for: {query}[/cyan]")

        try:
            # Check if this is a file path
            from pathlib import Path
            potential_file = Path(query)

            if potential_file.exists() and potential_file.is_file():
                await self._debug_file(potential_file)
            else:
                await self._debug_issue(query)

        except Exception as e:
            console.print(f"[red]❌ Debug setup failed: {str(e)}[/red]")

    async def _debug_file(self, file_path: Path):
        """Set up debugging for a specific file."""
        console.print(f"[dim]→ Analyzing file: {file_path}[/dim]")

        try:
            # Read file content
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()

            # Determine file type and suggest debugging approach
            file_ext = file_path.suffix.lower()

            console.print(f"\n[bold green]🔍 Debug Setup for {file_path.name}[/bold green]")

            if file_ext == '.py':
                await self._debug_python_file(file_path, content)
            elif file_ext in ['.js', '.ts', '.jsx', '.tsx']:
                await self._debug_javascript_file(file_path, content)
            elif file_ext in ['.java']:
                await self._debug_java_file(file_path, content)
            else:
                await self._debug_generic_file(file_path, content)

        except Exception as e:
            console.print(f"[red]❌ Error analyzing file: {str(e)}[/red]")

    async def _debug_python_file(self, file_path: Path, content: str):
        """Python-specific debugging setup."""
        console.print("[bold cyan]Python Debugging Strategy:[/bold cyan]")

        # Analyze for common patterns
        lines = content.split('\n')
        functions = [i+1 for i, line in enumerate(lines) if line.strip().startswith('def ') and not line.strip().startswith('def _')]
        classes = [i+1 for i, line in enumerate(lines) if line.strip().startswith('class ')]

        # Suggest breakpoint locations
        if functions:
            console.print(f"[bright_white]📍 Suggested breakpoints (functions):[/bright_white]")
            for line_num in functions[:5]:  # Show first 5
                func_name = lines[line_num-1].strip().split('(')[0].replace('def ', '')
                console.print(f"  • Line {line_num}: {func_name}")

        if classes:
            console.print(f"[bright_white]📍 Class definitions:[/bright_white]")
            for line_num in classes[:3]:  # Show first 3
                class_name = lines[line_num-1].strip().split('(')[0].replace('class ', '').rstrip(':')
                console.print(f"  • Line {line_num}: {class_name}")

        console.print(f"\n[bright_white]🛠️ Debug Commands:[/bright_white]")
        console.print(f"  • [green]python -m pdb {file_path}[/green] (Built-in debugger)")
        console.print(f"  • [green]python -c \"import pdb; pdb.set_trace(); exec(open('{file_path}').read())\"[/green]")

        # VSCode/IDE specific
        console.print(f"\n[bright_white]🎯 IDE Integration:[/bright_white]")
        console.print(f"  • Add breakpoints in your IDE at suggested lines")
        console.print(f"  • Use 'Run and Debug' in VS Code")
        console.print(f"  • Set up launch.json for complex debugging")

        # Error patterns
        if 'import' in content:
            console.print(f"\n[bright_white]🔍 Check for:[/bright_white]")
            console.print(f"  • Import errors (missing modules)")
            console.print(f"  • Circular imports")
            console.print(f"  • Module path issues")

    async def _debug_javascript_file(self, file_path: Path, content: str):
        """JavaScript/TypeScript-specific debugging setup."""
        console.print("[bold cyan]JavaScript/Node.js Debugging Strategy:[/bold cyan]")

        lines = content.split('\n')
        functions = [i+1 for i, line in enumerate(lines)
                    if ('function ' in line or '=>' in line) and line.strip() and not line.strip().startswith('//')]

        if functions:
            console.print(f"[bright_white]📍 Suggested breakpoints:[/bright_white]")
            for line_num in functions[:5]:
                console.print(f"  • Line {line_num}: {lines[line_num-1].strip()[:50]}...")

        console.print(f"\n[bright_white]🛠️ Debug Commands:[/bright_white]")
        console.print(f"  • [green]node --inspect-brk {file_path}[/green] (Node.js debugger)")
        console.print(f"  • [green]chrome://inspect[/green] (Chrome DevTools)")

        console.print(f"\n[bright_white]💡 Debug Tips:[/bright_white]")
        console.print(f"  • Add 'debugger;' statements in your code")
        console.print(f"  • Use console.log() for quick debugging")
        console.print(f"  • Check browser dev tools for client-side issues")

    async def _debug_java_file(self, file_path: Path, content: str):
        """Java-specific debugging setup."""
        console.print("[bold cyan]Java Debugging Strategy:[/bold cyan]")

        console.print(f"[bright_white]🛠️ Debug Commands:[/bright_white]")
        console.print(f"  • Compile: [green]javac {file_path}[/green]")
        console.print(f"  • Debug: [green]java -Xdebug -Xrunjdwp:transport=dt_socket,server=y,suspend=y,address=5005 ClassName[/green]")

        console.print(f"\n[bright_white]🎯 IDE Integration:[/bright_white]")
        console.print(f"  • Use IntelliJ IDEA or Eclipse debugger")
        console.print(f"  • Set breakpoints on method entry points")
        console.print(f"  • Enable exception breakpoints")

    async def _debug_generic_file(self, file_path: Path, content: str):
        """Generic file debugging setup."""
        console.print("[bold cyan]General Debugging Approach:[/bold cyan]")

        console.print(f"[bright_white]🔍 Analysis:[/bright_white]")
        console.print(f"  • File type: {file_path.suffix}")
        console.print(f"  • Size: {len(content)} characters")
        lines_count = len(content.split('\n'))
        console.print(f"  • Lines: {lines_count}")

        console.print(f"\n[bright_white]💡 Suggestions:[/bright_white]")
        console.print(f"  • Use appropriate language-specific debugger")
        console.print(f"  • Add logging/print statements")
        console.print(f"  • Review recent changes in git")
        console.print(f"  • Check documentation for the technology")

    async def _debug_issue(self, issue_description: str):
        """Debug a general issue description."""
        console.print(f"[dim]→ Analyzing issue: {issue_description}[/dim]")

        # Categorize the issue
        issue_lower = issue_description.lower()

        console.print(f"\n[bold green]🎯 Debug Strategy for: {issue_description}[/bold green]")

        if any(word in issue_lower for word in ['login', 'auth', 'authentication', 'password']):
            console.print("[bright_white]🔐 Authentication Issue Debug Plan:[/bright_white]")
            console.print("  1. Check user credentials and validation")
            console.print("  2. Verify session management")
            console.print("  3. Test API endpoints with tools like Postman")
            console.print("  4. Review authentication middleware")
            console.print("  5. Check database user records")

        elif any(word in issue_lower for word in ['database', 'sql', 'query', 'connection']):
            console.print("[bright_white]🗄️ Database Issue Debug Plan:[/bright_white]")
            console.print("  1. Test database connection")
            console.print("  2. Review SQL queries and syntax")
            console.print("  3. Check database logs")
            console.print("  4. Verify table schema and relationships")
            console.print("  5. Test with simple queries first")

        elif any(word in issue_lower for word in ['api', 'request', 'response', 'http']):
            console.print("[bright_white]🌐 API Issue Debug Plan:[/bright_white]")
            console.print("  1. Test API endpoints manually")
            console.print("  2. Check request/response formats")
            console.print("  3. Verify HTTP status codes")
            console.print("  4. Review API documentation")
            console.print("  5. Check CORS and headers")

        elif any(word in issue_lower for word in ['ui', 'interface', 'frontend', 'display']):
            console.print("[bright_white]🎨 UI Issue Debug Plan:[/bright_white]")
            console.print("  1. Inspect element in browser dev tools")
            console.print("  2. Check CSS styles and conflicts")
            console.print("  3. Review JavaScript console for errors")
            console.print("  4. Test on different browsers/devices")
            console.print("  5. Verify data binding and state management")

        else:
            console.print("[bright_white]🔧 General Debug Plan:[/bright_white]")
            console.print("  1. Reproduce the issue consistently")
            console.print("  2. Isolate the problem area")
            console.print("  3. Add logging/debugging statements")
            console.print("  4. Test with minimal examples")
            console.print("  5. Review recent code changes")

        # General debugging tips
        console.print(f"\n[bright_white]💡 Debug Tools & Techniques:[/bright_white]")
        console.print("  • Use step-through debugging in your IDE")
        console.print("  • Add strategic logging statements")
        console.print("  • Create unit tests for the problematic area")
        console.print("  • Use version control to bisect when issue started")
        console.print("  • Rubber duck debugging - explain the problem aloud")

        console.print(f"\n[bright_white]📚 Next Steps:[/bright_white]")
        console.print("  1. Start with the most likely cause")
        console.print("  2. Test one thing at a time")
        console.print("  3. Document your findings")
        console.print("  4. Use '/explain <error>' for specific error messages")
        console.print("  5. Create a minimal reproducible example")

    async def _cmd_explain(self, args: str):
        """Explain error or code concept."""
        if not args.strip():
            console.print("[red]❌ Usage: /explain <error_message_or_code_concept>[/red]")
            console.print("[dim]Examples:[/dim]")
            console.print("[dim]  /explain ImportError: No module named 'requests'[/dim]")
            console.print("[dim]  /explain async/await in Python[/dim]")
            console.print("[dim]  /explain 404 error[/dim]")
            return

        query = args.strip()

        # Check if this is an error message or code concept
        is_error = any(error_type in query.lower() for error_type in [
            'error', 'exception', 'traceback', 'failed', 'cannot', 'unable',
            '404', '500', '403', '401', 'timeout', 'refused'
        ])

        console.print(f"[dim]→ {'Analyzing error' if is_error else 'Explaining concept'}: {query[:60]}{'...' if len(query) > 60 else ''}[/dim]")

        try:
            from core.services.llm import llm_service

            if not llm_service or not llm_service.available():
                # Fallback to basic explanations
                await self._provide_basic_explanation(query, is_error)
                return

            # Use AI to provide detailed explanation
            if is_error:
                prompt = f"""
Analyze this error and provide a comprehensive explanation:

Error: {query}

Please provide:
1. What this error means in simple terms
2. Common causes of this error
3. Step-by-step solutions to fix it
4. How to prevent it in the future
5. Related documentation or resources

Format your response clearly with sections and examples where helpful.
"""
            else:
                prompt = f"""
Explain this programming concept clearly:

Concept: {query}

Please provide:
1. Clear definition and explanation
2. How and when to use it
3. Practical examples
4. Best practices
5. Common pitfalls to avoid
6. Related concepts

Format your response clearly with sections and examples.
"""

            explanation = await llm_service.complete(prompt)

            console.print(f"\n[bold cyan]{'🔍 Error Analysis' if is_error else '📚 Concept Explanation'}[/bold cyan]")
            console.print(Panel(explanation, border_style="cyan", padding=(1, 2)))

        except Exception as e:
            console.print(f"[red]❌ Error getting AI explanation: {str(e)}[/red]")
            await self._provide_basic_explanation(query, is_error)

    async def _provide_basic_explanation(self, query: str, is_error: bool):
        """Provide basic explanations without AI."""
        query_lower = query.lower()

        if is_error:
            console.print(f"\n[bold red]🔍 Error Analysis[/bold red]")

            # Common error patterns
            if 'importerror' in query_lower or 'no module named' in query_lower:
                console.print("[bright_white]Issue:[/bright_white] Missing Python package")
                console.print("[bright_white]Solutions:[/bright_white]")
                console.print("  • [green]pip install <package_name>[/green]")
                console.print("  • [green]conda install <package_name>[/green]")
                console.print("  • Check if package name is spelled correctly")
                console.print("  • Ensure you're in the right virtual environment")

            elif 'syntaxerror' in query_lower:
                console.print("[bright_white]Issue:[/bright_white] Code syntax is incorrect")
                console.print("[bright_white]Solutions:[/bright_white]")
                console.print("  • Check for missing colons, parentheses, or brackets")
                console.print("  • Verify proper indentation")
                console.print("  • Look for unclosed quotes or strings")

            elif '404' in query_lower:
                console.print("[bright_white]Issue:[/bright_white] Resource not found")
                console.print("[bright_white]Solutions:[/bright_white]")
                console.print("  • Check URL spelling and path")
                console.print("  • Verify the resource exists")
                console.print("  • Check server configuration")

            elif 'permission' in query_lower or '403' in query_lower:
                console.print("[bright_white]Issue:[/bright_white] Access denied")
                console.print("[bright_white]Solutions:[/bright_white]")
                console.print("  • Check file/directory permissions")
                console.print("  • Verify user authentication")
                console.print("  • Run with appropriate privileges")

            else:
                console.print(f"[bright_white]Error:[/bright_white] {query}")
                console.print("[bright_white]General troubleshooting:[/bright_white]")
                console.print("  • Check the full error stack trace")
                console.print("  • Search online for the exact error message")
                console.print("  • Verify your environment setup")
                console.print("  • Check recent code changes")

        else:
            console.print(f"\n[bold cyan]📚 Concept: {query}[/bold cyan]")

            # Common concept explanations
            if 'async' in query_lower or 'await' in query_lower:
                console.print("[bright_white]Async/Await:[/bright_white] Asynchronous programming pattern")
                console.print("  • Allows non-blocking operations")
                console.print("  • Use 'async def' to define async functions")
                console.print("  • Use 'await' to wait for async operations")
                console.print("  • Improves performance for I/O operations")

            elif 'git' in query_lower:
                console.print("[bright_white]Git:[/bright_white] Version control system")
                console.print("  • Tracks changes in files over time")
                console.print("  • Enables collaboration between developers")
                console.print("  • Key commands: add, commit, push, pull, merge")

            else:
                console.print(f"For detailed information about '{query}', try:")
                console.print(f"  • Online documentation")
                console.print(f"  • Official tutorials")
                console.print(f"  • Community forums")

        console.print(f"\n[dim]💡 For more detailed AI-powered explanations, ensure LLM service is configured[/dim]")

    async def _cmd_todo(self, args: str):
        """Add task to project todo list."""
        if not args.strip():
            # Show existing todos
            await self._show_todos()
            return

        # Parse arguments
        parts = args.strip().split()
        if parts[0] in ["list", "show"]:
            await self._show_todos()
            return
        elif parts[0] == "done" and len(parts) > 1:
            await self._complete_todo(int(parts[1]))
            return
        elif parts[0] == "remove" and len(parts) > 1:
            await self._remove_todo(int(parts[1]))
            return

        # Add new todo
        task_description = args.strip()
        await self._add_todo(task_description)

    async def _show_todos(self):
        """Show current todo list."""
        import json
        from pathlib import Path

        todo_file = Path.cwd() / ".casper" / "todos.json"
        if not todo_file.exists():
            console.print("[yellow]📝 No todos yet. Add one with: /todo <description>[/yellow]")
            return

        try:
            with open(todo_file) as f:
                todos = json.load(f)

            if not todos:
                console.print("[green]✅ All done! No active todos.[/green]")
                return

            console.print("\n[bold cyan]📋 Project Todos:[/bold cyan]")

            table = Table(show_header=True, header_style="bold cyan")
            table.add_column("#", style="dim", width=3)
            table.add_column("Status", width=8)
            table.add_column("Task", style="bright_white")
            table.add_column("Added", style="dim", width=12)

            for i, todo in enumerate(todos, 1):
                status = "✅ Done" if todo.get("completed", False) else "📝 Todo"
                status_style = "green" if todo.get("completed", False) else "yellow"

                created = datetime.fromisoformat(todo["created_at"]).strftime("%m/%d %H:%M")
                table.add_row(
                    str(i),
                    f"[{status_style}]{status}[/{status_style}]",
                    todo["description"],
                    created
                )

            console.print(table)
            console.print("\n[dim]Commands: /todo <new_task> | /todo done <#> | /todo remove <#>[/dim]")

        except Exception as e:
            console.print(f"[red]❌ Error reading todos: {str(e)}[/red]")

    async def _add_todo(self, description: str):
        """Add a new todo item."""
        import json
        from pathlib import Path

        todo_file = Path.cwd() / ".casper" / "todos.json"
        todo_file.parent.mkdir(parents=True, exist_ok=True)

        # Load existing todos
        todos = []
        if todo_file.exists():
            try:
                with open(todo_file) as f:
                    todos = json.load(f)
            except:
                todos = []

        # Add new todo
        new_todo = {
            "id": str(uuid4()),
            "description": description,
            "created_at": datetime.now().isoformat(),
            "completed": False,
            "completed_at": None
        }
        todos.append(new_todo)

        # Save
        with open(todo_file, 'w') as f:
            json.dump(todos, f, indent=2)

        console.print(f"[green]✅ Added todo: {description}[/green]")
        console.print("[dim]Use '/todo' to view all todos[/dim]")

    async def _complete_todo(self, todo_number: int):
        """Mark a todo as complete."""
        import json
        from pathlib import Path

        todo_file = Path.cwd() / ".casper" / "todos.json"
        if not todo_file.exists():
            console.print("[red]❌ No todos found[/red]")
            return

        try:
            with open(todo_file) as f:
                todos = json.load(f)

            if todo_number < 1 or todo_number > len(todos):
                console.print("[red]❌ Invalid todo number[/red]")
                return

            todo = todos[todo_number - 1]
            todo["completed"] = True
            todo["completed_at"] = datetime.now().isoformat()

            with open(todo_file, 'w') as f:
                json.dump(todos, f, indent=2)

            console.print(f"[green]✅ Completed: {todo['description']}[/green]")

        except Exception as e:
            console.print(f"[red]❌ Error completing todo: {str(e)}[/red]")

    async def _remove_todo(self, todo_number: int):
        """Remove a todo item."""
        import json
        from pathlib import Path

        todo_file = Path.cwd() / ".casper" / "todos.json"
        if not todo_file.exists():
            console.print("[red]❌ No todos found[/red]")
            return

        try:
            with open(todo_file) as f:
                todos = json.load(f)

            if todo_number < 1 or todo_number > len(todos):
                console.print("[red]❌ Invalid todo number[/red]")
                return

            removed_todo = todos.pop(todo_number - 1)

            with open(todo_file, 'w') as f:
                json.dump(todos, f, indent=2)

            console.print(f"[green]✅ Removed: {removed_todo['description']}[/green]")

        except Exception as e:
            console.print(f"[red]❌ Error removing todo: {str(e)}[/red]")

    async def _cmd_standup(self, args: str):
        """Generate standup summary from recent activity."""
        import subprocess
        from datetime import datetime, timedelta
        from pathlib import Path

        console.print("[cyan]→ Generating standup summary...[/cyan]")

        # Get time range
        since = args.strip() if args else "yesterday"

        # Get recent commits
        commit_result = subprocess.run(
            ['git', 'log', f'--since={since}', '--oneline', '--author-date-order'],
            capture_output=True, text=True
        )
        commits = commit_result.stdout.strip().split('\n') if commit_result.stdout else []

        # Get current branch
        branch_result = subprocess.run(
            ['git', 'branch', '--show-current'],
            capture_output=True, text=True
        )
        current_branch = branch_result.stdout.strip()

        # Get modified files
        status_result = subprocess.run(
            ['git', 'status', '--porcelain'],
            capture_output=True, text=True
        )
        modified_files = len(status_result.stdout.strip().split('\n')) if status_result.stdout.strip() else 0

        # Check for todos
        todo_file = Path(".casper/todos.json")
        todos_summary = "No todos"
        if todo_file.exists():
            import json
            try:
                with open(todo_file) as f:
                    todos = json.load(f)
                    pending = [t for t in todos if t['status'] == 'pending']
                    completed_today = [t for t in todos if t['status'] == 'completed'
                                      and 'completed_at' in t
                                      and datetime.fromisoformat(t['completed_at']).date() == datetime.now().date()]
                    todos_summary = f"{len(pending)} pending, {len(completed_today)} completed today"
            except:
                pass

        # Generate standup report
        console.print("\n[bold]📊 Standup Summary[/bold]")
        console.print(f"[dim]{datetime.now().strftime('%B %d, %Y')}[/dim]\n")

        console.print("[bold cyan]Yesterday/Recently:[/bold cyan]")
        if commits:
            for commit in commits[:5]:  # Show max 5 commits
                console.print(f"  • {commit}")
        else:
            console.print("  • No commits since yesterday")

        console.print("\n[bold cyan]Today:[/bold cyan]")
        console.print(f"  • Working on: {current_branch}")
        console.print(f"  • Modified files: {modified_files}")
        console.print(f"  • Todos: {todos_summary}")

        console.print("\n[bold cyan]Blockers:[/bold cyan]")

        # Check for merge conflicts
        conflict_check = subprocess.run(
            ['git', 'diff', '--check'],
            capture_output=True, text=True
        )
        if conflict_check.returncode != 0:
            console.print("  • [red]Merge conflicts detected[/red]")
        else:
            console.print("  • None identified")

        # Add quick stats
        console.print("\n[bold cyan]Quick Stats:[/bold cyan]")

        # Lines changed
        diff_stat = subprocess.run(
            ['git', 'diff', '--stat'],
            capture_output=True, text=True
        )
        if diff_stat.stdout:
            lines = diff_stat.stdout.strip().split('\n')[-1]
            console.print(f"  • Uncommitted changes: {lines}")

        # Test status hint
        if Path("pytest.ini").exists() or Path("pyproject.toml").exists():
            console.print("  • Run /test to check test status")

        console.print("\n[dim]💡 Tip: Use /todo to manage daily tasks[/dim]")

    async def _cmd_deploy(self, args: str):
        """Deploy to specified environment."""
        import subprocess
        from pathlib import Path

        if not args:
            console.print("[red]❌ Usage: /deploy <environment>[/red]")
            console.print("[dim]Example: /deploy staging or /deploy production[/dim]")
            return

        environment = args.strip().lower()
        console.print(f"[cyan]→ Preparing deployment to {environment}...[/cyan]")

        # Pre-deployment checklist
        console.print("\n[bold]📋 Pre-deployment Checks:[/bold]")

        checks_passed = True

        # Check for uncommitted changes
        status_result = subprocess.run(
            ['git', 'status', '--porcelain'],
            capture_output=True, text=True
        )
        if status_result.stdout.strip():
            console.print("[red]❌ Uncommitted changes detected[/red]")
            checks_passed = False
        else:
            console.print("[green]✅ Working directory clean[/green]")

        # Check current branch
        branch_result = subprocess.run(
            ['git', 'branch', '--show-current'],
            capture_output=True, text=True
        )
        current_branch = branch_result.stdout.strip()

        if environment == 'production' and current_branch != 'main':
            console.print(f"[yellow]⚠️ Not on main branch (current: {current_branch})[/yellow]")
            checks_passed = False
        else:
            console.print(f"[green]✅ On branch: {current_branch}[/green]")

        # Run tests
        console.print("\n[cyan]→ Running tests...[/cyan]")
        test_passed = False

        if Path("package.json").exists():
            # Node.js project
            result = subprocess.run(['npm', 'test'], capture_output=True)
            test_passed = result.returncode == 0
        elif Path("pytest.ini").exists() or Path("pyproject.toml").exists():
            # Python project
            result = subprocess.run(['python', '-m', 'pytest'], capture_output=True)
            test_passed = result.returncode == 0

        if test_passed:
            console.print("[green]✅ Tests passed[/green]")
        else:
            console.print("[red]❌ Tests failed[/red]")
            checks_passed = False

        if not checks_passed:
            console.print("\n[red]❌ Pre-deployment checks failed[/red]")
            console.print("[dim]Fix issues above before deploying[/dim]")
            return

        # Deployment strategies based on common platforms
        console.print("\n[bold]🚀 Deployment Process:[/bold]")

        # Check for common deployment configurations
        deployed = False

        # Docker deployment
        if Path("Dockerfile").exists():
            console.print("[cyan]Docker deployment detected[/cyan]")
            console.print(f"[dim]Build: docker build -t app:{environment} .[/dim]")
            console.print(f"[dim]Push: docker push app:{environment}[/dim]")
            console.print(f"[dim]Deploy: docker run app:{environment}[/dim]")
            deployed = True

        # Heroku deployment
        elif Path("Procfile").exists():
            console.print("[cyan]Heroku deployment detected[/cyan]")
            console.print(f"[dim]Deploy: git push heroku-{environment} {current_branch}:main[/dim]")
            deployed = True

        # Vercel/Netlify deployment
        elif Path("vercel.json").exists() or Path("netlify.toml").exists():
            console.print("[cyan]Serverless deployment detected[/cyan]")
            console.print(f"[dim]Deploy: vercel --prod (or netlify deploy --prod)[/dim]")
            deployed = True

        # Generic deployment
        if not deployed:
            console.print("[yellow]⚠️ No standard deployment configuration found[/yellow]")
            console.print("\n[bold]Generic Deployment Steps:[/bold]")
            console.print("1. Build the application")
            console.print("2. Run integration tests")
            console.print("3. Update environment variables")
            console.print("4. Deploy to target server")
            console.print("5. Verify deployment")
            console.print("6. Monitor for issues")

        # Create deployment log
        deploy_log = f".casper/deployments/{environment}-{datetime.now().strftime('%Y%m%d-%H%M%S')}.log"
        Path(".casper/deployments").mkdir(exist_ok=True, parents=True)

        with open(deploy_log, 'w') as f:
            f.write(f"""Deployment Log
Environment: {environment}
Branch: {current_branch}
Timestamp: {datetime.now().isoformat()}
Tests: {'PASSED' if test_passed else 'FAILED'}
""")

        console.print(f"\n[green]✅ Deployment log: {deploy_log}[/green]")
        console.print("[dim]Complete deployment using your platform's commands above[/dim]")

    async def _cmd_sync(self, args: str):
        """Sync with remote repository and update dependencies."""
        import subprocess
        from pathlib import Path

        current_dir = Path.cwd()

        # Parse arguments
        force = "--force" in args or "-f" in args
        skip_deps = "--no-deps" in args
        verbose = "--verbose" in args or "-v" in args

        console.print("[cyan]🔄 Starting repository sync...[/cyan]")

        try:
            # 1. Check if we're in a git repository
            try:
                subprocess.run(['git', 'status'], check=True, capture_output=True)
            except subprocess.CalledProcessError:
                console.print("[red]❌ Not in a git repository[/red]")
                return

            # 2. Check for uncommitted changes
            status_result = subprocess.run(['git', 'status', '--porcelain'],
                                        capture_output=True, text=True, check=True)

            if status_result.stdout.strip() and not force:
                console.print("[yellow]⚠️ You have uncommitted changes:[/yellow]")
                for line in status_result.stdout.strip().split('\n'):
                    console.print(f"  {line}")
                console.print("[dim]Use '--force' to sync anyway, or commit changes first[/dim]")
                return

            # 3. Fetch latest changes
            console.print("[dim]→ Fetching latest changes...[/dim]")
            fetch_result = subprocess.run(['git', 'fetch'], capture_output=True, text=True)

            if fetch_result.returncode != 0:
                console.print(f"[red]❌ Git fetch failed: {fetch_result.stderr}[/red]")
                return

            # 4. Check if we're behind
            behind_result = subprocess.run(
                ['git', 'rev-list', '--count', 'HEAD..@{u}'],
                capture_output=True, text=True
            )

            if behind_result.returncode == 0 and behind_result.stdout.strip():
                commits_behind = int(behind_result.stdout.strip())
                if commits_behind > 0:
                    console.print(f"[dim]→ {commits_behind} commits behind. Pulling changes...[/dim]")

                    pull_result = subprocess.run(['git', 'pull'], capture_output=True, text=True)

                    if pull_result.returncode != 0:
                        console.print(f"[red]❌ Git pull failed: {pull_result.stderr}[/red]")
                        return

                    if verbose and pull_result.stdout:
                        console.print(f"[dim]{pull_result.stdout}[/dim]")

                    console.print("[green]✅ Repository updated[/green]")
                else:
                    console.print("[green]✅ Repository already up to date[/green]")

            if not skip_deps:
                # 5. Update dependencies
                console.print("[dim]→ Checking for dependency updates...[/dim]")

                # Python dependencies
                if (current_dir / "requirements.txt").exists():
                    console.print("[dim]→ Updating Python dependencies...[/dim]")
                    pip_result = subprocess.run(
                        ['pip', 'install', '-r', 'requirements.txt', '--upgrade'],
                        capture_output=True, text=True
                    )
                    if pip_result.returncode == 0:
                        console.print("[green]✅ Python dependencies updated[/green]")
                    else:
                        console.print(f"[yellow]⚠️ Python deps warning: {pip_result.stderr[:100]}[/yellow]")

                elif (current_dir / "pyproject.toml").exists():
                    console.print("[dim]→ Updating Poetry dependencies...[/dim]")
                    poetry_result = subprocess.run(['poetry', 'install'], capture_output=True, text=True)
                    if poetry_result.returncode == 0:
                        console.print("[green]✅ Poetry dependencies updated[/green]")
                    else:
                        console.print(f"[yellow]⚠️ Poetry warning: {poetry_result.stderr[:100]}[/yellow]")

                # Node.js dependencies
                if (current_dir / "package.json").exists():
                    console.print("[dim]→ Updating Node.js dependencies...[/dim]")

                    # Try yarn first, then npm
                    if (current_dir / "yarn.lock").exists():
                        npm_result = subprocess.run(['yarn', 'install'], capture_output=True, text=True)
                        pkg_manager = "Yarn"
                    else:
                        npm_result = subprocess.run(['npm', 'install'], capture_output=True, text=True)
                        pkg_manager = "npm"

                    if npm_result.returncode == 0:
                        console.print(f"[green]✅ {pkg_manager} dependencies updated[/green]")
                    else:
                        console.print(f"[yellow]⚠️ {pkg_manager} warning: {npm_result.stderr[:100]}[/yellow]")

                # 6. Check for migrations (if applicable)
                migration_files = list(current_dir.glob("**/migrations/*.py")) + \
                                list(current_dir.glob("**/migrate/*.sql"))

                if migration_files:
                    console.print("[dim]→ Migration files detected[/dim]")
                    console.print("[yellow]💡 You may want to run database migrations[/yellow]")

                    # Try to detect migration command
                    if (current_dir / "manage.py").exists():
                        console.print("[dim]Suggested: python manage.py migrate[/dim]")
                    elif (current_dir / "artisan").exists():
                        console.print("[dim]Suggested: php artisan migrate[/dim]")

            console.print("\n[bold green]🎉 Sync completed successfully![/bold green]")

            # Show summary
            summary_items = ["Repository updated"]
            if not skip_deps:
                summary_items.append("Dependencies refreshed")

            console.print(f"[dim]Summary: {', '.join(summary_items)}[/dim]")

        except subprocess.CalledProcessError as e:
            console.print(f"[red]❌ Sync failed: {str(e)}[/red]")
        except Exception as e:
            console.print(f"[red]❌ Unexpected error during sync: {str(e)}[/red]")

    # === PERSONALIZATION COMMAND HANDLERS ===

    async def _cmd_custom(self, args: str):
        """Handle custom command management."""
        if not args:
            # Show all custom commands
            personalization_manager.show_custom_commands()
            return

        parts = args.split(' ', 1)
        action = parts[0].lower()

        if action == "list":
            personalization_manager.show_custom_commands()

        elif action == "add":
            # Interactive custom command creation
            name = Prompt.ask("Custom command name (without #)")
            description = Prompt.ask("Description")

            console.print("\n[dim]Enter slash commands to execute (one per line, empty line to finish):[/dim]")
            commands = []
            while True:
                cmd = Prompt.ask(f"Command {len(commands) + 1}", default="")
                if not cmd:
                    break
                commands.append(cmd)

            if not commands:
                console.print("[red]❌ No commands specified[/red]")
                return

            # Ask for parameters
            params = []
            if Confirm.ask("Does this command need parameters?"):
                console.print("[dim]Enter parameter names (like NAME, TYPE, PATH):[/dim]")
                while True:
                    param = Prompt.ask(f"Parameter {len(params) + 1}", default="")
                    if not param:
                        break
                    params.append(param.upper())

            personalization_manager.create_custom_command(name, description, commands, params)

        elif action == "delete":
            if len(parts) < 2:
                console.print("[red]❌ Usage: /custom delete <command_name>[/red]")
                return

            cmd_name = parts[1].strip()
            personalization_manager.delete_custom_command(cmd_name)

        elif action == "prefs":
            personalization_manager.show_preferences()

        else:
            console.print("[red]❌ Usage: /custom [list|add|delete|prefs][/red]")

    async def _cmd_favorite(self, args: str):
        """Handle favorite commands."""
        if not args:
            favorites = personalization_manager.favorites
            if favorites:
                console.print("\n[bold yellow]⭐ Favorite Commands:[/bold yellow]")
                for fav in favorites:
                    console.print(f"  • {fav}")
            else:
                console.print("[yellow]No favorite commands yet[/yellow]")
                console.print("[dim]Add with: /favorite add <command>[/dim]")
            return

        parts = args.split(' ', 1)
        if len(parts) < 2:
            console.print("[red]❌ Usage: /favorite [add|remove] <command>[/red]")
            return

        action = parts[0].lower()
        command = parts[1].strip()

        if action == "add":
            personalization_manager.add_to_favorites(command)
        elif action == "remove":
            personalization_manager.remove_from_favorites(command)
        else:
            console.print("[red]❌ Usage: /favorite [add|remove] <command>[/red]")

    async def _cmd_theme(self, args: str):
        """Handle theme management."""
        if not args:
            # Show current theme info
            console.print("[yellow]🚧 Theme system - Coming soon![/yellow]")
            console.print("[dim]Available themes: default, dark, minimal, hacker, corporate[/dim]")
            return

        parts = args.split(' ', 1)
        action = parts[0].lower()

        if action == "list":
            console.print("\n[bold cyan]Available Themes:[/bold cyan]")
            for theme_name, theme in personalization_manager.themes.items():
                console.print(f"  • [bold]{theme_name}[/bold] - {theme.primary_color}/{theme.secondary_color}")

        elif action == "set" and len(parts) > 1:
            theme_name = parts[1].strip()
            console.print(f"[yellow]🚧 Setting theme to '{theme_name}' - Coming soon![/yellow]")

        else:
            console.print("[red]❌ Usage: /theme [list|set <theme_name>][/red]")

    async def _cmd_profile(self, args: str):
        """Handle project profile management."""
        if not args:
            # Show all profiles
            profiles = personalization_manager.project_profiles
            if profiles:
                console.print("\n[bold cyan]Project Profiles:[/bold cyan]")
                for name, profile in profiles.items():
                    console.print(f"  • [bold]{name}[/bold] ({profile.type}) - {profile.ai_provider}")
            else:
                console.print("[yellow]No project profiles defined[/yellow]")
                console.print("[dim]Create one with: /profile create <name> <type>[/dim]")
            return

        parts = args.split(' ')
        action = parts[0].lower()

        if action == "list":
            await self._cmd_profile("")  # Show all profiles

        elif action == "create" and len(parts) >= 3:
            name = parts[1]
            project_type = parts[2]
            personalization_manager.create_project_profile(name, project_type)

        elif action == "use" and len(parts) >= 2:
            profile_name = parts[1]
            console.print(f"[yellow]🚧 Using profile '{profile_name}' - Coming soon![/yellow]")

        else:
            console.print("[red]❌ Usage: /profile [list|create <name> <type>|use <name>][/red]")


    # === CONTEXT & PROJECT MANAGEMENT IMPLEMENTATIONS ===

    async def _cmd_context(self, args: str):
        """Manage project contexts and mental models."""
        from core.services.context_manager import context_manager

        if not args.strip():
            await context_manager.list_contexts()
            return

        parts = args.strip().split()
        action = parts[0].lower()

        if action == "save":
            name = parts[1] if len(parts) > 1 else None
            await context_manager.save_context(name)

        elif action == "restore":
            if len(parts) < 2:
                console.print("[red]❌ Usage: /context restore <context_name>[/red]")
                return
            await context_manager.restore_context(parts[1])

        elif action == "list":
            await context_manager.list_contexts()

        else:
            console.print("[red]❌ Usage: /context [save|restore|list] [context_name][/red]")

    async def _cmd_switch(self, args: str):
        """Smart project switching with context preservation."""
        from core.services.context_manager import context_manager
        from pathlib import Path

        if not args.strip():
            console.print("[red]❌ Usage: /switch <project_name> [--save-current][/red]")
            return

        parts = args.strip().split()
        project_name = parts[0]
        save_current = "--save-current" in parts

        # Save current context if requested
        if save_current:
            current_project = Path.cwd().name
            console.print(f"[dim]→ Saving current context: {current_project}[/dim]")
            await context_manager.save_context(current_project)

        # Attempt to restore the target context
        success = await context_manager.restore_context(project_name)

        if success:
            console.print(f"[green]✅ Switched to project: {project_name}[/green]")
            console.print("[dim]→ Context restored with full mental model[/dim]")
        else:
            console.print(f"[yellow]⚠️ Context '{project_name}' not found[/yellow]")
            console.print("[dim]Use '/context list' to see available contexts[/dim]")

    async def _cmd_notes(self, args: str):
        """Contextual note-taking linked to code/commits."""
        from core.services.productivity import productivity_service

        if not args.strip():
            console.print("[red]❌ Usage: /notes [add|list|search] [note_text][/red]")
            return

        parts = args.strip().split(None, 1)
        action = parts[0].lower()
        content = parts[1] if len(parts) > 1 else None

        if action not in ["add", "list", "search"]:
            # If no action specified, assume 'add'
            action = "add"
            content = args.strip()

        success = await productivity_service.manage_notes(action, content)

        if not success:
            console.print("[red]❌ Note operation failed[/red]")

    async def _cmd_env(self, args: str):
        """Environment variable management."""
        from core.services.env_manager import env_manager

        if not args.strip():
            await env_manager.list_variables()
            return

        parts = args.strip().split()
        action = parts[0].lower()

        if action == "list":
            show_values = "--values" in parts
            await env_manager.list_variables(show_values)

        elif action == "set" and len(parts) >= 3:
            key = parts[1]
            value = " ".join(parts[2:])
            await env_manager.set_variable(key, value)

        elif action == "get" and len(parts) >= 2:
            await env_manager.get_variable(parts[1])

        elif action == "delete" and len(parts) >= 2:
            await env_manager.delete_variable(parts[1])

        elif action == "encrypt":
            await env_manager.encrypt_env()

        elif action == "sync":
            await env_manager.sync_environments()

        else:
            console.print("[red]❌ Usage: /env [list|set <key> <value>|get <key>|delete <key>|encrypt|sync][/red]")

    # Placeholder implementations for other new commands
    async def _cmd_proposal(self, args: str):
        """Generate AI-powered business proposal."""
        from core.services.business import business_service

        if not args.strip():
            console.print("[red]❌ Usage: /proposal <client_name> [--template=<type>] [--hours][/red]")
            console.print("[dim]Templates: standard, detailed, agile[/dim]")
            return

        # Parse arguments
        parts = args.split()
        client_name = []
        template = "standard"
        include_hours = False

        for part in parts:
            if part.startswith("--template="):
                template = part.split("=", 1)[1]
            elif part == "--hours":
                include_hours = True
            else:
                client_name.append(part)

        if not client_name:
            console.print("[red]❌ Client name is required[/red]")
            return

        client_name = " ".join(client_name)

        success = await business_service.generate_proposal(
            client_name=client_name,
            template_type=template,
            include_hours=include_hours
        )

        if not success:
            console.print("[red]❌ Failed to generate proposal[/red]")

    async def _cmd_estimate(self, args: str):
        """Generate AI-powered project estimation."""
        from core.services.business import business_service

        if not args.strip():
            console.print("[red]❌ Usage: /estimate <project_description> [--detailed] [--risks][/red]")
            return

        # Parse arguments
        detailed = "--detailed" in args
        include_risks = "--risks" in args or True  # Default to including risks

        # Remove flags from project description
        project_description = args.replace("--detailed", "").replace("--risks", "").strip()

        if not project_description:
            console.print("[red]❌ Project description is required[/red]")
            return

        estimate = await business_service.estimate_project(
            project_description=project_description,
            detailed=detailed,
            include_risks=include_risks
        )

        if not estimate:
            console.print("[red]❌ Failed to generate estimate[/red]")

    async def _cmd_invoice(self, args: str):
        """Generate invoice with time tracking."""
        from core.services.business import business_service

        if not args.strip():
            console.print("[red]❌ Usage: /invoice <client_name> [--hours=<number>] [--template][/red]")
            return

        # Parse arguments
        parts = args.split()
        client_name = []
        hours = None
        template = "standard"

        i = 0
        while i < len(parts):
            part = parts[i]
            if part.startswith("--hours="):
                try:
                    hours = float(part.split("=", 1)[1])
                except ValueError:
                    console.print("[red]❌ Invalid hours value[/red]")
                    return
            elif part.startswith("--template="):
                template = part.split("=", 1)[1]
            elif part == "--template":
                template = "detailed"
            else:
                client_name.append(part)
            i += 1

        if not client_name:
            console.print("[red]❌ Client name is required[/red]")
            return

        client_name = " ".join(client_name)

        success = await business_service.generate_invoice(
            client_name=client_name,
            hours=hours,
            template=template
        )

        if not success:
            console.print("[red]❌ Failed to generate invoice[/red]")

    async def _cmd_panic(self, args: str):
        """Emergency troubleshooting and recovery procedures."""
        from core.services.emergency import emergency_service

        # Parse arguments
        show_logs = "--logs" in args or True  # Default show logs
        create_backup = "--backup" not in args  # Default create backup unless --no-backup
        auto_rollback = "--rollback" in args

        resolved = await emergency_service.panic_mode(
            show_logs=show_logs,
            create_backup=create_backup,
            auto_rollback=auto_rollback
        )

        if not resolved:
            console.print("\n[yellow]⚠️ Manual intervention may be required[/yellow]")
            console.print("[dim]Check the incident report for details[/dim]")

    async def _cmd_hotfix(self, args: str):
        """Rapid hotfix deployment with minimal testing."""
        from core.services.emergency import emergency_service

        if not args.strip():
            console.print("[red]❌ Usage: /hotfix <issue_description> [--deploy][/red]")
            return

        # Parse arguments
        deploy = "--deploy" in args
        issue_description = args.replace("--deploy", "").strip()

        if not issue_description:
            console.print("[red]❌ Issue description is required[/red]")
            return

        success = await emergency_service.create_hotfix(
            issue_description=issue_description,
            deploy=deploy
        )

        if not success:
            console.print("[red]❌ Hotfix failed. Manual intervention required.[/red]")

    async def _cmd_focus(self, args: str):
        """Deep work session management with distraction blocking."""
        from core.services.productivity import productivity_service

        # Parse arguments
        action = "status"  # Default
        duration = None

        if args.strip():
            parts = args.strip().split()
            if parts[0] in ["start", "stop", "status"]:
                action = parts[0]
                if action == "start" and len(parts) > 1:
                    try:
                        duration = int(parts[1])
                    except ValueError:
                        console.print("[red]❌ Invalid duration[/red]")
                        return

        success = await productivity_service.manage_focus(action, duration)

        if not success and action == "start":
            console.print("[red]❌ Failed to start focus session[/red]")

    async def _cmd_til(self, args: str):
        """Today I Learned - knowledge capture and indexing."""
        from core.services.productivity import productivity_service

        if not args.strip():
            console.print("[red]❌ Usage: /til <learning_text> [--tags tag1,tag2] [--project name][/red]")
            return

        # Parse arguments
        learning_text = args
        tags = []
        project = None

        # Extract tags
        if "--tags" in args:
            import re
            tag_match = re.search(r'--tags\s+([\w,]+)', args)
            if tag_match:
                tags = tag_match.group(1).split(',')
                learning_text = args.replace(tag_match.group(0), '').strip()

        # Extract project
        if "--project" in args:
            import re
            proj_match = re.search(r'--project\s+(\S+)', args)
            if proj_match:
                project = proj_match.group(1)
                learning_text = learning_text.replace(proj_match.group(0), '').strip()

        success = await productivity_service.capture_til(learning_text, tags, project)

        if not success:
            console.print("[red]❌ Failed to capture learning[/red]")

    async def _cmd_migrate(self, args: str):
        """Database migration management."""
        from core.services.development import development_service

        if not args.strip():
            console.print("[red]❌ Usage: /migrate [create <name>|up|down|status|rollback][/red]")
            return

        parts = args.strip().split()
        action = parts[0].lower()
        name = " ".join(parts[1:]) if len(parts) > 1 else None

        success = await development_service.manage_migration(action, name)

        if not success:
            console.print("[red]❌ Migration operation failed[/red]")

    async def _cmd_seed(self, args: str):
        """Database seeding management."""
        from core.services.development import development_service

        if not args.strip():
            console.print("[red]❌ Usage: /seed [run|create <seeder>|rollback][/red]")
            return

        parts = args.strip().split()
        action = parts[0].lower()
        seeder_name = " ".join(parts[1:]) if len(parts) > 1 else None

        success = await development_service.manage_seeding(action, seeder_name)

        if not success:
            console.print("[red]❌ Seeding operation failed[/red]")

    async def _cmd_scan(self, args: str):
        """Security vulnerability scanning."""
        from core.services.development import development_service

        # Parse arguments
        target = "all"  # Default
        auto_fix = False

        if args.strip():
            parts = args.strip().split()
            if parts[0] in ["deps", "code", "all"]:
                target = parts[0]
            if "--fix" in parts:
                auto_fix = True

        issues = await development_service.security_scan(target, auto_fix)

        if not issues:
            console.print("[green]✅ Your project is secure![/green]")

    async def _cmd_lint(self, args: str):
        """Multi-language linting with auto-fix."""
        from core.services.development import development_service

        # Parse arguments
        file_pattern = None
        auto_fix = "--fix" in args
        scan_all = "--all" in args

        # Extract file pattern
        args_clean = args.replace("--fix", "").replace("--all", "").strip()
        if args_clean:
            file_pattern = args_clean

        results = await development_service.run_linting(file_pattern, auto_fix, scan_all)

        if not results:
            console.print("[green]✅ Code is clean![/green]")

    async def _cmd_api(self, args: str):
        """Generate REST/GraphQL API scaffolding."""
        from core.services.development import development_service

        if not args.strip():
            console.print("[red]❌ Usage: /api [rest|graphql] <resource_name> [--crud] [--auth][/red]")
            return

        parts = args.strip().split()
        if len(parts) < 2:
            console.print("[red]❌ API type and resource name are required[/red]")
            return

        api_type = parts[0].lower()
        if api_type not in ["rest", "graphql"]:
            console.print("[red]❌ API type must be 'rest' or 'graphql'[/red]")
            return

        resource_name = parts[1]
        include_crud = "--crud" in parts
        include_auth = "--auth" in parts

        success = await development_service.generate_api(
            api_type, resource_name, include_crud, include_auth
        )

        if not success:
            console.print("[red]❌ API generation failed[/red]")

    async def _cmd_logs(self, args: str):
        """Intelligent log analysis and error detection."""
        from core.services.development import development_service

        # Parse arguments
        action = "tail"  # Default
        pattern = None
        follow = False

        if args.strip():
            parts = args.strip().split()
            if parts[0] in ["tail", "search", "errors"]:
                action = parts[0]
                if action == "search" and len(parts) > 1:
                    pattern = " ".join(parts[1:])
            if "--follow" in parts:
                follow = True

        success = await development_service.analyze_logs(action, pattern, follow)

        if not success:
            console.print("[red]❌ Log analysis failed[/red]")

    async def _cmd_performance_profile(self, args: str):
        console.print(f"[yellow]🚧 /profile (performance) - Coming soon! Args: {args}[/yellow]")

# Global instance for easy access
slash_commands = None

def get_slash_commands(casper_cli=None) -> SlashCommandRegistry:
    """Get the global slash command registry."""
    global slash_commands
    if slash_commands is None:
        slash_commands = SlashCommandRegistry(casper_cli)
    return slash_commands