"""
CASPER Productivity Services
Implements focus management, knowledge capture, and note-taking for developers.
"""

import os
import json
import time
import subprocess
import asyncio
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from threading import Timer

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.prompt import Prompt, Confirm
from rich.progress import Progress, BarColumn, TimeRemainingColumn

from core.services.llm import llm_service

console = Console()


@dataclass
class FocusSession:
    """Focus session for deep work."""

    id: str
    start_time: datetime
    duration_minutes: int
    task: str
    completed: bool = False
    interruptions: int = 0
    notes: List[str] = field(default_factory=list)

    @property
    def end_time(self) -> datetime:
        return self.start_time + timedelta(minutes=self.duration_minutes)

    @property
    def remaining_minutes(self) -> int:
        if self.completed:
            return 0
        remaining = (self.end_time - datetime.now()).total_seconds() / 60
        return max(0, int(remaining))


@dataclass
class TILEntry:
    """Today I Learned entry."""

    id: str
    date: datetime
    content: str
    tags: List[str]
    project: Optional[str]
    code_snippet: Optional[str]
    resources: List[str] = field(default_factory=list)


@dataclass
class ContextualNote:
    """Note linked to code or commits."""

    id: str
    timestamp: datetime
    content: str
    context_type: str  # code, commit, file, project
    context_ref: str  # file path, commit hash, etc.
    tags: List[str] = field(default_factory=list)


class ProductivityService:
    """Handles productivity, knowledge, and note-taking commands."""

    def __init__(self):
        self.productivity_dir = Path.home() / ".casper" / "productivity"
        self.productivity_dir.mkdir(parents=True, exist_ok=True)

        self.focus_dir = self.productivity_dir / "focus"
        self.til_dir = self.productivity_dir / "til"
        self.notes_dir = self.productivity_dir / "notes"

        for dir_path in [self.focus_dir, self.til_dir, self.notes_dir]:
            dir_path.mkdir(parents=True, exist_ok=True)

        self.active_focus_session: Optional[FocusSession] = None
        self.focus_timer: Optional[Timer] = None

        # Load existing data
        self._load_productivity_data()

    def _load_productivity_data(self):
        """Load existing productivity data."""
        # Load active focus session if exists
        active_session_file = self.focus_dir / "active_session.json"
        if active_session_file.exists():
            try:
                with open(active_session_file, "r") as f:
                    data = json.load(f)
                    self.active_focus_session = FocusSession(
                        id=data["id"],
                        start_time=datetime.fromisoformat(data["start_time"]),
                        duration_minutes=data["duration_minutes"],
                        task=data["task"],
                        completed=data.get("completed", False),
                        interruptions=data.get("interruptions", 0),
                        notes=data.get("notes", []),
                    )

                    # Check if session is still active
                    if self.active_focus_session.remaining_minutes <= 0:
                        self.active_focus_session.completed = True
                        self._save_active_session()
            except:
                self.active_focus_session = None

    def _save_active_session(self):
        """Save the active focus session."""
        active_session_file = self.focus_dir / "active_session.json"

        if self.active_focus_session:
            with open(active_session_file, "w") as f:
                json.dump(
                    {
                        "id": self.active_focus_session.id,
                        "start_time": self.active_focus_session.start_time.isoformat(),
                        "duration_minutes": self.active_focus_session.duration_minutes,
                        "task": self.active_focus_session.task,
                        "completed": self.active_focus_session.completed,
                        "interruptions": self.active_focus_session.interruptions,
                        "notes": self.active_focus_session.notes,
                    },
                    f,
                    indent=2,
                )
        elif active_session_file.exists():
            active_session_file.unlink()

    async def manage_focus(self, action: str, duration: int = None) -> bool:
        """Deep work session management with distraction blocking."""

        if action == "start":
            if self.active_focus_session and not self.active_focus_session.completed:
                console.print("[yellow]⚠️ A focus session is already active[/yellow]")
                self._show_session_status()
                return False

            # Get session details
            if duration is None:
                duration_str = Prompt.ask("Session duration (minutes)", default="25")
                try:
                    duration = int(duration_str)
                except ValueError:
                    console.print("[red]Invalid duration[/red]")
                    return False

            task = Prompt.ask("What are you focusing on?")

            # Create new session
            session_id = datetime.now().strftime("%Y%m%d_%H%M%S")
            self.active_focus_session = FocusSession(
                id=session_id,
                start_time=datetime.now(),
                duration_minutes=duration,
                task=task,
            )

            self._save_active_session()

            # Start distraction blocking
            await self._start_distraction_blocking()

            # Display session start
            console.print(
                Panel(
                    f"[bold green]🎯 Focus Session Started[/bold green]\n\n"
                    f"[bold]Task:[/bold] {task}\n"
                    f"[bold]Duration:[/bold] {duration} minutes\n"
                    f"[bold]End Time:[/bold] {self.active_focus_session.end_time.strftime('%H:%M')}\n\n"
                    f"[dim]Distractions blocked. Deep work mode active.[/dim]",
                    title="Focus Mode",
                    border_style="green",
                )
            )

            # Set timer for session end
            self._set_session_timer(duration * 60)

            # Show productivity tips
            tips = [
                "Close unnecessary browser tabs",
                "Put your phone on silent",
                "Take a deep breath and begin",
                "Remember: Quality over quantity",
            ]
            console.print("\n[bold cyan]Focus Tips:[/bold cyan]")
            for tip in tips:
                console.print(f"  • {tip}")

            return True

        elif action == "stop":
            if not self.active_focus_session:
                console.print("[yellow]No active focus session[/yellow]")
                return False

            # End session
            self.active_focus_session.completed = True
            session_duration = (
                datetime.now() - self.active_focus_session.start_time
            ).total_seconds() / 60

            # Get session notes
            if Confirm.ask("Add session notes?"):
                notes = Prompt.ask("Session notes")
                self.active_focus_session.notes.append(notes)

            # Save session history
            self._save_session_history()

            # Stop distraction blocking
            await self._stop_distraction_blocking()

            # Display session summary
            console.print(
                Panel(
                    f"[bold green]✅ Focus Session Complete![/bold green]\n\n"
                    f"[bold]Task:[/bold] {self.active_focus_session.task}\n"
                    f"[bold]Duration:[/bold] {session_duration:.0f} minutes\n"
                    f"[bold]Interruptions:[/bold] {self.active_focus_session.interruptions}\n"
                    f"[bold]Productivity Score:[/bold] {self._calculate_productivity_score()}/100",
                    title="Session Complete",
                    border_style="green",
                )
            )

            # Generate AI insights
            if self.active_focus_session.notes:
                insights = await self._generate_productivity_insights()
                if insights:
                    console.print("\n[bold cyan]AI Insights:[/bold cyan]")
                    console.print(insights)

            self.active_focus_session = None
            self._save_active_session()

            return True

        elif action == "status":
            self._show_session_status()
            return True

        else:
            console.print("[red]❌ Invalid action. Use: start, stop, or status[/red]")
            return False

    def _show_session_status(self):
        """Show current focus session status."""
        if not self.active_focus_session:
            console.print("[yellow]No active focus session[/yellow]")

            # Show session history
            history = self._get_session_history()
            if history:
                console.print("\n[bold]Recent Sessions:[/bold]")
                table = Table(show_header=True, header_style="bold cyan")
                table.add_column("Date", style="bright_white")
                table.add_column("Task", style="yellow")
                table.add_column("Duration", justify="right")
                table.add_column("Score", justify="right")

                for session in history[-5:]:
                    table.add_row(
                        session["date"],
                        session["task"][:40],
                        f"{session['duration']} min",
                        str(session.get("score", "N/A")),
                    )

                console.print(table)
        else:
            remaining = self.active_focus_session.remaining_minutes

            if remaining > 0:
                console.print(
                    Panel(
                        f"[bold cyan]🎯 Focus Session Active[/bold cyan]\n\n"
                        f"[bold]Task:[/bold] {self.active_focus_session.task}\n"
                        f"[bold]Time Remaining:[/bold] {remaining} minutes\n"
                        f"[bold]Interruptions:[/bold] {self.active_focus_session.interruptions}\n\n"
                        f"[dim]Use '/focus stop' to end session early[/dim]",
                        title="Current Session",
                        border_style="cyan",
                    )
                )

                # Show progress bar
                with Progress(
                    "[progress.description]{task.description}",
                    BarColumn(),
                    "[progress.percentage]{task.percentage:>3.0f}%",
                    TimeRemainingColumn(),
                ) as progress:
                    total = self.active_focus_session.duration_minutes
                    completed = total - remaining
                    task = progress.add_task(
                        "Progress", total=total, completed=completed
                    )
                    time.sleep(0.5)  # Show progress briefly
            else:
                console.print(
                    "[yellow]Session time expired. Use '/focus stop' to complete.[/yellow]"
                )

    async def _start_distraction_blocking(self):
        """Start blocking distracting websites and apps."""
        # This is a simplified implementation
        # In production, would integrate with system-level blocking

        blocks = [
            "social media sites",
            "news websites",
            "video streaming",
            "messaging apps",
        ]

        console.print("\n[dim]Blocking distractions:[/dim]")
        for block in blocks:
            console.print(f"  • Blocking {block}...")
            await asyncio.sleep(0.1)  # Simulate blocking

        # Create hosts file backup (simplified)
        hosts_backup = self.focus_dir / "hosts_backup"
        if not hosts_backup.exists():
            # Would backup /etc/hosts here in production
            pass

    async def _stop_distraction_blocking(self):
        """Stop blocking distractions."""
        console.print("[dim]Removing distraction blocks...[/dim]")
        # Would restore original hosts file in production

    def _set_session_timer(self, seconds: int):
        """Set a timer for session end notification."""

        def session_ended():
            console.print("\n" + "=" * 50)
            console.print("[bold yellow]⏰ Focus session time is up![/bold yellow]")
            console.print("Use '/focus stop' to complete the session")
            console.print("=" * 50 + "\n")

        if self.focus_timer:
            self.focus_timer.cancel()

        self.focus_timer = Timer(seconds, session_ended)
        self.focus_timer.start()

    def _calculate_productivity_score(self) -> int:
        """Calculate productivity score based on session metrics."""
        if not self.active_focus_session:
            return 0

        score = 100

        # Deduct for interruptions
        score -= self.active_focus_session.interruptions * 10

        # Bonus for completing full duration
        actual_duration = (
            datetime.now() - self.active_focus_session.start_time
        ).total_seconds() / 60
        planned_duration = self.active_focus_session.duration_minutes

        if actual_duration >= planned_duration:
            score += 10
        else:
            # Deduct for ending early
            completion_ratio = actual_duration / planned_duration
            score -= int((1 - completion_ratio) * 20)

        return max(0, min(100, score))

    def _save_session_history(self):
        """Save completed session to history."""
        history_file = self.focus_dir / "history.json"

        history = []
        if history_file.exists():
            with open(history_file, "r") as f:
                history = json.load(f)

        session_data = {
            "id": self.active_focus_session.id,
            "date": self.active_focus_session.start_time.strftime("%Y-%m-%d"),
            "task": self.active_focus_session.task,
            "duration": int(
                (datetime.now() - self.active_focus_session.start_time).total_seconds()
                / 60
            ),
            "interruptions": self.active_focus_session.interruptions,
            "score": self._calculate_productivity_score(),
            "notes": self.active_focus_session.notes,
        }

        history.append(session_data)

        # Keep only last 100 sessions
        if len(history) > 100:
            history = history[-100:]

        with open(history_file, "w") as f:
            json.dump(history, f, indent=2)

    def _get_session_history(self) -> List[Dict]:
        """Get focus session history."""
        history_file = self.focus_dir / "history.json"

        if history_file.exists():
            with open(history_file, "r") as f:
                return json.load(f)
        return []

    async def _generate_productivity_insights(self) -> str:
        """Generate AI insights about productivity session."""
        if not self.active_focus_session:
            return ""

        prompt = f"""
Based on this focus session:
- Task: {self.active_focus_session.task}
- Duration: {(datetime.now() - self.active_focus_session.start_time).total_seconds() / 60:.0f} minutes
- Interruptions: {self.active_focus_session.interruptions}
- Notes: {' '.join(self.active_focus_session.notes)}

Provide brief insights on:
1. Task completion effectiveness
2. Focus quality based on interruptions
3. One specific tip for next session

Keep response under 100 words.
"""

        insights = await llm_service.complete(
            prompt,
            system="You are a productivity coach providing actionable insights.",
            max_tokens=200,
        )

        return insights

    async def capture_til(
        self, learning: str, tags: List[str] = None, project: str = None
    ) -> bool:
        """Today I Learned - knowledge capture and indexing."""
        console.print("[bold cyan]Capturing learning...[/bold cyan]")

        # Parse tags from learning text if not provided
        if not tags:
            tags = []
            # Extract hashtags
            import re

            hashtags = re.findall(r"#(\w+)", learning)
            tags.extend(hashtags)

            # Auto-detect technology tags
            tech_keywords = [
                "python",
                "javascript",
                "react",
                "django",
                "api",
                "database",
                "git",
                "docker",
                "aws",
                "testing",
                "security",
                "performance",
            ]
            for keyword in tech_keywords:
                if keyword in learning.lower():
                    tags.append(keyword)

        # Extract code snippet if present
        code_snippet = None
        if "```" in learning:
            # Extract code block
            code_match = re.search(r"```[\w]*\n(.*?)\n```", learning, re.DOTALL)
            if code_match:
                code_snippet = code_match.group(1)

        # Detect project if not specified
        if not project:
            project = Path.cwd().name

        # Create TIL entry
        til_id = datetime.now().strftime("%Y%m%d_%H%M%S")
        til_entry = TILEntry(
            id=til_id,
            date=datetime.now(),
            content=learning,
            tags=tags,
            project=project,
            code_snippet=code_snippet,
        )

        # Generate enhanced learning with AI
        enhanced = await self._enhance_til_with_ai(learning)

        if enhanced:
            til_entry.resources = self._extract_resources(enhanced)

        # Save TIL entry
        til_file = self.til_dir / f"{til_id}.json"
        with open(til_file, "w") as f:
            json.dump(
                {
                    "id": til_entry.id,
                    "date": til_entry.date.isoformat(),
                    "content": til_entry.content,
                    "enhanced": enhanced,
                    "tags": til_entry.tags,
                    "project": til_entry.project,
                    "code_snippet": til_entry.code_snippet,
                    "resources": til_entry.resources,
                },
                f,
                indent=2,
            )

        # Update TIL index
        self._update_til_index(til_entry)

        # Display confirmation
        console.print(
            Panel(
                f"[green]✅ Learning captured![/green]\n\n"
                f"[bold]Topic:[/bold] {learning[:100]}...\n"
                f"[bold]Tags:[/bold] {', '.join(tags) if tags else 'none'}\n"
                f"[bold]Project:[/bold] {project}",
                title="TIL Entry Saved",
                border_style="green",
            )
        )

        # Show daily learning stats
        stats = self._get_til_stats()
        console.print(f"\n[bold]Learning Stats:[/bold]")
        console.print(f"  • Today: {stats['today']} entries")
        console.print(f"  • This week: {stats['week']} entries")
        console.print(f"  • Total: {stats['total']} entries")

        return True

    async def _enhance_til_with_ai(self, learning: str) -> str:
        """Enhance TIL entry with AI-generated context."""
        prompt = f"""
Based on this learning: {learning}

Provide:
1. A brief explanation of why this is important
2. Related concepts to explore
3. Practical application example
4. One recommended resource or documentation link

Keep response concise and actionable.
"""

        enhanced = await llm_service.complete(
            prompt,
            system="You are a technical mentor helping developers learn and grow.",
            max_tokens=300,
        )

        return enhanced

    def _extract_resources(self, text: str) -> List[str]:
        """Extract resource URLs from text."""
        import re

        urls = re.findall(r"https?://[^\s]+", text)
        return urls[:5]  # Limit to 5 resources

    def _update_til_index(self, entry: TILEntry):
        """Update the TIL index for searching."""
        index_file = self.til_dir / "index.json"

        index = []
        if index_file.exists():
            with open(index_file, "r") as f:
                index = json.load(f)

        index.append(
            {
                "id": entry.id,
                "date": entry.date.isoformat(),
                "summary": entry.content[:100],
                "tags": entry.tags,
                "project": entry.project,
            }
        )

        # Keep only last 500 entries in index
        if len(index) > 500:
            index = index[-500:]

        with open(index_file, "w") as f:
            json.dump(index, f, indent=2)

    def _get_til_stats(self) -> Dict[str, int]:
        """Get TIL statistics."""
        index_file = self.til_dir / "index.json"

        if not index_file.exists():
            return {"today": 0, "week": 0, "total": 0}

        with open(index_file, "r") as f:
            index = json.load(f)

        today = datetime.now().date()
        week_ago = today - timedelta(days=7)

        today_count = sum(
            1
            for entry in index
            if datetime.fromisoformat(entry["date"]).date() == today
        )

        week_count = sum(
            1
            for entry in index
            if datetime.fromisoformat(entry["date"]).date() >= week_ago
        )

        return {"today": today_count, "week": week_count, "total": len(index)}

    async def manage_notes(self, action: str, content: str = None) -> bool:
        """Contextual note-taking linked to code/commits."""

        if action == "add":
            if not content:
                content = Prompt.ask("Note content")

            # Detect context
            context_type, context_ref = await self._detect_note_context()

            # Extract tags
            import re

            tags = re.findall(r"#(\w+)", content)

            # Create note
            note_id = datetime.now().strftime("%Y%m%d_%H%M%S")
            note = ContextualNote(
                id=note_id,
                timestamp=datetime.now(),
                content=content,
                context_type=context_type,
                context_ref=context_ref,
                tags=tags,
            )

            # Save note
            note_file = self.notes_dir / f"{note_id}.json"
            with open(note_file, "w") as f:
                json.dump(
                    {
                        "id": note.id,
                        "timestamp": note.timestamp.isoformat(),
                        "content": note.content,
                        "context_type": note.context_type,
                        "context_ref": note.context_ref,
                        "tags": note.tags,
                    },
                    f,
                    indent=2,
                )

            console.print(
                Panel(
                    f"[green]✅ Note saved![/green]\n\n"
                    f"[bold]Context:[/bold] {context_type} - {context_ref[:50]}...\n"
                    f"[bold]Tags:[/bold] {', '.join(tags) if tags else 'none'}",
                    title="Note Created",
                    border_style="green",
                )
            )

            return True

        elif action == "list":
            notes = self._list_notes()

            if not notes:
                console.print("[yellow]No notes found[/yellow]")
                return True

            table = Table(
                title="Recent Notes", show_header=True, header_style="bold cyan"
            )
            table.add_column("Date", style="bright_white")
            table.add_column("Context", style="yellow")
            table.add_column("Note", style="white")
            table.add_column("Tags", style="dim")

            for note in notes[-10:]:
                table.add_row(
                    note["date"],
                    f"{note['context_type']}",
                    note["content"][:50] + "...",
                    ", ".join(note.get("tags", [])),
                )

            console.print(table)
            return True

        elif action == "search":
            if not content:
                content = Prompt.ask("Search query")

            results = self._search_notes(content)

            if not results:
                console.print("[yellow]No matching notes found[/yellow]")
            else:
                console.print(f"\n[bold]Found {len(results)} matching notes:[/bold]")
                for note in results:
                    console.print(
                        f"\n[yellow]{note['date']}[/yellow] - {note['context_type']}"
                    )
                    console.print(f"  {note['content'][:100]}...")
                    if note.get("tags"):
                        console.print(f"  [dim]Tags: {', '.join(note['tags'])}[/dim]")

            return True

        else:
            console.print("[red]❌ Invalid action. Use: add, list, or search[/red]")
            return False

    async def _detect_note_context(self) -> Tuple[str, str]:
        """Detect current context for note."""
        context_type = "general"
        context_ref = Path.cwd().name

        # Check if in git repo
        try:
            # Get current branch
            result = subprocess.run(
                ["git", "branch", "--show-current"],
                capture_output=True,
                text=True,
                check=True,
            )
            branch = result.stdout.strip()

            # Get last commit
            result = subprocess.run(
                ["git", "log", "-1", "--oneline"],
                capture_output=True,
                text=True,
                check=True,
            )
            commit = result.stdout.strip()

            context_type = "commit"
            context_ref = f"{branch}: {commit}"

        except:
            # Check if editing a specific file
            # This would integrate with editor state in production
            pass

        return context_type, context_ref

    def _list_notes(self) -> List[Dict]:
        """List all notes."""
        notes = []

        for note_file in self.notes_dir.glob("*.json"):
            try:
                with open(note_file, "r") as f:
                    note_data = json.load(f)
                    notes.append(
                        {
                            "date": datetime.fromisoformat(
                                note_data["timestamp"]
                            ).strftime("%Y-%m-%d %H:%M"),
                            "content": note_data["content"],
                            "context_type": note_data["context_type"],
                            "context_ref": note_data["context_ref"],
                            "tags": note_data.get("tags", []),
                        }
                    )
            except:
                pass

        return sorted(notes, key=lambda x: x["date"], reverse=True)

    def _search_notes(self, query: str) -> List[Dict]:
        """Search notes by content or tags."""
        query_lower = query.lower()
        results = []

        for note_file in self.notes_dir.glob("*.json"):
            try:
                with open(note_file, "r") as f:
                    note_data = json.load(f)

                    # Search in content
                    if query_lower in note_data["content"].lower():
                        results.append(
                            {
                                "date": datetime.fromisoformat(
                                    note_data["timestamp"]
                                ).strftime("%Y-%m-%d %H:%M"),
                                "content": note_data["content"],
                                "context_type": note_data["context_type"],
                                "context_ref": note_data["context_ref"],
                                "tags": note_data.get("tags", []),
                            }
                        )
                        continue

                    # Search in tags
                    if any(
                        query_lower in tag.lower() for tag in note_data.get("tags", [])
                    ):
                        results.append(
                            {
                                "date": datetime.fromisoformat(
                                    note_data["timestamp"]
                                ).strftime("%Y-%m-%d %H:%M"),
                                "content": note_data["content"],
                                "context_type": note_data["context_type"],
                                "context_ref": note_data["context_ref"],
                                "tags": note_data.get("tags", []),
                            }
                        )
            except:
                pass

        return results[:20]  # Limit to 20 results


# Global instance
productivity_service = ProductivityService()
