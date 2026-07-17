"""
Secure Command Proxy for CASPER Terminal Infrastructure.
Handles execution of CASPER CLI commands through the terminal interface with security enforcement.
"""

import asyncio
import logging
import os
import sys
import json
from typing import Dict, List, Any, Optional, Set
from pathlib import Path
from datetime import datetime
from uuid import uuid4

from core.orchestrator.coordinator import AgentCoordinator
from core.orchestrator.task_analyzer import TaskAnalyzer
from core.context.manager import ContextManager
from core.agents.base import TaskPriority, AgentStatus
from .security import SecurityMiddleware, SecurityViolation, CommandRisk

logger = logging.getLogger(__name__)


class CommandProxy:
    """Secure proxy for executing CASPER CLI commands through the terminal interface."""

    def __init__(self, security_middleware: Optional[SecurityMiddleware] = None):
        self.coordinator: Optional[AgentCoordinator] = None
        self.context_manager: Optional[ContextManager] = None
        self.task_analyzer: Optional[TaskAnalyzer] = None
        self.security = security_middleware or SecurityMiddleware()
        self._initialized = False

        # Command execution limits and security settings
        self.max_concurrent_tasks = 5
        self.active_tasks: Set[str] = set()
        self.command_rate_limits = {
            "task": {"max_per_minute": 10, "requests": []},
            "status": {"max_per_minute": 60, "requests": []},
            "analyze": {"max_per_minute": 30, "requests": []},
            "list": {"max_per_minute": 30, "requests": []},
        }

    async def initialize(self):
        """Initialize the command proxy with CASPER components."""
        if self._initialized:
            return

        try:
            # Initialize CASPER components
            self.context_manager = ContextManager()
            self.coordinator = AgentCoordinator(self.context_manager)
            self.task_analyzer = TaskAnalyzer()

            # Start coordinator
            await self.coordinator.start()
            self._initialized = True

            logger.info("Command proxy initialized successfully")

        except Exception as e:
            logger.error(f"Failed to initialize command proxy: {e}")
            raise

    async def shutdown(self):
        """Shutdown the command proxy."""
        if self.coordinator:
            await self.coordinator.stop()

        self._initialized = False
        logger.info("Command proxy shutdown complete")

    async def execute_casper_command(self, command: str, args: List[str] = None,
                                   user_id: Optional[str] = None, session_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Execute a CASPER CLI command with security validation and return the result.

        Args:
            command: The CASPER command to execute (e.g., 'task', 'status', 'analyze')
            args: Command arguments
            user_id: Optional user identifier for security logging
            session_id: Optional session identifier for security logging

        Returns:
            Dict containing the command result and metadata

        Raises:
            SecurityViolation: If command violates security policy
        """
        args = args or []
        session_id = session_id or str(uuid4())
        start_time = datetime.now()

        if not self._initialized:
            try:
                await self.initialize()
            except Exception as e:
                execution_time = (datetime.now() - start_time).total_seconds() * 1000
                return {
                    "command": command,
                    "args": args,
                    "execution_time_ms": execution_time,
                    "timestamp": start_time.isoformat(),
                    "user_id": user_id,
                    "session_id": session_id,
                    "success": False,
                    "error": str(e),
                    "message": "Command proxy initialization failed",
                }

        # Validate command security
        full_command = f"casper {command} {' '.join(args)}"
        try:
            # Check rate limits
            if not await self._check_rate_limits(command, user_id):
                raise SecurityViolation(f"Rate limit exceeded for command: {command}",
                                       full_command, CommandRisk.MEDIUM)

            # Check concurrent task limits
            if command == "task" and len(self.active_tasks) >= self.max_concurrent_tasks:
                raise SecurityViolation(f"Maximum concurrent tasks ({self.max_concurrent_tasks}) exceeded",
                                       full_command, CommandRisk.HIGH)

            # Log security event
            self.security._log_security_event(
                "CASPER_COMMAND_EXECUTION", full_command, session_id, user_id,
                CommandRisk.LOW, True, f"Executing CASPER command: {command}"
            )

        except SecurityViolation as e:
            # Log security violation
            self.security._log_security_event(
                "CASPER_COMMAND_BLOCKED", full_command, session_id, user_id,
                e.risk_level, False, str(e)
            )
            raise e

        try:
            logger.info(f"Executing CASPER command: {command} {' '.join(args)} (user: {user_id}, session: {session_id})")

            result = None
            task_id = None

            if command == "task":
                result = await self._handle_task_command(args, user_id, session_id)
                task_id = result.get("task_id")
                if task_id:
                    self.active_tasks.add(task_id)
            elif command == "status":
                result = await self._handle_status_command(args, user_id, session_id)
            elif command == "analyze":
                result = await self._handle_analyze_command(args, user_id, session_id)
            elif command == "list":
                result = await self._handle_list_command(args, user_id, session_id)
            elif command == "help":
                result = await self._handle_help_command(args, user_id, session_id)
            elif command == "init":
                result = await self._handle_init_command(args, user_id, session_id)
            else:
                result = {
                    "success": False,
                    "error": f"Unknown command: {command}",
                    "message": f"'{command}' is not a recognized CASPER command. Use 'casper help' for available commands."
                }

            execution_time = (datetime.now() - start_time).total_seconds() * 1000

            # Log successful execution
            if result.get("success", False):
                self.security._log_security_event(
                    "CASPER_COMMAND_SUCCESS", full_command, session_id, user_id,
                    CommandRisk.LOW, True, f"Command executed successfully in {execution_time:.2f}ms"
                )

            return {
                "command": command,
                "args": args,
                "execution_time_ms": execution_time,
                "timestamp": start_time.isoformat(),
                "user_id": user_id,
                "session_id": session_id,
                "task_id": task_id,
                **result
            }

        except Exception as e:
            execution_time = (datetime.now() - start_time).total_seconds() * 1000
            logger.error(f"Error executing command '{command}': {e}")

            # Log execution error
            self.security._log_security_event(
                "CASPER_COMMAND_ERROR", full_command, session_id, user_id,
                CommandRisk.MEDIUM, False, f"Command execution failed: {str(e)}"
            )

            return {
                "command": command,
                "args": args,
                "execution_time_ms": execution_time,
                "timestamp": start_time.isoformat(),
                "user_id": user_id,
                "session_id": session_id,
                "success": False,
                "error": str(e),
                "message": "Command execution failed"
            }

    async def _check_rate_limits(self, command: str, user_id: Optional[str]) -> bool:
        """Check if command execution is within rate limits."""
        if command not in self.command_rate_limits:
            return True  # No rate limit for unknown commands

        rate_limit = self.command_rate_limits[command]
        current_time = datetime.now()
        cutoff_time = current_time.timestamp() - 60  # 1 minute ago

        # Clean old requests
        rate_limit["requests"] = [
            req_time for req_time in rate_limit["requests"]
            if req_time > cutoff_time
        ]

        # Check if under limit
        if len(rate_limit["requests"]) >= rate_limit["max_per_minute"]:
            return False

        # Add current request
        rate_limit["requests"].append(current_time.timestamp())
        return True

    def cleanup_completed_tasks(self, task_id: str):
        """Remove completed task from active tasks tracking."""
        self.active_tasks.discard(task_id)

    async def _handle_task_command(self, args: List[str], user_id: Optional[str] = None,
                                  session_id: Optional[str] = None) -> Dict[str, Any]:
        """Handle 'casper task' command."""
        if not args:
            return {
                "success": False,
                "error": "Missing task description",
                "message": "Usage: casper task <description> [--priority high|medium|low]"
            }

        # Parse arguments
        task_description = " ".join(args)
        priority = "medium"

        # Simple argument parsing for priority
        if "--priority" in args:
            try:
                priority_index = args.index("--priority")
                if priority_index + 1 < len(args):
                    priority = args[priority_index + 1]
                    # Remove priority args from task description
                    task_args = args[:priority_index] + args[priority_index + 2:]
                    task_description = " ".join(task_args)
            except (ValueError, IndexError):
                pass

        # Convert priority
        priority_map = {
            "high": TaskPriority.HIGH,
            "medium": TaskPriority.MEDIUM,
            "low": TaskPriority.LOW
        }
        task_priority = priority_map.get(priority.lower(), TaskPriority.MEDIUM)

        try:
            # Analyze task
            metrics, required_agents, suggested_priority = self.task_analyzer.analyze_task(task_description)

            # Submit task
            task_id = await self.coordinator.submit_task(task_description, task_priority)

            return {
                "success": True,
                "task_id": str(task_id),
                "message": f"Task submitted successfully",
                "data": {
                    "task_description": task_description,
                    "priority": priority,
                    "analysis": {
                        "lines_of_code_estimate": metrics.lines_of_code_estimate,
                        "file_count_estimate": metrics.file_count_estimate,
                        "component_count": metrics.component_count,
                        "integration_points": metrics.integration_points,
                        "external_dependencies": metrics.external_dependencies,
                        "required_agents": [agent.value for agent in required_agents],
                        "suggested_priority": suggested_priority.value
                    }
                }
            }

        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "message": "Failed to submit task"
            }

    async def _handle_status_command(self, args: List[str], user_id: Optional[str] = None,
                                    session_id: Optional[str] = None) -> Dict[str, Any]:
        """Handle 'casper status' command."""
        try:
            stats = self.coordinator.get_coordinator_stats()
            agent_pool = stats.get("agent_pool", {})

            return {
                "success": True,
                "message": "System status retrieved",
                "data": {
                    "system_status": {
                        "active_tasks": stats.get("active_tasks", 0),
                        "queued_tasks": stats.get("queued_tasks", 0),
                        "context_sessions": stats.get("context_sessions", 0),
                    },
                    "agent_pool": {
                        "total_agents": agent_pool.get("total_agents", 0),
                        "busy_agents": agent_pool.get("busy_agents", 0),
                        "available_by_role": agent_pool.get("available_by_role", {}),
                    },
                    "token_usage": {
                        "total": stats.get("token_usage_total", 0)
                    }
                }
            }

        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "message": "Failed to retrieve system status"
            }

    async def _handle_analyze_command(self, args: List[str], user_id: Optional[str] = None,
                                     session_id: Optional[str] = None) -> Dict[str, Any]:
        """Handle 'casper analyze' command."""
        if not args:
            return {
                "success": False,
                "error": "Missing task description",
                "message": "Usage: casper analyze <description>"
            }

        task_description = " ".join(args)

        try:
            metrics, required_agents, priority = self.task_analyzer.analyze_task(task_description)

            return {
                "success": True,
                "message": "Task analysis completed",
                "data": {
                    "task_description": task_description,
                    "analysis": {
                        "complexity_score": self.task_analyzer._calculate_complexity_score(task_description.lower()),
                        "lines_of_code_estimate": metrics.lines_of_code_estimate,
                        "file_count_estimate": metrics.file_count_estimate,
                        "component_count": metrics.component_count,
                        "integration_points": metrics.integration_points,
                        "external_dependencies": metrics.external_dependencies,
                        "required_agents": [agent.value for agent in required_agents],
                        "suggested_priority": priority.value,
                        "estimated_time_minutes": TaskAnalyzer.estimate_completion_time(metrics)
                    }
                }
            }

        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "message": "Failed to analyze task"
            }

    async def _handle_list_command(self, args: List[str], user_id: Optional[str] = None,
                                  session_id: Optional[str] = None) -> Dict[str, Any]:
        """Handle 'casper list' command."""
        try:
            limit = 10
            if args and args[0].isdigit():
                limit = int(args[0])

            results = await self.coordinator.get_results(limit)

            task_list = []
            for result in results:
                task_list.append({
                    "task_id": str(result.task_id)[:8],
                    "agent_role": result.agent_role.value,
                    "status": result.status.value,
                    "token_usage": result.token_usage.get("total", 0),
                    "output_preview": result.output[:100] + "..." if len(result.output) > 100 else result.output,
                    "errors": result.errors
                })

            return {
                "success": True,
                "message": f"Retrieved {len(task_list)} recent tasks",
                "data": {
                    "tasks": task_list,
                    "count": len(task_list)
                }
            }

        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "message": "Failed to retrieve task list"
            }

    async def _handle_help_command(self, args: List[str], user_id: Optional[str] = None,
                                  session_id: Optional[str] = None) -> Dict[str, Any]:
        """Handle 'casper help' command."""
        help_text = {
            "commands": {
                "task <description>": "Submit a new task for execution",
                "analyze <description>": "Analyze a task without executing it",
                "status": "Show current system status and agent pool",
                "list [count]": "List recent tasks (default: 10)",
                "init [--project <dir>]": "Initialize CASPER in a project directory",
                "help [command]": "Show help information"
            },
            "options": {
                "--priority": "Set task priority (high, medium, low)",
                "--project": "Specify project directory for initialization"
            },
            "examples": [
                "casper task 'Create a new API endpoint for user management'",
                "casper task 'Fix login bug' --priority high",
                "casper analyze 'Implement user authentication system'",
                "casper status",
                "casper list 20"
            ]
        }

        return {
            "success": True,
            "message": "CASPER CLI Help",
            "data": help_text
        }

    async def _handle_init_command(self, args: List[str], user_id: Optional[str] = None,
                                  session_id: Optional[str] = None) -> Dict[str, Any]:
        """Handle 'casper init' command."""
        try:
            # Parse project directory argument
            project_dir = Path.cwd()
            if "--project" in args:
                try:
                    project_index = args.index("--project")
                    if project_index + 1 < len(args):
                        project_dir = Path(args[project_index + 1]).resolve()
                except (ValueError, IndexError):
                    pass

            # Create CASPER directories
            directories = [
                ".casper/context",
                ".casper/knowledge",
                ".casper/logs/agent-decisions",
                ".casper/logs/code-changes",
                ".casper/checkpoints",
                ".casper/output",
                ".casper/config",
            ]

            created_dirs = []
            for relative in directories:
                full_path = project_dir / relative
                full_path.mkdir(parents=True, exist_ok=True)
                created_dirs.append(str(full_path))

            # Create configuration file
            config = {
                "version": "0.1.0",
                "project_root": str(project_dir),
                "output_dir": str(project_dir / ".casper" / "output"),
                "max_tokens_per_task": 100000,
                "agent_settings": {
                    # "auto" → resolved dynamically at runtime by LLMService.
                    "primary_model": "auto",
                    "worker_model": "auto",
                },
                "terminal": {
                    "enabled": True,
                    "shell": os.environ.get('SHELL', '/bin/bash'),
                    "security": {
                        "command_filtering": True,
                        "sandbox_mode": False
                    }
                }
            }

            config_path = project_dir / ".casper/config/casper.json"
            config_path.write_text(json.dumps(config, indent=2))

            return {
                "success": True,
                "message": f"CASPER initialized successfully",
                "data": {
                    "project_directory": str(project_dir),
                    "config_file": str(config_path),
                    "created_directories": created_dirs,
                    "output_directory": str(project_dir / ".casper" / "output")
                }
            }

        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "message": "Failed to initialize CASPER project"
            }

    def get_available_commands(self) -> List[str]:
        """Get list of available CASPER commands."""
        return ["task", "status", "analyze", "list", "help", "init"]

    def is_valid_command(self, command: str) -> bool:
        """Check if a command is valid CASPER command."""
        return command in self.get_available_commands()
