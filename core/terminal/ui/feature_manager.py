"""Persistent, deterministic feature layer for the CASPER terminal UI."""

from __future__ import annotations

import json
import os
import shlex
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping, MutableMapping, Optional


@dataclass(frozen=True)
class LocalCommandResult:
    """Outcome of a command handled entirely by the TUI."""

    handled: bool
    message: str = ""
    exit_requested: bool = False


@dataclass(frozen=True)
class TranscriptEntry:
    timestamp: str
    pane: str
    kind: str
    content: str


THEMES: dict[str, dict[str, Any]] = {
    "auto": {"syntax": "monokai", "border": "cyan", "text": "default"},
    "dark": {"syntax": "monokai", "border": "bright_blue", "text": "white"},
    "light": {"syntax": "friendly", "border": "blue", "text": "black"},
    "mono": {"syntax": "bw", "border": "white", "text": "default"},
    "high-contrast": {
        "syntax": "monokai",
        "border": "bright_white",
        "text": "bright_white",
    },
}

LAYOUT_PRESETS: dict[str, dict[str, tuple[bool, int]]] = {
    "default": {
        "reasoning": (True, 15),
        "input": (True, 5),
        "code": (True, 20),
        "tests": (True, 10),
    },
    "compact": {
        "reasoning": (True, 8),
        "input": (True, 3),
        "code": (True, 12),
        "tests": (True, 6),
    },
    "focus-code": {
        "reasoning": (False, 8),
        "input": (True, 4),
        "code": (True, 32),
        "tests": (False, 8),
    },
    "focus-tests": {
        "reasoning": (False, 8),
        "input": (True, 4),
        "code": (True, 12),
        "tests": (True, 24),
    },
}

COMMAND_HELP: dict[str, str] = {
    "/accessibility": "Apply standard, high-contrast, plain, or reduced-motion profile",
    "/bookmark": "Add, list, or show transcript bookmarks",
    "/clear": "Clear all panes while preserving persistent history",
    "/commands": "Search the local command palette",
    "/export": "Export transcript as text, markdown, or JSON",
    "/help": "Show TUI help",
    "/history": "Show or search persistent command history",
    "/import": "Import a transcript from JSON, Markdown, or text",
    "/layout": "Apply a named layout preset",
    "/macro": "Record, list, and replay local command macros",
    "/notify": "Publish an accessible status notification",
    "/pane": "Show, hide, toggle, or resize a pane",
    "/quit": "Exit the interactive TUI",
    "/recover": "Restore the last autosaved pane state",
    "/redo": "Reapply the last reverted pane edit",
    "/search": "Search all current pane output",
    "/session": "Save, load, or list named TUI sessions",
    "/settings": "Show effective TUI preferences and state paths",
    "/shortcut": "List or customize shortcut labels",
    "/status": "Show live TUI status",
    "/theme": "Select auto, dark, light, or mono theme",
    "/undo": "Revert the last pane edit",
}


class TerminalFeatureManager:
    """Owns TUI preferences, durable state, transcripts, and local commands."""

    def __init__(self, state_root: Optional[Path | str] = None) -> None:
        root = Path(state_root) if state_root else self._default_state_root()
        self.state_root = root.expanduser().resolve()
        self.sessions_dir = self.state_root / "sessions"
        self.exports_dir = self.state_root / "exports"
        self.settings_path = self.state_root / "settings.json"
        self.history_path = self.state_root / "history.txt"
        self.recovery_path = self.state_root / "recovery.json"
        self.bookmarks_path = self.state_root / "bookmarks.json"
        self.macros_path = self.state_root / "macros.json"
        self._ensure_directories()

        self.settings: dict[str, Any] = {
            "theme": "auto",
            "layout": "default",
            "plain": False,
            "reduced_motion": False,
            "max_history": 500,
            "shortcuts": {
                "help": "F1",
                "reasoning": "F5",
                "code": "F6",
                "tests": "F7",
                "clear": "Ctrl+L",
                "refresh": "Ctrl+R",
            },
        }
        self.settings.update(self._read_json(self.settings_path, {}))
        self.transcript: list[TranscriptEntry] = []
        self.notifications: list[str] = []
        self.undo_stack: list[dict[str, str]] = []
        self.redo_stack: list[dict[str, str]] = []
        self.recording_macro: Optional[str] = None
        self.recording_commands: list[str] = []

    @staticmethod
    def _default_state_root() -> Path:
        override = os.environ.get("CASPER_TUI_HOME")
        if override:
            return Path(override)
        state_home = os.environ.get("XDG_STATE_HOME")
        if state_home:
            return Path(state_home) / "casper" / "tui"
        return Path.home() / ".local" / "state" / "casper" / "tui"

    def _ensure_directories(self) -> None:
        for directory in (self.state_root, self.sessions_dir, self.exports_dir):
            directory.mkdir(mode=0o700, parents=True, exist_ok=True)

    @staticmethod
    def _read_json(path: Path, default: Any) -> Any:
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except (FileNotFoundError, json.JSONDecodeError, OSError, TypeError):
            return default

    @staticmethod
    def _atomic_write(path: Path, content: str) -> None:
        path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
        temporary = path.with_suffix(path.suffix + ".tmp")
        temporary.write_text(content, encoding="utf-8")
        os.chmod(temporary, 0o600)
        os.replace(temporary, path)

    def _write_json(self, path: Path, payload: Any) -> None:
        self._atomic_write(path, json.dumps(payload, indent=2, sort_keys=True) + "\n")

    def save_settings(self) -> None:
        self._write_json(self.settings_path, self.settings)

    @property
    def no_color(self) -> bool:
        return bool(
            os.environ.get("NO_COLOR") is not None or self.settings.get("plain")
        )

    @property
    def theme(self) -> dict[str, Any]:
        name = (
            "high-contrast"
            if self.settings.get("accessibility") == "high-contrast"
            else self.settings.get("theme", "auto")
        )
        return THEMES.get(str(name), THEMES["auto"])

    def history(self) -> list[str]:
        try:
            return [
                line
                for line in self.history_path.read_text(encoding="utf-8").splitlines()
                if line
            ]
        except OSError:
            return []

    def record_history(self, command: str) -> None:
        command = command.strip()
        if not command:
            return
        commands = self.history()
        if commands and commands[-1] == command:
            return
        commands.append(command)
        limit = max(1, int(self.settings.get("max_history", 500)))
        self._atomic_write(self.history_path, "\n".join(commands[-limit:]) + "\n")

    def search_history(self, query: str = "") -> list[str]:
        needle = query.casefold()
        return [item for item in reversed(self.history()) if needle in item.casefold()]

    @staticmethod
    def pane_snapshot(panes: Mapping[str, Any]) -> dict[str, Any]:
        return {
            name: {
                "title": pane.title,
                "content": pane.content,
                "visible": bool(pane.visible),
                "height": int(pane.height),
                "syntax_language": pane.syntax_language,
            }
            for name, pane in panes.items()
        }

    def remember_edit(self, panes: Mapping[str, Any]) -> None:
        snapshot = {name: str(pane.content) for name, pane in panes.items()}
        if not self.undo_stack or self.undo_stack[-1] != snapshot:
            self.undo_stack.append(snapshot)
            del self.undo_stack[:-100]
        self.redo_stack.clear()

    def undo(
        self, panes: MutableMapping[str, Any], pane_name: Optional[str] = None
    ) -> bool:
        if not self.undo_stack:
            return False
        current = {name: str(pane.content) for name, pane in panes.items()}
        previous = self.undo_stack.pop()
        self.redo_stack.append(current)
        targets = [pane_name] if pane_name else list(panes)
        for name in targets:
            if name in panes and name in previous:
                panes[name].content = previous[name]
        self.autosave(panes)
        return True

    def redo(
        self, panes: MutableMapping[str, Any], pane_name: Optional[str] = None
    ) -> bool:
        if not self.redo_stack:
            return False
        current = {name: str(pane.content) for name, pane in panes.items()}
        following = self.redo_stack.pop()
        self.undo_stack.append(current)
        targets = [pane_name] if pane_name else list(panes)
        for name in targets:
            if name in panes and name in following:
                panes[name].content = following[name]
        self.autosave(panes)
        return True

    def append_transcript(self, pane: str, kind: str, content: str) -> None:
        self.transcript.append(
            TranscriptEntry(
                timestamp=datetime.now(timezone.utc).isoformat(),
                pane=pane,
                kind=kind,
                content=content,
            )
        )

    def autosave(self, panes: Mapping[str, Any]) -> None:
        payload = {
            "version": 1,
            "saved_at": datetime.now(timezone.utc).isoformat(),
            "panes": self.pane_snapshot(panes),
            "transcript": [asdict(item) for item in self.transcript[-2000:]],
        }
        self._write_json(self.recovery_path, payload)

    def restore(
        self, panes: MutableMapping[str, Any], path: Optional[Path] = None
    ) -> bool:
        payload = self._read_json(path or self.recovery_path, {})
        pane_data = payload.get("panes") if isinstance(payload, dict) else None
        if not isinstance(pane_data, dict):
            return False
        for name, state in pane_data.items():
            if name not in panes or not isinstance(state, dict):
                continue
            pane = panes[name]
            for key in ("title", "content", "visible", "height", "syntax_language"):
                if key in state:
                    setattr(pane, key, state[key])
        transcript = payload.get("transcript", [])
        self.transcript = [
            TranscriptEntry(**item) for item in transcript if isinstance(item, dict)
        ]
        return True

    def apply_layout(self, panes: MutableMapping[str, Any], preset: str) -> bool:
        layout = LAYOUT_PRESETS.get(preset)
        if not layout:
            return False
        for name, (visible, height) in layout.items():
            if name in panes:
                panes[name].visible = visible
                panes[name].height = height
        self.settings["layout"] = preset
        self.save_settings()
        self.autosave(panes)
        return True

    def search_panes(self, panes: Mapping[str, Any], query: str) -> list[str]:
        needle = query.casefold()
        results: list[str] = []
        for name, pane in panes.items():
            for number, line in enumerate(str(pane.content).splitlines(), 1):
                if needle in line.casefold():
                    results.append(f"{name}:{number}: {line.strip()}")
        return results

    def notify(self, message: str) -> None:
        if message:
            self.notifications.append(message)
            del self.notifications[:-50]

    def save_session(self, name: str, panes: Mapping[str, Any]) -> Path:
        safe = self._safe_name(name)
        path = self.sessions_dir / f"{safe}.json"
        self.autosave(panes)
        self._atomic_write(path, self.recovery_path.read_text(encoding="utf-8"))
        return path

    @staticmethod
    def _safe_name(name: str) -> str:
        safe = "".join(char for char in name.strip() if char.isalnum() or char in "-_")
        if not safe:
            raise ValueError(
                "a name containing letters, numbers, '-' or '_' is required"
            )
        return safe[:80]

    def list_sessions(self) -> list[str]:
        return sorted(path.stem for path in self.sessions_dir.glob("*.json"))

    def export_transcript(
        self, format_name: str, destination: Optional[str] = None
    ) -> Path:
        format_name = format_name.lower()
        suffixes = {"text": ".txt", "markdown": ".md", "json": ".json"}
        if format_name not in suffixes:
            raise ValueError("format must be text, markdown, or json")
        stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        path = (
            Path(destination).expanduser()
            if destination
            else self.exports_dir / f"transcript-{stamp}{suffixes[format_name]}"
        )
        if format_name == "json":
            content = (
                json.dumps([asdict(item) for item in self.transcript], indent=2) + "\n"
            )
        elif format_name == "markdown":
            content = (
                "# CASPER TUI Transcript\n\n"
                + "\n\n".join(
                    f"## {item.pane} · {item.kind} · {item.timestamp}\n\n```text\n{item.content}\n```"
                    for item in self.transcript
                )
                + "\n"
            )
        else:
            content = (
                "\n".join(
                    f"[{item.timestamp}] {item.pane}/{item.kind}: {item.content}"
                    for item in self.transcript
                )
                + "\n"
            )
        self._atomic_write(path.resolve(), content)
        return path.resolve()

    def import_transcript(self, source: str) -> int:
        path = Path(source).expanduser().resolve()
        content = path.read_text(encoding="utf-8")
        imported: list[TranscriptEntry] = []
        if path.suffix.lower() == ".json":
            payload = json.loads(content)
            if not isinstance(payload, list):
                raise ValueError("JSON transcript must contain a list")
            imported = [
                TranscriptEntry(**item) for item in payload if isinstance(item, dict)
            ]
        else:
            imported = [
                TranscriptEntry(
                    timestamp=datetime.now(timezone.utc).isoformat(),
                    pane="reasoning",
                    kind="import",
                    content=content,
                )
            ]
        self.transcript.extend(imported)
        return len(imported)

    def add_bookmark(self, name: str) -> None:
        if not self.transcript:
            raise ValueError("nothing has been written to the transcript")
        bookmarks = self._read_json(self.bookmarks_path, {})
        bookmarks[self._safe_name(name)] = asdict(self.transcript[-1])
        self._write_json(self.bookmarks_path, bookmarks)

    def bookmarks(self) -> dict[str, dict[str, str]]:
        value = self._read_json(self.bookmarks_path, {})
        return value if isinstance(value, dict) else {}

    def macros(self) -> dict[str, list[str]]:
        value = self._read_json(self.macros_path, {})
        return value if isinstance(value, dict) else {}

    def record_macro_command(self, command: str) -> None:
        if self.recording_macro and not command.startswith("/macro"):
            self.recording_commands.append(command)

    def set_shortcut(self, action: str, keys: str) -> None:
        self.settings.setdefault("shortcuts", {})[self._safe_name(action)] = keys
        self.save_settings()

    def apply_accessibility(self, profile: str) -> bool:
        if profile not in {"standard", "high-contrast", "plain", "reduced-motion"}:
            return False
        self.settings["accessibility"] = profile
        self.settings["plain"] = profile == "plain"
        self.settings["reduced_motion"] = profile == "reduced-motion"
        self.save_settings()
        return True

    def command_palette(self, query: str = "") -> list[str]:
        needle = query.casefold()
        return [
            f"{name} — {description}"
            for name, description in COMMAND_HELP.items()
            if needle in name.casefold() or needle in description.casefold()
        ]

    async def execute(self, ui: Any, command_line: str) -> LocalCommandResult:
        """Execute a local slash command, returning unhandled for normal AI prompts."""
        stripped = command_line.strip()
        legacy = {"help", "status", "history", "clear", "refresh", "exit", "quit"}
        if stripped.casefold() in legacy:
            stripped = "/" + stripped
        if not stripped.startswith("/"):
            return LocalCommandResult(False)
        try:
            parts = shlex.split(stripped)
        except ValueError as exc:
            return LocalCommandResult(True, f"Command parse error: {exc}")
        command = parts[0].casefold()
        args = parts[1:]
        self.record_history(stripped)
        self.record_macro_command(stripped)

        try:
            if command in {"/quit", "/exit"}:
                return LocalCommandResult(True, "Exit requested.", True)
            if command == "/help":
                return LocalCommandResult(
                    True,
                    "CASPER TUI local commands\n" + "\n".join(self.command_palette()),
                )
            if command == "/commands":
                return LocalCommandResult(
                    True,
                    "\n".join(self.command_palette(" ".join(args)))
                    or "No matching commands.",
                )
            if command == "/settings":
                return LocalCommandResult(
                    True,
                    json.dumps(
                        {**self.settings, "state_root": str(self.state_root)},
                        indent=2,
                        sort_keys=True,
                    ),
                )
            if command == "/theme":
                if not args:
                    return LocalCommandResult(
                        True, f"Theme: {self.settings.get('theme', 'auto')}"
                    )
                if args[0] not in {"auto", "dark", "light", "mono"}:
                    return LocalCommandResult(
                        True, "Theme must be auto, dark, light, or mono."
                    )
                self.settings["theme"] = args[0]
                self.save_settings()
                ui.refresh_console_capabilities()
                return LocalCommandResult(True, f"Theme set to {args[0]}.")
            if command == "/history":
                matches = self.search_history(" ".join(args))
                return LocalCommandResult(
                    True, "\n".join(matches[:100]) or "No history matches."
                )
            if command in {"/undo", "/redo"}:
                pane = args[0] if args else None
                changed = (
                    self.undo(ui.panes, pane)
                    if command == "/undo"
                    else self.redo(ui.panes, pane)
                )
                ui.rebuild_layout()
                return LocalCommandResult(
                    True,
                    f"{command[1:].title()} {'applied' if changed else 'unavailable'}.",
                )
            if command == "/layout":
                if not args:
                    return LocalCommandResult(
                        True, "Layouts: " + ", ".join(LAYOUT_PRESETS)
                    )
                changed = self.apply_layout(ui.panes, args[0])
                if changed:
                    ui.rebuild_layout()
                return LocalCommandResult(
                    True, f"Layout {args[0]} {'applied' if changed else 'not found'}."
                )
            if command == "/pane":
                return self._pane_command(ui, args)
            if command == "/recover":
                restored = self.restore(ui.panes)
                if restored:
                    ui.rebuild_layout()
                return LocalCommandResult(
                    True,
                    "Recovery restored." if restored else "No recovery state found.",
                )
            if command == "/search":
                if not args:
                    return LocalCommandResult(True, "Usage: /search QUERY")
                matches = self.search_panes(ui.panes, " ".join(args))
                return LocalCommandResult(
                    True, "\n".join(matches[:200]) or "No matches."
                )
            if command == "/notify":
                message = " ".join(args)
                if not message:
                    return LocalCommandResult(True, "Usage: /notify MESSAGE")
                self.notify(message)
                ui.refresh_layout()
                return LocalCommandResult(True, f"Notification: {message}")
            if command == "/session":
                return self._session_command(ui, args)
            if command == "/export":
                format_name = args[0] if args else "text"
                path = self.export_transcript(
                    format_name, args[1] if len(args) > 1 else None
                )
                return LocalCommandResult(True, f"Transcript exported to {path}")
            if command == "/import":
                if not args:
                    return LocalCommandResult(True, "Usage: /import PATH")
                count = self.import_transcript(args[0])
                return LocalCommandResult(
                    True,
                    f"Imported {count} transcript entr{'y' if count == 1 else 'ies'}.",
                )
            if command == "/bookmark":
                return self._bookmark_command(args)
            if command == "/macro":
                return await self._macro_command(ui, args)
            if command == "/shortcut":
                return self._shortcut_command(args)
            if command == "/accessibility":
                if not args:
                    return LocalCommandResult(
                        True, "Profiles: standard, high-contrast, plain, reduced-motion"
                    )
                applied = self.apply_accessibility(args[0])
                if applied:
                    ui.refresh_console_capabilities()
                return LocalCommandResult(
                    True,
                    f"Accessibility profile {args[0]} {'applied' if applied else 'not found'}.",
                )
            if command == "/status":
                visible = [name for name, pane in ui.panes.items() if pane.visible]
                return LocalCommandResult(
                    True,
                    f"running={ui.running} theme={self.settings.get('theme')} layout={self.settings.get('layout')} visible={','.join(visible)} transcript={len(self.transcript)}",
                )
            if command == "/clear":
                await ui.clear_screen()
                return LocalCommandResult(True, "Panes cleared.")
            if command == "/refresh":
                ui.rebuild_layout()
                return LocalCommandResult(True, "Layout refreshed.")
            return LocalCommandResult(
                True, f"Unknown local command: {command}. Use /commands."
            )
        except (OSError, ValueError, json.JSONDecodeError) as exc:
            return LocalCommandResult(True, f"{command} failed: {exc}")

    def _pane_command(self, ui: Any, args: list[str]) -> LocalCommandResult:
        if len(args) < 2 or args[0] not in ui.panes:
            return LocalCommandResult(
                True,
                "Usage: /pane reasoning|input|code|tests show|hide|toggle|height [N]",
            )
        pane = ui.panes[args[0]]
        action = args[1]
        if action == "show":
            pane.visible = True
        elif action == "hide":
            pane.visible = False
        elif action == "toggle":
            pane.visible = not pane.visible
        elif action == "height" and len(args) == 3:
            pane.height = max(3, min(80, int(args[2])))
        else:
            return LocalCommandResult(
                True, "Pane action must be show, hide, toggle, or height N."
            )
        self.autosave(ui.panes)
        ui.rebuild_layout()
        return LocalCommandResult(True, f"Pane {args[0]} updated.")

    def _session_command(self, ui: Any, args: list[str]) -> LocalCommandResult:
        if not args or args[0] == "list":
            return LocalCommandResult(
                True, "Sessions: " + (", ".join(self.list_sessions()) or "none")
            )
        if len(args) < 2 or args[0] not in {"save", "load"}:
            return LocalCommandResult(
                True, "Usage: /session save|load NAME or /session list"
            )
        if args[0] == "save":
            path = self.save_session(args[1], ui.panes)
            return LocalCommandResult(True, f"Session saved to {path}")
        restored = self.restore(
            ui.panes, self.sessions_dir / f"{self._safe_name(args[1])}.json"
        )
        if restored:
            ui.rebuild_layout()
        return LocalCommandResult(
            True, "Session loaded." if restored else "Session not found."
        )

    def _bookmark_command(self, args: list[str]) -> LocalCommandResult:
        if not args or args[0] == "list":
            return LocalCommandResult(
                True, "Bookmarks: " + (", ".join(sorted(self.bookmarks())) or "none")
            )
        if len(args) < 2 or args[0] not in {"add", "show"}:
            return LocalCommandResult(
                True, "Usage: /bookmark add|show NAME or /bookmark list"
            )
        if args[0] == "add":
            self.add_bookmark(args[1])
            return LocalCommandResult(True, f"Bookmark {args[1]} added.")
        item = self.bookmarks().get(self._safe_name(args[1]))
        return LocalCommandResult(
            True, json.dumps(item, indent=2) if item else "Bookmark not found."
        )

    async def _macro_command(self, ui: Any, args: list[str]) -> LocalCommandResult:
        if not args or args[0] == "list":
            return LocalCommandResult(
                True, "Macros: " + (", ".join(sorted(self.macros())) or "none")
            )
        if args[0] == "start" and len(args) == 2:
            self.recording_macro = self._safe_name(args[1])
            self.recording_commands = []
            return LocalCommandResult(True, f"Recording macro {self.recording_macro}.")
        if args[0] == "stop" and self.recording_macro:
            macros = self.macros()
            name = self.recording_macro
            macros[name] = list(self.recording_commands)
            self._write_json(self.macros_path, macros)
            self.recording_macro = None
            self.recording_commands = []
            return LocalCommandResult(True, f"Macro {name} saved.")
        if args[0] == "play" and len(args) == 2:
            commands = self.macros().get(self._safe_name(args[1]))
            if commands is None:
                return LocalCommandResult(True, "Macro not found.")
            messages = []
            for command in commands:
                result = await self.execute(ui, command)
                messages.append(result.message)
                if result.exit_requested:
                    return LocalCommandResult(True, "\n".join(messages), True)
            return LocalCommandResult(
                True, "\n".join(messages) or "Macro contained no commands."
            )
        return LocalCommandResult(
            True,
            "Usage: /macro start NAME, /macro stop, /macro play NAME, or /macro list",
        )

    def _shortcut_command(self, args: list[str]) -> LocalCommandResult:
        shortcuts = self.settings.setdefault("shortcuts", {})
        if not args or args[0] == "list":
            return LocalCommandResult(
                True,
                "\n".join(
                    f"{key}: {value}" for key, value in sorted(shortcuts.items())
                ),
            )
        if len(args) >= 4 and args[0] == "set" and args[2] == "to":
            self.set_shortcut(args[1], " ".join(args[3:]))
            return LocalCommandResult(
                True, f"Shortcut {args[1]} set to {' '.join(args[3:])}."
            )
        if len(args) == 3 and args[0] == "set":
            self.set_shortcut(args[1], args[2])
            return LocalCommandResult(True, f"Shortcut {args[1]} set to {args[2]}.")
        return LocalCommandResult(
            True, "Usage: /shortcut set ACTION KEYS or /shortcut list"
        )
