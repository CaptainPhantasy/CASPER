"""Transactional, project-contained workspace operations for harness tools."""

from __future__ import annotations

import asyncio
import difflib
import hashlib
import json
import os
import shutil
import time
import uuid
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Optional

from .models import ToolObservation, ToolSpec
from .registry import ToolRegistry


@dataclass
class WorkspaceChange:
    id: str
    path: str
    before_hash: str
    after_hash: str
    backup: str
    diff: str
    created_at: float
    undone: bool = False


class WorkspaceEngine:
    def __init__(self, project_root: Path | str, state_root: Optional[Path | str] = None) -> None:
        self.root = Path(project_root).expanduser().resolve()
        self.state_root = Path(state_root).expanduser().resolve() if state_root else self.root / ".casper" / "harness"
        self.backups = self.state_root / "backups"
        self.ledger_path = self.state_root / "workspace.jsonl"
        self.backups.mkdir(parents=True, exist_ok=True, mode=0o700)

    def resolve(self, raw: str) -> Path:
        candidate = (self.root / raw).resolve() if not os.path.isabs(raw) else Path(raw).resolve()
        if candidate != self.root and self.root not in candidate.parents:
            raise ValueError("path escapes the active project root")
        return candidate

    @staticmethod
    def _hash(content: str) -> str:
        return hashlib.sha256(content.encode("utf-8")).hexdigest()

    def read_file(self, path: str, max_bytes: int = 32_000) -> ToolObservation:
        target = self.resolve(path)
        if not target.is_file():
            return ToolObservation.error(
                f"File not found: {path}", "The path is not a readable file.",
                "Correct the repo-relative path and retry.", "Stop if the file is generated or external.",
            )
        raw = target.read_bytes()
        clipped = raw[:max_bytes]
        content = clipped.decode("utf-8", errors="replace")
        return ToolObservation.success(
            f"Read {path}.", data={"content": content, "truncated": len(raw) > max_bytes, "bytes": len(raw)},
            artifacts=[str(target)],
        )

    def list_files(self, path: str = ".", limit: int = 200) -> ToolObservation:
        target = self.resolve(path)
        if not target.is_dir():
            return ToolObservation.error(
                f"Directory not found: {path}", "The path is not a directory.",
                "Correct the repo-relative directory and retry.", "Stop if the directory is external.",
            )
        entries = sorted(item.name + ("/" if item.is_dir() else "") for item in target.iterdir())
        return ToolObservation.success(
            f"Listed {min(len(entries), limit)} of {len(entries)} entries.",
            data={"entries": entries[:limit], "truncated": len(entries) > limit},
        )

    def patch_file(
        self, path: str, old_text: str, new_text: str, expected_sha256: str = "",
    ) -> ToolObservation:
        target = self.resolve(path)
        before = target.read_text(encoding="utf-8", errors="strict") if target.exists() else ""
        before_hash = self._hash(before)
        if expected_sha256 and expected_sha256 != before_hash:
            return ToolObservation.error(
                f"Precondition failed for {path}.", "The file changed after the patch was prepared.",
                "Read the file again and regenerate the patch against its current hash.",
                "Stop if unrelated work would be overwritten.",
                data={"expected_sha256": expected_sha256, "actual_sha256": before_hash},
            )
        if old_text:
            count = before.count(old_text)
            if count != 1:
                return ToolObservation.error(
                    f"Patch anchor matched {count} times in {path}.",
                    "A transactional patch requires one exact anchor.",
                    "Use a larger unique old_text block and retry.",
                    "Stop if the intended edit cannot be isolated.",
                    data={"matches": count},
                )
            after = before.replace(old_text, new_text, 1)
        else:
            if target.exists() and before:
                return ToolObservation.error(
                    f"Refusing create-style patch for existing file: {path}",
                    "old_text was empty but the target already has content.",
                    "Supply an exact old_text anchor.", "Stop before replacing the whole file implicitly.",
                )
            after = new_text
        if after == before:
            return ToolObservation.warning("Patch made no changes.", data={"path": path})
        diff = "".join(difflib.unified_diff(
            before.splitlines(keepends=True), after.splitlines(keepends=True),
            fromfile=f"a/{path}", tofile=f"b/{path}",
        ))
        change_id = f"change_{uuid.uuid4().hex[:16]}"
        backup = self.backups / f"{change_id}.bak"
        backup.write_text(before, encoding="utf-8")
        temporary = target.with_name(f".{target.name}.{change_id}.tmp")
        try:
            target.parent.mkdir(parents=True, exist_ok=True)
            temporary.write_text(after, encoding="utf-8")
            os.replace(temporary, target)
        except Exception:
            temporary.unlink(missing_ok=True)
            raise
        change = WorkspaceChange(
            change_id, str(target.relative_to(self.root)), before_hash, self._hash(after),
            str(backup), diff, time.time(),
        )
        self._append_change(change)
        return ToolObservation.success(
            f"Applied transactional patch to {path}.",
            data={"change_id": change_id, "diff": diff, "before_sha256": before_hash, "after_sha256": change.after_hash},
            artifacts=[str(target)], next_actions=["Run the narrowest relevant verification."],
        )

    def changes(self) -> list[WorkspaceChange]:
        if not self.ledger_path.exists():
            return []
        result: list[WorkspaceChange] = []
        for line in self.ledger_path.read_text(encoding="utf-8").splitlines():
            try:
                result.append(WorkspaceChange(**json.loads(line)))
            except (TypeError, ValueError, json.JSONDecodeError):
                continue
        return result

    def _append_change(self, change: WorkspaceChange) -> None:
        self.ledger_path.parent.mkdir(parents=True, exist_ok=True)
        with self.ledger_path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(asdict(change), sort_keys=True) + "\n")

    def _rewrite_changes(self, changes: list[WorkspaceChange]) -> None:
        temporary = self.ledger_path.with_suffix(".tmp")
        temporary.write_text(
            "".join(json.dumps(asdict(item), sort_keys=True) + "\n" for item in changes), encoding="utf-8"
        )
        os.replace(temporary, self.ledger_path)

    def undo(self, change_id: str) -> ToolObservation:
        changes = self.changes()
        change = next((item for item in changes if item.id == change_id), None)
        if not change:
            return ToolObservation.error(
                f"Unknown workspace change: {change_id}", "No durable ledger entry has that id.",
                "List workspace changes and retry with an exact id.", "Stop if the ledger was removed.",
            )
        if change.undone:
            return ToolObservation.warning("The workspace change was already undone.")
        target = self.resolve(change.path)
        current = target.read_text(encoding="utf-8") if target.exists() else ""
        if self._hash(current) != change.after_hash:
            return ToolObservation.error(
                f"Refusing to undo {change.path}; it changed after the recorded patch.",
                "Undo would overwrite newer work.", "Inspect the current diff and restore manually if appropriate.",
                "Stop before overwriting unrelated changes.",
            )
        original = Path(change.backup).read_text(encoding="utf-8")
        if original:
            temporary = target.with_suffix(target.suffix + ".undo.tmp")
            temporary.write_text(original, encoding="utf-8")
            os.replace(temporary, target)
        else:
            quarantine = self.state_root / "quarantine"
            quarantine.mkdir(parents=True, exist_ok=True)
            shutil.move(str(target), quarantine / f"{change.id}_{target.name}")
        change.undone = True
        self._rewrite_changes(changes)
        return ToolObservation.success(f"Undid workspace change {change_id}.", artifacts=[str(target)])

    async def run_command(self, argv: list[str], timeout_seconds: int = 120) -> ToolObservation:
        if not argv or not isinstance(argv[0], str):
            return ToolObservation.error(
                "Command argv is empty.", "A command requires an executable.",
                "Supply an argv array beginning with an executable.", "Stop if shell syntax is required.",
            )
        executable = Path(argv[0]).name
        denied = {"rm", "sudo", "su", "dd", "mkfs", "sh", "bash", "zsh", "curl", "wget", "ssh", "scp"}
        allowed = {"python", "python3", "pytest", "node", "npm", "git", "ruff", "flake8", "cargo", "go", "make"}
        if executable in denied or executable not in allowed:
            return ToolObservation.error(
                f"Executable is outside the verification profile: {executable}",
                "The canonical command tool permits only known project build, test, lint, and Git inspection executables.",
                "Use a purpose-built typed tool or extend the explicit execution profile.",
                "Stop before invoking a shell, network client, privilege tool, or destructive utility.",
                data={"allowed_executables": sorted(allowed)},
            )
        if executable == "git" and len(argv) > 1 and argv[1] not in {"status", "diff", "log", "show", "branch", "rev-parse", "ls-files"}:
            return ToolObservation.error(
                f"Git subcommand is outside the read-only profile: {argv[1]}",
                "The generic command tool does not perform Git mutations.",
                "Use a dedicated typed Git tool with an explicit approval contract.",
                "Stop before push, reset, checkout, commit, merge, or rebase.",
            )
        for argument in argv[1:]:
            if argument.startswith("/"):
                try:
                    self.resolve(argument)
                except ValueError:
                    return ToolObservation.error(
                        "Command argument escapes the project root.",
                        f"Absolute path {argument!r} is outside the active project.",
                        "Use a project-contained path.", "Stop if external filesystem access is required.",
                    )
        process = await asyncio.create_subprocess_exec(
            *argv, cwd=str(self.root), stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE,
        )
        try:
            stdout, stderr = await asyncio.wait_for(process.communicate(), timeout=timeout_seconds)
        except asyncio.TimeoutError:
            process.kill()
            await process.wait()
            return ToolObservation.error(
                f"Command timed out after {timeout_seconds}s.", "The child process exceeded its bounded runtime.",
                "Narrow the command scope and retry.", "Stop if the same command hangs again.",
            )
        output = (stdout + stderr).decode("utf-8", errors="replace")
        output = output[-32_000:]
        data = {"argv": argv, "exit_code": process.returncode, "output": output}
        if process.returncode == 0:
            data["execution_profile"] = "project-verification-v1"
            return ToolObservation.success(f"Command passed: {' '.join(argv)}", data=data)
        return ToolObservation.error(
            f"Command failed with exit code {process.returncode}.",
            "The child process reported failure.", "Fix the first concrete error and retry the same command.",
            "Stop when credentials, external state, or destructive action is required.", data=data,
        )

    def register_tools(self, registry: ToolRegistry) -> None:
        registry.register(ToolSpec(
            "read_file", "Read one project-contained text file.",
            {"type": "object", "properties": {"path": {"type": "string"}}, "required": ["path"], "additionalProperties": False},
        ), lambda args: self.read_file(str(args["path"])))
        registry.register(ToolSpec(
            "list_files", "List one project-contained directory.",
            {"type": "object", "properties": {"path": {"type": "string"}}, "additionalProperties": False},
        ), lambda args: self.list_files(str(args.get("path", "."))))
        registry.register(ToolSpec(
            "patch_file", "Apply one exact, transactional text replacement or create a new file.",
            {"type": "object", "properties": {
                "path": {"type": "string"}, "old_text": {"type": "string"},
                "new_text": {"type": "string"}, "expected_sha256": {"type": "string"},
            }, "required": ["path", "old_text", "new_text"], "additionalProperties": False},
            mutates=True, risk="moderate", capabilities=("project files",),
        ), lambda args: self.patch_file(
            str(args["path"]), str(args["old_text"]), str(args["new_text"]), str(args.get("expected_sha256", "")),
        ))
        registry.register(ToolSpec(
            "run_command", "Run a bounded argv command without a shell.",
            {"type": "object", "properties": {
                "argv": {"type": "array"}, "timeout_seconds": {"type": "integer"},
            }, "required": ["argv"], "additionalProperties": False},
            mutates=True, risk="high", timeout_seconds=305, capabilities=("project-scoped verification processes",),
        ), lambda args: self.run_command(
            [str(item) for item in args["argv"]], int(args.get("timeout_seconds", 120)),
        ))
