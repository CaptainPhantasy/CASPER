"""
Decision Orchestrator for CASPER
Implements multi-agent orchestration and tool selection matrix from the logic plan
"""

import asyncio
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass
from enum import Enum
from pathlib import Path

from core.agents.base import AgentRole, BaseAgent
from core.ai.enhanced_command_interpreter import (
    InterpretedCommand,
    CommandType,
    Priority,
    ErrorSeverity,
)


class ExecutionModel(Enum):
    """Execution models for multi-agent coordination"""

    SEQUENTIAL_PIPELINE = "sequential"  # One after another
    PARALLEL_EXECUTION = "parallel"  # All at once
    DYNAMIC_ROUTING = "dynamic"  # Conditional flow
    HYBRID = "hybrid"  # Mix of parallel and sequential


class AgentSpecialization(Enum):
    """Specialized agent roles based on logic plan"""

    ARCHITECT = "architect"  # System design, architecture docs
    FRONTEND_DEV = "frontend_dev"  # UI/UX implementation
    BACKEND_DEV = "backend_dev"  # API/business logic
    DEVOPS = "devops"  # CI/CD, deployment
    QA_TESTER = "qa_tester"  # Test planning, bug detection
    CODE_REVIEWER = "reviewer"  # Code review, best practices
    SECURITY_AUDITOR = "security"  # Security audit


@dataclass
class ToolSelection:
    """Tool selection based on task type"""

    primary_tool: str
    secondary_tools: List[str]
    conditions: str
    fallback_strategy: str


@dataclass
class QualityGate:
    """Quality gates for stage validation"""

    name: str
    criteria: List[str]
    must_pass: bool
    rollback_on_fail: bool


@dataclass
class OrchestrationPlan:
    """Complete orchestration plan for multi-agent execution"""

    task_id: str
    agents: List[AgentSpecialization]
    execution_model: ExecutionModel
    tool_matrix: Dict[str, ToolSelection]
    quality_gates: List[QualityGate]
    estimated_duration_ms: int
    parallelization_factor: float  # 0-1, how much can be parallelized


class DecisionOrchestrator:
    """
    Orchestrates complex decision-making and multi-agent coordination.
    Implements the comprehensive logic chains from the plan.
    """

    # Tool Selection Matrix from logic plan
    TOOL_MATRIX = {
        "create_single_file": ToolSelection(
            primary_tool="Write",
            secondary_tools=["Bash (mkdir -p)"],
            conditions="Parent dir must exist",
            fallback_strategy="Create parent directories first",
        ),
        "create_multiple_files": ToolSelection(
            primary_tool="Write (multiple)",
            secondary_tools=["MultiEdit"],
            conditions="Related files",
            fallback_strategy="Sequential creation",
        ),
        "edit_single_file": ToolSelection(
            primary_tool="Edit",
            secondary_tools=["MultiEdit"],
            conditions="<5 changes",
            fallback_strategy="Use MultiEdit for complex",
        ),
        "edit_multiple_spots": ToolSelection(
            primary_tool="MultiEdit",
            secondary_tools=["Edit"],
            conditions="Same file",
            fallback_strategy="Split into multiple Edit calls",
        ),
        "search_by_name": ToolSelection(
            primary_tool="Glob",
            secondary_tools=["Bash (find)"],
            conditions="Pattern matching",
            fallback_strategy="Use find command",
        ),
        "search_by_content": ToolSelection(
            primary_tool="Grep",
            secondary_tools=["Task"],
            conditions="Text in files",
            fallback_strategy="Complex search with Task",
        ),
        "read_file": ToolSelection(
            primary_tool="Read",
            secondary_tools=[],
            conditions="Always use Read",
            fallback_strategy="No fallback - Read is required",
        ),
        "delete_files": ToolSelection(
            primary_tool="Bash (rm)",
            secondary_tools=[],
            conditions="With confirmation",
            fallback_strategy="Require explicit confirmation",
        ),
        "run_commands": ToolSelection(
            primary_tool="Bash",
            secondary_tools=["BashOutput"],
            conditions="Check sandbox",
            fallback_strategy="Use BashOutput for long-running",
        ),
        "install_packages": ToolSelection(
            primary_tool="Bash",
            secondary_tools=[],
            conditions="Detect package manager",
            fallback_strategy="Ask user for package manager",
        ),
        "web_research": ToolSelection(
            primary_tool="WebSearch",
            secondary_tools=["WebFetch"],
            conditions="Current information",
            fallback_strategy="Use WebFetch for specific URLs",
        ),
        "documentation_lookup": ToolSelection(
            primary_tool="WebFetch",
            secondary_tools=["MCP tools"],
            conditions="Library docs",
            fallback_strategy="Search online documentation",
        ),
        "complex_search": ToolSelection(
            primary_tool="Task",
            secondary_tools=["Glob", "Grep"],
            conditions="Multi-step exploration",
            fallback_strategy="Break into simpler searches",
        ),
        "git_operations": ToolSelection(
            primary_tool="Bash (git)",
            secondary_tools=[],
            conditions="Follow git practices",
            fallback_strategy="Use git GUI if available",
        ),
        "test_execution": ToolSelection(
            primary_tool="Bash",
            secondary_tools=["TodoWrite"],
            conditions="Platform-appropriate",
            fallback_strategy="Manual test execution",
        ),
    }

    def __init__(self):
        self.active_agents: Dict[str, BaseAgent] = {}
        self.execution_history: List[Dict] = []
        self.quality_metrics: Dict = {}

    async def orchestrate(self, command: InterpretedCommand) -> OrchestrationPlan:
        """
        Create orchestration plan based on interpreted command.
        Implements multi-agent task decomposition logic.
        """

        # Analyze task complexity
        complexity = self._assess_complexity(command)

        # Determine if multi-agent is beneficial
        if self._should_use_multi_agent(command, complexity):
            return await self._create_multi_agent_plan(command, complexity)
        else:
            return await self._create_single_agent_plan(command)

    def _assess_complexity(self, command: InterpretedCommand) -> Dict:
        """Assess task complexity for orchestration decisions"""
        complexity = {
            "score": 0,
            "factors": [],
            "estimated_operations": 0,
            "requires_coordination": False,
        }

        # Factor 1: Number of targets
        if len(command.targets) > 5:
            complexity["score"] += 30
            complexity["factors"].append("multiple_targets")
            complexity["requires_coordination"] = True

        # Factor 2: Command type complexity
        complex_types = [
            CommandType.CODE_GENERATION,
            CommandType.MULTI_AGENT,
            CommandType.INITIALIZATION,
        ]
        if command.command_type in complex_types:
            complexity["score"] += 40
            complexity["factors"].append("complex_operation")

        # Factor 3: Cross-cutting concerns
        if command.safety_checks and len(command.safety_checks) > 2:
            complexity["score"] += 20
            complexity["factors"].append("safety_critical")

        # Factor 4: Priority level
        if command.priority == Priority.COMPLEX:
            complexity["score"] += 30
            complexity["factors"].append("time_intensive")

        complexity["estimated_operations"] = len(command.targets) * 2

        return complexity

    def _should_use_multi_agent(
        self, command: InterpretedCommand, complexity: Dict
    ) -> bool:
        """Determine if multi-agent orchestration is beneficial"""

        # Explicit multi-agent request
        if command.command_type == CommandType.MULTI_AGENT:
            return True

        # Complexity threshold
        if complexity["score"] > 60:
            return True

        # Parallel execution benefit
        if command.execution_strategy == "parallel" and len(command.targets) > 3:
            return True

        # Cross-functional requirements
        if (
            command.command_type == CommandType.CODE_GENERATION
            and complexity["requires_coordination"]
        ):
            return True

        return False

    async def _create_multi_agent_plan(
        self, command: InterpretedCommand, complexity: Dict
    ) -> OrchestrationPlan:
        """Create multi-agent orchestration plan"""

        # Assign agent roles based on task
        agents = self._assign_agent_roles(command, complexity)

        # Determine execution model
        exec_model = self._determine_execution_model(command, agents)

        # Select tools for each agent
        tool_matrix = self._build_tool_matrix(command, agents)

        # Define quality gates
        quality_gates = self._define_quality_gates(command, complexity)

        # Calculate timing
        duration = self._estimate_total_duration(command, agents, exec_model)

        # Calculate parallelization factor
        parallel_factor = self._calculate_parallelization(agents, exec_model)

        return OrchestrationPlan(
            task_id=f"task_{command.raw_input[:20]}",
            agents=agents,
            execution_model=exec_model,
            tool_matrix=tool_matrix,
            quality_gates=quality_gates,
            estimated_duration_ms=duration,
            parallelization_factor=parallel_factor,
        )

    async def _create_single_agent_plan(
        self, command: InterpretedCommand
    ) -> OrchestrationPlan:
        """Create single-agent execution plan"""

        # Determine primary agent
        agent = self._map_to_agent_specialization(command.suggested_agent)

        # Get tool selection
        tool_key = self._get_tool_key(command)
        tool_selection = self.TOOL_MATRIX.get(
            tool_key, ToolSelection("Bash", [], "Default", "Manual execution")
        )

        # Simple quality gate
        quality_gates = [
            QualityGate(
                name="execution_complete",
                criteria=["task_completed", "no_errors"],
                must_pass=True,
                rollback_on_fail=False,
            )
        ]

        return OrchestrationPlan(
            task_id=f"task_{command.raw_input[:20]}",
            agents=[agent],
            execution_model=ExecutionModel.SEQUENTIAL_PIPELINE,
            tool_matrix={command.action: tool_selection},
            quality_gates=quality_gates,
            estimated_duration_ms=command.estimated_time_ms,
            parallelization_factor=0.0,
        )

    def _assign_agent_roles(
        self, command: InterpretedCommand, complexity: Dict
    ) -> List[AgentSpecialization]:
        """Assign agent roles based on task requirements"""
        agents = []

        # Primary agent based on command type
        if command.command_type == CommandType.CODE_GENERATION:
            agents.append(AgentSpecialization.ARCHITECT)

            # Add specialized developers
            if "frontend" in command.raw_input.lower():
                agents.append(AgentSpecialization.FRONTEND_DEV)
            if (
                "backend" in command.raw_input.lower()
                or "api" in command.raw_input.lower()
            ):
                agents.append(AgentSpecialization.BACKEND_DEV)

            # Add QA for complex generation
            if complexity["score"] > 70:
                agents.append(AgentSpecialization.QA_TESTER)
                agents.append(AgentSpecialization.CODE_REVIEWER)

        elif command.command_type == CommandType.TESTING:
            agents.append(AgentSpecialization.QA_TESTER)
            if complexity["score"] > 50:
                agents.append(AgentSpecialization.CODE_REVIEWER)

        elif command.command_type == CommandType.DEBUGGING:
            agents.append(AgentSpecialization.BACKEND_DEV)
            if "security" in command.raw_input.lower():
                agents.append(AgentSpecialization.SECURITY_AUDITOR)

        elif command.command_type == CommandType.GIT_OPERATION:
            agents.append(AgentSpecialization.DEVOPS)

        # Default fallback
        if not agents:
            agents.append(AgentSpecialization.BACKEND_DEV)

        return agents

    def _determine_execution_model(
        self, command: InterpretedCommand, agents: List[AgentSpecialization]
    ) -> ExecutionModel:
        """Determine optimal execution model"""

        # Single agent - always sequential
        if len(agents) == 1:
            return ExecutionModel.SEQUENTIAL_PIPELINE

        # Explicit strategy from command
        if command.execution_strategy == "parallel":
            return ExecutionModel.PARALLEL_EXECUTION
        elif command.execution_strategy == "sequential":
            return ExecutionModel.SEQUENTIAL_PIPELINE

        # Architecture + Development pattern
        if AgentSpecialization.ARCHITECT in agents:
            # Architect must complete before developers
            return ExecutionModel.HYBRID

        # QA and Review can be parallel
        if (
            AgentSpecialization.QA_TESTER in agents
            and AgentSpecialization.CODE_REVIEWER in agents
        ):
            return ExecutionModel.PARALLEL_EXECUTION

        # Default to sequential for safety
        return ExecutionModel.SEQUENTIAL_PIPELINE

    def _build_tool_matrix(
        self, command: InterpretedCommand, agents: List[AgentSpecialization]
    ) -> Dict[str, ToolSelection]:
        """Build tool selection matrix for agents"""
        tool_matrix = {}

        for agent in agents:
            # Get primary action for agent
            if agent == AgentSpecialization.ARCHITECT:
                tool_matrix["design"] = ToolSelection(
                    "Write", ["MultiEdit"], "Create design docs", "Manual documentation"
                )
            elif agent == AgentSpecialization.FRONTEND_DEV:
                tool_matrix["frontend"] = ToolSelection(
                    "Write",
                    ["Edit", "MultiEdit"],
                    "Component creation",
                    "Template generation",
                )
            elif agent == AgentSpecialization.BACKEND_DEV:
                tool_matrix["backend"] = ToolSelection(
                    "Write",
                    ["Edit", "MultiEdit"],
                    "API implementation",
                    "Boilerplate code",
                )
            elif agent == AgentSpecialization.QA_TESTER:
                tool_matrix["testing"] = ToolSelection(
                    "Bash", ["Write"], "Test execution", "Manual testing"
                )
            elif agent == AgentSpecialization.CODE_REVIEWER:
                tool_matrix["review"] = ToolSelection(
                    "Read", ["Grep"], "Code analysis", "Manual review"
                )
            elif agent == AgentSpecialization.DEVOPS:
                tool_matrix["deploy"] = ToolSelection(
                    "Bash", ["Write"], "Deployment scripts", "Manual deployment"
                )

        return tool_matrix

    def _define_quality_gates(
        self, command: InterpretedCommand, complexity: Dict
    ) -> List[QualityGate]:
        """Define quality gates based on task requirements"""
        gates = []

        # Basic validation gate
        gates.append(
            QualityGate(
                name="input_validation",
                criteria=["valid_targets", "permissions_ok"],
                must_pass=True,
                rollback_on_fail=False,
            )
        )

        # Safety gate for destructive operations
        if (
            "delete" in command.action
            or command.command_type == CommandType.FILE_OPERATION
        ):
            gates.append(
                QualityGate(
                    name="safety_check",
                    criteria=["backup_exists", "user_confirmed"],
                    must_pass=True,
                    rollback_on_fail=True,
                )
            )

        # Code quality gate
        if command.command_type in [CommandType.CODE_GENERATION, CommandType.DEBUGGING]:
            gates.append(
                QualityGate(
                    name="code_quality",
                    criteria=["syntax_valid", "linting_passed", "no_security_issues"],
                    must_pass=False,
                    rollback_on_fail=False,
                )
            )

        # Test gate
        if complexity["score"] > 60:
            gates.append(
                QualityGate(
                    name="test_validation",
                    criteria=["tests_pass", "coverage_maintained"],
                    must_pass=False,
                    rollback_on_fail=True,
                )
            )

        # Final assembly gate
        if len(command.targets) > 3:
            gates.append(
                QualityGate(
                    name="final_assembly",
                    criteria=["all_components_ready", "integration_verified"],
                    must_pass=True,
                    rollback_on_fail=True,
                )
            )

        return gates

    def _estimate_total_duration(
        self,
        command: InterpretedCommand,
        agents: List[AgentSpecialization],
        exec_model: ExecutionModel,
    ) -> int:
        """Estimate total execution duration in milliseconds"""

        # Base time per agent
        agent_times = {
            AgentSpecialization.ARCHITECT: 2000,
            AgentSpecialization.FRONTEND_DEV: 3000,
            AgentSpecialization.BACKEND_DEV: 3000,
            AgentSpecialization.QA_TESTER: 5000,
            AgentSpecialization.CODE_REVIEWER: 2000,
            AgentSpecialization.DEVOPS: 4000,
            AgentSpecialization.SECURITY_AUDITOR: 6000,
        }

        total_time = 0

        if exec_model == ExecutionModel.PARALLEL_EXECUTION:
            # Take maximum time
            total_time = max(agent_times.get(agent, 1000) for agent in agents)
        elif exec_model == ExecutionModel.SEQUENTIAL_PIPELINE:
            # Sum all times
            total_time = sum(agent_times.get(agent, 1000) for agent in agents)
        elif exec_model == ExecutionModel.HYBRID:
            # Architect first, then parallel for others
            if AgentSpecialization.ARCHITECT in agents:
                total_time = agent_times[AgentSpecialization.ARCHITECT]
                other_agents = [a for a in agents if a != AgentSpecialization.ARCHITECT]
                if other_agents:
                    total_time += max(
                        agent_times.get(agent, 1000) for agent in other_agents
                    )
            else:
                total_time = sum(agent_times.get(agent, 1000) for agent in agents)

        # Factor in number of targets
        target_factor = 1 + (len(command.targets) * 0.2)
        total_time = int(total_time * target_factor)

        return total_time

    def _calculate_parallelization(
        self, agents: List[AgentSpecialization], exec_model: ExecutionModel
    ) -> float:
        """Calculate parallelization factor (0-1)"""

        if exec_model == ExecutionModel.PARALLEL_EXECUTION:
            return 0.9  # High parallelization
        elif exec_model == ExecutionModel.SEQUENTIAL_PIPELINE:
            return 0.0  # No parallelization
        elif exec_model == ExecutionModel.HYBRID:
            # Some parallelization
            if len(agents) > 2:
                return 0.5
            return 0.3
        else:
            return 0.2  # Default low parallelization

    def _get_tool_key(self, command: InterpretedCommand) -> str:
        """Map command to tool matrix key"""

        # Map command attributes to tool keys
        if command.command_type == CommandType.FILE_OPERATION:
            if command.action == "create":
                if len(command.targets) == 1:
                    return "create_single_file"
                return "create_multiple_files"
            elif command.action == "modify":
                return "edit_single_file"
            elif command.action == "delete":
                return "delete_files"
        elif command.command_type == CommandType.TESTING:
            return "test_execution"
        elif command.command_type == CommandType.GIT_OPERATION:
            return "git_operations"
        elif command.command_type == CommandType.PACKAGE_MANAGEMENT:
            return "install_packages"

        return "run_commands"  # Default

    def _map_to_agent_specialization(self, agent_name: str) -> AgentSpecialization:
        """Map agent name to specialization enum"""
        mapping = {
            "worker": AgentSpecialization.BACKEND_DEV,
            "frontend_prime": AgentSpecialization.FRONTEND_DEV,
            "backend_prime": AgentSpecialization.BACKEND_DEV,
            "testing_prime": AgentSpecialization.QA_TESTER,
            "devops_prime": AgentSpecialization.DEVOPS,
            "master_prime": AgentSpecialization.ARCHITECT,
        }

        return mapping.get(agent_name, AgentSpecialization.BACKEND_DEV)

    async def execute_with_quality_gates(
        self, plan: OrchestrationPlan, actual_execution_func
    ) -> Dict:
        """Execute plan with quality gate checks"""

        results = {
            "task_id": plan.task_id,
            "status": "pending",
            "gates_passed": [],
            "gates_failed": [],
            "execution_time_ms": 0,
            "outputs": [],
        }

        start_time = asyncio.get_event_loop().time()

        try:
            # Pre-execution quality gates
            for gate in plan.quality_gates:
                if gate.name == "input_validation":
                    if not await self._validate_inputs(plan):
                        results["status"] = "failed"
                        results["gates_failed"].append(gate.name)
                        if gate.must_pass:
                            return results

            # Execute based on model
            if plan.execution_model == ExecutionModel.PARALLEL_EXECUTION:
                outputs = await self._execute_parallel(plan, actual_execution_func)
            elif plan.execution_model == ExecutionModel.HYBRID:
                outputs = await self._execute_hybrid(plan, actual_execution_func)
            else:
                outputs = await self._execute_sequential(plan, actual_execution_func)

            results["outputs"] = outputs

            # Post-execution quality gates
            for gate in plan.quality_gates:
                if gate.name in ["code_quality", "test_validation", "final_assembly"]:
                    if await self._check_quality_gate(gate, outputs):
                        results["gates_passed"].append(gate.name)
                    else:
                        results["gates_failed"].append(gate.name)
                        if gate.must_pass:
                            if gate.rollback_on_fail:
                                await self._rollback(plan, outputs)
                            results["status"] = "failed"
                            return results

            results["status"] = "completed"

        except Exception as e:
            results["status"] = "error"
            results["error"] = str(e)
            # Trigger cascading failure management
            await self._handle_cascading_failure(e, plan)

        finally:
            end_time = asyncio.get_event_loop().time()
            results["execution_time_ms"] = int((end_time - start_time) * 1000)

        return results

    async def _validate_inputs(self, plan: OrchestrationPlan) -> bool:
        """Validate inputs before execution"""
        # Simplified validation
        return True

    async def _execute_parallel(self, plan: OrchestrationPlan, exec_func) -> List:
        """Execute agents in parallel"""
        tasks = []
        for agent in plan.agents:
            tasks.append(exec_func(agent, plan.tool_matrix))
        return await asyncio.gather(*tasks)

    async def _execute_sequential(self, plan: OrchestrationPlan, exec_func) -> List:
        """Execute agents sequentially"""
        outputs = []
        for agent in plan.agents:
            output = await exec_func(agent, plan.tool_matrix)
            outputs.append(output)
        return outputs

    async def _execute_hybrid(self, plan: OrchestrationPlan, exec_func) -> List:
        """Execute with hybrid model (architect first, then parallel)"""
        outputs = []

        # Execute architect first if present
        if AgentSpecialization.ARCHITECT in plan.agents:
            architect_output = await exec_func(
                AgentSpecialization.ARCHITECT, plan.tool_matrix
            )
            outputs.append(architect_output)

            # Execute others in parallel
            other_agents = [
                a for a in plan.agents if a != AgentSpecialization.ARCHITECT
            ]
            if other_agents:
                parallel_outputs = await self._execute_parallel(
                    OrchestrationPlan(
                        task_id=plan.task_id,
                        agents=other_agents,
                        execution_model=ExecutionModel.PARALLEL_EXECUTION,
                        tool_matrix=plan.tool_matrix,
                        quality_gates=[],
                        estimated_duration_ms=0,
                        parallelization_factor=0,
                    ),
                    exec_func,
                )
                outputs.extend(parallel_outputs)
        else:
            outputs = await self._execute_sequential(plan, exec_func)

        return outputs

    async def _check_quality_gate(self, gate: QualityGate, outputs: List) -> bool:
        """Check if quality gate passes"""
        # Simplified check - would implement actual validation
        return True

    async def _rollback(self, plan: OrchestrationPlan, outputs: List):
        """Rollback changes on quality gate failure"""
        print(f"Rolling back task {plan.task_id}")
        # Implement rollback logic

    async def _handle_cascading_failure(
        self, error: Exception, plan: OrchestrationPlan
    ):
        """Handle cascading failures according to comprehensive plan"""

        failure_info = {
            "error": str(error),
            "affected_agents": plan.agents,
            "containment_strategy": None,
            "recovery_actions": [],
        }

        # Determine containment strategy
        if len(plan.agents) > 1:
            failure_info["containment_strategy"] = "isolate_failed_agent"
            failure_info["recovery_actions"] = [
                "retry_with_reduced_agents",
                "fallback_to_sequential",
                "manual_intervention",
            ]
        else:
            failure_info["containment_strategy"] = "stop_execution"
            failure_info["recovery_actions"] = [
                "log_error",
                "notify_user",
                "suggest_alternatives",
            ]

        # Log for pattern recognition
        self.execution_history.append(
            {
                "task_id": plan.task_id,
                "failure": failure_info,
                "timestamp": asyncio.get_event_loop().time(),
            }
        )

        print(f"Cascading failure handled: {failure_info}")


# Global orchestrator instance
decision_orchestrator = DecisionOrchestrator()
