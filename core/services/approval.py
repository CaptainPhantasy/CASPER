"""
Human-in-the-Loop Approval System for CASPER Prime
Ensures all file operations require explicit user consent.
"""

import json
from pathlib import Path
from typing import Dict, List, Optional
from enum import Enum


class ApprovalStatus(Enum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"


class FileOperation:
    def __init__(self, operation_type: str, path: str, content: str, agent_id: str):
        self.operation_type = operation_type  # "create", "modify", "delete"
        self.path = path
        self.content = content
        self.agent_id = agent_id
        self.status = ApprovalStatus.PENDING


class HILApprovalService:
    """
    Human-in-the-Loop approval service for file operations.
    All file writes must be approved by the user before execution.
    """
    
    def __init__(self):
        self.pending_operations: List[FileOperation] = []
        self.approved_operations: List[FileOperation] = []
        self.rejected_operations: List[FileOperation] = []
    
    def request_file_write_approval(self, path: str, content: str, agent_id: str) -> str:
        """
        Request approval for a file write operation.
        Returns operation ID for tracking.
        """
        operation = FileOperation("create", path, content, agent_id)
        self.pending_operations.append(operation)
        
        # In a real implementation, this would:
        # 1. Show the user a preview of the file
        # 2. Ask for explicit approval
        # 3. Wait for user response
        
        print(f"\n🚨 APPROVAL REQUIRED 🚨")
        print(f"Agent {agent_id} wants to create file: {path}")
        print(f"Content preview (first 200 chars):")
        print(f"{content[:200]}...")
        print(f"\nApprove this file creation? (y/n): ", end="")
        
        # This is a blocking call - in production this should be async
        response = input().strip().lower()
        
        if response in ['y', 'yes']:
            operation.status = ApprovalStatus.APPROVED
            self.approved_operations.append(operation)
            self.pending_operations.remove(operation)
            return "approved"
        else:
            operation.status = ApprovalStatus.REJECTED
            self.rejected_operations.append(operation)
            self.pending_operations.remove(operation)
            return "rejected"
    
    def get_pending_approvals(self) -> List[FileOperation]:
        """Get all pending approval requests."""
        return self.pending_operations
    
    def approve_operation(self, operation_id: int) -> bool:
        """Approve a specific operation by ID."""
        if operation_id < len(self.pending_operations):
            operation = self.pending_opera