"""
CASPER Workflow Management Service
Handles todo management, standup generation, and repository synchronization.
"""

import os
import json
import subprocess
from pathlib import Path
from typing import Dict, List, Optional
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict

from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.prompt import Confirm

console = Console()

@dataclass
class TodoItem:
    """Represents a todo item."""
    id: str
    description: str
    created_at: str
    completed: bool = False
    priority: str = "normal"  # low, normal, high, urgent
    tags: List[str] = None

    def __post_init__(self):
        if self.tags is None:
            self.tags = []

class WorkflowManager:
    """Manages project workflows, todos, and development activities."""

    def __init__(self):
        self.console = Console()
        self.todos_file = Path(".casper/todos.json")
        self.activity_file = Path(".casper/activity.json")

        # Ensure directories exist
        self.todos_file.parent.mkdir(parents=True, exist_ok=True)
        self.activity_file.parent.mkdir(parents=True, exist_ok=True)

    def _load_todos(self) -> List[TodoItem]:
        """Load todos from file."""
        if not self.todos_file.exists():
            return []

        try:
            with open(self.todos_file) as f:
                todos_data = json.load(f)
                return [TodoItem(**todo) for todo in todos_data]
        except Exception as e:
            console.print(f"[red]❌ Error loading todos: {e}[/red]")
            return []

    def _save_todos(self, todos: List[TodoItem]):
        """Save todos to file."""
        try:
            with open(self.todos_file, 'w') as f:
                json.dump([asdict(todo) for todo in todos], f, indent=2)
        except Exception as e:
            console.print(f"[red]❌ Error saving todos: {e}[/red]")

    def _log_activity(self, activity_type: str, description: str, metadata: Dict = None):
        """Log development activity."""
        activity = {
            "timestamp": datetime.now().isoformat(),
            "type": activity_type,
            "description": description,
            "metadata": metadata or {}
        }

        activities = []
        if self.activity_file.exists():
            try:
                with open(self.activity_file) as f:
                    activities = json.load(f)
            except:
                activities = []

        activities.append(activity)

        # Keep only last 100 activities
        activities = activities[-100:]

        try:
            with open(self.activity_file, 'w') as f:
                json.dump(activities, f, indent=2)
        except Exception as e:
            console.print(f"[yellow]⚠️ Could not log activity: {e}[/yellow]")

    async def add_todo(self, description: str, priority: str = "normal"):
        """Add a new todo item."""
        todos = self._load_todos()

        todo_id = str(len(todos) + 1)
        new_todo = TodoItem(
            id=todo_id,
            description=description,
            created_at=datetime.now().isoformat(),
            priority=priority
        )

        todos.append(new_todo)
        self._save_todos(todos)

        priority_color = {
            "low": "dim",
            "normal": "white",
            "high": "yellow",
            "urgent": "red"
        }.get(priority, "white")

        console.print(f"[green]✅ Added todo #{todo_id}:[/green] [{priority_color}]{description}[/{priority_color}]")
        self._log_activity("todo_added", f"Added todo: {description}", {"priority": priority})

    async def complete_todo(self, todo_id: str):
        """Mark a todo as completed."""
        todos = self._load_todos()

        for todo in todos:
            if todo.id == todo_id:
                todo.completed = True
                self._save_todos(todos)
                console.print(f"[green]✅ Completed todo #{todo_id}:[/green] {todo.description}")
                self._log_activity("todo_completed", f"Completed todo: {todo.description}")
                return

        console.print(f"[red]❌ Todo #{todo_id} not found[/red]")

    async def show_todos(self):
        """Display all todos."""
        todos = self._load_todos()

        if not todos:
            console.print("[yellow]📝 No todos yet[/yellow]")
            console.print("[dim]Add one with: /todo <description>[/dim]")
            return

        # Separate completed and pending todos
        pending = [t for t in todos if not t.completed]
        completed = [t for t in todos if t.completed]

        if pending:
            console.print("\n[bold cyan]📋 Pending Todos:[/bold cyan]")
            table = Table(show_header=True, header_style="bold cyan")
            table.add_column("ID", width=4, style="dim")
            table.add_column("Priority", width=8)
            table.add_column("Description", style="bright_white")
            table.add_column("Created", width=12, style="dim")

            for todo in pending:
                priority_style = {
                    "low": "dim",
                    "normal": "white",
                    "high": "yellow",
                    "urgent": "red"
                }.get(todo.priority, "white")

                created = datetime.fromisoformat(todo.created_at)
                table.add_row(
                    f"#{todo.id}",
                    f"[{priority_style}]{todo.priority.upper()}[/{priority_style}]",
                    todo.description,
                    created.strftime("%m/%d")
                )

            console.print(table)

        if completed:
            console.print(f"\n[dim]✅ Completed ({len(completed)} items) - use '/todo clear' to remove[/dim]")

    async def clear_todos(self):
        """Clear completed todos."""
        todos = self._load_todos()
        pending = [t for t in todos if not t.completed]
        completed_count = len(todos) - len(pending)

        if completed_count == 0:
            console.print("[yellow]No completed todos to clear[/yellow]")
            return

        if Confirm.ask(f"Clear {completed_count} completed todos?"):
            self._save_todos(pending)
            console.print(f"[green]✅ Cleared {completed_count} completed todos[/green]")

    async def generate_standup_summary(self, days: int = 1):
        """Generate standup summary from recent activity."""
        console.print(f"[dim]→ Generating standup summary for last {days} day(s)...[/dim]")

        # Get git activity
        git_summary = await self._get_git_activity_summary(days)

        # Get todos activity
        todos_summary = await self._get_todos_summary()

        # Get recent activity log
        activity_summary = self._get_recent_activity(days)

        # Create standup report
        console.print("\n[bold bright_cyan]🗣️  Standup Summary[/bold bright_cyan]")

        # Yesterday/Recent work
        if git_summary["commits"]:
            console.print("\n[bold green]✅ What I worked on:[/bold green]")
            for commit in git_summary["commits"][:5]:
                console.print(f"  • {commit}")

        # Current todos
        if todos_summary["pending"]:
            console.print("\n[bold yellow]🎯 Current focus:[/bold yellow]")
            for todo in todos_summary["pending"][:3]:
                priority_marker = "🔥" if todo["priority"] in ["high", "urgent"] else "📌"
                console.print(f"  {priority_marker} {todo['description']}")

        # Blockers (if any failed operations in activity log)
        blockers = [a for a in activity_summary if "error" in a["type"] or "failed" in a["description"].lower()]
        if blockers:
            console.print("\n[bold red]🚫 Blockers/Issues:[/bold red]")
            for blocker in blockers[-3:]:
                console.print(f"  • {blocker['description']}")

        # Stats
        console.print(f"\n[dim]📊 Activity: {git_summary['commit_count']} commits, {len(todos_summary['pending'])} active todos, {len(activity_summary)} actions[/dim]")

    async def _get_git_activity_summary(self, days: int) -> Dict:
        """Get git commit summary for recent days."""
        try:
            since_date = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")

            # Get recent commits
            result = subprocess.run([
                'git', 'log',
                '--since', since_date,
                '--pretty=format:%s',
                '--max-count=10'
            ], capture_output=True, text=True, check=True)

            commits = [line.strip() for line in result.stdout.strip().split('\n') if line.strip()]

            return {
                "commits": commits,
                "commit_count": len(commits)
            }
        except subprocess.CalledProcessError:
            return {"commits": [], "commit_count": 0}

    def _get_todos_summary(self) -> Dict:
        """Get current todos summary."""
        todos = self._load_todos()
        pending = [asdict(t) for t in todos if not t.completed]
        completed = [asdict(t) for t in todos if t.completed]

        return {
            "pending": pending,
            "completed": completed,
            "total": len(todos)
        }

    def _get_recent_activity(self, days: int) -> List[Dict]:
        """Get recent development activities."""
        if not self.activity_file.exists():
            return []

        try:
            with open(self.activity_file) as f:
                activities = json.load(f)

            # Filter by date
            cutoff_date = datetime.now() - timedelta(days=days)
            recent = []

            for activity in activities:
                activity_date = datetime.fromisoformat(activity["timestamp"])
                if activity_date >= cutoff_date:
                    recent.append(activity)

            return recent[-20:]  # Last 20 activities
        except:
            return []

    async def sync_repository(self, force: bool = False):
        """Sync with remote repository and update dependencies."""
        console.print("[dim]→ Syncing repository...[/dim]")

        try:
            # Check if we're in a git repository
            subprocess.run(['git', 'status'], check=True, capture_output=True)

            # Get current branch
            branch_result = subprocess.run(['git', 'branch', '--show-current'],
                                         capture_output=True, text=True, check=True)
            current_branch = branch_result.stdout.strip()

            console.print(f"[dim]→ Current branch: {current_branch}[/dim]")

            # Check for local changes
            status_result = subprocess.run(['git', 'status', '--porcelain'],
                                        capture_output=True, text=True, check=True)

            if status_result.stdout.strip() and not force:
                console.print("[yellow]⚠️ You have uncommitted changes[/yellow]")
                console.print("[dim]Use '/sync --force' to stash and sync, or commit changes first[/dim]")
                return

            # Stash changes if force and there are changes
            if status_result.stdout.strip() and force:
                console.print("[dim]→ Stashing local changes...[/dim]")
                subprocess.run(['git', 'stash', 'push', '-m', f'Auto-stash before sync {datetime.now()}'],
                             check=True)

            # Fetch from origin
            console.print("[dim]→ Fetching from origin...[/dim]")
            subprocess.run(['git', 'fetch', 'origin'], check=True)

            # Pull changes
            console.print("[dim]→ Pulling changes...[/dim]")
            pull_result = subprocess.run(['git', 'pull', 'origin', current_branch],
                                       capture_output=True, text=True, check=True)

            if "Already up to date" in pull_result.stdout:
                console.print("[green]✅ Repository already up to date[/green]")
            else:
                console.print("[green]✅ Repository updated[/green]")
                # Show what was updated
                lines = pull_result.stdout.strip().split('\n')
                for line in lines[:5]:  # Show first 5 lines
                    if line.strip():
                        console.print(f"[dim]  {line}[/dim]")

            # Update dependencies if package files exist
            await self._update_dependencies()

            console.print("[green]✅ Sync completed successfully[/green]")
            self._log_activity("repo_sync", f"Synced repository on branch {current_branch}")

        except subprocess.CalledProcessError as e:
            console.print(f"[red]❌ Git sync failed: {e}[/red]")
            if e.stdout:
                console.print(f"[dim]Output: {e.stdout.decode() if isinstance(e.stdout, bytes) else e.stdout}[/dim]")
        except Exception as e:
            console.print(f"[red]❌ Sync error: {str(e)}[/red]")

    async def _update_dependencies(self):
        """Update project dependencies based on detected package files."""
        cwd = Path.cwd()
        updated = False

        # Python dependencies
        if (cwd / "requirements.txt").exists():
            console.print("[dim]→ Updating Python dependencies...[/dim]")
            try:
                subprocess.run(['pip', 'install', '-r', 'requirements.txt'],
                             check=True, capture_output=True)
                console.print("[green]✅ Python dependencies updated[/green]")
                updated = True
            except subprocess.CalledProcessError:
                console.print("[yellow]⚠️ Could not update Python dependencies[/yellow]")

        elif (cwd / "pyproject.toml").exists():
            console.print("[dim]→ Updating Python dependencies (poetry)...[/dim]")
            try:
                subprocess.run(['poetry', 'install'], check=True, capture_output=True)
                console.print("[green]✅ Poetry dependencies updated[/green]")
                updated = True
            except subprocess.CalledProcessError:
                console.print("[yellow]⚠️ Could not update poetry dependencies[/yellow]")

        # Node.js dependencies
        if (cwd / "package.json").exists():
            console.print("[dim]→ Updating Node.js dependencies...[/dim]")
            package_manager = "yarn" if (cwd / "yarn.lock").exists() else "npm"
            try:
                subprocess.run([package_manager, 'install'], check=True, capture_output=True)
                console.print(f"[green]✅ {package_manager} dependencies updated[/green]")
                updated = True
            except subprocess.CalledProcessError:
                console.print(f"[yellow]⚠️ Could not update {package_manager} dependencies[/yellow]")

        if updated:
            self._log_activity("deps_update", "Updated project dependencies")

# Global instance
workflow_manager = WorkflowManager()