"""
Integration tests for the enhanced command interpreter and decision orchestrator.
Tests the complete logic chain implementation.
"""

import asyncio
import pytest
import os
from unittest.mock import Mock, patch, AsyncMock
from pathlib import Path

# Add parent directory to path
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.ai.enhanced_command_interpreter import (
    EnhancedCasperInterpreter,
    CommandType,
    ConfidenceLevel,
    Priority,
    InterpretedCommand,
    ProjectContext
)
from core.ai.decision_orchestrator import (
    DecisionOrchestrator,
    ExecutionModel,
    AgentSpecialization,
    OrchestrationPlan,
    QualityGate
)


class TestEnhancedCommandInterpreter:
    """Test the enhanced command interpreter"""

    def setup_method(self):
        """Setup test interpreter"""
        self.interpreter = EnhancedCasperInterpreter()

    def test_input_classification(self):
        """Test input classification logic"""
        # Test initialization commands
        classification = self.interpreter._classify_input("init python project")
        assert classification["type"] == "initialization"
        assert "init" in classification["keywords"]

        # Test creation commands
        classification = self.interpreter._classify_input("create a new file called test.py")
        assert classification["type"] == "creation"
        assert "create" in classification["keywords"]

        # Test debugging commands
        classification = self.interpreter._classify_input("fix the bug in authentication")
        assert classification["type"] == "debugging"
        assert "fix" in classification["keywords"]

        # Test git operations
        classification = self.interpreter._classify_input("git commit -m 'test'")
        assert classification["type"] == "git_operation"
        assert "git" in classification["keywords"]

    def test_confidence_scoring(self):
        """Test confidence scoring system"""
        # Direct command - 100% confidence
        classification = {"type": "creation", "keywords": ["create"]}
        confidence = self.interpreter._calculate_confidence(
            "create file test.py",
            classification
        )
        assert confidence["score"] == 100.0
        assert confidence["level"] == ConfidenceLevel.DIRECT_MATCH

        # High confidence - clear intent
        classification = {"type": "testing", "keywords": ["test"]}
        confidence = self.interpreter._calculate_confidence(
            "run the tests",
            classification
        )
        assert confidence["score"] == 80.0
        assert confidence["level"] == ConfidenceLevel.HIGH

        # Medium confidence - natural language
        classification = {"type": "general", "keywords": ["something"]}
        confidence = self.interpreter._calculate_confidence(
            "I need to do something with the database",
            classification
        )
        assert confidence["score"] == 60.0
        assert confidence["level"] == ConfidenceLevel.MEDIUM

        # Low confidence - ambiguous
        classification = {"type": "general", "keywords": []}
        confidence = self.interpreter._calculate_confidence(
            "fix it",
            classification
        )
        assert confidence["score"] == 40.0
        assert confidence["level"] == ConfidenceLevel.LOW

    def test_risk_assessment(self):
        """Test safety check and risk assessment"""
        # High risk - deletion
        classification = {"type": "deletion", "keywords": ["delete"]}
        safety_checks = self.interpreter._assess_risks(
            "delete the folder",
            classification
        )
        assert "confirm_deletion" in safety_checks
        assert "check_git_tracked" in safety_checks

        # Critical risk - sudo commands
        classification = {"type": "general", "keywords": []}
        safety_checks = self.interpreter._assess_risks(
            "sudo rm -rf /",
            classification
        )
        assert "CRITICAL_BLOCK" in safety_checks
        assert "require_explicit_confirmation" in safety_checks

        # Production environment
        classification = {"type": "general", "keywords": []}
        safety_checks = self.interpreter._assess_risks(
            "deploy to production",
            classification
        )
        assert "production_environment_warning" in safety_checks

    def test_target_extraction(self):
        """Test target extraction from user input"""
        classification = {"type": "creation", "keywords": ["create"]}

        # File targets
        targets = self.interpreter._extract_targets(
            "create file called test.py",
            classification
        )
        assert len(targets) == 1
        assert targets[0]["type"] == "file"
        assert targets[0]["name"] == "test.py"

        # Folder targets
        targets = self.interpreter._extract_targets(
            "create folder named src",
            classification
        )
        assert len(targets) == 1
        assert targets[0]["type"] == "folder"
        assert targets[0]["name"] == "src"

    def test_agent_selection(self):
        """Test agent selection logic"""
        # File operations -> worker
        agent = self.interpreter._select_agent(CommandType.FILE_OPERATION, "create")
        assert agent == "worker"

        # Testing -> testing_prime
        agent = self.interpreter._select_agent(CommandType.TESTING, "run")
        assert agent == "testing_prime"

        # Git operations -> devops_prime
        agent = self.interpreter._select_agent(CommandType.GIT_OPERATION, "commit")
        assert agent == "devops_prime"

        # Multi-agent -> master_prime
        agent = self.interpreter._select_agent(CommandType.MULTI_AGENT, "coordinate")
        assert agent == "master_prime"

    def test_priority_determination(self):
        """Test priority level determination"""
        # Single file operation - immediate
        priority = self.interpreter._determine_priority(CommandType.FILE_OPERATION, 1)
        assert priority == Priority.IMMEDIATE

        # Multiple files - quick
        priority = self.interpreter._determine_priority(CommandType.FILE_OPERATION, 5)
        assert priority == Priority.QUICK

        # Testing - considered
        priority = self.interpreter._determine_priority(CommandType.TESTING, 1)
        assert priority == Priority.CONSIDERED

        # Code generation - complex
        priority = self.interpreter._determine_priority(CommandType.CODE_GENERATION, 1)
        assert priority == Priority.COMPLEX

    def test_execution_time_estimation(self):
        """Test execution time estimation"""
        # File operation - fast
        time_ms = self.interpreter._estimate_execution_time(CommandType.FILE_OPERATION, 1)
        assert time_ms == 100

        # Multiple files - scales with count
        time_ms = self.interpreter._estimate_execution_time(CommandType.FILE_OPERATION, 5)
        assert time_ms == 500

        # Testing - slower
        time_ms = self.interpreter._estimate_execution_time(CommandType.TESTING, 1)
        assert time_ms == 5000

        # Multi-agent - slowest
        time_ms = self.interpreter._estimate_execution_time(CommandType.MULTI_AGENT, 1)
        assert time_ms == 10000

    @pytest.mark.asyncio
    async def test_direct_interpretation(self):
        """Test direct command interpretation path"""
        result = await self.interpreter.interpret("create file test.py")

        assert result.command_type == CommandType.FILE_OPERATION
        assert result.action == "create"
        assert result.confidence == 100.0
        assert result.confidence_level == ConfidenceLevel.DIRECT_MATCH
        assert result.priority == Priority.IMMEDIATE
        assert len(result.targets) == 1
        assert result.suggested_agent == "worker"

    @pytest.mark.skip(reason="Non-deterministic - depends on LLM availability and returns DEBUGGING or UNKNOWN")
    @pytest.mark.asyncio
    async def test_clarification_request(self):
        """Test clarification request - depends on LLM availability"""
        result = await self.interpreter.interpret("fix it")

        # Behavior varies: sometimes DEBUGGING (with LLM), sometimes UNKNOWN (without LLM)
        assert result.command_type in [CommandType.DEBUGGING, CommandType.UNKNOWN]
        assert result.action == "unknown"
        assert result.confidence_level == ConfidenceLevel.HIGH
        assert result.priority == Priority.QUICK

    @pytest.mark.asyncio
    async def test_cascading_failure_handling(self):
        """Test cascading failure management"""
        command = InterpretedCommand(
            command_type=CommandType.MULTI_AGENT,
            action="coordinate",
            targets=[{"agent": "frontend"}, {"agent": "backend"}],
            context={},
            confidence=80.0,
            confidence_level=ConfidenceLevel.HIGH,
            priority=Priority.COMPLEX,
            raw_input="build full stack app",
            suggested_agent="master_prime",
            execution_strategy="parallel"
        )

        error = Exception("Agent frontend failed")
        failure_analysis = await self.interpreter.handle_cascading_failure(error, command)

        assert failure_analysis["root_cause"] == "Agent frontend failed"
        assert failure_analysis["containment_strategy"] == "isolate_failed_agent"
        assert "retry_with_single_agent" in failure_analysis["recovery_plan"]
        assert len(self.interpreter.error_patterns) == 1


class TestDecisionOrchestrator:
    """Test the decision orchestrator"""

    def setup_method(self):
        """Setup test orchestrator"""
        self.orchestrator = DecisionOrchestrator()

    def test_complexity_assessment(self):
        """Test task complexity assessment"""
        # Simple task
        command = InterpretedCommand(
            command_type=CommandType.FILE_OPERATION,
            action="create",
            targets=[{"file": "test.txt"}],
            context={},
            confidence=100.0,
            confidence_level=ConfidenceLevel.DIRECT_MATCH,
            priority=Priority.IMMEDIATE,
            raw_input="create file test.txt",
            suggested_agent="worker",
            execution_strategy="sequential",
            safety_checks=[]
        )

        complexity = self.orchestrator._assess_complexity(command)
        assert complexity["score"] == 0
        assert complexity["requires_coordination"] == False

        # Complex task
        command.targets = [{"file": f"file_{i}.txt"} for i in range(10)]
        command.command_type = CommandType.CODE_GENERATION
        command.priority = Priority.COMPLEX
        command.safety_checks = ["check1", "check2", "check3"]

        complexity = self.orchestrator._assess_complexity(command)
        assert complexity["score"] > 60
        assert complexity["requires_coordination"] == True
        assert "multiple_targets" in complexity["factors"]
        assert "complex_operation" in complexity["factors"]

    def test_multi_agent_decision(self):
        """Test multi-agent orchestration decision"""
        # Should use multi-agent for complex tasks
        command = InterpretedCommand(
            command_type=CommandType.CODE_GENERATION,
            action="generate",
            targets=[{"component": f"comp_{i}"} for i in range(5)],
            context={},
            confidence=80.0,
            confidence_level=ConfidenceLevel.HIGH,
            priority=Priority.COMPLEX,
            raw_input="generate components",
            suggested_agent="master_prime",
            execution_strategy="parallel",
            safety_checks=[]
        )

        complexity = {"score": 70, "requires_coordination": True}
        should_multi = self.orchestrator._should_use_multi_agent(command, complexity)
        assert should_multi == True

        # Should not use multi-agent for simple tasks
        command.command_type = CommandType.FILE_OPERATION
        command.targets = [{"file": "test.txt"}]
        complexity = {"score": 10, "requires_coordination": False}
        should_multi = self.orchestrator._should_use_multi_agent(command, complexity)
        assert should_multi == False

    def test_agent_role_assignment(self):
        """Test agent role assignment based on task"""
        # Code generation task
        command = InterpretedCommand(
            command_type=CommandType.CODE_GENERATION,
            action="generate",
            targets=[],
            context={},
            confidence=80.0,
            confidence_level=ConfidenceLevel.HIGH,
            priority=Priority.COMPLEX,
            raw_input="create frontend and backend components",
            suggested_agent="master_prime",
            execution_strategy="parallel",
            safety_checks=[]
        )

        complexity = {"score": 80}
        agents = self.orchestrator._assign_agent_roles(command, complexity)

        assert AgentSpecialization.ARCHITECT in agents
        assert AgentSpecialization.FRONTEND_DEV in agents
        assert AgentSpecialization.BACKEND_DEV in agents
        assert AgentSpecialization.QA_TESTER in agents  # Added for high complexity

    def test_execution_model_determination(self):
        """Test execution model selection"""
        command = Mock()

        # Single agent - sequential
        agents = [AgentSpecialization.BACKEND_DEV]
        model = self.orchestrator._determine_execution_model(command, agents)
        assert model == ExecutionModel.SEQUENTIAL_PIPELINE

        # Architect present - hybrid
        agents = [AgentSpecialization.ARCHITECT, AgentSpecialization.FRONTEND_DEV]
        model = self.orchestrator._determine_execution_model(command, agents)
        assert model == ExecutionModel.HYBRID

        # QA and Review - parallel
        agents = [AgentSpecialization.QA_TESTER, AgentSpecialization.CODE_REVIEWER]
        model = self.orchestrator._determine_execution_model(command, agents)
        assert model == ExecutionModel.PARALLEL_EXECUTION

    def test_quality_gate_definition(self):
        """Test quality gate creation"""
        command = InterpretedCommand(
            command_type=CommandType.CODE_GENERATION,
            action="create",
            targets=[{"file": f"file_{i}.txt"} for i in range(5)],
            context={},
            confidence=80.0,
            confidence_level=ConfidenceLevel.HIGH,
            priority=Priority.COMPLEX,
            raw_input="create files",
            suggested_agent="worker",
            execution_strategy="parallel",
            safety_checks=[]
        )

        complexity = {"score": 70}
        gates = self.orchestrator._define_quality_gates(command, complexity)

        # Should have basic validation
        assert any(g.name == "input_validation" for g in gates)

        # Should have code quality for code generation
        assert any(g.name == "code_quality" for g in gates)

        # Should have test validation for high complexity
        assert any(g.name == "test_validation" for g in gates)

        # Should have final assembly for multiple targets
        assert any(g.name == "final_assembly" for g in gates)

    def test_tool_selection_matrix(self):
        """Test tool selection from matrix"""
        # Create single file
        tool_key = "create_single_file"
        selection = self.orchestrator.TOOL_MATRIX[tool_key]
        assert selection.primary_tool == "Write"
        assert "Bash (mkdir -p)" in selection.secondary_tools

        # Search by content
        tool_key = "search_by_content"
        selection = self.orchestrator.TOOL_MATRIX[tool_key]
        assert selection.primary_tool == "Grep"
        assert "Task" in selection.secondary_tools

        # Git operations
        tool_key = "git_operations"
        selection = self.orchestrator.TOOL_MATRIX[tool_key]
        assert selection.primary_tool == "Bash (git)"

    def test_parallelization_calculation(self):
        """Test parallelization factor calculation"""
        # Parallel execution - high factor
        agents = [AgentSpecialization.FRONTEND_DEV, AgentSpecialization.BACKEND_DEV]
        factor = self.orchestrator._calculate_parallelization(
            agents,
            ExecutionModel.PARALLEL_EXECUTION
        )
        assert factor == 0.9

        # Sequential - no parallelization
        factor = self.orchestrator._calculate_parallelization(
            agents,
            ExecutionModel.SEQUENTIAL_PIPELINE
        )
        assert factor == 0.0

        # Hybrid with multiple agents - medium
        agents = [AgentSpecialization.ARCHITECT, AgentSpecialization.FRONTEND_DEV, AgentSpecialization.BACKEND_DEV]
        factor = self.orchestrator._calculate_parallelization(
            agents,
            ExecutionModel.HYBRID
        )
        assert factor == 0.5

    @pytest.mark.asyncio
    async def test_orchestration_plan_creation(self):
        """Test complete orchestration plan creation"""
        command = InterpretedCommand(
            command_type=CommandType.CODE_GENERATION,
            action="generate",
            targets=[{"component": "UserAuth"}],
            context={},
            confidence=80.0,
            confidence_level=ConfidenceLevel.HIGH,
            priority=Priority.COMPLEX,
            raw_input="create user authentication system",
            suggested_agent="master_prime",
            execution_strategy="parallel",
            safety_checks=["security_review"]
        )

        plan = await self.orchestrator.orchestrate(command)

        assert isinstance(plan, OrchestrationPlan)
        assert len(plan.agents) > 0
        assert plan.execution_model in ExecutionModel
        assert len(plan.tool_matrix) > 0
        assert len(plan.quality_gates) > 0
        assert plan.estimated_duration_ms > 0
        assert 0 <= plan.parallelization_factor <= 1

    @pytest.mark.asyncio
    async def test_quality_gate_execution(self):
        """Test quality gate execution during plan"""
        plan = OrchestrationPlan(
            task_id="test_task",
            agents=[AgentSpecialization.BACKEND_DEV],
            execution_model=ExecutionModel.SEQUENTIAL_PIPELINE,
            tool_matrix={},
            quality_gates=[
                QualityGate(
                    name="input_validation",
                    criteria=["valid_inputs"],
                    must_pass=True,
                    rollback_on_fail=False
                )
            ],
            estimated_duration_ms=1000,
            parallelization_factor=0.0
        )

        # Mock execution function
        async def mock_exec(agent, tools):
            return {"status": "success", "output": "test"}

        # Execute with gates
        with patch.object(self.orchestrator, '_validate_inputs', return_value=True):
            results = await self.orchestrator.execute_with_quality_gates(plan, mock_exec)

        assert results["status"] == "completed"
        assert len(results["outputs"]) == 1
        # execution_time_ms may be 0 for fast mock execution
        assert results["execution_time_ms"] >= 0


def run_tests():
    """Run all integration tests"""
    pytest.main([__file__, "-v", "-s", "--tb=short"])


if __name__ == "__main__":
    run_tests()