"""
Task Analyzer - Analyzes task complexity and requirements.
Determines optimal agent allocation and execution strategy.
"""

import re
from dataclasses import dataclass, field
from typing import Dict, List, Set, Tuple

from core.agents.base import AgentRole, TaskPriority


@dataclass
class TaskMetrics:
    """Metrics for task complexity analysis."""
    lines_of_code_estimate: int = 0
    file_count_estimate: int = 0
    component_count: int = 0
    integration_points: int = 0
    external_dependencies: int = 0
    test_coverage_required: bool = False
    documentation_required: bool = False
    deployment_required: bool = False


class TaskAnalyzer:
    """
    Analyzes tasks to determine complexity and resource requirements.
    """

    # Keywords indicating different aspects of complexity
    COMPLEXITY_KEYWORDS = {
        "simple": ["fix", "update", "change", "modify", "adjust", "tweak"],
        "moderate": ["add", "implement", "create", "build", "develop"],
        "complex": ["refactor", "redesign", "architect", "migrate", "integrate", "orchestrate"],
        "system": ["system", "platform", "application", "service", "infrastructure"]
    }

    COMPONENT_INDICATORS = {
        "frontend": ["ui", "interface", "component", "page", "view", "form", "button",
                     "react", "vue", "angular", "dashboard", "layout", "style", "css"],
        "backend": ["api", "endpoint", "database", "server", "auth", "crud",
                    "model", "schema", "migration", "queue", "worker"],
        "testing": ["test", "spec", "coverage", "assertion", "mock", "e2e"],
        "infrastructure": ["deploy", "docker", "kubernetes", "ci", "cd", "pipeline", "terraform", "helm", "prometheus"],
        "documentation": ["document", "readme", "guide", "tutorial", "comment"]
    }

    @classmethod
    def analyze_task(cls, task_description: str) -> Tuple[TaskMetrics, Set[AgentRole], TaskPriority]:
        """
        Perform comprehensive task analysis.
        Returns metrics, required agents, and suggested priority.
        """
        task_lower = task_description.lower()
        metrics = TaskMetrics()
        required_agents = set()
        priority = TaskPriority.MEDIUM

        # Analyze complexity
        complexity_score = cls._calculate_complexity_score(task_lower)

        # Estimate scope
        metrics.lines_of_code_estimate = cls._estimate_loc(task_lower, complexity_score)
        metrics.file_count_estimate = cls._estimate_file_count(task_lower)
        metrics.component_count = cls._count_components(task_lower)

        # Identify requirements
        metrics.integration_points = cls._count_integration_points(task_lower)
        metrics.external_dependencies = cls._count_external_dependencies(task_lower)
        metrics.test_coverage_required = cls._requires_testing(task_lower)
        metrics.documentation_required = cls._requires_documentation(task_lower)
        metrics.deployment_required = cls._requires_deployment(task_lower)

        # Determine required agents
        required_agents = cls._determine_required_agents(task_lower, metrics)

        # Determine priority
        priority = cls._determine_priority(task_lower, complexity_score, metrics)

        return metrics, required_agents, priority

    @classmethod
    def _calculate_complexity_score(cls, task: str) -> int:
        """
        Calculate complexity score from 1-10.
        """
        score = 5  # Base score

        # Adjust based on keywords
        for keyword in cls.COMPLEXITY_KEYWORDS["simple"]:
            if keyword in task:
                score -= 1
                break

        for keyword in cls.COMPLEXITY_KEYWORDS["complex"]:
            if keyword in task:
                score += 2
                break

        for keyword in cls.COMPLEXITY_KEYWORDS["system"]:
            if keyword in task:
                score += 1

        # Adjust based on scope indicators
        if "entire" in task or "full" in task or "complete" in task:
            score += 2
        if "multiple" in task or "various" in task or "several" in task:
            score += 1
        if "production" in task or "scalable" in task:
            score += 1

        return min(max(score, 1), 10)  # Clamp to 1-10

    @classmethod
    def _estimate_loc(cls, task: str, complexity: int) -> int:
        """
        Estimate lines of code based on task description.
        """
        base_loc = complexity * 50  # Base estimate

        # Adjust based on specific indicators
        if "api" in task:
            base_loc += 200
        if "crud" in task:
            base_loc += 300
        if "authentication" in task:
            base_loc += 400
        if "dashboard" in task:
            base_loc += 500
        if "test" in task:
            base_loc += 200

        return base_loc

    @classmethod
    def _estimate_file_count(cls, task: str) -> int:
        """
        Estimate number of files to be created/modified.
        """
        count = 1  # Minimum

        # Check for multi-file indicators
        if "component" in task:
            count += 2
        if "api" in task:
            count += 3
        if "test" in task:
            count += 2
        if "model" in task or "schema" in task:
            count += 2
        if "multiple" in task or "various" in task:
            count *= 2

        return count

    @classmethod
    def _count_components(cls, task: str) -> int:
        """
        Count distinct components mentioned in task.
        """
        components = 0
        for category, keywords in cls.COMPONENT_INDICATORS.items():
            if any(keyword in task for keyword in keywords):
                components += 1
        return components

    @classmethod
    def _count_integration_points(cls, task: str) -> int:
        """
        Count potential integration points.
        """
        integration_keywords = [
            "integrate", "connect", "api", "webhook", "callback",
            "interface", "bridge", "adapter", "middleware"
        ]
        return sum(1 for keyword in integration_keywords if keyword in task)

    @classmethod
    def _count_external_dependencies(cls, task: str) -> int:
        """
        Count external dependencies mentioned.
        """
        dependency_patterns = [
            r"\b(stripe|paypal|aws|google|firebase|twilio|sendgrid)\b",
            r"\b(redis|postgres|mysql|mongodb|elasticsearch)\b",
            r"\b(oauth|jwt|ssl|https)\b"
        ]
        count = 0
        for pattern in dependency_patterns:
            if re.search(pattern, task, re.IGNORECASE):
                count += 1
        return count

    @classmethod
    def _requires_testing(cls, task: str) -> bool:
        """
        Determine if task requires testing.
        """
        return any(keyword in task for keyword in [
            "test", "spec", "coverage", "quality", "production", "critical"
        ])

    @classmethod
    def _requires_documentation(cls, task: str) -> bool:
        """
        Determine if task requires documentation.
        """
        return any(keyword in task for keyword in [
            "document", "readme", "guide", "api", "public", "library"
        ])

    @classmethod
    def _requires_deployment(cls, task: str) -> bool:
        """
        Determine if task requires deployment setup.
        """
        return any(keyword in task for keyword in [
            "deploy", "production", "hosting", "ci", "cd", "pipeline"
        ])

    @classmethod
    def _determine_required_agents(cls, task: str, metrics: TaskMetrics) -> Set[AgentRole]:
        """
        Determine which agents are needed based on task and metrics.
        """
        required = {AgentRole.MASTER}  # Always need master for coordination

        # Check component indicators
        if any(keyword in task for keyword in cls.COMPONENT_INDICATORS["frontend"]):
            required.add(AgentRole.FRONTEND_PRIME)

        if any(keyword in task for keyword in cls.COMPONENT_INDICATORS["backend"]):
            required.add(AgentRole.BACKEND_PRIME)

        if metrics.test_coverage_required or "test" in task:
            required.add(AgentRole.TESTING_PRIME)

        if metrics.deployment_required or any(keyword in task for keyword in cls.COMPONENT_INDICATORS["infrastructure"]):
            required.add(AgentRole.DEVOPS_PRIME)

        # If multiple components but no specific agents identified
        if metrics.component_count >= 2 and len(required) == 1:
            # Add common agents for complex tasks
            required.update([AgentRole.FRONTEND_PRIME, AgentRole.BACKEND_PRIME])

        # For simple tasks with no specific requirements
        if metrics.lines_of_code_estimate < 100 and len(required) == 1:
            required.add(AgentRole.WORKER)

        return required

    @classmethod
    def _determine_priority(cls, task: str, complexity: int, metrics: TaskMetrics) -> TaskPriority:
        """
        Determine task priority based on various factors.
        """
        # High priority indicators
        if any(keyword in task for keyword in ["urgent", "critical", "asap", "immediately"]):
            return TaskPriority.HIGH

        if "production" in task or "bug" in task or "fix" in task:
            return TaskPriority.HIGH

        # Low priority indicators
        if any(keyword in task for keyword in ["later", "eventually", "nice to have"]):
            return TaskPriority.LOW

        # Based on complexity
        if complexity >= 8 or metrics.integration_points >= 3:
            return TaskPriority.HIGH
        elif complexity <= 3 and metrics.component_count <= 1:
            return TaskPriority.LOW

        return TaskPriority.MEDIUM

    @classmethod
    def estimate_completion_time(cls, metrics: TaskMetrics) -> int:
        """
        Estimate completion time in minutes.
        """
        base_time = 10  # Base time in minutes

        # Add time based on metrics
        base_time += metrics.lines_of_code_estimate // 50  # 1 min per 50 LOC
        base_time += metrics.file_count_estimate * 5  # 5 min per file
        base_time += metrics.integration_points * 15  # 15 min per integration
        base_time += metrics.external_dependencies * 20  # 20 min per external dep

        if metrics.test_coverage_required:
            base_time += 30
        if metrics.documentation_required:
            base_time += 20
        if metrics.deployment_required:
            base_time += 30

        return base_time

    @classmethod
    def suggest_execution_strategy(cls, task: str, metrics: TaskMetrics) -> str:
        """
        Suggest optimal execution strategy.
        """
        if metrics.component_count >= 3:
            return "parallel_by_component"
        elif metrics.integration_points >= 2:
            return "sequential_with_integration"
        elif metrics.test_coverage_required:
            return "development_then_testing"
        elif "urgent" in task or "critical" in task:
            return "fast_track"
        else:
            return "standard"
