"""
Transformed Task Command
Production-ready task execution with ReAct reasoning and structured results.
Zero tolerance for print-only behavior - returns real data.
"""

import asyncio
from typing import Any, Dict, Optional
from core.commands.base import BaseCommand, CommandResult
from core.commands.react_engine import ReActEngine
from datetime import datetime


class TaskCommand(BaseCommand):
    """
    Transform the /task command to return structured results.
    Integrates with existing CASPER agent system while ensuring data return.
    """

    def __init__(self):
        super().__init__(name="task")
        self.description = "Execute a task using CASPER's agent system with ReAct reasoning"
        self.usage = "/task <task_description>"
        self.category = "Agent Execution"
        self.react_engine = ReActEngine()

    def _validate_input(self, args: str) -> bool:
        """Validate task command input"""
        return bool(args.strip())

    async def execute(self, args: str, context: Any = None) -> CommandResult:
        """
        Execute task with ReAct reasoning pattern.
        MUST return CommandResult with actual data - never just print.
        """
        # Clear previous reasoning
        self.react_engine.clear_reasoning_chain()

        try:
            # REASON phase
            reasoning = self.react_engine.reason(
                f"Execute task: {args}",
                {"context_type": str(type(context)), "has_context": context is not None}
            )

            # ACT phase - integrate with existing CASPER CLI
            action_result = self.react_engine.act(
                "Delegating to CASPER agent system",
                {"task": args, "delegation_method": "casper_cli_integration"}
            )

            # Try to use existing CASPER CLI if available
            execution_data = {}
            if hasattr(context, 'execute_task'):
                # CASPER CLI context available
                try:
                    # Execute through existing system
                    await context.execute_task(args)
                    execution_data = {
                        "method": "casper_cli_delegation",
                        "task": args,
                        "status": "delegated",
                        "timestamp": datetime.utcnow().isoformat() + "Z"
                    }

                    # OBSERVE phase - successful delegation
                    observation = self.react_engine.observe(
                        "Task successfully delegated to CASPER agent system",
                        execution_data
                    )

                except Exception as e:
                    execution_data = {
                        "method": "casper_cli_delegation",
                        "task": args,
                        "status": "failed",
                        "error": str(e),
                        "timestamp": datetime.utcnow().isoformat() + "Z"
                    }

                    # OBSERVE phase - delegation failed
                    observation = self.react_engine.observe(
                        f"Task delegation failed: {str(e)}",
                        execution_data
                    )

                    return CommandResult(
                        success=False,
                        output=f"Task execution failed: {str(e)}",
                        error=str(e),
                        data=execution_data,
                        reasoning=self.react_engine.get_reasoning_chain()
                    )

            else:
                # No CASPER CLI context - create structured task plan
                task_plan = self._create_task_plan(args)
                execution_data = {
                    "method": "task_planning",
                    "task": args,
                    "plan": task_plan,
                    "status": "planned",
                    "timestamp": datetime.utcnow().isoformat() + "Z",
                    "next_steps": task_plan.get("steps", [])
                }

                # OBSERVE phase - task planned
                observation = self.react_engine.observe(
                    "Task analyzed and execution plan created",
                    execution_data
                )

            # Return structured result with all data
            return CommandResult(
                success=True,
                output=f"Task processed: {args}",
                data={
                    "task": args,
                    "execution": execution_data,
                    "reasoning_summary": self.react_engine.summarize_reasoning(),
                    "timestamp": datetime.utcnow().isoformat() + "Z"
                },
                reasoning=self.react_engine.get_reasoning_chain()
            )

        except Exception as e:
            # OBSERVE phase - execution error
            self.react_engine.observe(
                f"Task execution encountered error: {str(e)}",
                {"error": str(e), "task": args}
            )

            return CommandResult(
                success=False,
                output=f"Task execution error: {str(e)}",
                error=str(e),
                data={
                    "task": args,
                    "error_details": str(e),
                    "reasoning_summary": self.react_engine.summarize_reasoning(),
                    "timestamp": datetime.utcnow().isoformat() + "Z"
                },
                reasoning=self.react_engine.get_reasoning_chain()
            )

    def _create_task_plan(self, task: str) -> Dict[str, Any]:
        """
        Create a structured task execution plan when CASPER CLI is not available.
        Returns real planning data - not placeholders.
        """
        task_lower = task.lower()

        # Analyze task complexity
        complexity = "low"
        required_agents = []

        if any(word in task_lower for word in ["create", "build", "implement", "develop"]):
            complexity = "medium"
            required_agents.append("development_agent")

        if any(word in task_lower for word in ["analyze", "review", "audit", "check"]):
            complexity = "low"
            required_agents.append("analysis_agent")

        if any(word in task_lower for word in ["test", "debug", "fix", "troubleshoot"]):
            complexity = "medium"
            required_agents.append("testing_agent")

        if any(word in task_lower for word in ["deploy", "release", "publish", "production"]):
            complexity = "high"
            required_agents.extend(["deployment_agent", "qa_agent"])

        # Create execution steps
        steps = [
            {"step": 1, "action": "Task analysis and validation", "agent": "master_agent"},
            {"step": 2, "action": f"Execute task: {task}", "agent": required_agents[0] if required_agents else "general_agent"},
            {"step": 3, "action": "Verify completion and results", "agent": "qa_agent"}
        ]

        return {
            "task": task,
            "complexity": complexity,
            "required_agents": required_agents,
            "steps": steps,
            "estimated_duration": "5-15 minutes" if complexity == "low" else "15-45 minutes",
            "plan_created_at": datetime.utcnow().isoformat() + "Z"
        }