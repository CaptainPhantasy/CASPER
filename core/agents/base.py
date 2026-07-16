"""
BaseAgent class with handoff protocol for CASPER Prime.
Provides foundation for all specialized agents with context management.
"""

import asyncio
import json
import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple
from uuid import UUID, uuid4

logger = logging.getLogger(__name__)


class AgentRole(Enum):
    """Defines specialized agent roles in the hierarchy."""

    MASTER = "master"
    FRONTEND_PRIME = "frontend_prime"
    BACKEND_PRIME = "backend_prime"
    TESTING_PRIME = "testing_prime"
    DEVOPS_PRIME = "devops_prime"
    WORKER = "worker"


class TaskPriority(Enum):
    """Task priority levels."""

    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class AgentStatus(Enum):
    """Agent execution status."""

    IDLE = "idle"
    PLANNING = "planning"
    BUILDING = "building"
    REVIEWING = "reviewing"
    COMPLETED = "completed"
    FAILED = "failed"
    BLOCKED = "blocked"


@dataclass
class Decision:
    """Records a decision made by an agent."""

    decision_id: UUID = field(default_factory=uuid4)
    timestamp: datetime = field(default_factory=datetime.now)
    decision: str = ""
    rationale: str = ""
    alternatives_considered: List[str] = field(default_factory=list)


@dataclass
class ContextBundle:
    """
    Lightweight context passed between agents.
    Follows R&D Framework - Reduce & Delegate strategies.
    """

    session_id: UUID = field(default_factory=uuid4)
    root_task_id: Optional[UUID] = None
    parent_task: str = ""
    structural_pointers: Dict[str, str] = field(default_factory=dict)
    decisions_made: List[Decision] = field(default_factory=list)
    next_actions: List[str] = field(default_factory=list)
    artifacts_created: List[str] = field(default_factory=list)
    token_count: int = 0
    max_tokens: int = 2000

    def add_pointer(self, key: str, location: str):
        """Add a structural pointer to where information can be found."""
        self.structural_pointers[key] = location

    def ensure_root(self) -> UUID:
        """Ensure the bundle carries a stable root task identifier."""
        if self.root_task_id is None:
            self.root_task_id = self.session_id
        return self.root_task_id

    def add_decision(
        self, decision: str, rationale: str, alternatives: List[str] = None
    ):
        """Record a decision made during task execution."""
        self.decisions_made.append(
            Decision(
                decision=decision,
                rationale=rationale,
                alternatives_considered=alternatives or [],
            )
        )

    def compress_if_needed(self):
        """Compress context if approaching token limit."""
        if self.token_count > self.max_tokens * 0.8:
            # Keep only most recent decisions
            if len(self.decisions_made) > 5:
                self.decisions_made = self.decisions_made[-5:]
            # Summarize structural pointers
            if len(self.structural_pointers) > 10:
                most_important = dict(list(self.structural_pointers.items())[-10:])
                self.structural_pointers = most_important

    def to_dict(self) -> Dict[str, Any]:
        """Serialize context bundle for transmission."""
        return {
            "session_id": str(self.session_id),
            "root_task_id": str(self.ensure_root()),
            "parent_task": self.parent_task,
            "structural_pointers": self.structural_pointers,
            "decisions_made": [
                {
                    "decision": d.decision,
                    "rationale": d.rationale,
                    "alternatives": d.alternatives_considered,
                    "timestamp": d.timestamp.isoformat(),
                }
                for d in self.decisions_made
            ],
            "next_actions": self.next_actions,
            "artifacts_created": self.artifacts_created,
            "token_count": self.token_count,
        }


@dataclass
class TaskDelegation:
    """Request to delegate work to another agent."""

    source_agent_id: UUID
    target_specialization: AgentRole
    task_description: str
    context_bundle: ContextBundle
    priority: TaskPriority = TaskPriority.MEDIUM
    dependencies: List[UUID] = field(default_factory=list)
    root_task_id: Optional[UUID] = None

    def __post_init__(self):
        if self.root_task_id is None:
            self.root_task_id = self.context_bundle.ensure_root()
        else:
            self.context_bundle.root_task_id = self.root_task_id


@dataclass
class AgentResult:
    """Result from an agent's task execution."""

    agent_id: UUID
    agent_role: AgentRole
    task_id: UUID
    status: AgentStatus
    context_bundle: ContextBundle
    output: str = ""
    errors: List[str] = field(default_factory=list)
    token_usage: Dict[str, int] = field(default_factory=dict)
    execution_time: float = 0.0


@dataclass
class ProgressUpdate:
    """Real-time progress update from an agent."""

    agent_id: UUID
    status: AgentStatus
    progress: int  # 0-100
    message: str
    token_usage: Dict[str, int]
    timestamp: datetime = field(default_factory=datetime.now)
    decisions: List[Dict[str, str]] = field(default_factory=list)


class BaseAgent(ABC):
    """
    Base class for all CASPER Prime agents.
    Implements handoff protocol and context management.
    """

    def __init__(self, agent_id: UUID = None, role: AgentRole = AgentRole.WORKER):
        self.agent_id = agent_id or uuid4()
        self.role = role
        self.status = AgentStatus.IDLE
        self.current_context: Optional[ContextBundle] = None
        self.task_history: List[AgentResult] = []
        self.token_usage = {"input": 0, "output": 0, "total": 0}
        self.progress_callbacks: List[callable] = []

    @abstractmethod
    async def analyze_task(self, task: str, context: ContextBundle) -> Tuple[bool, str]:
        """
        Analyze if this agent can handle the task.
        Returns (can_handle, reason).
        """
        pass

    @abstractmethod
    async def execute_task(self, task: str, context: ContextBundle) -> AgentResult:
        """
        Execute the assigned task with given context.
        Must update progress and manage handoffs.
        """
        pass

    async def initialize(self, context: ContextBundle) -> None:
        """
        Initialize the agent with system context and prompting.
        Called during layer spin-up sequence.
        """
        self.current_context = context
        self.status = AgentStatus.IDLE

        # Process initialization prompt if provided
        if "initialization_prompt" in context.structural_pointers:
            prompt = context.structural_pointers["initialization_prompt"]
            # Agent-specific initialization logic can be added in subclasses

        logger.info(
            f"Agent {self.role.value} initialized with session {context.session_id}"
        )

    async def shutdown(self) -> None:
        """
        Gracefully shutdown the agent.
        Clean up resources and save state if needed.
        """
        self.status = AgentStatus.COMPLETED

        # Save task history if needed
        if self.task_history:
            logger.info(
                f"Agent {self.role.value} completed {len(self.task_history)} tasks"
            )

        # Clear context to free memory
        self.current_context = None

        logger.info(f"Agent {self.role.value} shutdown complete")

    async def handoff(
        self,
        target_role: AgentRole,
        task: str,
        priority: TaskPriority = TaskPriority.MEDIUM,
    ) -> TaskDelegation:
        """
        Create a handoff to another agent.
        Packages current context efficiently.
        """
        if not self.current_context:
            self.current_context = ContextBundle()

        # Compress context before handoff
        self.current_context.compress_if_needed()

        # Propagate root task identifier
        root_task_id = self.current_context.ensure_root()

        # Add handoff metadata
        self.current_context.next_actions.append(f"Continue with: {task}")

        delegation = TaskDelegation(
            source_agent_id=self.agent_id,
            target_specialization=target_role,
            task_description=task,
            context_bundle=self.current_context,
            priority=priority,
            root_task_id=root_task_id,
        )

        await self._update_progress(
            AgentStatus.COMPLETED,
            100,
            f"Handing off to {target_role.value}: {task[:50]}...",
        )

        return delegation

    async def receive_handoff(self, delegation: TaskDelegation):
        """
        Receive work from another agent.
        Unpacks context and prepares for execution.
        """
        self.current_context = delegation.context_bundle
        self.status = AgentStatus.PLANNING

        await self._update_progress(
            AgentStatus.PLANNING,
            0,
            f"Received task from {delegation.source_agent_id}: {delegation.task_description[:50]}...",
        )

        # Analyze task feasibility
        can_handle, reason = await self.analyze_task(
            delegation.task_description, self.current_context
        )

        if not can_handle:
            return AgentResult(
                agent_id=self.agent_id,
                agent_role=self.role,
                task_id=delegation.context_bundle.session_id,
                status=AgentStatus.BLOCKED,
                context_bundle=self.current_context,
                errors=[f"Cannot handle task: {reason}"],
                token_usage=self.token_usage,
            )

        # Execute the task
        return await self.execute_task(
            delegation.task_description, self.current_context
        )

    async def _update_progress(self, status: AgentStatus, progress: int, message: str):
        """Send progress update to all registered callbacks."""
        self.status = status
        # Prepare recent decisions for UI
        decisions: List[Dict[str, str]] = []
        if self.current_context and self.current_context.decisions_made:
            for d in self.current_context.decisions_made[-5:]:
                decisions.append(
                    {
                        "decision": getattr(d, "decision", ""),
                        "rationale": getattr(d, "rationale", ""),
                        "timestamp": getattr(
                            d, "timestamp", datetime.now()
                        ).isoformat(),
                    }
                )

        update = ProgressUpdate(
            agent_id=self.agent_id,
            status=status,
            progress=progress,
            message=message,
            token_usage=self.token_usage.copy(),
            decisions=decisions,
        )

        for callback in self.progress_callbacks:
            try:
                await callback(update)
            except Exception as e:
                print(f"Progress callback error: {e}")

    def register_progress_callback(self, callback: callable):
        """Register a callback for progress updates."""
        self.progress_callbacks.append(callback)

    def _track_tokens(self, input_tokens: int, output_tokens: int):
        """Track token usage for economics."""
        self.token_usage["input"] += input_tokens
        self.token_usage["output"] += output_tokens
        self.token_usage["total"] += input_tokens + output_tokens

        if self.current_context:
            self.current_context.token_count = self.token_usage["total"]

    def _log_decision(
        self, decision: str, rationale: str, alternatives: List[str] = None
    ):
        """Log a decision to the context bundle."""
        if self.current_context:
            self.current_context.add_decision(decision, rationale, alternatives)

    def _add_artifact(self, artifact_path: str):
        """Record an artifact created during execution."""
        if self.current_context:
            self.current_context.artifacts_created.append(artifact_path)

    def _add_pointer(self, key: str, location: str):
        """Add a structural pointer to the context."""
        if self.current_context:
            self.current_context.add_pointer(key, location)
