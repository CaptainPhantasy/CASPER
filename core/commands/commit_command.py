"""
Transformed Commit Command
Production-ready git operations with ReAct reasoning and structured results.
Zero tolerance for print-only behavior - returns real git operation data.
"""

import subprocess
import os
from pathlib import Path
from typing import Any, Dict, List, Optional
from core.commands.base import BaseCommand, CommandResult
from core.commands.react_engine import ReActEngine
from datetime import datetime


class CommitCommand(BaseCommand):
    """
    Transform the /commit command to return structured git operation results.
    Performs real git operations with proper validation and status tracking.
    """

    def __init__(self):
        super().__init__(name="commit")
        self.description = (
            "Create git commits with automatic staging and intelligent commit messages"
        )
        self.usage = "/commit [message] or /commit (for auto-generated message)"
        self.category = "Git Operations"
        self.react_engine = ReActEngine()

    def _validate_input(self, args: str) -> bool:
        """Validate commit command input - args can be empty for auto-generated messages"""
        return True  # Empty args are allowed for auto-generated commit messages

    async def execute(self, args: str, context: Any = None) -> CommandResult:
        """
        Execute git commit with ReAct reasoning pattern.
        MUST return CommandResult with actual git operation data.
        """
        # Clear previous reasoning
        self.react_engine.clear_reasoning_chain()

        try:
            # REASON phase
            reasoning = self.react_engine.reason(
                (
                    f"Execute git commit with message: '{args}'"
                    if args
                    else "Execute git commit with auto-generated message"
                ),
                {"working_directory": os.getcwd(), "has_custom_message": bool(args)},
            )

            # Check if we're in a git repository
            if not await self._is_git_repository():
                return CommandResult(
                    success=False,
                    output="Not in a git repository",
                    error="Current directory is not a git repository",
                    data={
                        "working_directory": os.getcwd(),
                        "git_repository": False,
                        "timestamp": datetime.utcnow().isoformat() + "Z",
                    },
                    reasoning=self.react_engine.get_reasoning_chain(),
                )

            # ACT phase - perform git operations
            action_result = self.react_engine.act(
                "Performing git status check and commit operations",
                {
                    "message": args if args else "auto-generated",
                    "operation": "git_commit_sequence",
                },
            )

            # Execute the git commit process
            commit_data = await self._perform_commit(args.strip() if args else None)

            # OBSERVE phase
            if commit_data["success"]:
                observation = self.react_engine.observe(
                    f"Git commit completed successfully: {commit_data['commit_hash']}",
                    commit_data,
                )
            else:
                observation = self.react_engine.observe(
                    f"Git commit failed: {commit_data.get('error', 'Unknown error')}",
                    commit_data,
                )

            return CommandResult(
                success=commit_data["success"],
                output=commit_data["summary"],
                data={
                    "git_operation": commit_data,
                    "reasoning_summary": self.react_engine.summarize_reasoning(),
                    "timestamp": datetime.utcnow().isoformat() + "Z",
                },
                error=commit_data.get("error"),
                reasoning=self.react_engine.get_reasoning_chain(),
            )

        except Exception as e:
            # OBSERVE phase - execution error
            self.react_engine.observe(
                f"Git commit execution encountered error: {str(e)}",
                {"error": str(e), "message": args},
            )

            return CommandResult(
                success=False,
                output=f"Git commit error: {str(e)}",
                error=str(e),
                data={
                    "message": args,
                    "error_details": str(e),
                    "reasoning_summary": self.react_engine.summarize_reasoning(),
                    "timestamp": datetime.utcnow().isoformat() + "Z",
                },
                reasoning=self.react_engine.get_reasoning_chain(),
            )

    async def _is_git_repository(self) -> bool:
        """Check if current directory is a git repository"""
        try:
            result = subprocess.run(
                ["git", "rev-parse", "--git-dir"],
                capture_output=True,
                text=True,
                timeout=5,
            )
            return result.returncode == 0
        except Exception:
            return False

    async def _perform_commit(
        self, custom_message: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Perform the actual git commit operations.
        Returns real git operation data - not placeholders.
        """
        try:
            # Step 1: Get git status
            status_data = await self._get_git_status()
            if not status_data["success"]:
                return status_data

            # Step 2: Stage changes if there are unstaged changes
            if status_data["unstaged_files"]:
                stage_data = await self._stage_changes()
                if not stage_data["success"]:
                    return stage_data
            else:
                stage_data = {"staged": 0, "message": "No unstaged files to stage"}

            # Step 3: Check if there are staged changes to commit
            if not status_data["staged_files"] and not status_data["unstaged_files"]:
                return {
                    "success": False,
                    "error": "No changes to commit",
                    "summary": "Working directory clean - nothing to commit",
                    "status": status_data,
                    "staged": stage_data,
                }

            # Step 4: Generate commit message if not provided
            commit_message = custom_message or await self._generate_commit_message(
                status_data
            )

            # Step 5: Perform the commit
            commit_result = await self._execute_commit(commit_message)

            return {
                "success": commit_result["success"],
                "commit_hash": commit_result.get("commit_hash"),
                "commit_message": commit_message,
                "files_committed": status_data["staged_files"]
                + status_data["unstaged_files"],
                "status_before": status_data,
                "staging_result": stage_data,
                "commit_result": commit_result,
                "summary": commit_result["message"],
                "error": commit_result.get("error"),
            }

        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "summary": f"Commit operation failed: {str(e)}",
            }

    async def _get_git_status(self) -> Dict[str, Any]:
        """Get current git repository status"""
        try:
            result = subprocess.run(
                ["git", "status", "--porcelain"],
                capture_output=True,
                text=True,
                timeout=10,
            )

            if result.returncode != 0:
                return {
                    "success": False,
                    "error": f"Git status failed: {result.stderr}",
                    "staged_files": [],
                    "unstaged_files": [],
                }

            # Parse status output
            lines = result.stdout.strip().split("\n") if result.stdout.strip() else []
            staged_files = []
            unstaged_files = []

            for line in lines:
                if len(line) >= 2:
                    staged_status = line[0]
                    unstaged_status = line[1]
                    filename = line[3:].strip()

                    if staged_status != " " and staged_status != "?":
                        staged_files.append({"file": filename, "status": staged_status})

                    if unstaged_status != " " and unstaged_status != "?":
                        unstaged_files.append(
                            {"file": filename, "status": unstaged_status}
                        )
                    elif staged_status == "?" and unstaged_status == "?":
                        unstaged_files.append({"file": filename, "status": "untracked"})

            return {
                "success": True,
                "staged_files": staged_files,
                "unstaged_files": unstaged_files,
                "total_changes": len(staged_files) + len(unstaged_files),
            }

        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "staged_files": [],
                "unstaged_files": [],
            }

    async def _stage_changes(self) -> Dict[str, Any]:
        """Stage all unstaged changes"""
        try:
            # Add all changes
            result = subprocess.run(
                ["git", "add", "."], capture_output=True, text=True, timeout=30
            )

            if result.returncode != 0:
                return {
                    "success": False,
                    "error": f"Git add failed: {result.stderr}",
                    "staged": 0,
                }

            return {
                "success": True,
                "staged": "all_changes",
                "message": "All changes staged successfully",
            }

        except Exception as e:
            return {"success": False, "error": str(e), "staged": 0}

    async def _generate_commit_message(self, status_data: Dict[str, Any]) -> str:
        """Generate an intelligent commit message based on changes"""
        try:
            # Get list of changed files
            all_files = [f["file"] for f in status_data["staged_files"]] + [
                f["file"] for f in status_data["unstaged_files"]
            ]

            # Analyze file types and changes
            extensions = {}
            for filepath in all_files:
                ext = Path(filepath).suffix.lower()
                extensions[ext] = extensions.get(ext, 0) + 1

            # Generate message based on file types
            if ".py" in extensions and extensions[".py"] > 2:
                message = f"Update Python code ({extensions['.py']} files)"
            elif ".md" in extensions:
                message = "Update documentation"
            elif ".json" in extensions or ".yaml" in extensions or ".yml" in extensions:
                message = "Update configuration files"
            elif ".js" in extensions or ".ts" in extensions or ".tsx" in extensions:
                message = f"Update frontend code ({len(all_files)} files)"
            elif len(all_files) == 1:
                message = f"Update {Path(all_files[0]).name}"
            else:
                message = f"Update {len(all_files)} files"

            # Add automation signature
            message += f"\n\n🤖 Generated with [Claude Code](https://claude.ai/code)\n\nCo-Authored-By: Claude <noreply@anthropic.com>"

            return message

        except Exception:
            return "Automated commit\n\n🤖 Generated with [Claude Code](https://claude.ai/code)\n\nCo-Authored-By: Claude <noreply@anthropic.com>"

    async def _execute_commit(self, message: str) -> Dict[str, Any]:
        """Execute the git commit"""
        try:
            result = subprocess.run(
                ["git", "commit", "-m", message],
                capture_output=True,
                text=True,
                timeout=30,
            )

            if result.returncode != 0:
                return {
                    "success": False,
                    "error": result.stderr,
                    "message": f"Git commit failed: {result.stderr}",
                }

            # Extract commit hash from output
            commit_hash = None
            if result.stdout:
                lines = result.stdout.split("\n")
                for line in lines:
                    if "[" in line and "]" in line:
                        # Look for pattern like "[main abc1234]"
                        parts = line.split("[")
                        if len(parts) > 1:
                            hash_part = parts[1].split("]")[0]
                            if " " in hash_part:
                                commit_hash = hash_part.split(" ")[-1]
                        break

            return {
                "success": True,
                "commit_hash": commit_hash,
                "message": f"Commit created successfully: {commit_hash}",
                "output": result.stdout,
            }

        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "message": f"Commit execution failed: {str(e)}",
            }
