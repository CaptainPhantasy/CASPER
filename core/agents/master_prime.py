"""
Master Prime Agent - The orchestrator of CASPER Prime.
Analyzes tasks, determines complexity, and spawns specialized agents.
"""

import asyncio
import json
import re
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional, Set, Tuple
from uuid import UUID

from .base import (
    AgentRole, AgentStatus, BaseAgent, ContextBundle,
    AgentResult, TaskPriority, TaskDelegation
)
from core.services.llm import llm_service
from core.agentic.prompt_templates import DECOMPOSE_PROMPT, CRITIQUE_PROMPT, REFINE_PROMPT
from core.context.delegator import ContextDelegator


class TaskComplexity(Enum):
    """Task complexity levels for spawning decisions."""
    LOW = "low"  # Single file, simple logic
    MEDIUM = "medium"  # Multiple files, moderate logic
    HIGH = "high"  # Multiple components, complex integration


class ExecutionStrategy(Enum):
    """How to execute subtasks."""
    SEQUENTIAL = "sequential"
    PARALLEL = "parallel"
    HYBRID = "hybrid"


@dataclass
class TaskAnalysis:
    """Comprehensive task analysis result."""
    original_task: str
    complexity: TaskComplexity
    estimated_tokens: int
    required_agents: List[AgentRole]
    subtasks: List['SubTask']
    execution_strategy: ExecutionStrategy
    dependencies: Dict[str, List[str]] = field(default_factory=dict)
    risk_factors: List[str] = field(default_factory=list)
    success_criteria: List[str] = field(default_factory=list)


@dataclass
class SubTask:
    """Individual subtask for delegation."""
    task_id: UUID
    description: str
    agent_role: AgentRole
    priority: TaskPriority
    estimated_tokens: int
    dependencies: List[UUID] = field(default_factory=list)
    parallel_group: Optional[int] = None


class TaskComplexityAnalyzer:
    """Analyzes task complexity using multiple heuristics."""

    COMPLEXITY_INDICATORS = {
        TaskComplexity.HIGH: [
            r"entire\s+(system|application|platform)",
            r"(multiple|several|various)\s+components",
            r"(integrate|integration|orchestrate)",
            r"(microservice|distributed|scalable)",
            r"(authentication|authorization|security)\s+system",
            r"full[- ]stack",
            r"end[- ]to[- ]end",
            r"production[- ]ready"
        ],
        TaskComplexity.MEDIUM: [
            r"(api|endpoint|service)",
            r"(crud|database|model)",
            r"(component|module|feature)",
            r"(refactor|optimize|improve)",
            r"(test|testing)\s+(suite|coverage)",
            r"dashboard|interface|ui"
        ],
        TaskComplexity.LOW: [
            r"(fix|debug|patch)",
            r"(add|update|modify)\s+\w+",
            r"single\s+(file|function|method)",
            r"(simple|basic|minor)",
            r"(typo|formatting|style)"
        ]
    }

    AGENT_KEYWORDS = {
        AgentRole.FRONTEND_PRIME: [
            "ui", "interface", "component", "react", "frontend",
            "dashboard", "form", "button", "layout", "css", "style",
            "user experience", "ux", "responsive", "interactive"
        ],
        AgentRole.BACKEND_PRIME: [
            "api", "database", "server", "backend", "endpoint",
            "authentication", "authorization", "jwt", "rest", "graphql",
            "model", "schema", "migration", "crud", "service"
        ],
        AgentRole.TESTING_PRIME: [
            "test", "testing", "coverage", "unit test", "integration",
            "e2e", "mock", "stub", "assertion", "suite", "tdd"
        ],
        AgentRole.DEVOPS_PRIME: [
            "deploy", "deployment", "infrastructure", "ci/cd", "pipeline",
            "docker", "kubernetes", "terraform", "monitoring", "logging",
            "rollout", "scaling", "performance", "ops", "devops"
        ]
    }

    @classmethod
    def analyze(cls, task: str) -> Tuple[TaskComplexity, Set[AgentRole]]:
        """Analyze task complexity and required agents."""
        task_lower = task.lower()

        # Determine complexity
        complexity = cls._determine_complexity(task_lower)

        # Determine required agents
        required_agents = cls._determine_agents(task_lower, complexity)

        return complexity, required_agents

    @classmethod
    def _determine_complexity(cls, task: str) -> TaskComplexity:
        """Determine task complexity based on indicators."""
        # Check high complexity indicators first
        for pattern in cls.COMPLEXITY_INDICATORS[TaskComplexity.HIGH]:
            if re.search(pattern, task):
                return TaskComplexity.HIGH

        # Then medium
        for pattern in cls.COMPLEXITY_INDICATORS[TaskComplexity.MEDIUM]:
            if re.search(pattern, task):
                return TaskComplexity.MEDIUM

        # Default to low
        return TaskComplexity.LOW

    @classmethod
    def _determine_agents(cls, task: str, complexity: TaskComplexity) -> Set[AgentRole]:
        """Determine which agents are needed based on task content."""
        required = set()

        # Always include master for coordination
        required.add(AgentRole.MASTER)

        # Check for agent-specific keywords
        for role, keywords in cls.AGENT_KEYWORDS.items():
            if any(keyword in task for keyword in keywords):
                required.add(role)

        # High complexity tasks typically need multiple agents
        if complexity == TaskComplexity.HIGH and len(required) < 3:
            # Add commonly needed agents for complex tasks
            if "system" in task or "application" in task:
                required.update([AgentRole.FRONTEND_PRIME, AgentRole.BACKEND_PRIME])
            if "production" in task or "ready" in task:
                required.add(AgentRole.TESTING_PRIME)

        return required


class MasterPrimeAgent(BaseAgent):
    """
    Master orchestrator agent that analyzes tasks and coordinates execution.
    This is the brain of CASPER Prime.
    """

    def __init__(self):
        super().__init__(role=AgentRole.MASTER)
        self.analyzer = TaskComplexityAnalyzer()
        self.active_delegations: Dict[UUID, TaskDelegation] = {}
        self.completed_results: List[AgentResult] = []

    async def analyze_task(self, task: str, context: ContextBundle) -> Tuple[bool, str]:
        """Master can analyze any task."""
        return True, "Master Prime coordinates all tasks"

    async def execute_task(self, task: str, context: ContextBundle) -> AgentResult:
        """
        Master execution: analyze, decompose, delegate, coordinate.
        """
        try:
            self.current_context = context
            self.current_context.parent_task = task

            # Update status
            await self._update_progress(AgentStatus.PLANNING, 10, "Analyzing task complexity...")

            # Perform comprehensive task analysis
            analysis = await self.perform_task_analysis(task)

            # Log the analysis decision
            self._log_decision(
                f"Task complexity: {analysis.complexity.value}",
                f"Requires {len(analysis.required_agents)} agents, {len(analysis.subtasks)} subtasks",
                [str(agent.value) for agent in analysis.required_agents]
            )

            # Create execution plan
            await self._update_progress(AgentStatus.PLANNING, 30, "Creating execution plan...")
            execution_plan = await self.create_execution_plan(analysis)

            # Spawn agents and delegate tasks
            await self._update_progress(AgentStatus.BUILDING, 50, "Spawning specialized agents...")
            delegations = await self.spawn_and_delegate(execution_plan)

            # Delegate execution to coordinator; don't block here.
            await self._update_progress(AgentStatus.REVIEWING, 80, "Delegations created; monitoring child agents...")

            # Complete master planning step; children will continue.
            await self._update_progress(AgentStatus.COMPLETED, 100, "Master planning complete; execution in progress")

            return AgentResult(
                agent_id=self.agent_id,
                agent_role=self.role,
                task_id=context.session_id,
                status=AgentStatus.COMPLETED,
                context_bundle=self.current_context,
                output=f"Planned {len(delegations)} delegations using {analysis.execution_strategy.value} strategy",
                token_usage=self.token_usage
            )

        except Exception as e:
            return AgentResult(
                agent_id=self.agent_id,
                agent_role=self.role,
                task_id=context.session_id,
                status=AgentStatus.FAILED,
                context_bundle=context,
                errors=[str(e)],
                token_usage=self.token_usage
            )

    async def perform_task_analysis(self, task: str) -> TaskAnalysis:
        """
        Perform comprehensive task analysis using multiple strategies.
        """
        # Basic complexity analysis
        complexity, required_agents = self.analyzer.analyze(task)

        # LLM-aided decomposition (Reduce & Delegate) when available
        llm_subtasks: List[SubTask] = []
        if llm_service.available():
            try:
                llm_subtasks = await self.llm_decompose(task)
            except Exception:
                llm_subtasks = []

        # Heuristic decomposition as baseline/fallback
        heuristic_subtasks = await self.decompose_task(task, complexity, required_agents)

        # Merge: prefer LLM subtasks when present, else heuristics
        subtasks = llm_subtasks or heuristic_subtasks

        # Determine execution strategy
        strategy = self.determine_execution_strategy(subtasks)

        # Estimate token usage
        estimated_tokens = self.estimate_token_usage(complexity, len(subtasks))

        # Identify dependencies
        dependencies = self.identify_dependencies(subtasks)

        # Risk assessment
        risk_factors = self.assess_risks(task, complexity)

        # Success criteria
        success_criteria = self.define_success_criteria(task, subtasks)

        return TaskAnalysis(
            original_task=task,
            complexity=complexity,
            estimated_tokens=estimated_tokens,
            required_agents=list(required_agents),
            subtasks=subtasks,
            execution_strategy=strategy,
            dependencies=dependencies,
            risk_factors=risk_factors,
            success_criteria=success_criteria
        )

    async def llm_decompose(self, task: str) -> List[SubTask]:
        """Use LLM to propose a subtask graph with roles and priorities."""
        text = await llm_service.complete(DECOMPOSE_PROMPT.format(task=task), max_tokens=900)
        plan_json = text.strip()
        # Extract JSON array if code fences are present
        if plan_json.startswith("```"):
            plan_json = plan_json.split("\n", 1)[1]
            if plan_json.startswith("json"):
                plan_json = plan_json.split("\n", 1)[1]
            plan_json = plan_json.rsplit("```", 1)[0]

        import json as _json
        data = None
        try:
            data = _json.loads(plan_json)
        except Exception:
            # Attempt critique/refinement even if parsing fails (LLM may normalize)
            pass

        # Critique + refine loop
        critique = await llm_service.complete(CRITIQUE_PROMPT.format(plan_json=plan_json), max_tokens=400)
        refined = await llm_service.complete(REFINE_PROMPT.format(plan_json=plan_json, critique=critique), max_tokens=900)
        ref = refined.strip()
        if ref.startswith("```"):
            ref = ref.split("\n", 1)[1]
            if ref.startswith("json"):
                ref = ref.split("\n", 1)[1]
            ref = ref.rsplit("```", 1)[0]
        try:
            data = _json.loads(ref)
        except Exception:
            # Fall back to initial parse attempt
            try:
                data = data or _json.loads(plan_json)
            except Exception:
                self._log_decision("LLM decomposition parse_failed", plan_json[:200])
                return []

        subtasks: List[SubTask] = []
        id_map: List[UUID] = []
        for i, item in enumerate(data):
            role_str = str(item.get("role", "worker")).lower()
            role = {
                "master": AgentRole.MASTER,
                "backend_prime": AgentRole.BACKEND_PRIME,
                "frontend_prime": AgentRole.FRONTEND_PRIME,
                "testing_prime": AgentRole.TESTING_PRIME,
            "worker": AgentRole.WORKER,
            "devops_prime": AgentRole.DEVOPS_PRIME,
            }.get(role_str, AgentRole.WORKER)
            prio = str(item.get("priority", "medium")).lower()
            priority = TaskPriority.HIGH if prio == "high" else TaskPriority.LOW if prio == "low" else TaskPriority.MEDIUM
            st_id = UUID(int=1 + i)  # ephemeral, unique within plan
            id_map.append(st_id)
            subtasks.append(SubTask(
                task_id=st_id,
                description=item.get("description", ""),
                agent_role=role,
                priority=priority,
                estimated_tokens=500,
                dependencies=[]
            ))

        # Wire dependencies
        for i, item in enumerate(data):
            depends = item.get("depends_on") or []
            try:
                subtasks[i].dependencies = [id_map[j] for j in depends if isinstance(j, int) and 0 <= j < len(id_map)]
            except Exception:
                pass

        # Log a decision summary
        self._log_decision("Decomposition plan created", f"{len(subtasks)} subtasks from LLM", [s.agent_role.value for s in subtasks])
        return subtasks

    async def decompose_task(self,
                            task: str,
                            complexity: TaskComplexity,
                            required_agents: Set[AgentRole]) -> List[SubTask]:
        """
        Decompose task into manageable subtasks.
        """
        subtasks = []
        task_lower = task.lower()

        # Example decomposition for authentication system
        if "authentication" in task_lower and "system" in task_lower:
            subtasks.extend([
                SubTask(
                    task_id=UUID('00000000-0000-0000-0000-000000000001'),
                    description="Design database schema for users, sessions, and tokens",
                    agent_role=AgentRole.BACKEND_PRIME,
                    priority=TaskPriority.HIGH,
                    estimated_tokens=500,
                    parallel_group=1
                ),
                SubTask(
                    task_id=UUID('00000000-0000-0000-0000-000000000002'),
                    description="Implement JWT token generation and validation",
                    agent_role=AgentRole.BACKEND_PRIME,
                    priority=TaskPriority.HIGH,
                    estimated_tokens=800,
                    dependencies=[UUID('00000000-0000-0000-0000-000000000001')]
                ),
                SubTask(
                    task_id=UUID('00000000-0000-0000-0000-000000000003'),
                    description="Create login and registration forms with validation",
                    agent_role=AgentRole.FRONTEND_PRIME,
                    priority=TaskPriority.HIGH,
                    estimated_tokens=600,
                    parallel_group=1
                ),
                SubTask(
                    task_id=UUID('00000000-0000-0000-0000-000000000004'),
                    description="Implement password reset flow with email",
                    agent_role=AgentRole.BACKEND_PRIME,
                    priority=TaskPriority.MEDIUM,
                    estimated_tokens=700,
                    dependencies=[UUID('00000000-0000-0000-0000-000000000002')]
                ),
                SubTask(
                    task_id=UUID('00000000-0000-0000-0000-000000000005'),
                    description="Create password reset UI components",
                    agent_role=AgentRole.FRONTEND_PRIME,
                    priority=TaskPriority.MEDIUM,
                    estimated_tokens=400,
                    dependencies=[UUID('00000000-0000-0000-0000-000000000003')]
                ),
                SubTask(
                    task_id=UUID('00000000-0000-0000-0000-000000000006'),
                    description="Write comprehensive tests for authentication flow",
                    agent_role=AgentRole.TESTING_PRIME,
                    priority=TaskPriority.HIGH,
                    estimated_tokens=900,
                    dependencies=[
                        UUID('00000000-0000-0000-0000-000000000002'),
                        UUID('00000000-0000-0000-0000-000000000003')
                    ]
                )
            ])

        # Generic decomposition for other tasks
        elif complexity == TaskComplexity.HIGH:
            # High complexity: multiple specialized subtasks
            if AgentRole.BACKEND_PRIME in required_agents:
                subtasks.append(SubTask(
                    task_id=UUID('00000000-0000-0000-0000-000000000010'),
                    description=f"Design and implement backend architecture for: {task[:100]}",
                    agent_role=AgentRole.BACKEND_PRIME,
                    priority=TaskPriority.HIGH,
                    estimated_tokens=1000
                ))

            if AgentRole.FRONTEND_PRIME in required_agents:
                subtasks.append(SubTask(
                    task_id=UUID('00000000-0000-0000-0000-000000000011'),
                    description=f"Build user interface components for: {task[:100]}",
                    agent_role=AgentRole.FRONTEND_PRIME,
                    priority=TaskPriority.HIGH,
                    estimated_tokens=800
                ))

            if AgentRole.TESTING_PRIME in required_agents:
                subtasks.append(SubTask(
                    task_id=UUID('00000000-0000-0000-0000-000000000012'),
                    description=f"Create comprehensive test suite for: {task[:100]}",
                    agent_role=AgentRole.TESTING_PRIME,
                    priority=TaskPriority.MEDIUM,
                    estimated_tokens=600
                ))

            if AgentRole.DEVOPS_PRIME in required_agents:
                subtasks.append(SubTask(
                    task_id=UUID('00000000-0000-0000-0000-000000000013'),
                    description=f"Establish CI/CD and deployment strategy for: {task[:100]}",
                    agent_role=AgentRole.DEVOPS_PRIME,
                    priority=TaskPriority.MEDIUM,
                    estimated_tokens=700
                ))

        elif complexity == TaskComplexity.MEDIUM:
            # Medium complexity: focused subtasks
            subtasks.append(SubTask(
                task_id=UUID('00000000-0000-0000-0000-000000000020'),
                description=task,
                agent_role=list(required_agents)[0] if required_agents else AgentRole.WORKER,
                priority=TaskPriority.MEDIUM,
                estimated_tokens=500
            ))

        else:
            # Low complexity: single subtask
            subtasks.append(SubTask(
                task_id=UUID('00000000-0000-0000-0000-000000000030'),
                description=task,
                agent_role=AgentRole.WORKER,
                priority=TaskPriority.LOW,
                estimated_tokens=200
            ))

        return subtasks

    def determine_execution_strategy(self, subtasks: List[SubTask]) -> ExecutionStrategy:
        """
        Determine optimal execution strategy based on dependencies.
        """
        # Check for parallel groups
        has_parallel_groups = any(s.parallel_group is not None for s in subtasks)

        # Check for dependencies
        has_dependencies = any(s.dependencies for s in subtasks)

        if has_parallel_groups and has_dependencies:
            return ExecutionStrategy.HYBRID
        elif has_dependencies:
            return ExecutionStrategy.SEQUENTIAL
        else:
            return ExecutionStrategy.PARALLEL

    def estimate_token_usage(self, complexity: TaskComplexity, subtask_count: int) -> int:
        """
        Estimate total token usage for the task.
        """
        base_tokens = {
            TaskComplexity.LOW: 500,
            TaskComplexity.MEDIUM: 2000,
            TaskComplexity.HIGH: 5000
        }

        return base_tokens[complexity] + (subtask_count * 300)

    def identify_dependencies(self, subtasks: List[SubTask]) -> Dict[str, List[str]]:
        """
        Map dependencies between subtasks.
        """
        dependencies = {}
        for subtask in subtasks:
            if subtask.dependencies:
                dependencies[str(subtask.task_id)] = [str(d) for d in subtask.dependencies]
        return dependencies

    def assess_risks(self, task: str, complexity: TaskComplexity) -> List[str]:
        """
        Identify potential risks in task execution.
        """
        risks = []

        if complexity == TaskComplexity.HIGH:
            risks.append("Complex integration may require multiple iterations")
            risks.append("Token usage may exceed estimates")

        if "api" in task.lower() or "integration" in task.lower():
            risks.append("External dependencies may affect reliability")

        if "migration" in task.lower() or "refactor" in task.lower():
            risks.append("May affect existing functionality")

        return risks

    def define_success_criteria(self, task: str, subtasks: List[SubTask]) -> List[str]:
        """
        Define measurable success criteria.
        """
        criteria = [
            f"All {len(subtasks)} subtasks completed successfully",
            "No critical errors in execution",
            "Token usage within 20% of estimate"
        ]

        if "test" in task.lower():
            criteria.append("All tests passing")

        if "api" in task.lower():
            criteria.append("API endpoints responding correctly")

        if "ui" in task.lower() or "interface" in task.lower():
            criteria.append("UI components rendering without errors")

        return criteria

    async def create_execution_plan(self, analysis: TaskAnalysis) -> List[TaskDelegation]:
        """
        Create detailed execution plan with delegations.
        """
        delegations = []

        for subtask in analysis.subtasks:
            # Create context bundle for each subtask
            subtask_context = ContextBundle(
                parent_task=analysis.original_task,
                max_tokens=subtask.estimated_tokens
            )
            subtask_context.root_task_id = self.current_context.ensure_root() if self.current_context else None

            # Add relevant pointers
            subtask_context.add_pointer("task_analysis", f"master_prime/analysis/{self.agent_id}")
            subtask_context.add_pointer("dependencies", str(subtask.dependencies))

            # Prepare delegation metadata with ContextDelegator
            work_completed = {
                "output": "",
                "artifacts_created": self.current_context.artifacts_created if self.current_context else [],
                "decisions_made": [
                    {
                        "decision": d.decision,
                        "rationale": d.rationale,
                        "timestamp": d.timestamp.isoformat(),
                    }
                    for d in (self.current_context.decisions_made if self.current_context else [])
                ],
                "structural_pointers": self.current_context.structural_pointers if self.current_context else {},
            }
            handoff_bundle = ContextDelegator.prepare_handoff_bundle(
                subtask.description,
                self.role.value,
                subtask.agent_role.value,
                work_completed,
                ["Complete delegated subtask"],
            )
            subtask_context.add_pointer("handoff_metadata", json.dumps(handoff_bundle))

            # Create delegation
            delegation = TaskDelegation(
                source_agent_id=self.agent_id,
                target_specialization=subtask.agent_role,
                task_description=subtask.description,
                context_bundle=subtask_context,
                priority=subtask.priority,
                dependencies=subtask.dependencies
            )

            delegations.append(delegation)

        return delegations

    async def spawn_and_delegate(self, delegations: List[TaskDelegation]) -> List[TaskDelegation]:
        """
        Spawn required agents and delegate tasks.
        """
        # In real implementation, this would create actual agent instances
        # For now, we'll track the delegations
        for delegation in delegations:
            self.active_delegations[delegation.context_bundle.session_id] = delegation

            # Log the spawning decision
            self._log_decision(
                f"Spawning {delegation.target_specialization.value} agent",
                f"Task: {delegation.task_description[:50]}",
                []
            )

        return delegations

    async def coordinate_execution(self,
                                  delegations: List[TaskDelegation],
                                  strategy: ExecutionStrategy) -> List[AgentResult]:
        """
        Coordinate execution based on strategy.
        """
        results = []

        if strategy == ExecutionStrategy.PARALLEL:
            # Execute all tasks in parallel
            # In real implementation, this would use asyncio.gather()
            pass

        elif strategy == ExecutionStrategy.SEQUENTIAL:
            # Execute tasks one by one, respecting dependencies
            # In real implementation, this would execute in dependency order
            pass

        elif strategy == ExecutionStrategy.HYBRID:
            # Execute parallel groups, then dependent tasks
            # In real implementation, this would batch by parallel_group
            pass

        # For now, create mock results
        for delegation in delegations:
            result = AgentResult(
                agent_id=self.agent_id,
                agent_role=delegation.target_specialization,
                task_id=delegation.context_bundle.session_id,
                status=AgentStatus.COMPLETED,
                context_bundle=delegation.context_bundle,
                output=f"Completed: {delegation.task_description}",
                token_usage={"input": 100, "output": 100, "total": 200}
            )
            results.append(result)

        return results

    async def integrate_results(self, results: List[AgentResult]) -> AgentResult:
        """
        Integrate results from all agents into final result.
        """
        # Combine all context bundles
        integrated_context = ContextBundle(
            parent_task=self.current_context.parent_task
        )

        # Merge artifacts and decisions
        for result in results:
            integrated_context.artifacts_created.extend(result.context_bundle.artifacts_created)
            integrated_context.decisions_made.extend(result.context_bundle.decisions_made)

        # Calculate total token usage
        total_tokens = sum(r.token_usage.get("total", 0) for r in results)

        # Create final integrated result
        return AgentResult(
            agent_id=self.agent_id,
            agent_role=self.role,
            task_id=self.current_context.session_id,
            status=AgentStatus.COMPLETED,
            context_bundle=integrated_context,
            output=f"Successfully completed task with {len(results)} agents",
            token_usage={"total": total_tokens},
            execution_time=0.0  # Would calculate actual time
        )
