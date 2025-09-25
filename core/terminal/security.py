"""
Terminal Security Middleware for CASPER Prime.
Provides comprehensive security for terminal commands including:
- Command whitelisting and validation
- Process sandboxing and isolation
- Security audit logging
- Risk assessment and blocking
"""

import asyncio
import json
import logging
import re
import shlex
import subprocess
from datetime import datetime, timedelta
from enum import Enum
from pathlib import Path
from typing import Dict, List, Optional, Set, Union, Any, Callable
from uuid import uuid4
import hashlib
import os
import tempfile

logger = logging.getLogger(__name__)


class SecurityLevel(Enum):
    """Security levels for command execution."""
    SAFE = "safe"           # Safe commands that pose no security risk
    RESTRICTED = "restricted"  # Commands that require validation
    DANGEROUS = "dangerous"    # Commands that require approval
    BLOCKED = "blocked"        # Commands that are never allowed


class CommandRisk(Enum):
    """Risk assessment levels for commands."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class SecurityViolation(Exception):
    """Raised when a security violation is detected."""
    def __init__(self, message: str, command: str, risk_level: CommandRisk):
        super().__init__(message)
        self.command = command
        self.risk_level = risk_level


class AuditEvent:
    """Represents a security audit event."""

    def __init__(self, event_type: str, command: str, session_id: str,
                 user_id: Optional[str] = None, risk_level: CommandRisk = CommandRisk.LOW,
                 allowed: bool = True, reason: Optional[str] = None):
        self.event_id = str(uuid4())
        self.timestamp = datetime.now()
        self.event_type = event_type
        self.command = command
        self.session_id = session_id
        self.user_id = user_id
        self.risk_level = risk_level
        self.allowed = allowed
        self.reason = reason

    def to_dict(self) -> Dict[str, Any]:
        """Convert audit event to dictionary for logging."""
        return {
            "event_id": self.event_id,
            "timestamp": self.timestamp.isoformat(),
            "event_type": self.event_type,
            "command": self.command,
            "session_id": self.session_id,
            "user_id": self.user_id,
            "risk_level": self.risk_level.value,
            "allowed": self.allowed,
            "reason": self.reason
        }


class SecurityConfig:
    """Security configuration for terminal commands."""

    def __init__(self):
        self.safe_commands: Set[str] = {
            # Basic file operations
            "ls", "cat", "head", "tail", "less", "more", "file", "stat", "du", "df",
            # Directory navigation
            "pwd", "cd", "find", "locate", "which", "whereis",
            # Text processing
            "grep", "awk", "sed", "sort", "uniq", "wc", "cut", "tr",
            # CASPER specific commands
            "casper", "poetry", "pytest", "black", "flake8", "mypy",
            # Version control (read-only)
            "git status", "git log", "git show", "git diff", "git branch",
            # System info (read-only)
            "ps", "top", "whoami", "id", "date", "uptime", "uname",
            # Development tools
            "npm", "yarn", "node", "python", "python3", "pip", "pip3"
        }

        self.restricted_commands: Set[str] = {
            # File modifications (require validation)
            "touch", "mkdir", "rmdir", "cp", "mv", "chmod", "chown",
            # Git operations
            "git add", "git commit", "git push", "git pull", "git merge", "git rebase",
            # Package management
            "npm install", "yarn install", "pip install", "poetry install",
            # Build tools
            "make", "cmake", "docker build"
        }

        self.dangerous_commands: Set[str] = {
            # System modifications
            "sudo", "su", "passwd", "useradd", "userdel", "usermod",
            # Network operations
            "curl", "wget", "ssh", "scp", "rsync", "netcat", "nc",
            # Process control
            "kill", "killall", "pkill", "nohup", "screen", "tmux"
        }

        self.blocked_commands: Set[str] = {
            # Destructive operations
            "rm", "dd", "mkfs", "fdisk", "parted",
            # System control
            "reboot", "shutdown", "halt", "poweroff",
            # Security bypasses
            "exec", "eval", "source", ".",
            # Remote access
            "ftp", "telnet", "rsh", "rlogin"
        }

        # Regex patterns for additional security checks
        self.dangerous_patterns: List[re.Pattern] = [
            re.compile(r'rm\s+.*-r.*'),  # Recursive delete
            re.compile(r'>\s*/dev/'),     # Writing to device files
            re.compile(r'\|\s*sh\b'),     # Piping to shell
            re.compile(r'`.*`'),          # Command substitution
            re.compile(r'\$\(.*\)'),      # Command substitution
            re.compile(r'&&|;|\|'),       # Command chaining
            re.compile(r'<\s*\('),        # Process substitution
        ]

        # File path restrictions
        self.allowed_paths: Set[str] = {
            str(Path.cwd()),  # Current working directory
            str(Path.home()),  # User home directory
            "/tmp",
            "/var/tmp"
        }

        self.blocked_paths: Set[str] = {
            "/etc", "/bin", "/sbin", "/usr/bin", "/usr/sbin",
            "/boot", "/dev", "/proc", "/sys", "/root"
        }


class SecurityMiddleware:
    """Main security middleware for terminal commands."""

    def __init__(self, config: Optional[SecurityConfig] = None,
                 audit_callback: Optional[Callable[[AuditEvent], None]] = None):
        self.config = config or SecurityConfig()
        self.audit_callback = audit_callback
        self.audit_log: List[AuditEvent] = []
        self.session_contexts: Dict[str, Dict[str, Any]] = {}

        # Create audit log directory
        self.audit_dir = Path.cwd() / ".casper" / "security" / "audit"
        self.audit_dir.mkdir(parents=True, exist_ok=True)

    async def validate_command(self, command: str, session_id: str,
                              user_id: Optional[str] = None) -> bool:
        """
        Validate a command for security compliance.

        Args:
            command: The command to validate
            session_id: Terminal session ID
            user_id: Optional user identifier

        Returns:
            bool: True if command is allowed, False otherwise

        Raises:
            SecurityViolation: If command poses security risk
        """
        command = command.strip()
        if not command:
            return True

        # Parse command components
        try:
            parsed = shlex.split(command)
            base_command = parsed[0] if parsed else ""
        except ValueError:
            # Invalid shell syntax
            self._log_security_event("INVALID_SYNTAX", command, session_id, user_id,
                                   CommandRisk.HIGH, False, "Invalid shell syntax")
            raise SecurityViolation("Invalid shell syntax", command, CommandRisk.HIGH)

        # Assess command risk level
        risk_level = self._assess_command_risk(command, parsed)

        # Check security level
        security_level = self._get_security_level(base_command, command)

        # Apply security rules
        allowed = await self._apply_security_rules(command, parsed, security_level, risk_level)

        # Log the security event
        self._log_security_event("COMMAND_VALIDATION", command, session_id, user_id,
                               risk_level, allowed, f"Security level: {security_level.value}")

        if not allowed:
            raise SecurityViolation(f"Command blocked by security policy", command, risk_level)

        return True

    def _assess_command_risk(self, command: str, parsed: List[str]) -> CommandRisk:
        """Assess the risk level of a command."""
        base_command = parsed[0] if parsed else ""

        # Check for blocked commands (critical risk)
        if base_command in self.config.blocked_commands:
            return CommandRisk.CRITICAL

        # Check for dangerous patterns
        for pattern in self.config.dangerous_patterns:
            if pattern.search(command):
                return CommandRisk.HIGH

        # Check for dangerous commands
        if base_command in self.config.dangerous_commands:
            return CommandRisk.HIGH

        # Check for restricted commands
        if base_command in self.config.restricted_commands:
            return CommandRisk.MEDIUM

        # Check for path-based risks
        for arg in parsed[1:]:
            if self._is_dangerous_path(arg):
                return CommandRisk.HIGH

        return CommandRisk.LOW

    def _get_security_level(self, base_command: str, full_command: str) -> SecurityLevel:
        """Determine the security level for a command."""
        # Check blocked commands first
        if base_command in self.config.blocked_commands:
            return SecurityLevel.BLOCKED

        # Check for dangerous patterns
        for pattern in self.config.dangerous_patterns:
            if pattern.search(full_command):
                return SecurityLevel.BLOCKED

        # Check dangerous commands
        if base_command in self.config.dangerous_commands:
            return SecurityLevel.DANGEROUS

        # Check restricted commands
        if base_command in self.config.restricted_commands:
            return SecurityLevel.RESTRICTED

        # Check safe commands
        if base_command in self.config.safe_commands:
            return SecurityLevel.SAFE

        # Default to restricted for unknown commands
        return SecurityLevel.RESTRICTED

    async def _apply_security_rules(self, command: str, parsed: List[str],
                                  security_level: SecurityLevel, risk_level: CommandRisk) -> bool:
        """Apply security rules based on command and risk level."""

        # Always block blocked commands
        if security_level == SecurityLevel.BLOCKED:
            return False

        # Always allow safe commands with low risk
        if security_level == SecurityLevel.SAFE and risk_level == CommandRisk.LOW:
            return True

        # For restricted commands, perform additional checks
        if security_level == SecurityLevel.RESTRICTED:
            return await self._validate_restricted_command(command, parsed, risk_level)

        # For dangerous commands, require explicit approval (for now, block)
        if security_level == SecurityLevel.DANGEROUS:
            return False  # Could be extended to request approval

        return True

    async def _validate_restricted_command(self, command: str, parsed: List[str],
                                         risk_level: CommandRisk) -> bool:
        """Additional validation for restricted commands."""
        base_command = parsed[0]

        # File operations - check paths
        if base_command in ["cp", "mv", "chmod", "chown", "mkdir", "rmdir"]:
            for arg in parsed[1:]:
                if self._is_dangerous_path(arg):
                    return False

        # Git operations - ensure we're in a git repository
        if base_command == "git":
            if not self._is_git_repository():
                return False

        # Package installations - limit to known safe packages
        if base_command in ["pip", "npm", "yarn"] and "install" in parsed:
            return self._validate_package_installation(parsed)

        return True

    def _is_dangerous_path(self, path: str) -> bool:
        """Check if a path is considered dangerous."""
        if not path or path.startswith('-'):  # Skip options
            return False

        try:
            resolved_path = Path(path).resolve()
            path_str = str(resolved_path)

            # Check blocked paths
            for blocked_path in self.config.blocked_paths:
                if path_str.startswith(blocked_path):
                    return True

            return False
        except (OSError, ValueError):
            # If we can't resolve the path, consider it dangerous
            return True

    def _is_git_repository(self) -> bool:
        """Check if current directory is in a git repository."""
        try:
            subprocess.run(["git", "rev-parse", "--git-dir"],
                         check=True, capture_output=True)
            return True
        except (subprocess.CalledProcessError, FileNotFoundError):
            return False

    def _validate_package_installation(self, parsed: List[str]) -> bool:
        """Validate package installation commands."""
        # For now, be conservative and only allow known CASPER dependencies
        known_safe_packages = {
            "fastapi", "uvicorn", "websockets", "rich", "pydantic",
            "python-dotenv", "asyncio", "pathlib", "typing-extensions",
            "pytest", "black", "flake8", "mypy", "poetry"
        }

        for arg in parsed:
            if arg not in known_safe_packages and not arg.startswith('-'):
                return False

        return True

    def _log_security_event(self, event_type: str, command: str, session_id: str,
                           user_id: Optional[str], risk_level: CommandRisk,
                           allowed: bool, reason: Optional[str] = None):
        """Log a security event for audit purposes."""
        event = AuditEvent(event_type, command, session_id, user_id, risk_level, allowed, reason)

        # Add to in-memory log
        self.audit_log.append(event)

        # Write to audit file
        self._write_audit_event(event)

        # Call audit callback if provided
        if self.audit_callback:
            try:
                self.audit_callback(event)
            except Exception as e:
                logger.error(f"Error in audit callback: {e}")

        # Log to system logger
        log_level = logging.WARNING if not allowed or risk_level in [CommandRisk.HIGH, CommandRisk.CRITICAL] else logging.INFO
        logger.log(log_level, f"Security event: {event_type} - Command: {command[:100]} - Allowed: {allowed}")

    def _write_audit_event(self, event: AuditEvent):
        """Write audit event to file."""
        try:
            # Create daily audit log file
            log_date = event.timestamp.strftime("%Y-%m-%d")
            audit_file = self.audit_dir / f"security-{log_date}.jsonl"

            # Append event to file
            with open(audit_file, 'a', encoding='utf-8') as f:
                f.write(json.dumps(event.to_dict()) + '\n')

        except Exception as e:
            logger.error(f"Failed to write audit event to file: {e}")

    async def create_sandbox(self, session_id: str) -> Dict[str, Any]:
        """Create a sandboxed environment for command execution."""
        sandbox_dir = Path(tempfile.mkdtemp(prefix=f"casper-sandbox-{session_id}-"))

        # Create sandbox context
        sandbox_context = {
            "session_id": session_id,
            "sandbox_dir": str(sandbox_dir),
            "created_at": datetime.now(),
            "allowed_paths": [str(sandbox_dir)],
            "env_vars": {
                "HOME": str(sandbox_dir),
                "TMPDIR": str(sandbox_dir / "tmp"),
                "PATH": "/usr/local/bin:/usr/bin:/bin",  # Restricted PATH
                "SHELL": "/bin/bash",
                "TERM": "xterm-256color"
            }
        }

        # Create necessary directories in sandbox
        (sandbox_dir / "tmp").mkdir(parents=True, exist_ok=True)
        (sandbox_dir / "work").mkdir(parents=True, exist_ok=True)

        # Store sandbox context
        self.session_contexts[session_id] = sandbox_context

        self._log_security_event("SANDBOX_CREATED", f"Created sandbox at {sandbox_dir}",
                               session_id, None, CommandRisk.LOW, True)

        return sandbox_context

    async def cleanup_sandbox(self, session_id: str):
        """Clean up sandbox environment."""
        context = self.session_contexts.get(session_id)
        if not context:
            return

        try:
            sandbox_dir = Path(context["sandbox_dir"])
            if sandbox_dir.exists():
                import shutil
                shutil.rmtree(sandbox_dir, ignore_errors=True)

            del self.session_contexts[session_id]

            self._log_security_event("SANDBOX_CLEANUP", f"Cleaned up sandbox",
                                   session_id, None, CommandRisk.LOW, True)
        except Exception as e:
            logger.error(f"Failed to cleanup sandbox for session {session_id}: {e}")

    def get_audit_summary(self, hours: int = 24) -> Dict[str, Any]:
        """Get audit summary for the specified time period."""
        cutoff_time = datetime.now() - timedelta(hours=hours)
        recent_events = [event for event in self.audit_log if event.timestamp >= cutoff_time]

        summary = {
            "total_events": len(recent_events),
            "allowed_commands": len([e for e in recent_events if e.allowed]),
            "blocked_commands": len([e for e in recent_events if not e.allowed]),
            "risk_levels": {
                "low": len([e for e in recent_events if e.risk_level == CommandRisk.LOW]),
                "medium": len([e for e in recent_events if e.risk_level == CommandRisk.MEDIUM]),
                "high": len([e for e in recent_events if e.risk_level == CommandRisk.HIGH]),
                "critical": len([e for e in recent_events if e.risk_level == CommandRisk.CRITICAL])
            },
            "most_common_commands": self._get_most_common_commands(recent_events),
            "security_violations": [e.to_dict() for e in recent_events if not e.allowed]
        }

        return summary

    def _get_most_common_commands(self, events: List[AuditEvent]) -> List[Dict[str, Any]]:
        """Get most commonly used commands from events."""
        command_counts = {}
        for event in events:
            base_cmd = event.command.split()[0] if event.command else "unknown"
            command_counts[base_cmd] = command_counts.get(base_cmd, 0) + 1

        # Sort by count and return top 10
        sorted_commands = sorted(command_counts.items(), key=lambda x: x[1], reverse=True)[:10]
        return [{"command": cmd, "count": count} for cmd, count in sorted_commands]