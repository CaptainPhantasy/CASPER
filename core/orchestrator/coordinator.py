"""
Agent Coordinator - Manages agent lifecycle and execution.
Handles spawning, monitoring, and coordination of specialized agents.
"""

import asyncio
import time
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Optional, Set, Tuple
from uuid import UUID, uuid4

from core.agents.base import (
    AgentRole, AgentStatus, BaseAgent, AgentResult,
    TaskDelegation, ProgressUpdate, TaskPriority
)
from core.context.manager import ContextManager
from core.context.reducer import ContextReducer
from core.orchestrator.task_analyzer import TaskAnalyzer


@dataclass
class AgentInstance:
    """Represents a running agent instance."""
    agent_id: UUID
    agent_role: AgentRole
    agent: BaseAgent
    status: AgentStatus
    task_id: Optional[UUID] = None
    started_at: datetime = field(default_factory=datetime.now)
    completed_at: Optional[datetime] = None
    parent_agent_id: Optional[UUID] = None


class AgentPool:
    """
    Manages pool of available agents for different roles.
    Implements agent reuse and resource management.
    """

    def __init__(self, max_agents_per_role: int = 5):
        self.max_agents_per_role = max_agents_per_role
        self.available_agents: Dict[AgentRole, List[BaseAgent]] = {
            role: [] for role in AgentRole
        }
        self.busy_agents: Dict[UUID, AgentInstance] = {}
        self.agent_stats: Dict[UUID, Dict] = {}

    async def get_agent(self, role: AgentRole, create_if_needed: bool = True) -> Optional[BaseAgent]:
        """
        Get an available agent from the pool or create new one.
        """
        # Check for available agent
        if self.available_agents[role]:
            agent = self.available_agents[role].pop(0)
            return agent

        # Create new agent if allowed
        if create_if_needed:
            if len([a for a in self.busy_agents.values() if a.agent_role == role]) < self.max_agents_per_role:
                agent = await self._create_agent(role)
                return agent

        return None

    async def _create_agent(self, role: AgentRole) -> BaseAgent:
        """
        Factory method to create specialized agents.
        """
        # Import dynamically to avoid circular imports
        if role == AgentRole.MASTER:
            from core.agents.master_prime import MasterPrimeAgent
            return MasterPrimeAgent()
        elif role == AgentRole.BACKEND_PRIME:
            from core.agents.backend_prime import BackendPrimeAgent
            return BackendPrimeAgent()
        elif role == AgentRole.FRONTEND_PRIME:
            from core.agents.frontend_prime import FrontendPrimeAgent
            return FrontendPrimeAgent()
        elif role == AgentRole.TESTING_PRIME:
            from core.agents.testing_prime import TestingPrimeAgent
            return TestingPrimeAgent()
        elif role == AgentRole.DEVOPS_PRIME:
            from core.agents.devops_prime import DevOpsPrimeAgent
            return DevOpsPrimeAgent()
        else:
            from core.agents.worker import WorkerAgent
            return WorkerAgent()

    def mark_busy(self, agent: BaseAgent, task_id: UUID):
        """
        Mark agent as busy with a task.
        """
        instance = AgentInstance(
            agent_id=agent.agent_id,
            agent_role=agent.role,
            agent=agent,
            status=AgentStatus.IDLE,
            task_id=task_id
        )
        self.busy_agents[agent.agent_id] = instance

    def release_agent(self, agent_id: UUID):
        """
        Release agent back to available pool.
        """
        if agent_id in self.busy_agents:
            instance = self.busy_agents.pop(agent_id)
            instance.completed_at = datetime.now()

            # Update stats
            if agent_id not in self.agent_stats:
                self.agent_stats[agent_id] = {
                    "tasks_completed": 0,
                    "total_time": 0,
                    "errors": 0
                }

            stats = self.agent_stats[agent_id]
            stats["tasks_completed"] += 1
            stats["total_time"] += (instance.completed_at - instance.started_at).total_seconds()

            # Return to available pool
            if len(self.available_agents[instance.agent_role]) < self.max_agents_per_role:
                self.available_agents[instance.agent_role].append(instance.agent)

    def get_pool_stats(self) -> Dict:
        """
        Get statistics about the agent pool.
        """
        stats = {
            "total_agents": sum(len(agents) for agents in self.available_agents.values()) + len(self.busy_agents),
            "busy_agents": len(self.busy_agents),
            "available_by_role": {role.value: len(agents) for role, agents in self.available_agents.items()},
            "performance": self.agent_stats
        }
        return stats


class AgentCoordinator:
    """
    Central coordinator for all agent activities in CASPER Prime.
    Manages spawning, delegation, execution, and monitoring.
    """

    def __init__(self, context_manager: ContextManager = None):
        self.context_manager = context_manager or ContextManager()
        self.agent_pool = AgentPool()
        self.active_tasks: Dict[UUID, TaskDelegation] = {}
        self.task_queue: asyncio.Queue = asyncio.Queue()
        self.results_queue: asyncio.Queue = asyncio.Queue()
        self.progress_callbacks: List[callable] = []
        self.executor = ThreadPoolExecutor(max_workers=10)
        self._running = False
        self.token_usage_total = 0
        self.completed_task_count = 0
        self.task_children: Dict[UUID, Set[UUID]] = defaultdict(set)
        self.child_to_root: Dict[UUID, UUID] = {}
        self.pending_root_results: Dict[UUID, AgentResult] = {}

    async def start(self):
        """
        Start the coordinator background tasks.
        """
        self._running = True
        asyncio.create_task(self._process_task_queue())
        asyncio.create_task(self._monitor_agents())

    def _register_delegation(self, delegation: TaskDelegation):
        """Track delegation relationships for orchestration."""
        child_id = delegation.context_bundle.session_id
        root_id = delegation.root_task_id or delegation.context_bundle.ensure_root()
        delegation.context_bundle.root_task_id = root_id
        self.task_children.setdefault(root_id, set())
        if child_id != root_id:
            self.task_children[root_id].add(child_id)
            self.child_to_root[child_id] = root_id

    def _merge_child_into_root(self, root_result: Optional[AgentResult], child_result: AgentResult):
        """Accumulate child context and tokens into the pending root result."""
        if not root_result or not hasattr(root_result, "context_bundle"):
            return
        if hasattr(child_result, "token_usage"):
            for key, value in child_result.token_usage.items():
                if value is None:
                    continue
                root_result.token_usage[key] = root_result.token_usage.get(key, 0) + value
        child_context = getattr(child_result, "context_bundle", None)
        root_context = root_result.context_bundle
        if child_context and root_context:
            for artifact in getattr(child_context, "artifacts_created", []):
                if artifact not in root_context.artifacts_created:
                    root_context.artifacts_created.append(artifact)
            for decision in getattr(child_context, "decisions_made", []):
                root_context.decisions_made.append(decision)
        # Append textual summary for traceability
        snippet = (child_result.output or "").strip().splitlines()[0] if child_result.output else ""
        summary_line = f"{child_result.agent_role.value} ({child_result.status.value})"
        if snippet:
            summary_line += f": {snippet[:120]}"
        existing_output = root_result.output or ""
        root_result.output = (existing_output + "\n- " + summary_line).strip()

    async def stop(self):
        """
        Stop the coordinator.
        """
        self._running = False
        self.executor.shutdown(wait=False)

    async def submit_task(self, task: str, priority: TaskPriority = TaskPriority.MEDIUM) -> UUID:
        """
        Submit a new task to the coordinator.
        Returns task ID for tracking.
        """
        task_id = uuid4()

        # Analyze task to determine optimal agent routing
        metrics, required_agents, suggested_priority = TaskAnalyzer.analyze_task(task)

        # Use suggested priority if no explicit priority provided
        if priority == TaskPriority.MEDIUM and suggested_priority != TaskPriority.MEDIUM:
            priority = suggested_priority

        # Always initialize a typed ContextBundle for agent compatibility
        context_bundle = self.context_manager.load_context(task_id)
        if isinstance(context_bundle, dict):
            # Convert to ContextBundle if an older dict exists
            from core.agents.base import ContextBundle as _CB
            cb = _CB()
            cb.session_id = task_id
            cb.root_task_id = context_bundle.get("root_task_id") or task_id
            cb.parent_task = context_bundle.get("parent_task", task)
            cb.structural_pointers = context_bundle.get("structural_pointers", {})
            for d in context_bundle.get("decisions_made", []):
                try:
                    cb.add_decision(d.get("decision", ""), d.get("rationale", ""), d.get("alternatives", []))
                except Exception:
                    pass
            cb.next_actions = context_bundle.get("next_actions", [])
            cb.artifacts_created = context_bundle.get("artifacts_created", [])
            cb.token_count = context_bundle.get("token_count", 0)
            context_bundle = cb
        elif context_bundle is None:
            from core.agents.base import ContextBundle as _CB
            context_bundle = _CB()
            context_bundle.session_id = task_id
            context_bundle.root_task_id = task_id
            context_bundle.parent_task = task

        # Determine target agent based on analysis
        # If only worker is needed, route directly to worker instead of master
        if required_agents == {AgentRole.WORKER}:
            target_agent = AgentRole.WORKER
        else:
            target_agent = AgentRole.MASTER

        delegation = TaskDelegation(
            source_agent_id=UUID('00000000-0000-0000-0000-000000000000'),  # System
            target_specialization=target_agent,
            task_description=task,
            context_bundle=context_bundle,
            priority=priority,
            root_task_id=task_id
        )

        # Add to queue
        await self.task_queue.put((priority.value, delegation))
        self.active_tasks[task_id] = delegation

        return task_id

    async def _process_task_queue(self):
        """
        Background task to process queued delegations.
        """
        while self._running:
            try:
                # Get highest priority task
                if not self.task_queue.empty():
                    _, delegation = await self.task_queue.get()
                    await self._execute_delegation(delegation)
                else:
                    await asyncio.sleep(0.1)
            except Exception as e:
                print(f"Task processing error: {e}")

    async def _execute_delegation(self, delegation: TaskDelegation):
        """
        Execute a single delegation by spawning appropriate agent.
        """
        # Get agent from pool
        agent = await self.agent_pool.get_agent(delegation.target_specialization)
        if not agent:
            # Add retry counter to prevent infinite retries
            retry_count = getattr(delegation, '_retry_count', 0)
            if retry_count < 3:  # Max 3 retries
                delegation._retry_count = retry_count + 1
                await self.task_queue.put((delegation.priority.value, delegation))
                await asyncio.sleep(1)
            else:
                print(f"Failed to get agent for {delegation.target_specialization} after 3 retries")
            return

        # Track delegation relationships
        self._register_delegation(delegation)

        # Mark agent as busy
        self.agent_pool.mark_busy(agent, delegation.context_bundle.session_id)

        # Apply final compression before handoff
        delegation.context_bundle.compress_if_needed()

        # Register progress callback
        agent.register_progress_callback(self._handle_progress_update)

        try:
            # Execute task
            result = await agent.receive_handoff(delegation)

            # Check for new delegations from this agent before handling the result
            if hasattr(agent, 'active_delegations') and agent.active_delegations:
                for delegation_id, new_delegation in list(agent.active_delegations.items()):
                    new_delegation.root_task_id = new_delegation.root_task_id or delegation.context_bundle.ensure_root()
                    self._register_delegation(new_delegation)
                    if delegation_id not in self.active_tasks:
                        await self.task_queue.put((new_delegation.priority.value, new_delegation))
                        self.active_tasks[delegation_id] = new_delegation
                agent.active_delegations.clear()

            # Handle result
            await self._handle_agent_result(result)

        except Exception as e:
            print(f"Agent execution error: {e}")
            result = AgentResult(
                agent_id=agent.agent_id,
                agent_role=agent.role,
                task_id=delegation.context_bundle.session_id,
                status=AgentStatus.FAILED,
                context_bundle=delegation.context_bundle,
                errors=[str(e)]
            )
            await self._handle_agent_result(result)

        finally:
            # Release agent
            self.agent_pool.release_agent(agent.agent_id)

    async def _handle_agent_result(self, result: AgentResult):
        """
        Handle result from agent execution.
        """
        queue_payloads: List[Tuple[AgentResult, str]] = []

        # Determine root relationship
        try:
            root_id = result.context_bundle.ensure_root() if hasattr(result.context_bundle, "ensure_root") else self.child_to_root.get(result.task_id, result.task_id)
        except Exception:
            root_id = self.child_to_root.get(result.task_id, result.task_id)

        is_root_result = result.task_id == root_id

        if is_root_result:
            children_pending = set(self.task_children.get(root_id, set()))
            if children_pending:
                if result.status == AgentStatus.COMPLETED:
                    result.status = AgentStatus.REVIEWING
                self.pending_root_results[root_id] = result
                queue_payloads.append((result, f"Waiting on {len(children_pending)} delegated agent(s)"))
            else:
                queue_payloads.append((result, f"Task completed by {result.agent_role.value}"))
                self.task_children.pop(root_id, None)
                self.pending_root_results.pop(root_id, None)
        else:
            # Merge into parent and mark this child complete
            self._merge_child_into_root(self.pending_root_results.get(root_id), result)
            child_set = self.task_children.get(root_id)
            if child_set and result.task_id in child_set:
                child_set.discard(result.task_id)
            self.child_to_root.pop(result.task_id, None)
            queue_payloads.append((result, f"Task completed by {result.agent_role.value}"))

            # Finalize root when all children resolved
            if child_set is not None and len(child_set) == 0:
                self.task_children.pop(root_id, None)
                root_result = self.pending_root_results.pop(root_id, None)
                if root_result:
                    root_result.status = AgentStatus.COMPLETED
                    if hasattr(root_result.context_bundle, "compress_if_needed"):
                        root_result.context_bundle.compress_if_needed()
                        root_bundle_dict = root_result.context_bundle.to_dict()
                        self.context_manager.store_context(root_result.task_id, root_bundle_dict)
                    queue_payloads.append((root_result, f"Task completed by {root_result.agent_role.value}"))

        # Update metrics for the direct agent result
        self.token_usage_total += result.token_usage.get("total", 0)
        if result.status == AgentStatus.COMPLETED:
            self.completed_task_count += 1

        # Persist context for the direct agent result
        if hasattr(result.context_bundle, "to_dict"):
            bundle_dict = result.context_bundle.to_dict()
        else:
            bundle_dict = result.context_bundle or {}

        reduced_bundle = ContextReducer.reduce_to_token_limit(bundle_dict)
        self.context_manager.store_context(result.task_id, reduced_bundle)

        # Mark this delegation as no longer active
        self.active_tasks.pop(result.task_id, None)

        # Emit queued results and notify callbacks
        for emitted_result, message in queue_payloads:
            await self.results_queue.put(emitted_result)
            progress_status = emitted_result.status
            progress_value = 100 if progress_status == AgentStatus.COMPLETED else (90 if progress_status == AgentStatus.REVIEWING else 0)
            note = message or f"Task completed by {emitted_result.agent_role.value}"

            if emitted_result is not result and emitted_result.status == AgentStatus.COMPLETED:
                self.completed_task_count += 1

            for callback in self.progress_callbacks:
                try:
                    await callback(ProgressUpdate(
                        agent_id=emitted_result.agent_id,
                        status=progress_status,
                        progress=progress_value,
                        message=note,
                        token_usage=emitted_result.token_usage
                    ))
                except Exception as e:
                    print(f"Callback error: {e}")

    async def _handle_progress_update(self, update: ProgressUpdate):
        """
        Handle progress update from agent.
        """
        # Forward to registered callbacks
        for callback in self.progress_callbacks:
            try:
                await callback(update)
            except Exception as e:
                print(f"Progress callback error: {e}")

    async def _monitor_agents(self):
        """
        Monitor agent health and performance.
        """
        while self._running:
            try:
                # Check for stuck agents
                current_time = datetime.now()
                for agent_id, instance in list(self.agent_pool.busy_agents.items()):
                    # If agent has been busy for > 5 minutes, consider it stuck
                    if (current_time - instance.started_at).total_seconds() > 300:
                        print(f"Warning: Agent {agent_id} may be stuck")
                        # Could implement recovery logic here

                # Log pool stats periodically
                stats = self.agent_pool.get_pool_stats()
                if stats["busy_agents"] > 0:
                    print(f"Agent pool: {stats['busy_agents']} busy, {stats['total_agents']} total")

                await asyncio.sleep(10)  # Check every 10 seconds

            except Exception as e:
                print(f"Monitoring error: {e}")

    def register_progress_callback(self, callback: callable):
        """
        Register callback for progress updates.
        """
        self.progress_callbacks.append(callback)

    async def get_task_status(self, task_id: UUID) -> Dict:
        """
        Get status of a specific task.
        """
        if task_id in self.active_tasks:
            delegation = self.active_tasks[task_id]
            return {
                "task_id": str(task_id),
                "status": "active",
                "task": delegation.task_description,
                "assigned_to": delegation.target_specialization.value
            }

        # Check completed tasks in context
        context = self.context_manager.get_context_summary(task_id)
        return context

    async def get_results(self, limit: int = 10) -> List[AgentResult]:
        """
        Get recent results from the results queue.
        """
        results = []
        while not self.results_queue.empty() and len(results) < limit:
            result = await self.results_queue.get()
            results.append(result)
        return results

    async def coordinate_parallel_execution(self,
                                           delegations: List[TaskDelegation]) -> List[AgentResult]:
        """
        Coordinate parallel execution of multiple delegations.
        """
        tasks = []
        for delegation in delegations:
            task = asyncio.create_task(self._execute_delegation(delegation))
            tasks.append(task)

        # Wait for all to complete
        await asyncio.gather(*tasks)

        # Collect results
        results = await self.get_results(len(delegations))
        return results

    async def coordinate_sequential_execution(self,
                                             delegations: List[TaskDelegation]) -> List[AgentResult]:
        """
        Coordinate sequential execution respecting dependencies.
        """
        results = []
        completed_tasks: Set[UUID] = set()

        while delegations:
            # Find delegations with satisfied dependencies
            ready = [
                d for d in delegations
                if not d.dependencies or all(dep in completed_tasks for dep in d.dependencies)
            ]

            if not ready:
                # Deadlock or missing dependency
                print("Warning: No delegations ready, possible dependency issue")
                break

            # Execute ready delegations in parallel
            batch_results = await self.coordinate_parallel_execution(ready)
            results.extend(batch_results)

            # Mark as completed
            for result in batch_results:
                completed_tasks.add(result.task_id)

            # Remove executed delegations
            delegations = [d for d in delegations if d not in ready]

        return results

    def get_coordinator_stats(self) -> Dict:
        """
        Get overall coordinator statistics.
        """
        return {
            "active_tasks": len(self.active_tasks),
            "queued_tasks": self.task_queue.qsize(),
            "agent_pool": self.agent_pool.get_pool_stats(),
            "context_sessions": len(self.context_manager.get_active_sessions()),
            "token_usage_total": self.token_usage_total,
            "completed_tasks": self.completed_task_count,
        }
