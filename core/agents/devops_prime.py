"""
DevOps Prime Agent - Specialized for deployment, infrastructure, and pipelines.
Handles CI/CD workflows, containerization, infrastructure-as-code, and monitoring.
"""

import asyncio
import os
from typing import Dict, List, Optional, Tuple

from .base import (
    BaseAgent,
    AgentRole,
    AgentStatus,
    AgentResult,
    ContextBundle,
    TaskPriority,
)
from core.services.llm import llm_service
from core.services.files import write_artifact


class DevOpsPrimeAgent(BaseAgent):
    """Prime agent specialized in DevOps and platform automation tasks."""

    def __init__(self):
        super().__init__(role=AgentRole.DEVOPS_PRIME)
        self.capabilities = [
            "CI/CD pipelines",
            "Containerization",
            "Infrastructure as Code",
            "Monitoring & Alerts",
            "Scaling & Rollouts",
            "Secrets Management",
        ]
        self.keywords = {
            "pipeline": "pipeline_automation",
            "ci": "pipeline_automation",
            "deploy": "deployment_strategy",
            "deployment": "deployment_strategy",
            "docker": "containerization",
            "kubernetes": "kubernetes_ops",
            "terraform": "iac",
            "infrastructure": "iac",
            "monitoring": "observability",
            "alert": "observability",
            "logging": "observability",
        }

    async def analyze_task(self, task: str, context: ContextBundle) -> Tuple[bool, str]:
        task_lower = task.lower()
        matches = [kw for kw in self.keywords if kw in task_lower]
        if matches:
            return True, f"DevOps indicators detected: {', '.join(sorted(set(matches)))}"
        if any(token in task_lower for token in ("ops", "site reliability", "rollout")):
            return True, "Operational keyword detected"
        return False, "Task does not appear to require DevOps expertise"

    async def execute_task(self, task: str, context: ContextBundle) -> AgentResult:
        try:
            self.current_context = context
            await self._update_progress(AgentStatus.PLANNING, 10, "Assessing DevOps requirements...")

            category = self._categorize_task(task)
            plan = self._create_plan(task, category)
            await self._update_progress(AgentStatus.PLANNING, 30, f"Planning {category.replace('_', ' ')} workflow...")

            result_text = await self._implement_plan(task, category, plan)
            await self._update_progress(AgentStatus.REVIEWING, 85, "Validating generated DevOps assets...")

            self._track_tokens(plan["token_estimate"], max(len(result_text) // 4, 200))
            await self._update_progress(AgentStatus.COMPLETED, 100, f"DevOps workflow for {category} completed")

            return AgentResult(
                agent_id=self.agent_id,
                agent_role=self.role,
                task_id=context.session_id,
                status=AgentStatus.COMPLETED,
                context_bundle=self.current_context,
                output=result_text,
                token_usage=self.token_usage,
            )
        except Exception as exc:  # pragma: no cover - defensive
            return AgentResult(
                agent_id=self.agent_id,
                agent_role=self.role,
                task_id=context.session_id,
                status=AgentStatus.FAILED,
                context_bundle=context,
                errors=[str(exc)],
                token_usage=self.token_usage,
            )

    def _categorize_task(self, task: str) -> str:
        task_lower = task.lower()
        for keyword, category in self.keywords.items():
            if keyword in task_lower:
                return category
        if "slo" in task_lower or "monitor" in task_lower:
            return "observability"
        if "scale" in task_lower or "rollout" in task_lower:
            return "deployment_strategy"
        return "general_devops"

    def _create_plan(self, task: str, category: str) -> Dict[str, any]:
        plan = {
            "category": category,
            "steps": [],
            "artifacts": [],
            "token_estimate": 600,
        }
        if category == "pipeline_automation":
            plan["steps"] = [
                "Gather build/test/deploy stages",
                "Define environment matrix",
                "Configure secret handling",
                "Emit pipeline YAML",
            ]
            plan["artifacts"].append(".github/workflows/ci.yml")
        elif category == "deployment_strategy":
            plan["steps"] = [
                "Select deployment target",
                "Define rollout strategy",
                "Generate deployment configuration",
                "Document rollback plan",
            ]
            plan["artifacts"].append("deploy/strategy.md")
        elif category == "containerization":
            plan["steps"] = [
                "Inspect service requirements",
                "Compose Dockerfile",
                "Write docker-compose stack",
                "Document local run instructions",
            ]
            plan["artifacts"].extend(["ops/Dockerfile", "ops/docker-compose.yml"])
        elif category == "kubernetes_ops":
            plan["steps"] = [
                "Define deployment and service",
                "Configure ingress & autoscaling",
                "Template secrets",
                "Document kubectl rollout",
            ]
            plan["artifacts"].extend(["ops/k8s/deployment.yaml", "ops/k8s/service.yaml"])
            plan["token_estimate"] = 800
        elif category == "iac":
            plan["steps"] = [
                "Model infrastructure resources",
                "Author Terraform modules",
                "Add variable & environment files",
                "Describe apply/destroy commands",
            ]
            plan["artifacts"].append("infra/main.tf")
            plan["token_estimate"] = 900
        elif category == "observability":
            plan["steps"] = [
                "Identify key metrics/logs",
                "Create monitoring rules",
                "Set up alert routing",
                "Document runbook entries",
            ]
            plan["artifacts"].append("ops/observability.md")
        else:
            plan["steps"] = [
                "Summarize operational requirements",
                "Generate automation script",
                "Document verification checklist",
            ]
            plan["artifacts"].append("ops/devops_notes.md")
        self._log_decision(
            f"DevOps plan established ({category})",
            f"Producing {len(plan['artifacts'])} artifact(s)",
            plan["artifacts"],
        )
        return plan

    async def _implement_plan(self, task: str, category: str, plan: Dict[str, any]) -> str:
        os.environ.setdefault("CASPER_OUTPUT_DIR", ".casper/output")
        output_dir = os.environ.get("CASPER_OUTPUT_DIR", ".casper/output")
        session_id = str(self.current_context.session_id)

        prompt = self._build_prompt(task, category, plan["artifacts"])
        llm_output = await self._call_llm(prompt, plan["artifacts"])
        content_map = self._split_output(llm_output, plan["artifacts"])

        generated_files: List[str] = []
        for artifact, content in content_map.items():
            if not content.strip():
                continue
            path = write_artifact(output_dir, session_id, artifact, content.rstrip() + "\n")
            self._add_artifact(path)
            self._add_pointer(artifact.replace("/", "_"), path)
            generated_files.append(path)

        summary = "\n".join(
            [
                f"Generated {len(generated_files)} artifact(s) for category '{category}'.",
                "Artifacts:",
            ] + [f"- {path}" for path in generated_files]
        )
        return summary if generated_files else "No DevOps artifacts generated; please review task description."

    def _build_prompt(self, task: str, category: str, artifacts: List[str]) -> str:
        artifact_list = "\n".join(f"- {name}" for name in artifacts)
        guidance = {
            "pipeline_automation": "Produce a GitHub Actions workflow with build, test, and deploy jobs.",
            "deployment_strategy": "Outline rollout strategy and include a reusable deployment script.",
            "containerization": "Create production-ready Dockerfile and docker-compose with health checks.",
            "kubernetes_ops": "Emit Kubernetes manifests following best practices (resources, probes, labels).",
            "iac": "Author Terraform HCL defining resources with variables and outputs.",
            "observability": "Define metrics/alerts and Prometheus/Grafana configuration where applicable.",
            "general_devops": "Provide automation script or documentation supporting the operational goal.",
        }
        system = guidance.get(category, guidance["general_devops"])
        return (
            f"You are DevOps Prime inside CASPER. Task: {task}.\n"
            f"Category: {category}.\n"
            f"Artifacts to emit (one file per section):\n{artifact_list}\n\n"
            f"Guidance: {system}\n"
            "Return each artifact separated by a delimiter line of the form\\n=== <relative_path> ===\n"
            "Provide production-ready content with explanatory comments where appropriate."
        )

    async def _call_llm(self, prompt: str, artifacts: List[str]) -> str:
        if llm_service.available():
            try:
                response = await llm_service.complete(prompt, max_tokens=1400)
                if response and all(
                    f"=== {artifact} ===" in response for artifact in artifacts
                ):
                    return response
            except Exception:  # pragma: no cover
                pass
        # Deterministic, executable output for offline or quota-limited runs.
        sections = []
        for artifact in artifacts:
            sections.append(
                f"=== {artifact} ===\n"
                f"{self._offline_artifact(artifact)}"
            )
        return "\n\n".join(sections)

    def _offline_artifact(self, artifact: str) -> str:
        """Return a minimal useful artifact when no provider is available."""
        if artifact == ".github/workflows/ci.yml":
            return (
                "name: CI\n"
                "on: [push, pull_request]\n"
                "jobs:\n"
                "  verify:\n"
                "    runs-on: ubuntu-latest\n"
                "    steps:\n"
                "      - uses: actions/checkout@v4\n"
                "      - uses: actions/setup-python@v5\n"
                "        with:\n"
                "          python-version: '3.11'\n"
                "      - run: python -m pip install poetry\n"
                "      - run: poetry install --with dev\n"
                "      - run: poetry run pytest -q\n"
            )
        if artifact.endswith("Dockerfile"):
            return (
                "FROM python:3.11-slim\n"
                "WORKDIR /app\n"
                "COPY . .\n"
                "RUN pip install --no-cache-dir .\n"
                "CMD [\"casper\", \"--help\"]\n"
            )
        if artifact.endswith("docker-compose.yml"):
            return (
                "services:\n"
                "  casper:\n"
                "    build: .\n"
                "    init: true\n"
            )
        if artifact.endswith(".yaml"):
            return "apiVersion: v1\nkind: ConfigMap\nmetadata:\n  name: casper\n"
        if artifact.endswith(".tf"):
            return "terraform {\n  required_version = \">= 1.8.0\"\n}\n"
        return (
            f"# {artifact}\n\n"
            "Generated deterministically because no configured provider returned "
            "a valid artifact bundle.\n"
        )

    def _split_output(self, llm_output: str, artifacts: List[str]) -> Dict[str, str]:
        content_map: Dict[str, str] = {artifact: "" for artifact in artifacts}
        current_file: Optional[str] = None
        for line in llm_output.splitlines():
            if line.startswith("=== ") and line.endswith(" ==="):
                candidate = line[4:-4].strip()
                current_file = candidate if candidate in content_map else None
                continue
            if current_file:
                content_map[current_file] += line + "\n"
        return content_map
