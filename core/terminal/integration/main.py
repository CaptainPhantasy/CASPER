"""
CASPER Prime Terminal Integration - AGENT PSI Implementation
Main entry point that orchestrates all terminal components into a working coding terminal.
PRODUCTION GRADE - Zero placeholders, everything must work.
"""

import asyncio
import logging
import os
from datetime import datetime
from typing import Dict, Any, Optional
from pathlib import Path

from fastapi import FastAPI, WebSocket, WebSocketDisconnect

from ..interfaces import (
    IIntegration,
    ISession,
    IStreaming,
    IParser,
    ITerminalUI,
    SessionState,
    TerminalError,
)
from ..pty_manager import PTYManager
from ..websocket_handler import TerminalWebSocketHandler
from ..command_proxy import CommandProxy
from ..security import SecurityMiddleware
from .fallbacks import (
    FallbackNLParser,
    FallbackSessionManager,
    FallbackStreamingProcessor,
    FallbackTerminalUI,
)

# Import agent layer initialization
from core.agents.layer_initialization import AgentLayerInitializer

logger = logging.getLogger(__name__)

# Import specialist implementations independently. One stale optional component
# must not disable the working TUI, session manager, or streaming engine.
try:
    from ..session.coding_session import CodingSession
except ImportError as exc:
    logger.warning("Coding session implementation unavailable: %s", exc)
    CodingSession = None

try:
    from ..streaming.streaming_orchestrator import StreamingOrchestrator
except ImportError as exc:
    logger.warning("Streaming implementation unavailable: %s", exc)
    StreamingOrchestrator = None

try:
    from ..nlp.intent_parser import IntentParser
except ImportError as exc:
    logger.warning("NLP implementation unavailable: %s", exc)
    IntentParser = None

try:
    from ..ui.terminal_ui import TerminalUI as AgentTerminalUI
except ImportError as exc:
    logger.warning("Terminal UI implementation unavailable: %s", exc)
    AgentTerminalUI = None

AGENTS_AVAILABLE = any(
    component is not None
    for component in (
        CodingSession,
        StreamingOrchestrator,
        IntentParser,
        AgentTerminalUI,
    )
)


class TerminalIntegration(IIntegration):
    """
    Main integration class that orchestrates all terminal components.
    Implements the IIntegration interface with production-grade reliability.
    """

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """Initialize the terminal integration with all components."""
        self.config = config or self._load_default_config()

        # Core components
        self.session_manager: Optional[ISession] = None
        self.streaming_processor: Optional[IStreaming] = None
        self.nlp_parser: Optional[IParser] = None
        self.terminal_ui: Optional[ITerminalUI] = None

        # Existing infrastructure
        self.pty_manager: Optional[PTYManager] = None
        self.websocket_handler: Optional[TerminalWebSocketHandler] = None
        self.command_proxy: Optional[CommandProxy] = None
        self.security: Optional[SecurityMiddleware] = None

        # Agent layer management
        self.agent_initializer: Optional[AgentLayerInitializer] = None
        self.agent_session: Optional[Dict[str, Any]] = None

        # State management
        self.is_initialized = False
        self.active_sessions: Dict[str, SessionState] = {}
        self.mcp_connections: Dict[str, WebSocket] = {}

        # MCP Server for IDE integration
        self.mcp_server: Optional[FastAPI] = None

    def _load_default_config(self) -> Dict[str, Any]:
        """Load default configuration for terminal integration."""
        return {
            "session_timeout_minutes": 30,
            "max_concurrent_sessions": 10,
            "streaming_chunk_size": 100,
            "max_context_tokens": 200000,
            "enable_mcp_server": True,
            "mcp_server_port": 8743,
            "log_level": "INFO",
            "security_enabled": True,
            "persistence_path": ".casper/terminal_sessions",
            "temp_dir": "/tmp/casper/terminal",
        }

    async def initialize_terminal(self) -> None:
        """Initialize all terminal components with comprehensive error handling."""
        if self.is_initialized:
            logger.warning("Terminal already initialized")
            return

        try:
            logger.info("Initializing CASPER Prime Terminal Integration...")

            # Initialize agent layers first - this sets up the orchestration system
            logger.info("Starting agent layer initialization sequence...")
            await self._initialize_agent_layers()

            # Ensure directories exist
            await self._ensure_directories()

            # Initialize core infrastructure components
            await self._initialize_infrastructure()

            # Initialize agent-specific components
            await self._initialize_agent_components()

            # Initialize MCP server if enabled
            if self.config.get("enable_mcp_server", True):
                await self._initialize_mcp_server()

            self.is_initialized = True
            logger.info("Terminal integration initialization complete")

        except Exception as e:
            logger.error(f"Failed to initialize terminal: {e}")
            await self.shutdown()  # Clean up partial initialization
            raise TerminalError(f"Terminal initialization failed: {e}")

    async def _initialize_agent_layers(self) -> None:
        """Initialize the agent layer system with proper sequencing."""
        try:
            logger.info("Initializing agent layer system...")

            # Create the agent layer initializer
            self.agent_initializer = AgentLayerInitializer()

            # Initialize all agent layers with proper prompting
            self.agent_session = (
                await self.agent_initializer.initialize_casper_session()
            )

            logger.info(
                f"Agent layers initialized successfully: {self.agent_session['status']}"
            )
            logger.info(f"Session ID: {self.agent_session['session_id']}")

            # Log layer initialization results
            for layer_name, layer_info in self.agent_session.get("layers", {}).items():
                logger.info(
                    f"  {layer_name}: {layer_info.get('agents_count', 0)} agents initialized"
                )

        except Exception as e:
            logger.error(f"Failed to initialize agent layers: {e}")
            raise TerminalError(f"Agent layer initialization failed: {e}")

    async def _ensure_directories(self) -> None:
        """Ensure required directories exist."""
        dirs = [
            self.config["persistence_path"],
            self.config["temp_dir"],
            os.path.join(self.config["temp_dir"], "sessions"),
            os.path.join(self.config["temp_dir"], "streams"),
        ]

        for directory in dirs:
            Path(directory).mkdir(parents=True, exist_ok=True)

    async def _initialize_infrastructure(self) -> None:
        """Initialize existing CASPER infrastructure components."""
        # PTY Manager for process interaction
        self.pty_manager = PTYManager()
        await self.pty_manager.start()

        # Command proxy for secure command execution
        self.command_proxy = CommandProxy()
        await self.command_proxy.initialize()

        # Security middleware
        if self.config.get("security_enabled", True):
            self.security = SecurityMiddleware()

        # WebSocket handler for real-time communication
        self.websocket_handler = TerminalWebSocketHandler()
        await self.websocket_handler.start()

        logger.info("Infrastructure components initialized")

    async def _initialize_agent_components(self) -> None:
        """Initialize components created by specialist agents."""
        try:
            # Initialize components with fallbacks
            await self._initialize_session_manager()
            await self._initialize_streaming_processor()
            await self._initialize_nlp_parser()
            await self._initialize_terminal_ui()

            logger.info("Agent components initialized")

        except ImportError as e:
            logger.warning(f"Some agent components not available: {e}")
            # Fall back to basic implementations for missing components
            await self._initialize_fallback_components()

    async def _initialize_fallback_components(self) -> None:
        """Initialize fallback implementations if agent components are missing."""
        from .fallbacks import (
            FallbackSessionManager,
            FallbackStreamingProcessor,
            FallbackNLParser,
            FallbackTerminalUI,
        )

        if not self.session_manager:
            self.session_manager = FallbackSessionManager()

        if not self.streaming_processor:
            self.streaming_processor = FallbackStreamingProcessor()

        if not self.nlp_parser:
            self.nlp_parser = FallbackNLParser()

        if not self.terminal_ui:
            self.terminal_ui = FallbackTerminalUI()
            await self.terminal_ui.start_ui()

        logger.info("Fallback components initialized")

    async def _initialize_session_manager(self) -> None:
        """Initialize session manager with error handling and fallback."""
        try:
            if AGENTS_AVAILABLE and CodingSession:
                # Use agent implementation - adapt to ISession interface
                from .adapters import CodingSessionAdapter

                self.session_manager = CodingSessionAdapter(
                    persistence_path=self.config["persistence_path"],
                    session_timeout=self.config["session_timeout_minutes"],
                )
                logger.info("Using agent-based session manager")
            else:
                raise ImportError("Agent session manager not available")

        except Exception as e:
            logger.warning(f"Could not initialize agent session manager: {e}")
            self.session_manager = FallbackSessionManager()
            logger.info("Using fallback session manager")

    async def _initialize_streaming_processor(self) -> None:
        """Initialize streaming processor with error handling and fallback."""
        try:
            if AGENTS_AVAILABLE and StreamingOrchestrator:
                # Use agent implementation - adapt to IStreaming interface
                from .adapters import StreamingOrchestratorAdapter

                self.streaming_processor = StreamingOrchestratorAdapter(
                    max_concurrent_streams=self.config.get("max_concurrent_streams", 10)
                )
                logger.info("Using agent-based streaming processor")
            else:
                raise ImportError("Agent streaming processor not available")

        except Exception as e:
            logger.warning(f"Could not initialize agent streaming processor: {e}")
            self.streaming_processor = FallbackStreamingProcessor()
            logger.info("Using fallback streaming processor")

    async def _initialize_nlp_parser(self) -> None:
        """Initialize NLP parser with error handling and fallback."""
        try:
            if AGENTS_AVAILABLE and IntentParser:
                # Use agent implementation - adapt to IParser interface
                from .adapters import IntentParserAdapter

                self.nlp_parser = IntentParserAdapter()
                logger.info("Using agent-based NLP parser")
            else:
                raise ImportError("Agent NLP parser not available")

        except Exception as e:
            logger.warning(f"Could not initialize agent NLP parser: {e}")
            self.nlp_parser = FallbackNLParser()
            logger.info("Using fallback NLP parser")

    async def _initialize_terminal_ui(self) -> None:
        """Initialize terminal UI with error handling and fallback."""
        try:
            if AGENTS_AVAILABLE and AgentTerminalUI:
                # Use agent implementation if it implements ITerminalUI
                if hasattr(AgentTerminalUI, "start_ui"):
                    self.terminal_ui = AgentTerminalUI()
                    bind_integration = getattr(
                        self.terminal_ui, "bind_integration", None
                    )
                    if bind_integration:
                        bind_integration(self)
                    await self.terminal_ui.start_ui()
                    logger.info("Using agent-based terminal UI")
                else:
                    raise AttributeError(
                        "Agent UI doesn't implement ITerminalUI interface"
                    )
            else:
                raise ImportError("Agent terminal UI not available")

        except Exception as e:
            logger.warning(f"Could not initialize agent terminal UI: {e}")
            self.terminal_ui = FallbackTerminalUI()
            await self.terminal_ui.start_ui()
            logger.info("Using fallback terminal UI")

    async def _initialize_mcp_server(self) -> None:
        """Initialize Model Context Protocol server for IDE integration."""
        from .mcp_server import MCPServer

        self.mcp_server = MCPServer(
            port=self.config["mcp_server_port"], integration=self
        )
        await self.mcp_server.start()
        logger.info(f"MCP server started on port {self.config['mcp_server_port']}")

    async def start_interactive_session(self) -> None:
        """Start the main interactive coding session."""
        if not self.is_initialized:
            await self.initialize_terminal()

        try:
            logger.info("Starting CASPER Prime interactive terminal session...")

            # Create new session
            session_id = f"interactive_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            session_state = await self.session_manager.start_session(session_id)
            self.active_sessions[session_id] = session_state

            # Welcome message
            await self.terminal_ui.show_progress("CASPER Prime Terminal Ready", 100.0)

            # Main interaction loop
            while True:
                try:
                    # Get user input
                    user_input = await self.terminal_ui.get_user_input("casper> ")

                    if not user_input.strip():
                        continue

                    if user_input.lower() in ["exit", "quit", "bye"]:
                        break

                    # Process the input
                    if await self._process_user_input(session_id, user_input):
                        break

                except KeyboardInterrupt:
                    logger.info("Received keyboard interrupt")
                    break
                except Exception as e:
                    logger.error(f"Error in interactive session: {e}")
                    await self.terminal_ui.show_error(f"Error: {e}")

            # Clean up session
            await self._cleanup_session(session_id)
            logger.info("Interactive session ended")

        except Exception as e:
            logger.error(f"Interactive session failed: {e}")
            raise TerminalError(f"Interactive session failed: {e}")

    async def _process_user_input(self, session_id: str, user_input: str) -> bool:
        """Process local TUI commands or route an AI request through the pipeline."""
        try:
            execute_command = getattr(self.terminal_ui, "execute_command", None)
            if execute_command:
                local_result = await execute_command(user_input)
                if local_result.handled:
                    return bool(local_result.exit_requested)

            # Parse the input into coding intent
            intent = await self.nlp_parser.parse_input(user_input)

            # Get session context
            session_context = await self.session_manager.get_context()

            # Stream the response
            async for chunk in self.streaming_processor.stream_response(
                intent, session_context
            ):
                await self.terminal_ui.display_stream(chunk)

            # Add interaction to session
            await self.session_manager.add_interaction(user_input, "Response processed")
            await self.session_manager.persist()
            return False

        except Exception as e:
            logger.error(f"Error processing user input: {e}")
            await self.terminal_ui.show_error(f"Processing error: {e}")
            return False

    async def handle_mcp_connection(self, websocket: WebSocket) -> None:
        """Handle Model Context Protocol connection from IDE."""
        try:
            await websocket.accept()
            connection_id = f"mcp_{datetime.now().strftime('%Y%m%d_%H%M%S_%f')}"
            self.mcp_connections[connection_id] = websocket

            logger.info(f"MCP connection established: {connection_id}")

            # Send welcome message
            await websocket.send_json(
                {
                    "type": "mcp_welcome",
                    "server": "CASPER Prime Terminal",
                    "version": "1.0",
                    "capabilities": [
                        "code_completion",
                        "code_analysis",
                        "project_context",
                        "terminal_integration",
                    ],
                }
            )

            # Handle MCP messages
            while True:
                try:
                    data = await websocket.receive_json()
                    await self._handle_mcp_message(connection_id, data)

                except WebSocketDisconnect:
                    break
                except Exception as e:
                    logger.error(f"MCP message error: {e}")
                    await websocket.send_json({"type": "error", "message": str(e)})

        except Exception as e:
            logger.error(f"MCP connection error: {e}")
        finally:
            if connection_id in self.mcp_connections:
                del self.mcp_connections[connection_id]
            logger.info(f"MCP connection closed: {connection_id}")

    async def _handle_mcp_message(
        self, connection_id: str, data: Dict[str, Any]
    ) -> None:
        """Handle individual MCP protocol messages."""
        message_type = data.get("type")
        websocket = self.mcp_connections[connection_id]

        if message_type == "code_completion":
            # Handle code completion request
            partial = data.get("partial", "")
            context = data.get("context", {})
            suggestions = await self.nlp_parser.suggest_completion(partial, context)

            await websocket.send_json(
                {
                    "type": "completion_response",
                    "request_id": data.get("request_id"),
                    "suggestions": suggestions,
                }
            )

        elif message_type == "code_analysis":
            # Handle code analysis request
            code = data.get("code", "")
            language = await self.nlp_parser.detect_language(code)
            entities = await self.nlp_parser.extract_entities(code)

            await websocket.send_json(
                {
                    "type": "analysis_response",
                    "request_id": data.get("request_id"),
                    "language": language,
                    "entities": entities,
                }
            )

        elif message_type == "terminal_command":
            # Handle terminal command through MCP
            command = data.get("command", "")
            session_id = f"mcp_{connection_id}"

            # Create MCP session if needed
            if session_id not in self.active_sessions:
                session_state = await self.session_manager.start_session(session_id)
                self.active_sessions[session_id] = session_state

            # Process command
            await self._process_user_input(session_id, command)

        else:
            logger.warning(f"Unknown MCP message type: {message_type}")

    async def _cleanup_session(self, session_id: str) -> None:
        """Clean up a terminal session."""
        if session_id in self.active_sessions:
            del self.active_sessions[session_id]
        logger.info(f"Session cleaned up: {session_id}")

    async def shutdown(self) -> None:
        """Gracefully shutdown the terminal integration."""
        logger.info("Shutting down CASPER Prime Terminal Integration...")

        try:
            # Close all MCP connections
            for websocket in list(self.mcp_connections.values()):
                try:
                    await websocket.close()
                except Exception as exc:
                    logger.debug("WebSocket close failed during shutdown: %s", exc)
            self.mcp_connections.clear()

            # Clean up all sessions
            for session_id in list(self.active_sessions.keys()):
                await self._cleanup_session(session_id)

            # Shutdown MCP server
            if self.mcp_server:
                await self.mcp_server.stop()

            # Shutdown UI
            if self.terminal_ui:
                shutdown_ui = getattr(self.terminal_ui, "shutdown", None)
                if shutdown_ui:
                    await shutdown_ui()
                else:
                    await self.terminal_ui.clear_screen()

            # Shutdown infrastructure
            if self.websocket_handler:
                await self.websocket_handler.stop()

            if self.command_proxy:
                await self.command_proxy.shutdown()

            if self.pty_manager:
                await self.pty_manager.stop()

            # Shutdown agent layers (must be done last to clean up orchestration)
            if self.agent_initializer:
                logger.info("Shutting down agent layers...")
                await self.agent_initializer.shutdown()

            self.is_initialized = False
            logger.info("Terminal integration shutdown complete")

        except Exception as e:
            logger.error(f"Error during shutdown: {e}")


# Main entry point
async def main():
    """Main entry point for the CASPER Prime Terminal."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )

    integration = None
    try:
        # Create integration instance
        integration = TerminalIntegration()

        # Initialize and start
        await integration.initialize_terminal()
        await integration.start_interactive_session()

    except KeyboardInterrupt:
        logger.info("Terminal interrupted by user")
    except Exception as e:
        logger.error(f"Terminal failed: {e}")
    finally:
        if integration is not None:
            try:
                await integration.shutdown()
            except Exception as exc:
                logger.debug("Terminal shutdown failed: %s", exc)


if __name__ == "__main__":
    asyncio.run(main())
