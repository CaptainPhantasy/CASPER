"""
Enhanced Human-in-the-Loop Approval System for CASPER Prime
Provides seamless approval request and granting process with multiple interfaces.
"""

import asyncio
import json
import uuid
import os
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Callable, Any
from enum import Enum
from dataclasses import dataclass, field
import threading
from queue import Queue, Empty


class ApprovalStatus(Enum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    EXPIRED = "expired"
    AUTO_APPROVED = "auto_approved"


class ApprovalMode(Enum):
    STRICT = "strict"      # All operations require manual approval
    AUTO = "auto"          # Safe operations auto-approved
    YOLO = "yolo"          # All operations auto-approved
    INTERACTIVE = "interactive"  # Smart prompting with context


@dataclass
class ApprovalRequest:
    """Enhanced approval request with full context"""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    operation_type: str = ""  # create, modify, delete, execute
    resource_type: str = ""   # file, folder, command, api
    path: str = ""
    content: str = ""
    agent_id: str = ""
    agent_name: str = ""
    task_context: str = ""
    risk_level: str = "low"  # low, medium, high, critical
    status: ApprovalStatus = ApprovalStatus.PENDING
    created_at: datetime = field(default_factory=datetime.now)
    expires_at: datetime = field(default_factory=lambda: datetime.now() + timedelta(minutes=5))
    approved_at: Optional[datetime] = None
    approved_by: str = ""
    rejection_reason: str = ""
    future: Optional[asyncio.Future] = field(default=None, compare=False, repr=False)
    auto_approve_reasons: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization"""
        return {
            "id": self.id,
            "operation_type": self.operation_type,
            "resource_type": self.resource_type,
            "path": self.path,
            "content_preview": self.content[:200] + "..." if len(self.content) > 200 else self.content,
            "agent_id": self.agent_id,
            "agent_name": self.agent_name,
            "task_context": self.task_context,
            "risk_level": self.risk_level,
            "status": self.status.value,
            "created_at": self.created_at.isoformat(),
            "expires_at": self.expires_at.isoformat(),
            "approved_at": self.approved_at.isoformat() if self.approved_at else None,
            "approved_by": self.approved_by,
            "auto_approve_reasons": self.auto_approve_reasons
        }

    def format_for_display(self) -> str:
        """Format approval request for terminal display"""
        risk_colors = {
            "low": "green",
            "medium": "yellow",
            "high": "orange",
            "critical": "red"
        }
        risk_color = risk_colors.get(self.risk_level, "white")

        return f"""
╔══════════════════════════════════════════════════════════════════╗
║                    APPROVAL REQUEST                              ║
╠══════════════════════════════════════════════════════════════════╣
║ ID:        {self.id[:8]}...                                     ║
║ Agent:     {self.agent_name:40}                  ║
║ Operation: {self.operation_type} {self.resource_type:30}    ║
║ Path:      {self.path:40}                        ║
║ Risk:      [{risk_color}]{self.risk_level.upper()}[/{risk_color}]                                            ║
║ Context:   {self.task_context[:40]}...                          ║
╠══════════════════════════════════════════════════════════════════╣
║ Content Preview:                                                 ║
║ {self.content[:60]}...                                          ║
╠══════════════════════════════════════════════════════════════════╣
║ Commands:                                                        ║
║   • Type 'y' or 'yes' to APPROVE                               ║
║   • Type 'n' or 'no' to REJECT                                 ║
║   • Type 'v' to VIEW full content                              ║
║   • Type 'a' to APPROVE ALL pending                            ║
║   • Type 's' to SKIP (decide later)                            ║
╚══════════════════════════════════════════════════════════════════╝
"""


class ApprovalPolicy:
    """Policy for auto-approval decisions"""

    SAFE_OPERATIONS = {
        "create": ["*.md", "*.txt", "*.log", "README*", "LICENSE*", ".gitignore"],
        "modify": ["*.md", "*.txt", "*.log"],
        "execute": ["ls", "pwd", "echo", "cat", "grep", "find"],
    }

    DANGEROUS_PATTERNS = [
        "rm -rf",
        "sudo",
        "/etc/",
        "/usr/",
        "/bin/",
        ".ssh/",
        "credentials",
        "password",
        "secret",
        "token",
        "api_key"
    ]

    @classmethod
    def assess_risk(cls, request: ApprovalRequest) -> str:
        """Assess risk level of an operation"""

        # Check for dangerous patterns
        content_lower = request.content.lower()
        path_lower = request.path.lower()

        for pattern in cls.DANGEROUS_PATTERNS:
            if pattern in content_lower or pattern in path_lower:
                return "critical"

        # Check operation type
        if request.operation_type == "delete":
            if request.resource_type == "folder":
                return "high"
            return "medium"

        # Check file paths
        if request.path.startswith("/"):
            return "high"

        # Check for safe operations
        if request.operation_type in cls.SAFE_OPERATIONS:
            safe_patterns = cls.SAFE_OPERATIONS[request.operation_type]
            for pattern in safe_patterns:
                if pattern.replace("*", "") in request.path:
                    return "low"

        return "medium"

    @classmethod
    def can_auto_approve(cls, request: ApprovalRequest, mode: ApprovalMode) -> tuple[bool, List[str]]:
        """Determine if request can be auto-approved based on policy"""
        reasons = []

        if mode == ApprovalMode.YOLO:
            reasons.append("YOLO mode - auto-approving all")
            return True, reasons

        if mode == ApprovalMode.STRICT:
            return False, ["Strict mode - manual approval required"]

        # AUTO and INTERACTIVE modes
        risk = cls.assess_risk(request)
        request.risk_level = risk

        if risk in ["high", "critical"]:
            return False, [f"Risk level {risk} requires manual approval"]

        if risk == "low":
            reasons.append("Low risk operation")

            # Additional checks for AUTO mode
            if mode == ApprovalMode.AUTO:
                if request.operation_type == "create":
                    if request.path.endswith((".md", ".txt", ".log")):
                        reasons.append("Creating documentation/text file")
                        return True, reasons
                    if "README" in request.path or "LICENSE" in request.path:
                        reasons.append("Creating standard project file")
                        return True, reasons

        return False, ["Does not meet auto-approval criteria"]


class EnhancedApprovalService:
    """
    Enhanced approval service with multiple interfaces and smart routing.
    """

    def __init__(self):
        self.mode = self._get_approval_mode()
        self.pending_requests: Dict[str, ApprovalRequest] = {}
        self.completed_requests: List[ApprovalRequest] = []
        self.approval_queue = Queue()
        self.notification_callbacks: List[Callable] = []
        self.interactive_handler: Optional[Callable] = None
        self.batch_approval_enabled = False
        self.approval_patterns: List[Dict] = []  # Learn from user behavior

        # Start background cleanup thread
        self.cleanup_thread = threading.Thread(target=self._cleanup_expired, daemon=True)
        self.cleanup_thread.start()

        print(f"🎯 Enhanced Approval Service initialized in {self.mode.value.upper()} mode")

    def _get_approval_mode(self) -> ApprovalMode:
        """Get approval mode from environment"""
        mode_str = os.environ.get('CASPER_APPROVAL_MODE', 'INTERACTIVE').upper()
        try:
            return ApprovalMode[mode_str]
        except KeyError:
            return ApprovalMode.INTERACTIVE

    def set_interactive_handler(self, handler: Callable):
        """Set the interactive approval handler (for terminal integration)"""
        self.interactive_handler = handler

    def add_notification_callback(self, callback: Callable):
        """Add a callback for approval notifications"""
        self.notification_callbacks.append(callback)

    async def request_approval(
        self,
        operation_type: str,
        resource_type: str,
        path: str,
        content: str = "",
        agent_id: str = "",
        agent_name: str = "",
        task_context: str = ""
    ) -> str:
        """
        Request approval with enhanced context and routing.
        Returns: "approved", "rejected", or "expired"
        """

        # Create approval request
        request = ApprovalRequest(
            operation_type=operation_type,
            resource_type=resource_type,
            path=path,
            content=content,
            agent_id=agent_id,
            agent_name=agent_name or agent_id[:8],
            task_context=task_context
        )

        # Assess risk and check auto-approval
        request.risk_level = ApprovalPolicy.assess_risk(request)
        can_auto, reasons = ApprovalPolicy.can_auto_approve(request, self.mode)
        request.auto_approve_reasons = reasons

        # Handle auto-approval
        if can_auto:
            request.status = ApprovalStatus.AUTO_APPROVED
            request.approved_at = datetime.now()
            request.approved_by = "system-policy"
            self.completed_requests.append(request)

            self._print_auto_approval(request)
            return "approved"

        # Handle manual approval
        request.future = asyncio.Future()
        self.pending_requests[request.id] = request

        # Notify callbacks
        await self._notify_callbacks(request)

        # Display approval request based on mode
        if self.mode == ApprovalMode.INTERACTIVE and self.interactive_handler:
            # Use interactive handler if available
            asyncio.create_task(self._handle_interactive(request))
        else:
            # Fallback to console display
            self._print_approval_request(request)

        # Wait for approval with timeout
        try:
            result = await asyncio.wait_for(
                request.future,
                timeout=(request.expires_at - datetime.now()).total_seconds()
            )
            return result
        except asyncio.TimeoutError:
            request.status = ApprovalStatus.EXPIRED
            self.completed_requests.append(request)
            if request.id in self.pending_requests:
                del self.pending_requests[request.id]
            self._print_expiration(request)
            return "expired"

    async def _handle_interactive(self, request: ApprovalRequest):
        """Handle interactive approval through registered handler"""
        if self.interactive_handler:
            try:
                await self.interactive_handler(request)
            except Exception as e:
                print(f"Interactive handler error: {e}")
                self._print_approval_request(request)

    def approve(self, request_id: str, approved_by: str = "user") -> bool:
        """Approve a specific request"""
        if request_id in self.pending_requests:
            request = self.pending_requests[request_id]
            request.status = ApprovalStatus.APPROVED
            request.approved_at = datetime.now()
            request.approved_by = approved_by

            # Learn from approval
            self._learn_from_decision(request, approved=True)

            # Resolve future
            if request.future and not request.future.done():
                request.future.set_result("approved")

            # Move to completed
            self.completed_requests.append(request)
            del self.pending_requests[request_id]

            print(f"✅ Approved: {request.operation_type} {request.path}")
            return True
        return False

    def reject(self, request_id: str, reason: str = "") -> bool:
        """Reject a specific request"""
        if request_id in self.pending_requests:
            request = self.pending_requests[request_id]
            request.status = ApprovalStatus.REJECTED
            request.approved_at = datetime.now()
            request.rejection_reason = reason

            # Learn from rejection
            self._learn_from_decision(request, approved=False)

            # Resolve future
            if request.future and not request.future.done():
                request.future.set_result("rejected")

            # Move to completed
            self.completed_requests.append(request)
            del self.pending_requests[request_id]

            print(f"❌ Rejected: {request.operation_type} {request.path}")
            if reason:
                print(f"   Reason: {reason}")
            return True
        return False

    def approve_all(self, pattern: str = "*") -> int:
        """Approve all pending requests matching pattern"""
        approved = 0
        for request_id in list(self.pending_requests.keys()):
            request = self.pending_requests[request_id]
            if pattern == "*" or pattern in request.path:
                if self.approve(request_id, "batch-approval"):
                    approved += 1
        return approved

    def reject_all(self, pattern: str = "*", reason: str = "batch rejection") -> int:
        """Reject all pending requests matching pattern"""
        rejected = 0
        for request_id in list(self.pending_requests.keys()):
            request = self.pending_requests[request_id]
            if pattern == "*" or pattern in request.path:
                if self.reject(request_id, reason):
                    rejected += 1
        return rejected

    def get_pending(self) -> List[ApprovalRequest]:
        """Get all pending approval requests"""
        return list(self.pending_requests.values())

    def get_pending_by_risk(self, risk_level: str) -> List[ApprovalRequest]:
        """Get pending requests by risk level"""
        return [r for r in self.pending_requests.values() if r.risk_level == risk_level]

    def find_request(self, partial_id: str) -> Optional[ApprovalRequest]:
        """Find request by partial ID (for user convenience)"""
        for request_id, request in self.pending_requests.items():
            if request_id.startswith(partial_id):
                return request
        return None

    async def _notify_callbacks(self, request: ApprovalRequest):
        """Notify all registered callbacks"""
        for callback in self.notification_callbacks:
            try:
                if asyncio.iscoroutinefunction(callback):
                    await callback(request)
                else:
                    callback(request)
            except Exception as e:
                print(f"Callback error: {e}")

    def _print_approval_request(self, request: ApprovalRequest):
        """Print approval request to console"""
        risk_symbols = {
            "low": "✓",
            "medium": "⚠",
            "high": "⚠️",
            "critical": "🚨"
        }
        symbol = risk_symbols.get(request.risk_level, "•")

        print(f"\n{symbol} APPROVAL REQUIRED [{request.risk_level.upper()}]")
        print(f"ID: {request.id[:8]}...")
        print(f"Agent: {request.agent_name} wants to {request.operation_type} {request.resource_type}")
        print(f"Path: {request.path}")
        if request.task_context:
            print(f"Context: {request.task_context}")
        if request.content:
            preview = request.content[:100] + "..." if len(request.content) > 100 else request.content
            print(f"Content: {preview}")
        print(f"Expires: {request.expires_at.strftime('%H:%M:%S')}")
        print("\n→ To approve: approve <id> or approve all")
        print("→ To reject: reject <id> or reject all")

    def _print_auto_approval(self, request: ApprovalRequest):
        """Print auto-approval notification"""
        print(f"\n✨ AUTO-APPROVED: {request.operation_type} {request.path}")
        if request.auto_approve_reasons:
            print(f"   Reasons: {', '.join(request.auto_approve_reasons)}")

    def _print_expiration(self, request: ApprovalRequest):
        """Print expiration notification"""
        print(f"\n⏰ EXPIRED: Approval request for {request.path} has timed out")

    def _learn_from_decision(self, request: ApprovalRequest, approved: bool):
        """Learn from user decisions to improve future auto-approval"""
        pattern = {
            "operation": request.operation_type,
            "resource": request.resource_type,
            "path_pattern": request.path,
            "risk_level": request.risk_level,
            "approved": approved,
            "timestamp": datetime.now()
        }
        self.approval_patterns.append(pattern)

        # Limit pattern history
        if len(self.approval_patterns) > 100:
            self.approval_patterns = self.approval_patterns[-100:]

    def _cleanup_expired(self):
        """Background thread to clean up expired requests"""
        while True:
            try:
                now = datetime.now()
                expired_ids = []

                for request_id, request in self.pending_requests.items():
                    if now > request.expires_at:
                        expired_ids.append(request_id)

                for request_id in expired_ids:
                    request = self.pending_requests[request_id]
                    request.status = ApprovalStatus.EXPIRED

                    # Resolve future
                    if request.future and not request.future.done():
                        request.future.set_result("expired")

                    self.completed_requests.append(request)
                    del self.pending_requests[request_id]
                    print(f"\n⏰ Request {request_id[:8]}... expired")

                # Sleep for 30 seconds before next cleanup
                threading.Event().wait(30)

            except Exception as e:
                print(f"Cleanup thread error: {e}")

    def get_statistics(self) -> Dict[str, Any]:
        """Get approval statistics"""
        stats = {
            "mode": self.mode.value,
            "pending": len(self.pending_requests),
            "completed": len(self.completed_requests),
            "approved": len([r for r in self.completed_requests if r.status == ApprovalStatus.APPROVED]),
            "rejected": len([r for r in self.completed_requests if r.status == ApprovalStatus.REJECTED]),
            "auto_approved": len([r for r in self.completed_requests if r.status == ApprovalStatus.AUTO_APPROVED]),
            "expired": len([r for r in self.completed_requests if r.status == ApprovalStatus.EXPIRED]),
            "by_risk": {
                "low": len([r for r in self.pending_requests.values() if r.risk_level == "low"]),
                "medium": len([r for r in self.pending_requests.values() if r.risk_level == "medium"]),
                "high": len([r for r in self.pending_requests.values() if r.risk_level == "high"]),
                "critical": len([r for r in self.pending_requests.values() if r.risk_level == "critical"])
            }
        }
        return stats


# Global enhanced approval service instance
enhanced_approval_service = EnhancedApprovalService()


# Convenience functions for backward compatibility
async def request_file_write_approval(path: str, content: str, agent_id: str) -> str:
    """Backward compatible function for file write approval"""
    return await enhanced_approval_service.request_approval(
        operation_type="create",
        resource_type="file",
        path=path,
        content=content,
        agent_id=agent_id
    )

async def request_file_modify_approval(path: str, content: str, agent_id: str) -> str:
    """Backward compatible function for file modification approval"""
    return await enhanced_approval_service.request_approval(
        operation_type="modify",
        resource_type="file",
        path=path,
        content=content,
        agent_id=agent_id
    )

async def request_file_delete_approval(path: str, agent_id: str) -> str:
    """Backward compatible function for file deletion approval"""
    return await enhanced_approval_service.request_approval(
        operation_type="delete",
        resource_type="file",
        path=path,
        agent_id=agent_id
    )