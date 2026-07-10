"""
CASPER Agent Layer Initialization System
Handles the spin-up sequence for all agent layers with proper prompting.
"""

import asyncio
import logging
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional, Any
from uuid import UUID, uuid4

from core.agents.base import AgentRole, AgentStatus, BaseAgent, ContextBundle
from core.orchestrator.coordinator import AgentCoordinator
from core.context.manager import ContextManager

logger = logging.getLogger(__name__)


class AgentLayer(Enum):
    """Agent layer hierarchy in CASPER system."""
    LAYER_0 = "layer_0"  # Foundation layer - system orchestration
    LAYER_1 = "layer_1"  # Prime agents layer - specialized domains
    LAYER_2 = "layer_2"  # Task execution layer - worker agents
    LAYER_3 = "layer_3"  # Integration layer - external services


@dataclass
class LayerConfiguration:
    """Configuration for each agent layer."""
    layer: AgentLayer
    agents: List[AgentRole]
    initialization_prompt: str
    max_agents: int = 5
    parallel_init: bool = True
    dependencies: List[AgentLayer] = field(default_factory=list)


class AgentLayerInitializer:
    """
    Manages the initialization and spin-up of agent layers.
    Ensures proper sequencing and prompting of agents.
    """

    # Layer 0 Foundation Prompt - System Orchestrator
    LAYER_0_PROMPT = """
    You are the Layer 0 Foundation Agent for CASPER Prime.

    ROLE: System Orchestrator and Master Coordinator

    RESPONSIBILITIES:
    1. Initialize and manage the agent hierarchy
    2. Coordinate inter-layer communication
    3. Monitor system health and performance
    4. Manage context flow between agents
    5. Handle system-wide decisions and escalations

    INITIALIZATION SEQUENCE:
    - Verify system resources and dependencies
    - Initialize context management system
    - Prepare agent spawning infrastructure
    - Establish communication channels
    - Begin Layer 1 agent initialization

    OPERATIONAL PRINCIPLES:
    - Maintain system stability as highest priority
    - Optimize resource allocation across agents
    - Ensure clean handoffs between layers
    - Monitor and prevent circular dependencies
    - Maintain audit trail of all decisions

    CONTEXT MANAGEMENT:
    - Maximum context per agent: 200,000 tokens
    - Context compression at 80% threshold
    - Structural pointers for large artifacts
    - Session-based context isolation

    You are now active and ready to orchestrate the CASPER system.
    """

    # Layer 1 Prime Agents Prompt Template
    LAYER_1_PROMPT_TEMPLATE = """
    You are a Layer 1 Prime Agent: {agent_role}

    SPECIALIZATION: {specialization}

    RESPONSIBILITIES:
    {responsibilities}

    COMMUNICATION PROTOCOL:
    - Report to Layer 0 orchestrator
    - Coordinate with peer Prime agents
    - Delegate to Layer 2 worker agents
    - Interface with Layer 3 integrations

    CONTEXT GUIDELINES:
    - Accept context bundles from Layer 0
    - Create task-specific contexts for Layer 2
    - Maintain decision audit trail
    - Report progress via WebSocket

    OPERATIONAL MODE: Active
    """

    def __init__(self, coordinator: AgentCoordinator = None):
        """Initialize the layer initialization system."""
        self.coordinator = coordinator or AgentCoordinator()
        self.context_manager = ContextManager()
        self.initialized_layers: Dict[AgentLayer, bool] = {
            layer: False for layer in AgentLayer
        }
        self.layer_agents: Dict[AgentLayer, List[BaseAgent]] = {}
        self.session_id = uuid4()

        # Define layer configurations
        self.layer_configs = self._create_layer_configurations()

    def _create_layer_configurations(self) -> Dict[AgentLayer, LayerConfiguration]:
        """Create configuration for each agent layer."""
        return {
            AgentLayer.LAYER_0: LayerConfiguration(
                layer=AgentLayer.LAYER_0,
                agents=[AgentRole.MASTER],
                initialization_prompt=self.LAYER_0_PROMPT,
                max_agents=1,
                parallel_init=False,
                dependencies=[]
            ),
            AgentLayer.LAYER_1: LayerConfiguration(
                layer=AgentLayer.LAYER_1,
                agents=[
                    AgentRole.FRONTEND_PRIME,
                    AgentRole.BACKEND_PRIME,
                    AgentRole.TESTING_PRIME,
                    AgentRole.DEVOPS_PRIME
                ],
                initialization_prompt=self.LAYER_1_PROMPT_TEMPLATE,
                max_agents=4,
                parallel_init=True,
                dependencies=[AgentLayer.LAYER_0]
            ),
            AgentLayer.LAYER_2: LayerConfiguration(
                layer=AgentLayer.LAYER_2,
                agents=[AgentRole.WORKER],
                initialization_prompt="Layer 2 Worker Agent initialized for task execution.",
                max_agents=10,
                parallel_init=True,
                dependencies=[AgentLayer.LAYER_1]
            ),
            AgentLayer.LAYER_3: LayerConfiguration(
                layer=AgentLayer.LAYER_3,
                agents=[],  # External integrations, added dynamically
                initialization_prompt="Layer 3 Integration Agent ready for external services.",
                max_agents=5,
                parallel_init=True,
                dependencies=[AgentLayer.LAYER_1]
            )
        }

    async def initialize_casper_session(self) -> Dict[str, Any]:
        """
        Initialize a complete CASPER session with all agent layers.
        This is the main entry point for starting the system.
        """
        logger.info(f"Initializing CASPER session: {self.session_id}")

        try:
            # Start coordinator
            await self.coordinator.start()

            # Initialize layers in sequence
            initialization_results = {}

            # Layer 0 - Foundation
            logger.info("Initializing Layer 0 - Foundation")
            layer_0_result = await self._initialize_layer(AgentLayer.LAYER_0)
            initialization_results["layer_0"] = layer_0_result

            # Layer 1 - Prime Agents (parallel)
            logger.info("Initializing Layer 1 - Prime Agents")
            layer_1_result = await self._initialize_layer(AgentLayer.LAYER_1)
            initialization_results["layer_1"] = layer_1_result

            # Layer 2 - Workers (on-demand, initialize pool)
            logger.info("Preparing Layer 2 - Worker Pool")
            layer_2_result = await self._prepare_worker_pool()
            initialization_results["layer_2"] = layer_2_result

            # Layer 3 - Integrations (on-demand)
            logger.info("Preparing Layer 3 - Integration Services")
            layer_3_result = await self._prepare_integration_layer()
            initialization_results["layer_3"] = layer_3_result

            # Verify all layers are operational
            await self._verify_system_health()

            return {
                "session_id": str(self.session_id),
                "status": "initialized",
                "timestamp": datetime.now().isoformat(),
                "layers": initialization_results,
                "health_check": await self._get_system_health()
            }

        except Exception as e:
            logger.error(f"Failed to initialize CASPER session: {e}")
            await self.shutdown()
            raise

    async def _initialize_layer(self, layer: AgentLayer) -> Dict[str, Any]:
        """Initialize a specific agent layer."""
        config = self.layer_configs[layer]

        # Check dependencies
        for dep_layer in config.dependencies:
            if not self.initialized_layers[dep_layer]:
                raise RuntimeError(f"Dependency {dep_layer} not initialized for {layer}")

        agents_initialized = []

        if config.parallel_init and len(config.agents) > 1:
            # Initialize agents in parallel
            tasks = [
                self._initialize_agent(role, config)
                for role in config.agents
            ]
            agents = await asyncio.gather(*tasks, return_exceptions=True)

            for agent, role in zip(agents, config.agents):
                if isinstance(agent, Exception):
                    logger.error(f"Failed to initialize {role}: {agent}")
                else:
                    agents_initialized.append(agent)
        else:
            # Initialize agents sequentially
            for role in config.agents:
                try:
                    agent = await self._initialize_agent(role, config)
                    agents_initialized.append(agent)
                except Exception as e:
                    logger.error(f"Failed to initialize {role}: {e}")

        # Store initialized agents
        self.layer_agents[layer] = agents_initialized
        self.initialized_layers[layer] = True

        return {
            "layer": layer.value,
            "agents_count": len(agents_initialized),
            "agents": [agent.role.value for agent in agents_initialized],
            "status": "initialized"
        }

    async def _initialize_agent(self, role: AgentRole, config: LayerConfiguration) -> BaseAgent:
        """Initialize a single agent with proper prompting."""
        # Get agent from pool
        agent = await self.coordinator.agent_pool.get_agent(role)

        if not agent:
            raise RuntimeError(f"Failed to create agent for role {role}")

        # Create initialization context
        context = ContextBundle(
            session_id=self.session_id,
            parent_task="system_initialization"
        )

        # Add role-specific prompt
        if config.layer == AgentLayer.LAYER_0:
            prompt = config.initialization_prompt
        elif config.layer == AgentLayer.LAYER_1:
            prompt = self._generate_prime_agent_prompt(role)
        else:
            prompt = config.initialization_prompt

        context.add_pointer("initialization_prompt", prompt)
        context.add_pointer("layer", config.layer.value)
        context.add_pointer("session_id", str(self.session_id))

        # Initialize the agent with context
        await agent.initialize(context)

        logger.info(f"Initialized {role.value} agent in {config.layer.value}")

        return agent

    def _generate_prime_agent_prompt(self, role: AgentRole) -> str:
        """Generate role-specific prompt for Prime agents."""
        role_configs = {
            AgentRole.FRONTEND_PRIME: {
                "specialization": "Frontend Development & UI/UX",
                "responsibilities": """
                - React/TypeScript development
                - Component architecture design
                - State management implementation
                - UI/UX optimization
                - Accessibility compliance
                - Performance optimization
                """
            },
            AgentRole.BACKEND_PRIME: {
                "specialization": "Backend Development & Architecture",
                "responsibilities": """
                - API design and implementation
                - Database architecture
                - Service integration
                - Security implementation
                - Performance optimization
                - Scalability planning
                """
            },
            AgentRole.TESTING_PRIME: {
                "specialization": "Testing & Quality Assurance",
                "responsibilities": """
                - Test strategy design
                - Unit test implementation
                - Integration testing
                - E2E test automation
                - Performance testing
                - Security testing
                """
            },
            AgentRole.DEVOPS_PRIME: {
                "specialization": "DevOps & Infrastructure",
                "responsibilities": """
                - CI/CD pipeline management
                - Infrastructure as Code
                - Container orchestration
                - Monitoring and logging
                - Security compliance
                - Deployment automation
                """
            }
        }

        config = role_configs.get(role, {
            "specialization": "General Development",
            "responsibilities": "General development tasks"
        })

        return self.LAYER_1_PROMPT_TEMPLATE.format(
            agent_role=role.value,
            specialization=config["specialization"],
            responsibilities=config["responsibilities"]
        )

    async def _prepare_worker_pool(self) -> Dict[str, Any]:
        """Prepare the worker agent pool for Layer 2."""
        # Pre-warm the worker pool with a few agents
        initial_workers = 2
        workers_created = []

        for _ in range(initial_workers):
            try:
                worker = await self.coordinator.agent_pool.get_agent(AgentRole.WORKER)
                if worker:
                    workers_created.append(worker)
            except Exception as e:
                logger.warning(f"Failed to create worker: {e}")

        return {
            "layer": "layer_2",
            "pool_size": len(workers_created),
            "max_workers": self.layer_configs[AgentLayer.LAYER_2].max_agents,
            "status": "ready"
        }

    async def _prepare_integration_layer(self) -> Dict[str, Any]:
        """Prepare the integration layer for external services."""
        # Integration agents are created on-demand
        # Here we just prepare the infrastructure

        integrations_available = []

        # Check for available integrations
        if os.environ.get("GITHUB_TOKEN"):
            integrations_available.append("github")

        if os.environ.get("SLACK_WEBHOOK"):
            integrations_available.append("slack")

        if os.environ.get("JIRA_API_KEY"):
            integrations_available.append("jira")

        return {
            "layer": "layer_3",
            "available_integrations": integrations_available,
            "status": "ready"
        }

    async def _verify_system_health(self) -> None:
        """Verify all layers are operational."""
        for layer in [AgentLayer.LAYER_0, AgentLayer.LAYER_1]:
            if not self.initialized_layers[layer]:
                raise RuntimeError(f"Critical layer {layer} not initialized")

        # Verify Layer 0 agent is responsive
        if AgentLayer.LAYER_0 in self.layer_agents:
            master_agent = self.layer_agents[AgentLayer.LAYER_0][0]
            if master_agent.status == AgentStatus.FAILED:
                raise RuntimeError("Layer 0 Master agent failed initialization")

        logger.info("System health check passed")

    async def _get_system_health(self) -> Dict[str, Any]:
        """Get current system health status."""
        return {
            "layers_initialized": {
                layer.value: initialized
                for layer, initialized in self.initialized_layers.items()
            },
            "agent_pool_stats": self.coordinator.agent_pool.get_pool_stats(),
            "context_manager_status": {
                "active": True,
                "session_id": str(self.session_id)
            },
            "timestamp": datetime.now().isoformat()
        }

    async def shutdown(self) -> None:
        """Shutdown all agent layers gracefully."""
        logger.info("Shutting down agent layers...")

        # Shutdown in reverse order
        for layer in reversed(list(AgentLayer)):
            if layer in self.layer_agents:
                for agent in self.layer_agents[layer]:
                    try:
                        await agent.shutdown()
                    except Exception as e:
                        logger.warning(f"Error shutting down agent: {e}")

        # Stop coordinator
        await self.coordinator.stop()

        logger.info("Agent layers shutdown complete")


# Convenience function for session startup
async def start_casper_session() -> Dict[str, Any]:
    """
    Start a new CASPER session with all agent layers initialized.
    This is the main entry point for the system.
    """
    initializer = AgentLayerInitializer()
    return await initializer.initialize_casper_session()


import os