"""
CASPER Brain - The central nervous system that connects AI interpretation to execution
"""

import asyncio
from typing import Optional, Dict, Any
from pathlib import Path

from core.ai.command_interpreter import (
    command_interpreter,
    CommandType,
    InterpretedCommand,
)
from core.cli import CasperCLI
from core.agents.base import ContextBundle
from core.services.llm import llm_service


class CasperBrain:
    """
    The brain of CASPER - processes all input through AI interpretation
    before executing. This is the equivalent of how Claude processes
    your commands before executing them.
    """

    def __init__(self):
        self.interpreter = command_interpreter
        self.cli = None  # Lazy init
        self.conversation_history = []

    async def initialize(self):
        """Initialize the brain and its connections"""
        if not self.cli:
            self.cli = CasperCLI()
            await self.cli.initialize()

    async def process_input(self, user_input: str) -> Dict[str, Any]:
        """
        Main entry point - process any user input through AI interpretation.
        This is like Claude's main processing loop.
        """

        # Step 1: Interpret what the user wants
        interpretation = await self.interpreter.interpret(user_input)

        # Step 2: Validate the interpretation
        is_valid, validation_msg = await self.interpreter.validate_interpretation(
            interpretation
        )

        if not is_valid:
            return {
                "success": False,
                "message": validation_msg,
                "interpretation": interpretation,
            }

        # Step 3: Explain what we're about to do (transparency)
        explanation = self.interpreter.explain_interpretation(interpretation)

        # Step 4: Route to appropriate handler
        result = await self._execute_interpretation(interpretation)

        return {
            "success": result.get("success", False),
            "message": result.get("message", ""),
            "explanation": explanation,
            "interpretation": interpretation,
            "result": result,
        }

    async def _execute_interpretation(
        self, command: InterpretedCommand
    ) -> Dict[str, Any]:
        """Execute the interpreted command through the appropriate system"""

        # Initialize CLI if needed
        if not self.cli:
            await self.initialize()

        # Route based on command type
        if command.command_type == CommandType.FILE_OPERATION:
            return await self._handle_file_operation(command)

        elif command.command_type == CommandType.CODE_GENERATION:
            return await self._handle_code_generation(command)

        elif command.command_type == CommandType.TESTING:
            return await self._handle_testing(command)

        elif command.command_type == CommandType.DEBUGGING:
            return await self._handle_debugging(command)

        elif command.command_type == CommandType.DOCUMENTATION:
            return await self._handle_documentation(command)

        elif command.command_type == CommandType.SYSTEM_QUERY:
            return await self._handle_system_query(command)

        elif command.command_type == CommandType.CONVERSATION:
            return await self._handle_conversation(command)

        else:
            return {
                "success": False,
                "message": "I don't know how to handle that type of command yet.",
            }

    async def _handle_file_operation(
        self, command: InterpretedCommand
    ) -> Dict[str, Any]:
        """Handle file system operations"""

        # Build task description for CASPER
        task_parts = []

        for target in command.targets:
            target_type = target.get("type", "item")
            name = target.get("name", "")
            path = target.get("path", name)
            content = target.get("content", "")

            if command.action == "create":
                if target_type == "file":
                    # Use just the name, not full path, to avoid confusing Worker agent
                    if content:
                        task = f"create a file called {name} with the content {content}"
                    else:
                        task = f"create a file called {name}"
                    # Add path context if it's in a subfolder
                    if "/" in path and path != name:
                        folder = "/".join(path.split("/")[:-1])
                        task += f" in the {folder} folder"
                elif target_type == "folder":
                    # Keep it simple for folder creation
                    task = f"create a folder named {name}"
                else:
                    task = f"create {name}"
                task_parts.append(task)

            elif command.action in ["modify", "edit", "update"]:
                task = f"modify the file {path}"
                if content:
                    task += f" to contain {content}"
                task_parts.append(task)

            elif command.action in ["delete", "remove"]:
                task = f"delete {target_type} {path}"
                task_parts.append(task)

        if not task_parts:
            return {"success": False, "message": "No clear file operation to perform"}

        # Execute through CASPER CLI
        results = []
        for task in task_parts:
            try:
                await self.cli.execute_task(task)
                results.append({"task": task, "success": True})
            except Exception as e:
                results.append({"task": task, "success": False, "error": str(e)})

        success = all(r["success"] for r in results)
        return {
            "success": success,
            "message": (
                "File operations completed" if success else "Some operations failed"
            ),
            "details": results,
        }

    async def _handle_code_generation(
        self, command: InterpretedCommand
    ) -> Dict[str, Any]:
        """Handle code generation requests"""

        tasks = []
        for target in command.targets:
            target_type = target.get("type", "")
            name = target.get("name", "")
            details = target.get("details", {})

            if target_type == "component" and details.get("framework") == "react":
                task = f"create a new React component called {name}"
            elif target_type == "function":
                task = f"create a new function called {name}"
            elif target_type == "class":
                task = f"create a new class called {name}"
            else:
                task = f"generate {target_type} {name}"

            tasks.append(task)

        # Use the appropriate agent
        results = []
        for task in tasks:
            try:
                await self.cli.execute_task(task, priority="high")
                results.append({"task": task, "success": True})
            except Exception as e:
                results.append({"task": task, "success": False, "error": str(e)})

        return {
            "success": all(r["success"] for r in results),
            "message": "Code generation completed",
            "details": results,
        }

    async def _handle_testing(self, command: InterpretedCommand) -> Dict[str, Any]:
        """Handle testing requests"""

        # Build testing task
        if command.action == "run":
            task = "run the test suite"
        elif command.action == "create":
            task = "create unit tests"
        else:
            task = f"{command.action} tests"

        try:
            await self.cli.execute_task(task, priority="high")
            return {"success": True, "message": "Testing task submitted"}
        except Exception as e:
            return {"success": False, "message": f"Testing failed: {e}"}

    async def _handle_debugging(self, command: InterpretedCommand) -> Dict[str, Any]:
        """Handle debugging requests"""

        targets = command.targets
        if targets:
            feature = targets[0].get("name", "system")
            task = f"debug and analyze issues with {feature}"
        else:
            task = "analyze and debug the current issues"

        try:
            await self.cli.execute_task(task, priority="high")
            return {"success": True, "message": "Debugging task initiated"}
        except Exception as e:
            return {"success": False, "message": f"Debugging failed: {e}"}

    async def _handle_documentation(
        self, command: InterpretedCommand
    ) -> Dict[str, Any]:
        """Handle documentation requests"""

        task = f"{command.action} documentation"
        if command.targets:
            target_names = [t.get("name", "") for t in command.targets]
            task += f" for {', '.join(target_names)}"

        try:
            await self.cli.execute_task(task)
            return {"success": True, "message": "Documentation task submitted"}
        except Exception as e:
            return {"success": False, "message": f"Documentation task failed: {e}"}

    async def _handle_system_query(self, command: InterpretedCommand) -> Dict[str, Any]:
        """Handle system queries (status, info, etc.)"""

        # These don't go through task execution, answer directly
        query = command.raw_input.lower()

        if "status" in query:
            # Get system status
            return {
                "success": True,
                "message": "CASPER is operational",
                "details": {
                    "agents": "ready",
                    "cli": "initialized" if self.cli else "not initialized",
                },
            }
        else:
            return {"success": True, "message": "System query received"}

    async def _handle_conversation(self, command: InterpretedCommand) -> Dict[str, Any]:
        """Handle conversational inputs"""

        # Use LLM to generate response
        prompt = f"""
        You are CASPER, an AI development assistant.
        The user said: "{command.raw_input}"

        Provide a helpful, concise response.
        """

        try:
            response = await llm_service.complete(prompt=prompt, max_tokens=500)
            return {
                "success": True,
                "message": response
                or "I understand. How can I help you with development?",
            }
        except:
            return {
                "success": True,
                "message": "I understand. How can I help you with development?",
            }

    async def shutdown(self):
        """Cleanup"""
        if self.cli:
            await self.cli.shutdown()


# Global instance
casper_brain = CasperBrain()
