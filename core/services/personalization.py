"""
CASPER Personalization System
Manages custom commands, themes, preferences, and user-specific configurations.
"""

import json
import re
from pathlib import Path
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict
from datetime import datetime

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.prompt import Prompt, Confirm
from rich.text import Text

from core.services.user_config import user_config

console = Console()

@dataclass
class CustomCommand:
    """Represents a custom user command."""
    name: str
    description: str
    command_sequence: List[str]  # List of slash commands to execute
    parameters: List[str] = None  # Parameters like $NAME, $TYPE
    category: str = "Custom"
    created_at: str = ""
    usage_count: int = 0

    def __post_init__(self):
        if self.parameters is None:
            self.parameters = []
        if not self.created_at:
            self.created_at = datetime.now().isoformat()

@dataclass
class Theme:
    """User interface theme configuration."""
    name: str
    primary_color: str = "cyan"
    secondary_color: str = "bright_green"
    accent_color: str = "yellow"
    error_color: str = "red"
    success_color: str = "green"
    prompt_style: str = "bold"
    banner_style: str = "cyan"

@dataclass
class WorkflowPreferences:
    """User workflow and behavior preferences."""
    default_ai_provider: str = "anthropic"
    auto_save_sessions: bool = True
    session_backup_frequency: int = 5  # minutes
    max_session_history: int = 50
    auto_clear_after_tasks: int = 10
    preferred_verbosity: str = "normal"  # quiet, normal, verbose
    show_progress_bars: bool = True
    enable_notifications: bool = True
    auto_sync_git: bool = False

@dataclass
class CodeGenPreferences:
    """Code generation and development preferences."""
    default_component_type: str = "react"
    naming_convention: str = "PascalCase"  # PascalCase, camelCase, snake_case
    test_framework: str = "jest"
    include_stories: bool = True
    include_types: bool = True
    default_license: str = "MIT"
    author_name: str = ""
    author_email: str = ""

@dataclass
class ProjectProfile:
    """Project-specific configuration profile."""
    name: str
    type: str  # react, python, nodejs, etc.
    ai_provider: str
    code_preferences: CodeGenPreferences
    custom_commands: List[str]  # List of command names specific to this profile
    git_config: Dict[str, str]

class PersonalizationManager:
    """Manages all user personalization features."""

    def __init__(self):
        self.user_dir = Path.home() / ".casper"
        self.personalization_file = self.user_dir / "personalization.json"
        self.custom_commands: Dict[str, CustomCommand] = {}
        self.themes: Dict[str, Theme] = {}
        self.workflow_prefs = WorkflowPreferences()
        self.codegen_prefs = CodeGenPreferences()
        self.project_profiles: Dict[str, ProjectProfile] = {}
        self.favorites: List[str] = []
        self.quick_actions: Dict[str, List[str]] = {}

        # Ensure directory exists
        self.user_dir.mkdir(parents=True, exist_ok=True)

        # Load existing personalization
        self._load_personalization()
        self._initialize_default_themes()

    def _load_personalization(self):
        """Load personalization settings from file."""
        if not self.personalization_file.exists():
            return

        try:
            with open(self.personalization_file) as f:
                data = json.load(f)

            # Load custom commands
            for cmd_data in data.get("custom_commands", []):
                cmd = CustomCommand(**cmd_data)
                self.custom_commands[cmd.name] = cmd

            # Load themes
            for theme_data in data.get("themes", []):
                theme = Theme(**theme_data)
                self.themes[theme.name] = theme

            # Load preferences
            if "workflow_preferences" in data:
                self.workflow_prefs = WorkflowPreferences(**data["workflow_preferences"])

            if "codegen_preferences" in data:
                self.codegen_prefs = CodeGenPreferences(**data["codegen_preferences"])

            # Load project profiles
            for profile_data in data.get("project_profiles", []):
                profile = ProjectProfile(
                    **{k: v for k, v in profile_data.items() if k != "code_preferences"},
                    code_preferences=CodeGenPreferences(**profile_data.get("code_preferences", {}))
                )
                self.project_profiles[profile.name] = profile

            # Load favorites and quick actions
            self.favorites = data.get("favorites", [])
            self.quick_actions = data.get("quick_actions", {})

        except Exception as e:
            console.print(f"[yellow]⚠️  Failed to load personalization: {e}[/yellow]")

    def _save_personalization(self):
        """Save personalization settings to file."""
        data = {
            "custom_commands": [asdict(cmd) for cmd in self.custom_commands.values()],
            "themes": [asdict(theme) for theme in self.themes.values()],
            "workflow_preferences": asdict(self.workflow_prefs),
            "codegen_preferences": asdict(self.codegen_prefs),
            "project_profiles": [
                {**asdict(profile), "code_preferences": asdict(profile.code_preferences)}
                for profile in self.project_profiles.values()
            ],
            "favorites": self.favorites,
            "quick_actions": self.quick_actions,
            "last_updated": datetime.now().isoformat()
        }

        with open(self.personalization_file, 'w') as f:
            json.dump(data, f, indent=2)

    def _initialize_default_themes(self):
        """Initialize default themes if none exist."""
        if not self.themes:
            self.themes.update({
                "default": Theme("default"),
                "dark": Theme("dark", "bright_blue", "bright_green", "bright_yellow"),
                "minimal": Theme("minimal", "white", "bright_white", "bright_cyan"),
                "hacker": Theme("hacker", "bright_green", "green", "bright_yellow"),
                "corporate": Theme("corporate", "blue", "bright_blue", "cyan")
            })

    # === CUSTOM COMMANDS ===

    def create_custom_command(self, name: str, description: str, command_sequence: List[str], parameters: List[str] = None):
        """Create a new custom command."""
        if name.startswith('#'):
            name = name[1:]  # Remove # prefix

        if name in self.custom_commands:
            if not Confirm.ask(f"Command #{name} already exists. Overwrite?"):
                return False

        cmd = CustomCommand(
            name=name,
            description=description,
            command_sequence=command_sequence,
            parameters=parameters or []
        )

        self.custom_commands[name] = cmd
        self._save_personalization()

        console.print(f"[green]✅ Custom command #{name} created![/green]")
        return True

    def delete_custom_command(self, name: str):
        """Delete a custom command."""
        if name.startswith('#'):
            name = name[1:]

        if name in self.custom_commands:
            del self.custom_commands[name]
            self._save_personalization()
            console.print(f"[green]✅ Custom command #{name} deleted[/green]")
            return True

        console.print(f"[red]❌ Custom command #{name} not found[/red]")
        return False

    def get_custom_command(self, name: str) -> Optional[CustomCommand]:
        """Get a custom command by name."""
        if name.startswith('#'):
            name = name[1:]
        return self.custom_commands.get(name)

    def list_custom_commands(self, category: Optional[str] = None) -> List[CustomCommand]:
        """List custom commands, optionally filtered by category."""
        commands = list(self.custom_commands.values())
        if category:
            commands = [cmd for cmd in commands if cmd.category == category]
        return sorted(commands, key=lambda x: (x.category, x.usage_count), reverse=True)

    async def execute_custom_command(self, name: str, args: List[str] = None, slash_commands=None):
        """Execute a custom command with parameter substitution."""
        if name.startswith('#'):
            name = name[1:]

        cmd = self.get_custom_command(name)
        if not cmd:
            console.print(f"[red]❌ Custom command #{name} not found[/red]")
            return False

        # Increment usage count
        cmd.usage_count += 1
        self._save_personalization()

        # Substitute parameters
        resolved_commands = []
        args = args or []

        for command in cmd.command_sequence:
            resolved_cmd = command
            for i, param in enumerate(cmd.parameters):
                if i < len(args):
                    resolved_cmd = resolved_cmd.replace(f"${param}", args[i])
                else:
                    # Prompt for missing parameters
                    value = Prompt.ask(f"Enter value for {param}")
                    resolved_cmd = resolved_cmd.replace(f"${param}", value)

            resolved_commands.append(resolved_cmd)

        # Execute commands
        console.print(f"[dim]→ Executing #{name}...[/dim]")
        for command in resolved_commands:
            if slash_commands:
                await slash_commands.execute(command)
            else:
                console.print(f"[dim]  {command}[/dim]")

        return True

    # === PREFERENCES MANAGEMENT ===

    def update_workflow_preferences(self, **kwargs):
        """Update workflow preferences."""
        for key, value in kwargs.items():
            if hasattr(self.workflow_prefs, key):
                setattr(self.workflow_prefs, key, value)
        self._save_personalization()

    def update_codegen_preferences(self, **kwargs):
        """Update code generation preferences."""
        for key, value in kwargs.items():
            if hasattr(self.codegen_prefs, key):
                setattr(self.codegen_prefs, key, value)
        self._save_personalization()

    def create_project_profile(self, name: str, project_type: str):
        """Create a new project profile."""
        profile = ProjectProfile(
            name=name,
            type=project_type,
            ai_provider=self.workflow_prefs.default_ai_provider,
            code_preferences=self.codegen_prefs,
            custom_commands=[],
            git_config={}
        )

        self.project_profiles[name] = profile
        self._save_personalization()

        console.print(f"[green]✅ Project profile '{name}' created[/green]")

    def add_to_favorites(self, command: str):
        """Add command to favorites."""
        if command not in self.favorites:
            self.favorites.append(command)
            self._save_personalization()
            console.print(f"[green]✅ Added {command} to favorites[/green]")

    def remove_from_favorites(self, command: str):
        """Remove command from favorites."""
        if command in self.favorites:
            self.favorites.remove(command)
            self._save_personalization()
            console.print(f"[green]✅ Removed {command} from favorites[/green]")

    def create_quick_action(self, name: str, commands: List[str]):
        """Create a quick action (multi-command shortcut)."""
        self.quick_actions[name] = commands
        self._save_personalization()
        console.print(f"[green]✅ Quick action '{name}' created[/green]")

    # === DISPLAY FUNCTIONS ===

    def show_custom_commands(self):
        """Display all custom commands."""
        commands = self.list_custom_commands()

        if not commands:
            console.print("[yellow]No custom commands defined[/yellow]")
            console.print("[dim]Create one with: /custom-add <name> <description> <commands>[/dim]")
            return

        table = Table(title="Custom Commands", show_header=True, header_style="bold cyan")
        table.add_column("Command", style="bright_green", width=15)
        table.add_column("Description", style="bright_white", width=30)
        table.add_column("Parameters", style="yellow", width=20)
        table.add_column("Uses", style="dim", width=8)

        for cmd in commands:
            params_str = ", ".join(f"${p}" for p in cmd.parameters) if cmd.parameters else "None"
            table.add_row(f"#{cmd.name}", cmd.description, params_str, str(cmd.usage_count))

        console.print(table)

    def show_preferences(self):
        """Display current preferences."""
        console.print("\n[bold cyan]CASPER Personalization Settings[/bold cyan]")

        # Workflow preferences
        workflow_table = Table(title="Workflow Preferences", show_header=True, header_style="bold green")
        workflow_table.add_column("Setting", style="bright_white", width=25)
        workflow_table.add_column("Value", style="bright_yellow", width=20)

        for key, value in asdict(self.workflow_prefs).items():
            workflow_table.add_row(key.replace('_', ' ').title(), str(value))

        console.print(workflow_table)

        # Code generation preferences
        codegen_table = Table(title="Code Generation Preferences", show_header=True, header_style="bold blue")
        codegen_table.add_column("Setting", style="bright_white", width=25)
        codegen_table.add_column("Value", style="bright_yellow", width=20)

        for key, value in asdict(self.codegen_prefs).items():
            codegen_table.add_row(key.replace('_', ' ').title(), str(value))

        console.print(codegen_table)

        # Favorites
        if self.favorites:
            console.print(f"\n[bold yellow]⭐ Favorite Commands:[/bold yellow]")
            for fav in self.favorites:
                console.print(f"  • {fav}")

# Global instance
personalization_manager = PersonalizationManager()