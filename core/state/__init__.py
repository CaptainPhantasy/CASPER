"""
CASPER State Management Module
Production-ready state management with real persistence
"""

from .simple_state_manager import SimpleStateManager, AgentTask, TaskStatus

# Try to import the full LangGraph version if available
try:
    from .langgraph_orchestrator import (
        ProductionStateManager,
        create_production_state_manager,
    )

    LANGGRAPH_AVAILABLE = True
except ImportError:
    LANGGRAPH_AVAILABLE = False
    ProductionStateManager = None
    create_production_state_manager = None


def create_state_manager(storage_path: str = None, use_langgraph: bool = True):
    """
    Factory function to create the best available state manager

    Args:
        storage_path: Path for persistent storage
        use_langgraph: Whether to use LangGraph version if available

    Returns:
        StateManager instance
    """
    if use_langgraph and LANGGRAPH_AVAILABLE:
        return create_production_state_manager(storage_path)
    else:
        return SimpleStateManager(storage_path)


__all__ = [
    "SimpleStateManager",
    "ProductionStateManager",
    "AgentTask",
    "TaskStatus",
    "create_state_manager",
    "create_production_state_manager",
    "LANGGRAPH_AVAILABLE",
]
