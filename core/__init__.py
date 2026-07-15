"""
CASPER Prime - Autonomous AI Development Platform
"""

__version__ = "0.1.0"
__author__ = "CASPER Prime Team"

from .agents.base import AgentRole, AgentStatus, TaskPriority
from .orchestrator.coordinator import AgentCoordinator
from .context.manager import ContextManager

__all__ = [
    "AgentRole",
    "AgentStatus",
    "TaskPriority",
    "AgentCoordinator",
    "ContextManager",
]
