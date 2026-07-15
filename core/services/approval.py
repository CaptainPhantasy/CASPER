"""
Human-in-the-Loop Approval System for CASPER Prime
Ensures all file operations require explicit user consent.
"""

import asyncio
import json
import os
import uuid
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Callable
from enum import Enum


class ApprovalStatus(Enum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"


class FileOperation:
    def __init__(self, operation_type: str, path: str, content: str, agent_id: str):
        self.id = str(uuid.uuid4())
        self.operation_type = operation_type  # "create", "modify", "delete"
        self.path = path
        self.content = content
        self.agent_id = agent_id
        self.status = ApprovalStatus.PENDING
        self.created_at = datetime.now()
        self.approved_at: Optional[datetime] = None
        self.future: Optional[asyncio.Future] = None

    def to_dict(self):
        return {
            "id": self.id,
            "operation_type": self.operation_type,
            "path": self.path,
            "content": (
                self.content[:200] + "..." if len(self.content) > 200 else self.content
            ),
            "agent_id": self.agent_id,
            "status": self.status.value,
            "created_at": self.created_at.isoformat(),
            "approved_at": self.approved_at.isoformat() if self.approved_at else None,
        }


class HILApprovalService:
    """
    Human-in-the-Loop approval service for file operations.
    All file writes must be approved by the user before execution.
    """

    def __init__(self):
        self.pending_operations: Dict[str, FileOperation] = {}
        self.approved_operations: List[FileOperation] = []
        self.rejected_operations: List[FileOperation] = []
        self.notification_callbacks: List[Callable] = []
        self.set_approval_mode(os.environ.get("CASPER_APPROVAL_MODE", "STRICT"))

    def set_approval_mode(self, mode: str):
        """Set the approval mode (STRICT, AUTO, YOLO)."""
        self.mode = mode.upper()
        if self.mode == "YOLO":
            print(
                "🚀 HIL Approval Service in YOLO mode - auto-approving all operations"
            )
        elif self.mode == "AUTO":
            # TODO: Implement a more sophisticated auto-approval logic.
            # For now, AUTO behaves like YOLO.
            print(
                "🚀 HIL Approval Service in AUTO mode - auto-approving all operations"
            )
        else:
            self.mode = "STRICT"
            print(
                "🚨 HIL Approval Service in STRICT mode - all operations require manual approval"
            )

    @property
    def auto_approve(self):
        return self.mode in ["YOLO", "AUTO"]

    def add_notification_callback(self, callback: Callable):
        """Add a callback to be notified when new approvals are needed."""
        self.notification_callbacks.append(callback)

    async def _notify_callbacks(self, operation: FileOperation):
        """Notify all registered callbacks about a new approval request."""
        for callback in self.notification_callbacks:
            try:
                if asyncio.iscoroutinefunction(callback):
                    await callback(operation)
                else:
                    callback(operation)
            except Exception as e:
                print(f"Error in approval callback: {e}")

    async def request_file_write_approval(
        self, path: str, content: str, agent_id: str
    ) -> str:
        """
        Request approval for a file write operation.
        Returns the approval result after user response.
        """
        operation = FileOperation("create", path, content, agent_id)

        # In YOLO mode, auto-approve immediately
        if self.auto_approve:
            operation.status = ApprovalStatus.APPROVED
            operation.approved_at = datetime.now()
            self.approved_operations.append(operation)

            print(f"\n🚀 AUTO-APPROVED (YOLO MODE) 🚀")
            print(f"Agent {agent_id} creating file: {path}")
            print(f"Operation ID: {operation.id}")

            return "approved"

        # Normal approval flow
        operation.future = asyncio.Future()
        self.pending_operations[operation.id] = operation

        # Notify callbacks (like WebSocket broadcast) about new approval request
        await self._notify_callbacks(operation)

        print(f"\n🚨 APPROVAL REQUIRED 🚨")
        print(f"Agent {agent_id} wants to create file: {path}")
        print(f"Approval ID: {operation.id}")

        # Wait for approval response via API
        try:
            result = await asyncio.wait_for(
                operation.future, timeout=300
            )  # 5 minute timeout
            return result
        except asyncio.TimeoutError:
            # Auto-reject after timeout
            operation.status = ApprovalStatus.REJECTED
            self.rejected_operations.append(operation)
            del self.pending_operations[operation.id]
            return "rejected"

    async def request_file_modify_approval(
        self, path: str, content: str, agent_id: str
    ) -> str:
        """
        Request approval for a file modification operation.
        Returns the approval result after user response.
        """
        operation = FileOperation("modify", path, content, agent_id)

        # In YOLO mode, auto-approve immediately
        if self.auto_approve:
            operation.status = ApprovalStatus.APPROVED
            operation.approved_at = datetime.now()
            self.approved_operations.append(operation)

            print(f"\n🚀 AUTO-APPROVED (YOLO MODE) 🚀")
            print(f"Agent {agent_id} modifying file: {path}")
            print(f"Operation ID: {operation.id}")

            return "approved"

        # Normal approval flow
        operation.future = asyncio.Future()
        self.pending_operations[operation.id] = operation

        # Notify callbacks (like WebSocket broadcast) about new approval request
        await self._notify_callbacks(operation)

        print(f"\n🚨 APPROVAL REQUIRED 🚨")
        print(f"Agent {agent_id} wants to modify file: {path}")
        print(f"Approval ID: {operation.id}")

        # Wait for approval response via API
        try:
            result = await asyncio.wait_for(
                operation.future, timeout=300
            )  # 5 minute timeout
            return result
        except asyncio.TimeoutError:
            # Auto-reject after timeout
            operation.status = ApprovalStatus.REJECTED
            self.rejected_operations.append(operation)
            del self.pending_operations[operation.id]
            return "rejected"

    async def request_file_delete_approval(self, path: str, agent_id: str) -> str:
        """
        Request approval for a file deletion operation.
        Returns the approval result after user response.
        """
        operation = FileOperation("delete", path, "", agent_id)

        # In YOLO mode, auto-approve immediately
        if self.auto_approve:
            operation.status = ApprovalStatus.APPROVED
            operation.approved_at = datetime.now()
            self.approved_operations.append(operation)

            print(f"\n🚀 AUTO-APPROVED (YOLO MODE) 🚀")
            print(f"Agent {agent_id} deleting file: {path}")
            print(f"Operation ID: {operation.id}")

            return "approved"

        # Normal approval flow
        operation.future = asyncio.Future()
        self.pending_operations[operation.id] = operation

        # Notify callbacks (like WebSocket broadcast) about new approval request
        await self._notify_callbacks(operation)

        print(f"\n🚨 APPROVAL REQUIRED 🚨")
        print(f"Agent {agent_id} wants to delete file: {path}")
        print(f"Approval ID: {operation.id}")

        # Wait for approval response via API
        try:
            result = await asyncio.wait_for(
                operation.future, timeout=300
            )  # 5 minute timeout
            return result
        except asyncio.TimeoutError:
            # Auto-reject after timeout
            operation.status = ApprovalStatus.REJECTED
            self.rejected_operations.append(operation)
            del self.pending_operations[operation.id]
            return "rejected"

    def get_pending_approvals(self) -> List[FileOperation]:
        """Get all pending approval requests."""
        return list(self.pending_operations.values())

    def get_pending_approvals_dict(self) -> List[Dict]:
        """Get all pending approval requests as dictionaries for API responses."""
        return [op.to_dict() for op in self.pending_operations.values()]

    def approve_operation(self, operation_id: str) -> bool:
        """Approve a specific operation by ID."""
        if operation_id in self.pending_operations:
            operation = self.pending_operations[operation_id]
            operation.status = ApprovalStatus.APPROVED
            operation.approved_at = datetime.now()

            # Resolve the future to unblock the waiting agent
            if operation.future and not operation.future.done():
                operation.future.set_result("approved")

            # Move to approved list
            self.approved_operations.append(operation)
            del self.pending_operations[operation_id]
            return True
        return False

    def reject_operation(self, operation_id: str) -> bool:
        """Reject a specific operation by ID."""
        if operation_id in self.pending_operations:
            operation = self.pending_operations[operation_id]
            operation.status = ApprovalStatus.REJECTED
            operation.approved_at = datetime.now()

            # Resolve the future to unblock the waiting agent
            if operation.future and not operation.future.done():
                operation.future.set_result("rejected")

            # Move to rejected list
            self.rejected_operations.append(operation)
            del self.pending_operations[operation_id]
            return True
        return False

    def get_operation_by_id(self, operation_id: str) -> Optional[FileOperation]:
        """Get an operation by its ID."""
        return self.pending_operations.get(operation_id)


# Global approval service instance
approval_service = HILApprovalService()
