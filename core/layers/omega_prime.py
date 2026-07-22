"""
Prime Layer 0 (Omega) - The ONLY entry point for user interaction.
All user input MUST pass through this layer. Direct tool access is FORBIDDEN.

Architecture:
USER → OMEGA (Layer 0) → SIGMA (Layer 1) → GAMMA (Layer 2) → ALPHA (Layer 3/Tools)

NO BYPASSING ALLOWED.
"""

import asyncio
import re
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime

from core.ai.enhanced_command_interpreter import (
    EnhancedCasperInterpreter,
    InterpretedCommand,
    CommandType,
    ConfidenceLevel
)
from core.ai.decision_orchestrator import DecisionOrchestrator
from core.agents.master_prime import MasterPrimeAgent
from core.services.enhanced_approval import EnhancedApprovalService


class AccessLevel(Enum):
    """Access control levels for layer security"""
    USER = "user"           # External user - can only talk to Omega
    OMEGA = "omega"         # Layer 0 - can talk to Sigma
    SIGMA = "sigma"         # Layer 1 - can talk to Gamma
    GAMMA = "gamma"         # Layer 2 - can talk to Alpha
    ALPHA = "alpha"         # Layer 3 - can access tools
    SYSTEM = "system"       # Internal system operations


class SecurityPolicy(Enum):
    """Security policies for input handling"""
    BLOCK_DIRECT_TOOLS = "block_direct_tools"
    BLOCK_SYSTEM_COMMANDS = "block_system_commands"
    BLOCK_FILE_PATHS = "block_file_paths"
    SANITIZE_INPUT = "sanitize_input"
    LOG_ALL = "log_all"


@dataclass
class OmegaRequest:
    """Structured request from user through Omega layer"""
    id: str
    raw_input: str
    sanitized_input: str
    timestamp: datetime
    access_level: AccessLevel = AccessLevel.USER
    blocked_patterns: List[str] = field(default_factory=list)
    security_flags: List[str] = field(default_factory=list)
    interpretation: Optional[InterpretedCommand] = None
    response: Optional[str] = None
    status: str = "pending"


class OmegaPrime:
    """
    Prime Layer 0 (Omega) - The supreme gatekeeper.

    This is the ONLY layer that users can interact with directly.
    All commands, requests, and inputs MUST pass through Omega.

    Responsibilities:
    1. Accept ALL user input
    2. Sanitize and validate input
    3. Block direct tool access attempts
    4. Route legitimate requests to Sigma (Layer 1)
    5. Return responses to user

    FORBIDDEN:
    - Users directly calling tools (Write, Edit, Bash, etc.)
    - Users accessing internal agents directly
    - Users bypassing Omega to reach lower layers
    """

    # Patterns that indicate direct tool access attempts (BLOCKED)
    BLOCKED_PATTERNS = [
        r'^Write\s*\(',           # Direct Write tool
        r'^Edit\s*\(',            # Direct Edit tool
        r'^Bash\s*\(',            # Direct Bash tool
        r'^Read\s*\(',            # Direct Read tool
        r'^MultiEdit\s*\(',       # Direct MultiEdit tool
        r'^WebSearch\s*\(',       # Direct WebSearch tool
        r'^Task\s*\(',            # Direct Task tool
        r'^TodoWrite\s*\(',       # Direct TodoWrite tool
        r'approval_service\.',    # Direct approval service access
        r'agent\.',              # Direct agent access
        r'from\s+core\.',        # Direct import attempts
        r'import\s+core\.',      # Direct import attempts
        r'__[a-z]+__',          # Dunder method access
        r'eval\s*\(',           # Eval attempts
        r'exec\s*\(',           # Exec attempts
        r'compile\s*\(',        # Compile attempts
        r'subprocess\.',        # Subprocess access
        r'os\.system',          # OS command execution
    ]

    # Patterns that are sanitized but allowed
    SANITIZE_PATTERNS = [
        (r'rm\s+-rf\s+/', 'delete folder'),  # Dangerous delete
        (r'sudo\s+', ''),                    # Remove sudo
        (r'chmod\s+777', 'chmod 755'),       # Safer permissions
        (r'/etc/', './'),                    # System paths
        (r'/usr/', './'),                    # System paths
        (r'/bin/', './'),                    # System paths
    ]

    def __init__(self):
        """Initialize Omega Prime - the gatekeeper"""
        self.interpreter = EnhancedCasperInterpreter()
        self.orchestrator = DecisionOrchestrator()
        self.approval_service = EnhancedApprovalService()
        self.master_agent = None  # Will be initialized on first use
        self.request_history: List[OmegaRequest] = []
        self.active_sessions: Dict[str, Any] = {}
        self.security_log: List[Dict] = []

        # Initialize fast path for /commands
        from core.layers.omega_fast_path import OmegaFastPath
        self.fast_path = OmegaFastPath(self)

        print("🛡️ OMEGA PRIME INITIALIZED - Layer 0 Security Active")
        print("⚡ Fast Path enabled for /commands (< 50ms response)")
        print("🚫 Direct tool access is now BLOCKED")
        print("✅ All requests must pass through Omega layer")

    async def process_user_input(self, user_input: str, session_id: str = "default") -> str:
        """
        THE ONLY METHOD USERS CAN ACCESS.

        Process user input through proper layer hierarchy.
        NO DIRECT TOOL ACCESS ALLOWED.

        Fast path for /commands: < 50ms response time
        Normal path for natural language: Full validation

        Args:
            user_input: Raw input from user
            session_id: Session identifier for context

        Returns:
            Processed response to user
        """

        # FAST PATH: Check for /commands first (< 10ms overhead)
        if user_input.startswith('/') and hasattr(self, 'fast_path'):
            is_fast, response = await self.fast_path.process_fast(user_input)
            if is_fast:
                return response

        # NORMAL PATH: Full security and interpretation
        # Create request object
        request = OmegaRequest(
            id=f"omega_{datetime.now().timestamp()}",
            raw_input=user_input,
            sanitized_input=user_input,
            timestamp=datetime.now()
        )

        # Step 1: Security check - block direct tool access
        is_blocked, blocked_patterns = self._check_blocked_patterns(user_input)
        if is_blocked:
            request.blocked_patterns = blocked_patterns
            request.status = "blocked"
            self._log_security_event("BLOCKED_DIRECT_ACCESS", request)

            return self._generate_blocked_response(blocked_patterns, user_input)

        # Step 2: Sanitize input
        sanitized_input = self._sanitize_input(user_input)
        request.sanitized_input = sanitized_input

        if sanitized_input != user_input:
            request.security_flags.append("input_sanitized")
            self._log_security_event("INPUT_SANITIZED", request)

        # Step 3: Interpret through AI (still in Omega layer)
        try:
            interpretation = await self.interpreter.interpret(sanitized_input)
            request.interpretation = interpretation

            # Step 4: Check if this requires lower layer access
            if self._requires_execution(interpretation):
                # Route to Sigma (Layer 1) via Master Prime
                response = await self._route_to_sigma(interpretation, request)
            else:
                # Handle within Omega (queries, help, etc.)
                response = await self._handle_in_omega(interpretation)

            request.response = response
            request.status = "completed"

        except Exception as e:
            request.status = "error"
            response = f"⚠️ Omega encountered an error: {str(e)}\nPlease rephrase your request."
            self._log_security_event("PROCESSING_ERROR", request)

        # Store request history
        self.request_history.append(request)
        if len(self.request_history) > 100:
            self.request_history = self.request_history[-100:]

        return response

    def _check_blocked_patterns(self, user_input: str) -> Tuple[bool, List[str]]:
        """Check if input contains blocked patterns (direct tool access)"""
        blocked = []

        for pattern in self.BLOCKED_PATTERNS:
            if re.search(pattern, user_input, re.IGNORECASE):
                blocked.append(pattern)

        return len(blocked) > 0, blocked

    def _sanitize_input(self, user_input: str) -> str:
        """Sanitize dangerous patterns in input"""
        sanitized = user_input

        for pattern, replacement in self.SANITIZE_PATTERNS:
            sanitized = re.sub(pattern, replacement, sanitized, flags=re.IGNORECASE)

        return sanitized

    def _generate_blocked_response(self, blocked_patterns: List[str], user_input: str) -> str:
        """Generate response when direct tool access is blocked"""

        # Detect what user was trying to do
        intent = self._detect_blocked_intent(user_input)

        response = "🚫 **Direct Tool Access Blocked**\n\n"
        response += "I detected an attempt to directly access internal tools or layers.\n"
        response += "This is not allowed for security reasons.\n\n"

        if intent:
            response += f"**What you were trying to do:** {intent}\n\n"
            response += "**How to do it properly:**\n"
            response += self._get_proper_command(intent)
        else:
            response += "**Proper usage:**\n"
            response += "• To create a file: 'create a file called example.py'\n"
            response += "• To edit code: 'modify the main function in app.py'\n"
            response += "• To run commands: 'list the files in the current directory'\n"
            response += "• To search: 'find all Python files with the word test'\n"

        response += "\n💡 **Remember:** Just describe what you want in natural language."
        response += "\nI'll handle the technical implementation through the proper layers."

        return response

    def _detect_blocked_intent(self, user_input: str) -> Optional[str]:
        """Detect what the user was trying to do with blocked commands"""

        if 'Write(' in user_input or 'create' in user_input.lower():
            return "Create or write a file"
        elif 'Edit(' in user_input or 'modify' in user_input.lower():
            return "Edit or modify a file"
        elif 'Bash(' in user_input or 'run' in user_input.lower():
            return "Execute a command"
        elif 'Read(' in user_input:
            return "Read a file"
        elif 'approval' in user_input.lower():
            return "Manage approvals"
        elif 'agent' in user_input.lower():
            return "Access an agent directly"

        return None

    def _get_proper_command(self, intent: str) -> str:
        """Get the proper natural language command for an intent"""

        proper_commands = {
            "Create or write a file": "Say: 'create a file called [filename] with [content]'",
            "Edit or modify a file": "Say: 'modify [filename] to [describe changes]'",
            "Execute a command": "Say: 'run [describe what command should do]'",
            "Read a file": "Say: 'show me the contents of [filename]'",
            "Manage approvals": "Say: 'approve pending operations' or 'show pending approvals'",
            "Access an agent directly": "Say what task you want done, I'll route it properly"
        }

        return proper_commands.get(intent, "Describe your task in natural language")

    def _requires_execution(self, interpretation: InterpretedCommand) -> bool:
        """Check if interpretation requires lower layer execution"""

        # These command types need execution
        execution_types = [
            CommandType.FILE_OPERATION,
            CommandType.CODE_GENERATION,
            CommandType.TESTING,
            CommandType.DEBUGGING,
            CommandType.GIT_OPERATION,
            CommandType.PACKAGE_MANAGEMENT,
            CommandType.INITIALIZATION,
            CommandType.MULTI_AGENT
        ]

        return interpretation.command_type in execution_types

    async def _route_to_sigma(self, interpretation: InterpretedCommand, request: OmegaRequest) -> str:
        """
        Route to Sigma layer (Layer 1) through Master Prime.
        Omega → Sigma → Gamma → Alpha
        """

        # Initialize Master Prime if needed (Sigma layer)
        if not self.master_agent:
            from core.agents.master_prime import MasterPrimeAgent
            self.master_agent = MasterPrimeAgent(
                agent_id="master_prime_sigma",
                name="Master Prime (Sigma Layer)"
            )

        # Create context bundle for lower layers
        from core.agents.base import ContextBundle
        context = ContextBundle(
            session_id=request.id,
            parent_task=interpretation.raw_input,
            caller_agent_id="omega_prime",
            metadata={
                "interpretation": interpretation.to_dict() if hasattr(interpretation, 'to_dict') else {},
                "security_flags": request.security_flags,
                "access_level": AccessLevel.SIGMA.value
            }
        )

        # Log layer transition
        self._log_security_event("ROUTE_TO_SIGMA", request)

        try:
            # Execute through Master Prime (Sigma)
            result = await self.master_agent.execute_task(
                task=interpretation.raw_input,
                context=context
            )

            # Format response
            if result.status.value == "completed":
                response = f"✅ Task completed successfully\n\n{result.output}"
            else:
                response = f"⚠️ Task status: {result.status.value}\n\n{result.output}"

            return response

        except Exception as e:
            return f"❌ Sigma layer error: {str(e)}"

    async def _handle_in_omega(self, interpretation: InterpretedCommand) -> str:
        """Handle requests that don't require lower layer execution"""

        if interpretation.command_type == CommandType.CONVERSATION:
            return await self._handle_conversation(interpretation)
        elif interpretation.command_type == CommandType.SYSTEM_QUERY:
            return await self._handle_query(interpretation)
        elif interpretation.command_type == CommandType.UNKNOWN:
            return self._handle_unknown(interpretation)
        else:
            return "This request type is pending implementation in Omega."

    async def _handle_conversation(self, interpretation: InterpretedCommand) -> str:
        """Handle conversational requests"""
        return f"I understand you're asking about: {interpretation.raw_input}\n" \
               f"Let me help you with that through the proper channels."

    async def _handle_query(self, interpretation: InterpretedCommand) -> str:
        """Handle system queries"""
        return f"System query processed: {interpretation.raw_input}"

    def _handle_unknown(self, interpretation: InterpretedCommand) -> str:
        """Handle unknown/unclear requests"""

        response = "🤔 I'm not quite sure what you're asking for.\n\n"

        if interpretation.context.get("possible_interpretations"):
            response += "Did you mean one of these?\n"
            for interp in interpretation.context["possible_interpretations"]:
                response += f"• {interp}\n"
        else:
            response += "Please try rephrasing your request in natural language.\n"
            response += "For example:\n"
            response += "• 'create a Python file called app.py'\n"
            response += "• 'run the test suite'\n"
            response += "• 'show me the project structure'\n"

        return response

    def _log_security_event(self, event_type: str, request: OmegaRequest):
        """Log security events for audit"""

        event = {
            "timestamp": datetime.now().isoformat(),
            "event_type": event_type,
            "request_id": request.id,
            "input_preview": request.raw_input[:100],
            "blocked_patterns": request.blocked_patterns,
            "security_flags": request.security_flags,
            "status": request.status
        }

        self.security_log.append(event)

        # Keep log size manageable
        if len(self.security_log) > 1000:
            self.security_log = self.security_log[-1000:]

        # Print important events
        if event_type in ["BLOCKED_DIRECT_ACCESS", "INPUT_SANITIZED"]:
            print(f"🛡️ Security: {event_type} - {request.raw_input[:50]}...")

    def get_security_report(self) -> Dict:
        """Get security report for current session"""

        total_requests = len(self.request_history)
        blocked_count = sum(1 for r in self.request_history if r.status == "blocked")
        sanitized_count = sum(1 for r in self.request_history if "input_sanitized" in r.security_flags)

        return {
            "total_requests": total_requests,
            "blocked_attempts": blocked_count,
            "sanitized_inputs": sanitized_count,
            "block_rate": f"{(blocked_count/total_requests*100):.1f}%" if total_requests > 0 else "0%",
            "recent_blocks": [
                {
                    "time": r.timestamp.strftime("%H:%M:%S"),
                    "input": r.raw_input[:50],
                    "patterns": r.blocked_patterns
                }
                for r in self.request_history[-5:]
                if r.status == "blocked"
            ],
            "active_sessions": len(self.active_sessions)
        }

    async def shutdown(self):
        """Clean shutdown of Omega layer"""
        print("🛡️ Omega Prime shutting down...")

        # Log final statistics
        report = self.get_security_report()
        print(f"📊 Session Statistics:")
        print(f"   • Total requests: {report['total_requests']}")
        print(f"   • Blocked attempts: {report['blocked_attempts']}")
        print(f"   • Security interventions: {report['sanitized_inputs']}")

        # Clean up resources
        if self.master_agent:
            # Shutdown lower layers properly
            pass


# Global Omega Prime instance - THE ONLY ENTRY POINT
omega_prime = OmegaPrime()


async def user_request(input_text: str) -> str:
    """
    THE ONLY FUNCTION USERS SHOULD CALL.

    All user requests MUST go through this function.
    Direct tool access is FORBIDDEN and will be blocked.

    Args:
        input_text: Natural language request from user

    Returns:
        Response from CASPER system
    """
    return await omega_prime.process_user_input(input_text)