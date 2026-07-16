"""High-ROI interaction engines for CASPER's terminal clients.

These objects contain no renderer code.  Both the interactive TUI and headless
clients can use the same parsing, routing, preview, and portability behavior.
"""

from __future__ import annotations

import difflib
import hashlib
import json
import os
import shutil
import time
from collections import OrderedDict
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Callable, Iterable, Mapping


@dataclass(frozen=True)
class SlashCommand:
    name: str
    description: str
    handler: Callable[[str], Any]
    aliases: tuple[str, ...] = ()


class SlashCommandRegistry:
    """Discoverable slash commands with aliases and shell-free parsing."""

    def __init__(self) -> None:
        self._commands: dict[str, SlashCommand] = {}

    def register(self, command: SlashCommand) -> None:
        keys = (command.name, *command.aliases)
        if not command.name or any(not key or key in self._commands for key in keys):
            raise ValueError(f"duplicate or empty slash command: {command.name}")
        for key in keys:
            self._commands[key] = command

    def execute(self, text: str) -> Any:
        if not text.startswith("/"):
            raise ValueError("slash command must start with /")
        name, _, arguments = text[1:].partition(" ")
        command = self._commands.get(name)
        if command is None:
            raise KeyError(name)
        return command.handler(arguments.strip())

    def complete(self, prefix: str) -> tuple[str, ...]:
        needle = prefix.lstrip("/")
        canonical = {command.name for command in self._commands.values()}
        return tuple(f"/{name}" for name in sorted(canonical) if name.startswith(needle))


@dataclass(frozen=True)
class Intent:
    name: str
    terms: tuple[str, ...]


class NaturalLanguageIntentRouter:
    """Transparent word-overlap routing with an explicit confidence floor."""

    def __init__(self, intents: Iterable[Intent], *, minimum_score: float = 0.2) -> None:
        self.intents = tuple(intents)
        self.minimum_score = minimum_score

    def route(self, text: str) -> tuple[str, float]:
        words = {word.strip(".,!?;:()[]{}\"'").lower() for word in text.split()}
        scored = [
            (intent.name, len(words.intersection(intent.terms)) / max(1, len(intent.terms)))
            for intent in self.intents
        ]
        name, score = max(scored, key=lambda item: (item[1], item[0]), default=("unknown", 0.0))
        return (name, score) if score >= self.minimum_score else ("unknown", score)


class CommandPalette:
    """Small deterministic fuzzy finder for commands, tools, and actions."""

    @staticmethod
    def search(query: str, candidates: Iterable[str], *, limit: int = 10) -> tuple[str, ...]:
        needle = query.lower().replace(" ", "")

        def score(candidate: str) -> tuple[int, int, str] | None:
            haystack = candidate.lower()
            positions: list[int] = []
            cursor = 0
            for character in needle:
                found = haystack.find(character, cursor)
                if found < 0:
                    return None
                positions.append(found)
                cursor = found + 1
            span = positions[-1] - positions[0] if positions else 0
            return (span, len(candidate), candidate)

        matches = [(rank, candidate) for candidate in candidates if (rank := score(candidate)) is not None]
        return tuple(candidate for _, candidate in sorted(matches)[:limit])


@dataclass
class SessionBranch:
    name: str
    parent: str | None
    messages: list[dict[str, Any]] = field(default_factory=list)


class SessionBranchManager:
    """Forkable conversation state without shared mutable message lists."""

    def __init__(self, messages: Iterable[Mapping[str, Any]] = ()) -> None:
        self.branches = {"main": SessionBranch("main", None, [dict(item) for item in messages])}

    def fork(self, source: str, target: str) -> SessionBranch:
        if target in self.branches or source not in self.branches:
            raise ValueError("invalid branch fork")
        parent = self.branches[source]
        branch = SessionBranch(target, source, [dict(item) for item in parent.messages])
        self.branches[target] = branch
        return branch


@dataclass(frozen=True)
class DiffResult:
    text: str
    additions: int
    deletions: int


class DiffPreview:
    @staticmethod
    def render(before: str, after: str, *, path: str) -> DiffResult:
        lines = list(difflib.unified_diff(
            before.splitlines(keepends=True), after.splitlines(keepends=True),
            fromfile=f"a/{path}", tofile=f"b/{path}",
        ))
        additions = sum(line.startswith("+") and not line.startswith("+++") for line in lines)
        deletions = sum(line.startswith("-") and not line.startswith("---") for line in lines)
        return DiffResult("".join(lines), additions, deletions)


class PatchConflictDetector:
    """Optimistic concurrency guard for model-generated file edits."""

    @staticmethod
    def fingerprint(content: bytes | str) -> str:
        raw = content.encode() if isinstance(content, str) else content
        return hashlib.sha256(raw).hexdigest()

    def unchanged(self, path: Path, expected_fingerprint: str) -> bool:
        return path.is_file() and self.fingerprint(path.read_bytes()) == expected_fingerprint


@dataclass(frozen=True)
class ModelProfile:
    name: str
    capabilities: frozenset[str]
    context_tokens: int
    cost_rank: int = 0


class ModelRouter:
    """Pick the least-expensive model satisfying task capabilities and context."""

    def __init__(self, profiles: Iterable[ModelProfile]) -> None:
        self.profiles = tuple(profiles)

    def select(self, required: Iterable[str], *, context_tokens: int = 0) -> ModelProfile:
        needs = frozenset(required)
        eligible = [
            profile for profile in self.profiles
            if needs <= profile.capabilities and profile.context_tokens >= context_tokens
        ]
        if not eligible:
            raise LookupError("no model satisfies task requirements")
        return min(eligible, key=lambda profile: (profile.cost_rank, profile.context_tokens, profile.name))


class ContentCache:
    """Bounded TTL cache keyed by stable content hashes."""

    def __init__(self, *, capacity: int = 128, ttl_seconds: float = 300.0) -> None:
        if capacity < 1:
            raise ValueError("capacity must be positive")
        self.capacity = capacity
        self.ttl_seconds = ttl_seconds
        self._items: OrderedDict[str, tuple[float, Any]] = OrderedDict()

    @staticmethod
    def key(namespace: str, content: bytes | str) -> str:
        raw = content.encode() if isinstance(content, str) else content
        return f"{namespace}:{hashlib.sha256(raw).hexdigest()}"

    def put(self, key: str, value: Any) -> None:
        self._items[key] = (time.monotonic(), value)
        self._items.move_to_end(key)
        while len(self._items) > self.capacity:
            self._items.popitem(last=False)

    def get(self, key: str) -> Any | None:
        item = self._items.get(key)
        if item is None:
            return None
        created, value = item
        if time.monotonic() - created > self.ttl_seconds:
            del self._items[key]
            return None
        self._items.move_to_end(key)
        return value


@dataclass(frozen=True)
class SessionBundle:
    version: int
    objective: str
    messages: tuple[dict[str, Any], ...]
    metadata: dict[str, Any]

    def dumps(self) -> str:
        return json.dumps(asdict(self), sort_keys=True, separators=(",", ":"))

    @classmethod
    def loads(cls, payload: str) -> "SessionBundle":
        data = json.loads(payload)
        if data.get("version") != 1 or not isinstance(data.get("messages"), list):
            raise ValueError("unsupported or malformed session bundle")
        return cls(1, str(data["objective"]), tuple(data["messages"]), dict(data.get("metadata", {})))


@dataclass(frozen=True)
class DoctorCheck:
    name: str
    passed: bool
    detail: str


class OnboardingDoctor:
    """Actionable local readiness checks used by help and first-run flows."""

    def inspect(self, project_root: Path, *, executables: Iterable[str] = ("git",)) -> tuple[DoctorCheck, ...]:
        checks = [
            DoctorCheck("project", project_root.is_dir(), str(project_root)),
            DoctorCheck("writable", os.access(project_root, os.W_OK), "workspace write access"),
        ]
        checks.extend(
            DoctorCheck(f"executable:{name}", shutil.which(name) is not None, shutil.which(name) or "not found")
            for name in executables
        )
        return tuple(checks)
