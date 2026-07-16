"""
CASPER Prime Terminal Integration Module
Complete integration orchestration for all terminal components.
PRODUCTION GRADE - Fully functional terminal with IDE integration.
"""

from .main import TerminalIntegration
from .mcp_server import MCPServer
from .adapters import (
    CodingSessionAdapter,
    StreamingOrchestratorAdapter,
    IntentParserAdapter,
    check_agent_compatibility,
)
from .fallbacks import (
    FallbackSessionManager,
    FallbackStreamingProcessor,
    FallbackNLParser,
    FallbackTerminalUI,
)

__all__ = [
    "TerminalIntegration",
    "MCPServer",
    "CodingSessionAdapter",
    "StreamingOrchestratorAdapter",
    "IntentParserAdapter",
    "check_agent_compatibility",
    "FallbackSessionManager",
    "FallbackStreamingProcessor",
    "FallbackNLParser",
    "FallbackTerminalUI",
]

# Version and metadata
__version__ = "1.0.0"
__author__ = "AGENT PSI - Integration Coordinator"
__description__ = "Complete terminal integration with MCP protocol support"
