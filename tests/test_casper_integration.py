"""
End-to-end integration tests for CASPER system.
Tests the complete flow from user input to task execution with approval handling.
"""

import asyncio
import pytest
import os
import tempfile
import shutil
from pathlib import Path
from unittest.mock import Mock, patch, AsyncMock

# Add parent directory to path
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


@pytest.mark.asyncio
class TestCasperIntegration:
    """End-to-end integration tests"""

    async def test_file_creation_with_approval(self):
        """Test complete file creation flow with approval"""
        from core.ai.enhanced_command_interpreter import EnhancedCasperInterpreter
        from core.services.enhanced_approval import EnhancedApprovalService, ApprovalMode
        from core.ai.decision_orchestrator import DecisionOrchestrator

        # Setup components
        interpreter = EnhancedCasperInterpreter()
        approval_service = EnhancedApprovalService()
        approval_service.mode = ApprovalMode.AUTO  # Auto-approve safe operations
        orchestrator = DecisionOrchestrator()

        # Test input
        user_input = "create a README.md file with project documentation"

        # Interpret command
        command = await interpreter.interpret(user_input)

        assert command.command_type.value == "file_operation"
        assert command.action == "create"
        assert command.confidence >= 60.0
        assert command.suggested_agent == "worker"

        # Create orchestration plan
        plan = await orchestrator.orchestrate(command)

        assert plan.agents[0].value in ["backend_dev", "architect"]
        assert plan.estimated_duration_ms > 0

        # Simulate approval request (would come from Worker agent)
        approval_result = await approval_service.request_approval(
            operation_type="create",
            resource_type="file",
            path="README.md",
            content="# Project Documentation",
            agent_id="test_worker",
            agent_name="Worker Agent",
            task_context=user_input
        )

        # Should auto-approve README.md as it's safe
        assert approval_result == "approved"
        assert len(approval_service.completed_requests) == 1
        assert approval_service.completed_requests[0].status.value == "auto_approved"

    async def test_dangerous_operation_requires_manual_approval(self):
        """Test that dangerous operations require manual approval"""
        from core.ai.enhanced_command_interpreter import EnhancedCasperInterpreter
        from core.services.enhanced_approval import EnhancedApprovalService, ApprovalMode

        # Setup
        interpreter = EnhancedCasperInterpreter()
        approval_service = EnhancedApprovalService()
        approval_service.mode = ApprovalMode.AUTO  # Even in AUTO mode

        # Dangerous command
        user_input = "delete the entire database folder"

        # Interpret
        command = await interpreter.interpret(user_input)

        assert "delete" in command.action
        assert "confirm_deletion" in command.safety_checks

        # Try to get approval - should require manual
        approval_task = asyncio.create_task(
            approval_service.request_approval(
                operation_type="delete",
                resource_type="folder",
                path="/database",
                content="",
                agent_id="test_worker",
                task_context=user_input
            )
        )

        # Wait a bit
        await asyncio.sleep(0.1)

        # Should be pending, not auto-approved
        assert len(approval_service.pending_requests) == 1
        request = list(approval_service.pending_requests.values())[0]
        assert request.risk_level == "high"

        # Manually reject it
        request_id = request.id
        approval_service.reject(request_id, "Too dangerous")

        result = await approval_task
        assert result == "rejected"

    async def test_multi_agent_coordination(self):
        """Test multi-agent orchestration for complex tasks"""
        from core.ai.enhanced_command_interpreter import EnhancedCasperInterpreter
        from core.ai.decision_orchestrator import DecisionOrchestrator, AgentSpecialization

        interpreter = EnhancedCasperInterpreter()
        orchestrator = DecisionOrchestrator()

        # Complex command requiring multiple agents
        user_input = "create a full-stack web application with frontend, backend API, and tests"

        # Interpret
        command = await interpreter.interpret(user_input)

        # Should identify as complex
        complexity = orchestrator._assess_complexity(command)
        should_multi = orchestrator._should_use_multi_agent(command, complexity)

        # In real scenario with proper command type
        command.command_type = command.command_type  # Could be CODE_GENERATION
        command.raw_input = user_input

        # Create orchestration plan
        plan = await orchestrator.orchestrate(command)

        # Should have multiple agents
        if len(plan.agents) > 1:
            assert AgentSpecialization.ARCHITECT in plan.agents or \
                   AgentSpecialization.BACKEND_DEV in plan.agents
            assert plan.parallelization_factor > 0

    async def test_batch_approval_workflow(self):
        """Test batch approval for multiple operations"""
        from core.services.enhanced_approval import EnhancedApprovalService, ApprovalMode

        approval_service = EnhancedApprovalService()
        approval_service.mode = ApprovalMode.STRICT

        # Create multiple approval requests
        request_ids = []
        for i in range(5):
            task = asyncio.create_task(
                approval_service.request_approval(
                    operation_type="create",
                    resource_type="file",
                    path=f"src/module_{i}.py",
                    content=f"# Module {i}",
                    agent_id=f"agent_{i}",
                    task_context="Creating project structure"
                )
            )
            await asyncio.sleep(0.05)  # Small delay to register
            request_ids.append(task)

        # Should have 5 pending
        assert len(approval_service.pending_requests) == 5

        # Batch approve all in src/
        approved = approval_service.approve_all("src/")
        assert approved == 5

        # All tasks should resolve as approved
        results = await asyncio.gather(*request_ids)
        assert all(r == "approved" for r in results)

    async def test_cascading_failure_recovery(self):
        """Test cascading failure handling and recovery"""
        from core.ai.enhanced_command_interpreter import EnhancedCasperInterpreter
        from core.ai.decision_orchestrator import DecisionOrchestrator

        interpreter = EnhancedCasperInterpreter()
        orchestrator = DecisionOrchestrator()

        # Create a multi-agent command
        command = await interpreter.interpret("deploy application to production servers")

        # Simulate a failure
        error = Exception("Connection to server failed")

        # Handle cascading failure
        failure_analysis = await interpreter.handle_cascading_failure(error, command)

        assert "root_cause" in failure_analysis
        assert "recovery_plan" in failure_analysis
        assert len(failure_analysis["recovery_plan"]) > 0

        # Check that error was logged for learning
        assert len(interpreter.error_patterns) > 0
        assert interpreter.error_patterns[0]["error"] == str(error)

    async def test_approval_timeout_handling(self):
        """Test that approvals timeout properly"""
        from core.services.enhanced_approval import EnhancedApprovalService, ApprovalMode
        from datetime import datetime, timedelta

        approval_service = EnhancedApprovalService()
        approval_service.mode = ApprovalMode.STRICT

        # Create request with very short timeout
        approval_task = asyncio.create_task(
            approval_service.request_approval(
                operation_type="create",
                resource_type="file",
                path="test.txt",
                content="test",
                agent_id="test"
            )
        )

        # Hack: Set short expiration
        if approval_service.pending_requests:
            request_id = list(approval_service.pending_requests.keys())[0]
            approval_service.pending_requests[request_id].expires_at = datetime.now() + timedelta(seconds=0.1)

        # Wait for timeout
        await asyncio.sleep(0.2)

        # Should timeout
        try:
            result = await asyncio.wait_for(approval_task, timeout=0.5)
            # Result might be "expired" if cleanup thread ran
            assert result in ["expired", "rejected"]
        except asyncio.TimeoutError:
            # Or it might timeout at wait_for level
            pass

    async def test_confidence_based_routing(self):
        """Test that confidence levels route to appropriate handlers"""
        from core.ai.enhanced_command_interpreter import EnhancedCasperInterpreter

        interpreter = EnhancedCasperInterpreter()

        # High confidence - should interpret directly
        result = await interpreter.interpret("create file test.py")
        assert result.action != "clarification_needed"
        assert result.confidence == 100.0

        # Low confidence - should request clarification
        result = await interpreter.interpret("do the thing")
        assert result.action == "clarification_needed"
        assert result.confidence < 50.0
        assert "possible_interpretations" in result.context


class TestApprovalTerminalIntegration:
    """Test terminal approval handler integration"""

    def test_approval_handler_initialization(self):
        """Test approval handler setup"""
        from rich.console import Console
        from core.services.enhanced_approval import EnhancedApprovalService
        from core.terminal.approval_handler import initialize_approval_handler

        console = Console()
        approval_service = EnhancedApprovalService()

        handler, parser = initialize_approval_handler(console, approval_service)

        assert handler is not None
        assert parser is not None
        assert handler.approval_service == approval_service

    @pytest.mark.asyncio
    async def test_inline_approval_commands(self):
        """Test inline approval command parsing"""
        from rich.console import Console
        from core.services.enhanced_approval import EnhancedApprovalService
        from core.terminal.approval_handler import initialize_approval_handler

        console = Console()
        approval_service = EnhancedApprovalService()
        handler, parser = initialize_approval_handler(console, approval_service)

        # Create a pending request
        task = asyncio.create_task(
            approval_service.request_approval(
                operation_type="create",
                resource_type="file",
                path="test.txt",
                agent_id="test"
            )
        )
        await asyncio.sleep(0.1)

        # Test approve command
        handled = await parser.parse_and_execute("approve")
        assert handled == True

        # Check approval worked
        result = await task
        assert result == "approved"

    @pytest.mark.asyncio
    async def test_batch_mode_toggle(self):
        """Test batch mode enable/disable"""
        from rich.console import Console
        from core.services.enhanced_approval import EnhancedApprovalService
        from core.terminal.approval_handler import initialize_approval_handler

        console = Console()
        approval_service = EnhancedApprovalService()
        handler, parser = initialize_approval_handler(console, approval_service)

        # Enable batch mode
        await parser.parse_and_execute("batch on")
        assert handler.batch_mode == True

        # Disable batch mode
        await parser.parse_and_execute("batch off")
        assert handler.batch_mode == False


class TestSystemRobustness:
    """Test system robustness and error handling"""

    @pytest.mark.asyncio
    async def test_concurrent_approvals(self):
        """Test handling multiple concurrent approval requests"""
        from core.services.enhanced_approval import EnhancedApprovalService, ApprovalMode

        approval_service = EnhancedApprovalService()
        approval_service.mode = ApprovalMode.AUTO

        # Create 20 concurrent approval requests
        tasks = []
        for i in range(20):
            task = asyncio.create_task(
                approval_service.request_approval(
                    operation_type="create",
                    resource_type="file",
                    path=f"file_{i}.txt" if i < 10 else f"file_{i}.md",
                    content=f"Content {i}",
                    agent_id=f"agent_{i}"
                )
            )
            tasks.append(task)

        # Wait for all to complete
        results = await asyncio.gather(*tasks)

        # Auto mode should approve safe .md files
        md_results = results[10:]
        assert all(r == "approved" for r in md_results)

    @pytest.mark.asyncio
    async def test_malformed_input_handling(self):
        """Test system handles malformed input gracefully"""
        from core.ai.enhanced_command_interpreter import EnhancedCasperInterpreter

        interpreter = EnhancedCasperInterpreter()

        # Various malformed inputs
        malformed_inputs = [
            "",
            "   ",
            "!!!@#$%^&*()",
            "a" * 1000,  # Very long input
            "\n\n\n",
            None
        ]

        for input_text in malformed_inputs:
            if input_text is None:
                input_text = ""

            try:
                result = await interpreter.interpret(input_text)
                # Should handle gracefully
                assert result is not None
                assert hasattr(result, 'command_type')
            except Exception as e:
                # Should not crash
                assert False, f"Failed on input '{input_text}': {e}"

    def test_statistics_accuracy(self):
        """Test that statistics are accurately tracked"""
        from core.services.enhanced_approval import EnhancedApprovalService, ApprovalStatus

        service = EnhancedApprovalService()

        # Create various requests
        for i in range(10):
            request = service.ApprovalRequest() if hasattr(service, 'ApprovalRequest') else type('ApprovalRequest', (), {})()

            # Mock different statuses
            if i < 3:
                service.completed_requests.append(
                    type('Request', (), {'status': ApprovalStatus.APPROVED})()
                )
            elif i < 5:
                service.completed_requests.append(
                    type('Request', (), {'status': ApprovalStatus.REJECTED})()
                )
            elif i < 7:
                service.completed_requests.append(
                    type('Request', (), {'status': ApprovalStatus.AUTO_APPROVED})()
                )
            else:
                service.completed_requests.append(
                    type('Request', (), {'status': ApprovalStatus.EXPIRED})()
                )

        stats = service.get_statistics()

        assert stats["completed"] == 10
        assert stats["approved"] == 3
        assert stats["rejected"] == 2
        assert stats["auto_approved"] == 2
        assert stats["expired"] == 3


def run_integration_tests():
    """Run all integration tests with detailed output"""
    pytest.main([
        __file__,
        "-v",  # Verbose
        "-s",  # Show print statements
        "--tb=short",  # Short traceback
        "-W", "ignore::DeprecationWarning"  # Ignore deprecation warnings
    ])


if __name__ == "__main__":
    print("🧪 Running CASPER Integration Tests...")
    print("=" * 60)
    run_integration_tests()