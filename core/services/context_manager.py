"""
CASPER Context Management Service
Full project mental model persistence and intelligent context switching for consultants.
"""

import os
import json
import shutil
import subprocess
from pathlib import Path
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.prompt import Prompt, Confirm
from rich.tree import Tree

from core.services.llm import llm_service

console = Console()


class ProjectContext:
    """Represents a complete project mental model."""

    def __init__(self, name: str, path: Path):
        self.name = name
        self.path = path
        self.created_at = datetime.now()
        self.last_accessed = datetime.now()

        # Core context data
        self.metadata = {}
        self.mental_model = ""
        self.active_tasks = []
        self.tech_stack = {}
        self.client_info = {}
        self.architecture_notes = ""
        self.current_focus = ""
        self.blockers = []
        self.next_steps = []
        self.code_patterns = {}
        self.environment_state = {}
        self.git_state = {}

    def to_dict(self) -> Dict:
        """Convert context to dictionary for serialization."""
        return {
            "name": self.name,
            "path": str(self.path),
            "created_at": self.created_at.isoformat(),
            "last_accessed": self.last_accessed.isoformat(),
            "metadata": self.metadata,
            "mental_model": self.mental_model,
            "active_tasks": self.active_tasks,
            "tech_stack": self.tech_stack,
            "client_info": self.client_info,
            "architecture_notes": self.architecture_notes,
            "current_focus": self.current_focus,
            "blockers": self.blockers,
            "next_steps": self.next_steps,
            "code_patterns": self.code_patterns,
            "environment_state": self.environment_state,
            "git_state": self.git_state,
        }

    @classmethod
    def from_dict(cls, data: Dict) -> "ProjectContext":
        """Create context from dictionary."""
        context = cls(data["name"], Path(data["path"]))
        context.created_at = datetime.fromisoformat(data["created_at"])
        context.last_accessed = datetime.fromisoformat(data["last_accessed"])
        context.metadata = data.get("metadata", {})
        context.mental_model = data.get("mental_model", "")
        context.active_tasks = data.get("active_tasks", [])
        context.tech_stack = data.get("tech_stack", {})
        context.client_info = data.get("client_info", {})
        context.architecture_notes = data.get("architecture_notes", "")
        context.current_focus = data.get("current_focus", "")
        context.blockers = data.get("blockers", [])
        context.next_steps = data.get("next_steps", [])
        context.code_patterns = data.get("code_patterns", {})
        context.environment_state = data.get("environment_state", {})
        context.git_state = data.get("git_state", {})
        return context


class ContextManager:
    """Manages project contexts and mental models."""

    def __init__(self):
        self.console = Console()
        self.contexts_dir = Path.home() / ".casper" / "contexts"
        self.contexts_dir.mkdir(parents=True, exist_ok=True)

        self.active_context: Optional[ProjectContext] = None
        self.contexts_index_file = self.contexts_dir / "index.json"

    def _load_contexts_index(self) -> Dict[str, Dict]:
        """Load the contexts index."""
        if self.contexts_index_file.exists():
            with open(self.contexts_index_file, "r") as f:
                return json.load(f)
        return {}

    def _save_contexts_index(self, index: Dict[str, Dict]):
        """Save the contexts index."""
        with open(self.contexts_index_file, "w") as f:
            json.dump(index, f, indent=2, default=str)

    def _get_context_file(self, name: str) -> Path:
        """Get the context file path for a given name."""
        return self.contexts_dir / f"{name}.json"

    async def _analyze_project(self, project_path: Path) -> Dict[str, Any]:
        """AI-powered project analysis to build mental model."""
        try:
            # Gather project information
            project_info = {
                "structure": self._analyze_project_structure(project_path),
                "tech_stack": self._detect_tech_stack(project_path),
                "git_info": self._get_git_info(project_path),
                "recent_commits": self._get_recent_commits(project_path),
            }

            # Try to generate AI-powered mental model
            try:
                prompt = f"""
Analyze this project and create a comprehensive mental model for a solo consultant developer.

Project Structure:
{project_info['structure']}

Technology Stack:
{json.dumps(project_info['tech_stack'], indent=2)}

Recent Git Activity:
{project_info['recent_commits']}

Create a mental model that includes:
1. Project purpose and business domain
2. Architecture overview and key patterns
3. Current development state and focus
4. Potential challenges and considerations
5. Next logical development steps

Be concise but comprehensive. Focus on what a consultant needs to quickly understand to be productive.
"""

                mental_model = await llm_service.complete(prompt)

            except Exception as llm_error:
                console.print(
                    f"[yellow]⚠️ AI analysis failed: {str(llm_error)}[/yellow]"
                )
                mental_model = self._generate_basic_mental_model(
                    project_info, project_path
                )

            return {
                "mental_model": mental_model,
                "tech_stack": project_info["tech_stack"],
                "git_state": project_info["git_info"],
                "analysis_timestamp": datetime.now().isoformat(),
            }

        except Exception as e:
            console.print(f"[yellow]⚠️ AI analysis failed: {str(e)}[/yellow]")
            return {
                "mental_model": f"Project at {project_path}\nManual analysis required.",
                "tech_stack": self._detect_tech_stack(project_path),
                "git_state": self._get_git_info(project_path),
            }

    def _analyze_project_structure(self, project_path: Path) -> str:
        """Analyze project directory structure."""
        structure = []
        try:
            # Get key directories and files
            important_patterns = [
                "src",
                "lib",
                "app",
                "components",
                "services",
                "tests",
                "docs",
                "package.json",
                "requirements.txt",
                "Dockerfile",
                "README.md",
                "tsconfig.json",
                "pyproject.toml",
                "Cargo.toml",
            ]

            for item in project_path.iterdir():
                if item.name.startswith("."):
                    continue

                if item.is_dir() and any(
                    pattern in item.name for pattern in important_patterns
                ):
                    structure.append(f"📁 {item.name}/")
                elif item.is_file() and any(
                    pattern in item.name for pattern in important_patterns
                ):
                    structure.append(f"📄 {item.name}")

            return "\n".join(structure[:20])  # Limit to first 20 items

        except Exception:
            return "Structure analysis unavailable"

    def _detect_tech_stack(self, project_path: Path) -> Dict[str, Any]:
        """Detect technology stack from project files."""
        tech_stack = {"languages": [], "frameworks": [], "databases": [], "tools": []}

        try:
            # Check for common files and patterns
            if (project_path / "package.json").exists():
                tech_stack["languages"].append("JavaScript/TypeScript")
                with open(project_path / "package.json", "r") as f:
                    pkg_data = json.load(f)
                    deps = {
                        **pkg_data.get("dependencies", {}),
                        **pkg_data.get("devDependencies", {}),
                    }

                    if "react" in deps:
                        tech_stack["frameworks"].append("React")
                    if "vue" in deps:
                        tech_stack["frameworks"].append("Vue")
                    if "express" in deps:
                        tech_stack["frameworks"].append("Express")
                    if "next" in deps:
                        tech_stack["frameworks"].append("Next.js")

            if (project_path / "requirements.txt").exists() or (
                project_path / "pyproject.toml"
            ).exists():
                tech_stack["languages"].append("Python")
                # Could parse requirements for frameworks like Django, Flask, FastAPI

            if (project_path / "Cargo.toml").exists():
                tech_stack["languages"].append("Rust")

            if (project_path / "go.mod").exists():
                tech_stack["languages"].append("Go")

            # Check for databases
            if any(
                (project_path / f).exists()
                for f in ["docker-compose.yml", "docker-compose.yaml"]
            ):
                tech_stack["tools"].append("Docker")

            return tech_stack

        except Exception:
            return tech_stack

    def _get_git_info(self, project_path: Path) -> Dict[str, Any]:
        """Get git repository information."""
        try:
            result = subprocess.run(
                ["git", "status", "--porcelain"],
                cwd=project_path,
                capture_output=True,
                text=True,
            )

            branch_result = subprocess.run(
                ["git", "branch", "--show-current"],
                cwd=project_path,
                capture_output=True,
                text=True,
            )

            return {
                "current_branch": (
                    branch_result.stdout.strip()
                    if branch_result.returncode == 0
                    else "unknown"
                ),
                "has_changes": (
                    bool(result.stdout.strip()) if result.returncode == 0 else False
                ),
                "is_git_repo": result.returncode == 0,
            }

        except Exception:
            return {
                "current_branch": "unknown",
                "has_changes": False,
                "is_git_repo": False,
            }

    def _get_recent_commits(self, project_path: Path, count: int = 5) -> str:
        """Get recent commit messages."""
        try:
            result = subprocess.run(
                ["git", "log", f"-{count}", "--oneline"],
                cwd=project_path,
                capture_output=True,
                text=True,
            )

            return (
                result.stdout.strip() if result.returncode == 0 else "No recent commits"
            )

        except Exception:
            return "Git history unavailable"

    async def save_context(
        self, name: Optional[str] = None, project_path: Optional[Path] = None
    ) -> bool:
        """Save current project context."""
        try:
            project_path = project_path or Path.cwd()
            name = name or project_path.name

            console.print(f"[dim]→ Analyzing project: {project_path.name}[/dim]")

            # Analyze project to build mental model
            analysis = await self._analyze_project(project_path)

            # Create context
            context = ProjectContext(name, project_path)
            context.mental_model = analysis["mental_model"]
            context.tech_stack = analysis["tech_stack"]
            context.git_state = analysis["git_state"]
            context.metadata = {
                "analysis_timestamp": analysis.get(
                    "analysis_timestamp", datetime.now().isoformat()
                ),
                "project_size": self._estimate_project_size(project_path),
                "last_modified": self._get_last_modified(project_path),
            }

            # Save context
            context_file = self._get_context_file(name)
            with open(context_file, "w") as f:
                json.dump(context.to_dict(), f, indent=2, default=str)

            # Update index
            index = self._load_contexts_index()
            index[name] = {
                "path": str(project_path),
                "last_saved": datetime.now().isoformat(),
                "size": context.metadata.get("project_size", "unknown"),
            }
            self._save_contexts_index(index)

            console.print(f"[green]✅ Context saved: {name}[/green]")
            console.print(
                Panel(
                    (
                        analysis["mental_model"][:300] + "..."
                        if len(analysis["mental_model"]) > 300
                        else analysis["mental_model"]
                    ),
                    title="🧠 Mental Model Preview",
                    border_style="green",
                )
            )

            return True

        except Exception as e:
            console.print(f"[red]❌ Error saving context: {str(e)}[/red]")
            return False

    async def restore_context(self, name: str) -> bool:
        """Restore a saved project context."""
        try:
            context_file = self._get_context_file(name)
            if not context_file.exists():
                console.print(f"[red]❌ Context '{name}' not found[/red]")
                return False

            with open(context_file, "r") as f:
                context_data = json.load(f)

            context = ProjectContext.from_dict(context_data)
            context.last_accessed = datetime.now()

            # Display context information
            console.print(f"[green]✅ Restored context: {name}[/green]")

            # Show mental model
            console.print(
                Panel(
                    context.mental_model,
                    title="🧠 Project Mental Model",
                    border_style="cyan",
                )
            )

            # Show tech stack
            if context.tech_stack:
                tech_info = []
                for category, items in context.tech_stack.items():
                    if items:
                        tech_info.append(f"**{category.title()}:** {', '.join(items)}")

                if tech_info:
                    console.print(
                        Panel(
                            "\n".join(tech_info),
                            title="🔧 Technology Stack",
                            border_style="blue",
                        )
                    )

            # Show git state
            if context.git_state.get("is_git_repo"):
                git_info = f"Branch: {context.git_state['current_branch']}"
                if context.git_state["has_changes"]:
                    git_info += " (has uncommitted changes)"
                console.print(f"[dim]Git: {git_info}[/dim]")

            # Show next steps if available
            if context.next_steps:
                console.print("\n[bold yellow]Next Steps:[/bold yellow]")
                for i, step in enumerate(context.next_steps, 1):
                    console.print(f"  {i}. {step}")

            self.active_context = context

            # Update access time
            with open(context_file, "w") as f:
                json.dump(context.to_dict(), f, indent=2, default=str)

            return True

        except Exception as e:
            console.print(f"[red]❌ Error restoring context: {str(e)}[/red]")
            return False

    async def list_contexts(self) -> bool:
        """List all saved contexts."""
        try:
            index = self._load_contexts_index()

            if not index:
                console.print("[yellow]⚠️ No saved contexts found[/yellow]")
                console.print(
                    "[dim]Use '/context save' to create your first context[/dim]"
                )
                return True

            table = Table(
                title="💾 Saved Project Contexts",
                show_header=True,
                header_style="bold cyan",
            )
            table.add_column("Name", style="yellow")
            table.add_column("Path", style="white")
            table.add_column("Last Saved", style="dim")
            table.add_column("Size", style="green")

            for name, info in sorted(index.items()):
                last_saved = datetime.fromisoformat(info["last_saved"])
                time_ago = self._time_ago(last_saved)
                table.add_row(
                    name,
                    str(Path(info["path"]).name),
                    time_ago,
                    info.get("size", "unknown"),
                )

            console.print(table)
            console.print(
                f"\n[dim]Use '/context restore <name>' to restore a context[/dim]"
            )

            return True

        except Exception as e:
            console.print(f"[red]❌ Error listing contexts: {str(e)}[/red]")
            return False

    def _estimate_project_size(self, project_path: Path) -> str:
        """Estimate project size."""
        try:
            total_files = sum(
                1
                for _ in project_path.rglob("*")
                if _.is_file() and not _.name.startswith(".")
            )

            if total_files < 10:
                return "Small"
            elif total_files < 50:
                return "Medium"
            elif total_files < 200:
                return "Large"
            else:
                return "Enterprise"

        except Exception:
            return "Unknown"

    def _get_last_modified(self, project_path: Path) -> str:
        """Get last modification time of project."""
        try:
            latest_time = 0
            for file_path in project_path.rglob("*"):
                if file_path.is_file() and not file_path.name.startswith("."):
                    mtime = file_path.stat().st_mtime
                    latest_time = max(latest_time, mtime)

            return (
                datetime.fromtimestamp(latest_time).isoformat()
                if latest_time > 0
                else "unknown"
            )

        except Exception:
            return "unknown"

    def _time_ago(self, dt: datetime) -> str:
        """Get human-readable time difference."""
        now = datetime.now()
        diff = now - dt

        if diff.days > 0:
            return f"{diff.days}d ago"
        elif diff.seconds > 3600:
            return f"{diff.seconds // 3600}h ago"
        elif diff.seconds > 60:
            return f"{diff.seconds // 60}m ago"
        else:
            return "just now"

    def _generate_basic_mental_model(
        self, project_info: Dict, project_path: Path
    ) -> str:
        """Generate a basic mental model when AI analysis fails."""
        tech_stack = project_info.get("tech_stack", "Unknown")
        structure = project_info.get("structure", "Standard project")

        return f"""# Project Mental Model (Basic Analysis)

**Location:** {project_path}
**Technology Stack:** {tech_stack}
**Project Structure:** {structure}

## Key Components
- Standard project layout detected
- Technology stack: {tech_stack}
- Manual analysis required for detailed insights

## Development Context
This is a basic fallback analysis. For detailed insights, ensure LLM service is properly configured.

**Note:** AI-powered analysis temporarily unavailable."""


# Global instance
context_manager = ContextManager()
