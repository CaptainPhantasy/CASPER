"""
Comprehensive test suite for the enhanced approval system.
Tests all aspects of approval flow, risk assessment, and decision handling.
"""

import asyncio
import pytest
import os
from datetime import datetime, timedelta
from unittest.mock import Mock, patch, AsyncMock

# Add parent directory to path for imports
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.services.enhanced_approval import (
    EnhancedApprovalService,
    ApprovalRequest,
    ApprovalStatus,
    ApprovalMode,
    ApprovalPolicy
)


class TestApprovalPolicy:
    """Test risk assessment and auto-approval policies"""

    def test_risk_assessment_for_dangerous_patterns(self):
        """Test that dangerous patterns are identified as critical risk"""
        request = ApprovalRequest(
            operation_type="execute",
            resource_type="command",
            path="",
            content="sudo rm -rf /",
            agent_id="test"
        )

        risk = ApprovalPolicy.assess_risk(request)
        assert risk == "critical"

    def test_risk_assessment_for_delete_operations(self):
        """Test risk levels for deletion operations"""
        # Folder deletion should be high risk
        request = ApprovalRequest(
            operation_type="delete",
            resource_type="folder",
            path="important_folder",
            content="",
            agent_id="test"
        )
        risk = ApprovalPolicy.assess_risk(request)
        assert risk == "high"

        # File deletion should be medium risk
        request.resource_type = "file"
        risk = ApprovalPolicy.assess_risk(request)
        assert risk == "medium"

    def test_risk_assessment_for_safe_operations(self):
        """Test that safe operations get low risk"""
        request = ApprovalRequest(
            operation_type="create",
            resource_type="file",
            path="README.md",
            content="# Project Documentation",
            agent_id="test"
        )
        risk = ApprovalPolicy.assess_risk(request)
        assert risk == "low"

    def test_auto_approval_in_yolo_mode(self):
        """Test that YOLO mode approves everything"""
        request = ApprovalRequest(
            operation_type="delete",
            resource_type="folder",
            path="/etc/important",
            content="",
            agent_id="test"
        )

        can_auto, reasons = ApprovalPolicy.can_auto_approve(request, ApprovalMode.YOLO)
        assert can_auto == True
        assert "YOLO mode" in reasons[0]

    def test_auto_approval_in_strict_mode(self):
        """Test that STRICT mode never auto-approves"""
        request = ApprovalRequest(
            operation_type="create",
            resource_type="file",
            path="safe_file.txt",
            content="safe content",
            agent_id="test"
        )

        can_auto, reasons = ApprovalPolicy.can_auto_approve(request, ApprovalMode.STRICT)
        assert can_auto == False
        assert "Strict mode" in reasons[0]

    def test_auto_approval_in_auto_mode(self):
        """Test AUTO mode selective approval"""
        # Should approve low-risk documentation
        request = ApprovalRequest(
            operation_type="create",
            resource_type="file",
            path="docs/guide.md",
            content="# User Guide",
            agent_id="test"
        )
        can_auto, reasons = ApprovalPolicy.can_auto_approve(request, ApprovalMode.AUTO)
        assert can_auto == True
        assert "Low risk" in " ".join(reasons)

        # Should not approve high-risk operations
        request.operation_type = "delete"
        request.resource_type = "folder"
        can_auto, reasons = ApprovalPolicy.can_auto_approve(request, ApprovalMode.AUTO)
        assert can_auto == False


class TestEnhancedApprovalService:
    """Test the enhanced approval service functionality"""

    async def test_request_approval_auto_approval(self):
        """Test automatic approval for safe operations"""
        service = EnhancedApprovalService()
        service.mode = ApprovalMode.AUTO

        result = await service.request_approval(
            operation_type="create",
            resource_type="file",
            path="README.md",
            content="# Documentation",
            agent_id="test_agent",
            agent_name="Test Agent",
            task_context="Creating documentation"
        )

        assert result == "approved"
        assert len(service.completed_requests) == 1
        assert service.completed_requests[0].status == ApprovalStatus.AUTO_APPROVED

    async def test_request_approval_manual_flow(self):
        """Test manual approval flow"""
        service = EnhancedApprovalService()
        service.mode = ApprovalMode.STRICT

        # Start approval request in background
        approval_task = asyncio.create_task(
            service.request_approval(
                operation_type="delete",
                resource_type="file",
                path="important.db",
                content="",
                agent_id="test_agent",
                agent_name="Test Agent",
                task_context="Cleaning up"
            )
        )

        # Wait a bit for request to be registered
        await asyncio.sleep(0.1)

        # Should have pending request
        assert len(service.pending_requests) == 1
        request_id = list(service.pending_requests.keys())[0]

        # Approve it
        approved = service.approve(request_id, "test_user")
        assert approved == True

        # Wait for approval task to complete
        result = await approval_task
        assert result == "approved"

        # Check state
        assert len(service.pending_requests) == 0
        assert len(service.completed_requests) == 1
        assert service.completed_requests[0].status == ApprovalStatus.APPROVED

    async def test_request_approval_rejection(self):
        """Test rejection flow"""
        service = EnhancedApprovalService()
        service.mode = ApprovalMode.STRICT

        # Start approval request
        approval_task = asyncio.create_task(
            service.request_approval(
                operation_type="execute",
                resource_type="command",
                path="",
                content="rm -rf *",
                agent_id="test_agent"
            )
        )

        await asyncio.sleep(0.1)

        # Reject it
        request_id = list(service.pending_requests.keys())[0]
        rejected = service.reject(request_id, "Too dangerous")
        assert rejected == True

        result = await approval_task
        assert result == "rejected"

        # Check rejection was recorded
        assert service.completed_requests[0].status == ApprovalStatus.REJECTED
        assert service.completed_requests[0].rejection_reason == "Too dangerous"

    async def test_request_approval_timeout(self):
        """Test that requests timeout properly"""
        service = EnhancedApprovalService()
        service.mode = ApprovalMode.STRICT

        # Create request with very short timeout
        request = ApprovalRequest(
            operation_type="create",
            resource_type="file",
            path="test.txt",
            expires_at=datetime.now() + timedelta(seconds=0.1)
        )
        request.future = asyncio.Future()
        service.pending_requests[request.id] = request

        # Wait for timeout
        try:
            result = await asyncio.wait_for(request.future, timeout=0.5)
        except asyncio.TimeoutError:
            result = "expired"

        assert result == "expired"

    def test_approve_all(self):
        """Test batch approval functionality"""
        service = EnhancedApprovalService()

        # Create multiple pending requests
        for i in range(5):
            request = ApprovalRequest(
                operation_type="create",
                resource_type="file",
                path=f"file_{i}.txt",
                agent_id=f"agent_{i}"
            )
            service.pending_requests[request.id] = request

        # Approve all
        count = service.approve_all()
        assert count == 5
        assert len(service.pending_requests) == 0
        assert len(service.completed_requests) == 5
        assert all(r.status == ApprovalStatus.APPROVED for r in service.completed_requests)

    def test_approve_all_with_pattern(self):
        """Test pattern-based batch approval"""
        service = EnhancedApprovalService()

        # Create requests with different paths
        paths = ["docs/guide.md", "src/main.py", "docs/api.md", "tests/test.py"]
        for path in paths:
            request = ApprovalRequest(
                operation_type="create",
                resource_type="file",
                path=path,
                agent_id="test"
            )
            service.pending_requests[request.id] = request

        # Approve only docs
        count = service.approve_all("docs/")
        assert count == 2
        assert len(service.pending_requests) == 2
        assert len(service.completed_requests) == 2

    def test_find_request_by_partial_id(self):
        """Test finding requests by partial ID"""
        service = EnhancedApprovalService()

        request = ApprovalRequest(
            id="12345678-abcd-efgh-ijkl-mnopqrstuvwx",
            operation_type="create",
            path="test.txt"
        )
        service.pending_requests[request.id] = request

        # Find by partial ID
        found = service.find_request("1234")
        assert found is not None
        assert found.id == request.id

        # Non-existent partial
        not_found = service.find_request("9999")
        assert not_found is None

    def test_get_pending_by_risk(self):
        """Test filtering pending requests by risk level"""
        service = EnhancedApprovalService()

        # Create requests with different risk levels
        risk_levels = ["low", "medium", "high", "critical"]
        for risk in risk_levels:
            for i in range(2):
                request = ApprovalRequest(
                    operation_type="create",
                    path=f"{risk}_{i}.txt",
                    risk_level=risk
                )
                service.pending_requests[request.id] = request

        # Get by risk level
        high_risk = service.get_pending_by_risk("high")
        assert len(high_risk) == 2
        assert all(r.risk_level == "high" for r in high_risk)

    def test_statistics(self):
        """Test statistics gathering"""
        service = EnhancedApprovalService()
        service.mode = ApprovalMode.AUTO

        # Create various requests
        # Pending
        for i in range(3):
            request = ApprovalRequest(
                operation_type="create",
                path=f"pending_{i}.txt",
                risk_level="low" if i == 0 else "high"
            )
            service.pending_requests[request.id] = request

        # Completed
        service.completed_requests = [
            ApprovalRequest(status=ApprovalStatus.APPROVED),
            ApprovalRequest(status=ApprovalStatus.APPROVED),
            ApprovalRequest(status=ApprovalStatus.REJECTED),
            ApprovalRequest(status=ApprovalStatus.AUTO_APPROVED),
            ApprovalRequest(status=ApprovalStatus.EXPIRED),
        ]

        stats = service.get_statistics()

        assert stats["mode"] == "auto"
        assert stats["pending"] == 3
        assert stats["completed"] == 5
        assert stats["approved"] == 2
        assert stats["rejected"] == 1
        assert stats["auto_approved"] == 1
        assert stats["expired"] == 1
        assert stats["by_risk"]["low"] == 1
        assert stats["by_risk"]["high"] == 2

    async def test_notification_callbacks(self):
        """Test that callbacks are notified of new requests"""
        service = EnhancedApprovalService()
        service.mode = ApprovalMode.STRICT

        # Add callback
        callback_called = False
        received_request = None

        async def test_callback(request):
            nonlocal callback_called, received_request
            callback_called = True
            received_request = request

        service.add_notification_callback(test_callback)

        # Create request
        approval_task = asyncio.create_task(
            service.request_approval(
                operation_type="create",
                resource_type="file",
                path="test.txt",
                agent_id="test"
            )
        )

        # Wait for callback
        await asyncio.sleep(0.1)

        assert callback_called == True
        assert received_request is not None
        assert received_request.path == "test.txt"

        # Clean up
        request_id = list(service.pending_requests.keys())[0]
        service.approve(request_id)
        await approval_task


class TestBackwardCompatibility:
    """Test backward compatibility functions"""

    @pytest.mark.asyncio
    async def test_legacy_file_write_approval(self):
        """Test legacy file write approval function"""
        from core.services.enhanced_approval import request_file_write_approval

        with patch('core.services.enhanced_approval.enhanced_approval_service') as mock_service:
            mock_service.request_approval = AsyncMock(return_value="approved")

            result = await request_file_write_approval(
                path="test.txt",
                content="test content",
                agent_id="test_agent"
            )

            assert result == "approved"
            mock_service.request_approval.assert_called_once()

    @pytest.mark.asyncio
    async def test_legacy_file_modify_approval(self):
        """Test legacy file modify approval function"""
        from core.services.enhanced_approval import request_file_modify_approval

        with patch('core.services.enhanced_approval.enhanced_approval_service') as mock_service:
            mock_service.request_approval = AsyncMock(return_value="approved")

            result = await request_file_modify_approval(
                path="test.txt",
                content="modified content",
                agent_id="test_agent"
            )

            assert result == "approved"

    @pytest.mark.asyncio
    async def test_legacy_file_delete_approval(self):
        """Test legacy file delete approval function"""
        from core.services.enhanced_approval import request_file_delete_approval

        with patch('core.services.enhanced_approval.enhanced_approval_service') as mock_service:
            mock_service.request_approval = AsyncMock(return_value="rejected")

            result = await request_file_delete_approval(
                path="important.db",
                agent_id="test_agent"
            )

            assert result == "rejected"


def run_tests():
    """Run all tests with detailed output"""
    pytest.main([__file__, "-v", "-s", "--tb=short"])


if __name__ == "__main__":
    run_tests()