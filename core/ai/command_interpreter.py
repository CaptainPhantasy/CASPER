"""
Central AI Command Interpreter for CASPER
This is the brain that interprets ALL user input and directs the system accordingly.
"""

import json
import os
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass
from enum import Enum

from core.services.llm import llm_service


class CommandType(Enum):
    """Types of commands CASPER can handle"""
    FILE_OPERATION = "file_operation"
    CODE_GENERATION = "code_generation"
    TESTING = "testing"
    DEBUGGING = "debugging"
    DOCUMENTATION = "documentation"
    SYSTEM_QUERY = "system_query"
    CONVERSATION = "conversation"
    UNKNOWN = "unknown"


@dataclass
class InterpretedCommand:
    """Structured representation of user intent"""
    command_type: CommandType
    action: str  # Specific action (create, modify, delete, etc.)
    targets: List[Dict[str, Any]]  # What to act on
    context: Dict[str, Any]  # Additional context
    confidence: float  # How confident the AI is in this interpretation
    raw_input: str  # Original user input
    suggested_agent: str  # Which agent should handle this


class CasperCommandInterpreter:
    """
    Central AI interpreter that understands user intent and directs CASPER.
    This is the equivalent of your (Claude's) interpretation layer.
    """

    def __init__(self):
        self.context_history: List[InterpretedCommand] = []
        self.project_context = self._load_project_context()

    def _load_project_context(self) -> Dict:
        """Load context about the current project"""
        context = {
            "project_root": os.environ.get("CASPER_PROJECT_ROOT", str(Path.cwd())),
            "project_type": None,  # Could detect: react, python, etc.
            "existing_files": [],
            "recent_operations": []
        }

        # Detect project type
        root = Path(context["project_root"])
        if (root / "package.json").exists():
            context["project_type"] = "javascript"
        elif (root / "requirements.txt").exists() or (root / "pyproject.toml").exists():
            context["project_type"] = "python"

        return context

    async def interpret(self, user_input: str) -> InterpretedCommand:
        """
        Main interpretation method - the brain of CASPER.
        Takes natural language and returns structured intent.
        """

        # Build context-aware prompt
        prompt = self._build_interpretation_prompt(user_input)

        try:
            response = await llm_service.complete(prompt=prompt, max_tokens=800)

            if response:
                return self._parse_interpretation(response, user_input)
            else:
                return self._fallback_interpretation(user_input)

        except Exception as e:
            print(f"AI interpretation failed: {e}")
            return self._fallback_interpretation(user_input)

    def _build_interpretation_prompt(self, user_input: str) -> str:
        """Build a context-aware prompt for interpretation"""

        # Include recent context
        recent_context = ""
        if self.context_history:
            recent = self.context_history[-3:]  # Last 3 commands
            recent_context = "Recent commands:\n"
            for cmd in recent:
                recent_context += f"- {cmd.action}: {cmd.raw_input[:50]}...\n"

        prompt = f"""
        You are the AI interpreter for CASPER, a development assistant system.
        Analyze the user's input and determine their intent.

        Current project type: {self.project_context.get('project_type', 'unknown')}
        Project root: {self.project_context['project_root']}

        {recent_context}

        User input: "{user_input}"

        Determine:
        1. Command type (file_operation, code_generation, testing, debugging, documentation, system_query, conversation)
        2. Specific action (create, modify, delete, run, analyze, etc.)
        3. Targets (files, folders, code elements, etc.)
        4. Any additional context

        Return a JSON object with this structure:
        {{
            "command_type": "file_operation|code_generation|testing|etc",
            "action": "specific action verb",
            "confidence": 0.0-1.0,
            "targets": [
                {{
                    "type": "file|folder|component|function|etc",
                    "name": "name or identifier",
                    "path": "full path if applicable",
                    "content": "content if provided",
                    "details": {{}}
                }}
            ],
            "context": {{
                "location": "where to perform action",
                "requirements": [],
                "constraints": [],
                "related_files": []
            }},
            "suggested_agent": "worker|frontend_prime|backend_prime|testing_prime|devops_prime|master",
            "reasoning": "brief explanation of interpretation"
        }}

        Examples:

        Input: "create a new React component called UserProfile"
        Output: {{"command_type": "code_generation", "action": "create", "confidence": 0.95, "targets": [{{"type": "component", "name": "UserProfile", "path": "src/components/UserProfile.jsx", "details": {{"framework": "react"}}}}], "suggested_agent": "frontend_prime"}}

        Input: "make a folder for tests"
        Output: {{"command_type": "file_operation", "action": "create", "confidence": 0.9, "targets": [{{"type": "folder", "name": "tests", "path": "tests"}}], "suggested_agent": "worker"}}

        Input: "debug why the login isn't working"
        Output: {{"command_type": "debugging", "action": "analyze", "confidence": 0.85, "targets": [{{"type": "feature", "name": "login"}}], "suggested_agent": "backend_prime"}}

        Return ONLY the JSON object.
        """

        return prompt

    def _parse_interpretation(self, response: str, user_input: str) -> InterpretedCommand:
        """Parse AI response into InterpretedCommand"""
        try:
            # Extract JSON from response
            import re
            json_match = re.search(r'\{.*\}', response, re.DOTALL)
            if not json_match:
                return self._fallback_interpretation(user_input)

            data = json.loads(json_match.group())

            # Map to enum
            cmd_type = CommandType.UNKNOWN
            for ct in CommandType:
                if ct.value == data.get("command_type"):
                    cmd_type = ct
                    break

            interpreted = InterpretedCommand(
                command_type=cmd_type,
                action=data.get("action", "unknown"),
                targets=data.get("targets", []),
                context=data.get("context", {}),
                confidence=float(data.get("confidence", 0.5)),
                raw_input=user_input,
                suggested_agent=data.get("suggested_agent", "worker")
            )

            # Add to history for context
            self.context_history.append(interpreted)
            if len(self.context_history) > 10:
                self.context_history.pop(0)

            return interpreted

        except Exception as e:
            print(f"Failed to parse AI interpretation: {e}")
            return self._fallback_interpretation(user_input)

    def _fallback_interpretation(self, user_input: str) -> InterpretedCommand:
        """Basic interpretation when AI fails"""
        user_lower = user_input.lower()

        # Simple keyword matching
        if any(word in user_lower for word in ["create", "make", "new", "add"]):
            if "file" in user_lower or "." in user_input:
                cmd_type = CommandType.FILE_OPERATION
                action = "create"
                suggested_agent = "worker"
            elif "folder" in user_lower or "directory" in user_lower:
                cmd_type = CommandType.FILE_OPERATION
                action = "create"
                suggested_agent = "worker"
            elif any(word in user_lower for word in ["component", "module", "class", "function"]):
                cmd_type = CommandType.CODE_GENERATION
                action = "create"
                suggested_agent = "frontend_prime" if "component" in user_lower else "backend_prime"
            else:
                cmd_type = CommandType.UNKNOWN
                action = "unknown"
                suggested_agent = "master"
        elif any(word in user_lower for word in ["test", "testing"]):
            cmd_type = CommandType.TESTING
            action = "run"
            suggested_agent = "testing_prime"
        elif any(word in user_lower for word in ["debug", "fix", "error", "bug"]):
            cmd_type = CommandType.DEBUGGING
            action = "analyze"
            suggested_agent = "backend_prime"
        else:
            cmd_type = CommandType.CONVERSATION
            action = "respond"
            suggested_agent = "master"

        return InterpretedCommand(
            command_type=cmd_type,
            action=action,
            targets=[],
            context={},
            confidence=0.3,  # Low confidence for fallback
            raw_input=user_input,
            suggested_agent=suggested_agent
        )

    def explain_interpretation(self, command: InterpretedCommand) -> str:
        """Generate human-readable explanation of interpretation"""
        explanation = f"I understood that you want to {command.action}"

        if command.targets:
            target_desc = ", ".join([
                f"{t.get('type', 'item')} '{t.get('name', 'unnamed')}'"
                for t in command.targets
            ])
            explanation += f" {target_desc}"

        if command.command_type == CommandType.FILE_OPERATION:
            explanation += " in the file system"
        elif command.command_type == CommandType.CODE_GENERATION:
            explanation += " as new code"
        elif command.command_type == CommandType.TESTING:
            explanation += " for testing"

        explanation += f" (Confidence: {command.confidence:.0%})"

        return explanation

    async def validate_interpretation(self, command: InterpretedCommand) -> Tuple[bool, str]:
        """
        Validate that the interpretation makes sense and is safe to execute.
        Returns (is_valid, explanation)
        """

        # Check confidence threshold
        if command.confidence < 0.4:
            return False, "I'm not confident enough in my interpretation. Could you rephrase?"

        # Check for dangerous operations
        if command.action in ["delete", "remove", "destroy"]:
            if command.confidence < 0.8:
                return False, "This looks like a destructive operation. Please be more specific."

        # Validate file paths don't escape project
        project_root = Path(self.project_context["project_root"])
        for target in command.targets:
            if target.get("path"):
                target_path = Path(target["path"])
                if target_path.is_absolute():
                    if not str(target_path).startswith(str(project_root)):
                        return False, f"Path {target_path} is outside the project"

        return True, "Interpretation validated"


# Global instance
command_interpreter = CasperCommandInterpreter()