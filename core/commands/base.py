"""
CASPER Command Base System
Production-grade command framework with structured results and ReAct integration.
Zero tolerance for placeholders or mocks - all commands return real data.
"""

from dataclasses import dataclass, field
from typing import Any, Dict, Optional, List
from abc import ABC, abstractmethod
from datetime import datetime
import traceback
from uuid import uuid4


@dataclass
class CommandResult:
    """
    Every command MUST return this structured result.
    Zero tolerance for print-only commands - all must return data.
    """
    success: bool
    output: str
    data: Dict[str, Any] = field(default_factory=dict)
    error: Optional[str] = None
    reasoning: Optional[List[str]] = None
    execution_id: str = field(default_factory=lambda: str(uuid4()))
    timestamp: str = field(default_factory=lambda: datetime.utcnow().isoformat() + "Z")
    command_name: str = ""
    args: str = ""

    def __post_init__(self):
        """Ensure data integrity"""
        if not isinstance(self.data, dict):
            self.data = {}
        if self.reasoning is None:
            self.reasoning = []


class CommandError(Exception):
    """Base exception for command execution errors"""
    def __init__(self, message: str, command_name: str = "", args: str = ""):
        super().__init__(message)
        self.command_name = command_name
        self.args = args


class BaseCommand(ABC):
    """
    All commands inherit from this base class.
    Enforces structured execution with ReAct reasoning.
    """

    def __init__(self, name: str):
        self.name = name
        self.description = ""
        self.usage = ""
        self.category = "General"

    @abstractmethod
    async def execute(self, args: str, context: Any = None) -> CommandResult:
        """
        Execute the command with ReAct reasoning pattern:
        1. Reason: Analyze what needs to be done
        2. Act: Perform the action
        3. Observe: Capture results

        MUST return CommandResult - never just print.
        """
        raise NotImplementedError

    async def safe_execute(self, args: str, context: Any = None) -> CommandResult:
        """
        Wrapper that ensures all commands return CommandResult even on error.
        Implements zero-tolerance error handling.
        """
        reasoning = []

        try:
            # REASON phase
            reasoning.append(f"REASON: Executing {self.name} command with args: {args}")

            # Validate input
            if not self._validate_input(args):
                return CommandResult(
                    success=False,
                    output="Invalid input provided",
                    error=f"Input validation failed for command {self.name}",
                    reasoning=reasoning,
                    command_name=self.name,
                    args=args
                )

            reasoning.append(f"REASON: Input validated successfully")

            # ACT phase - execute the actual command
            reasoning.append(f"ACT: Beginning execution of {self.name}")
            result = await self.execute(args, context)

            # OBSERVE phase - ensure result structure
            if not isinstance(result, CommandResult):
                reasoning.append(f"OBSERVE: Command returned invalid result type, wrapping")
                return CommandResult(
                    success=False,
                    output=str(result) if result else "Command returned None",
                    error=f"Command {self.name} did not return CommandResult",
                    reasoning=reasoning,
                    command_name=self.name,
                    args=args
                )

            # Enhance result with metadata
            result.reasoning = (result.reasoning or []) + reasoning
            result.command_name = self.name
            result.args = args

            reasoning.append(f"OBSERVE: Command completed successfully with {len(result.data)} data items")
            return result

        except Exception as e:
            reasoning.append(f"OBSERVE: Command failed with error: {str(e)}")
            return CommandResult(
                success=False,
                output=f"Command {self.name} failed",
                error=str(e),
                data={"traceback": traceback.format_exc()},
                reasoning=reasoning,
                command_name=self.name,
                args=args
            )

    def _validate_input(self, args: str) -> bool:
        """
        Override in subclasses to add specific validation.
        Default implementation allows any input.
        """
        return True

    def get_help(self) -> Dict[str, str]:
        """Return help information for this command"""
        return {
            "name": self.name,
            "description": self.description,
            "usage": self.usage,
            "category": self.category
        }


class CommandRegistry:
    """
    Registry for all transformed commands.
    Enforces that all commands return CommandResult.
    """

    def __init__(self):
        self.commands: Dict[str, BaseCommand] = {}

    def register(self, command: BaseCommand):
        """Register a command in the registry"""
        self.commands[command.name] = command

    def get_command(self, name: str) -> Optional[BaseCommand]:
        """Get a command by name"""
        return self.commands.get(name.lstrip('/'))

    async def execute_command(self, command_name: str, args: str, context: Any = None) -> CommandResult:
        """
        Execute a command by name, ensuring it returns CommandResult.
        Zero tolerance for commands that don't follow the pattern.
        """
        command = self.get_command(command_name)
        if not command:
            return CommandResult(
                success=False,
                output=f"Command not found: {command_name}",
                error=f"Unknown command: {command_name}",
                command_name=command_name,
                args=args
            )

        return await command.safe_execute(args, context)

    def list_commands(self) -> List[Dict[str, str]]:
        """List all registered commands with their metadata"""
        return [cmd.get_help() for cmd in self.commands.values()]


# Global registry instance
command_registry = CommandRegistry()