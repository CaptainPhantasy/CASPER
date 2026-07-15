"""
Context Delegator - R&D Framework DELEGATE strategy.
Manages efficient handoffs between agents.
"""

import json
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple
from uuid import UUID


class ContextDelegator:
    """
    Implements DELEGATE strategy for efficient agent handoffs.
    Ensures smooth context transfer with minimal overhead.
    """

    @classmethod
    def prepare_handoff_bundle(
        cls,
        task: str,
        from_agent: str,
        to_agent: str,
        work_completed: Dict,
        next_steps: List[str],
        dependencies: List[str] = None,
    ) -> Dict:
        """
        Prepare optimized context bundle for handoff.
        """
        bundle = {
            "handoff_metadata": {
                "from_agent": from_agent,
                "to_agent": to_agent,
                "timestamp": datetime.now().isoformat(),
                "task": task[:200],  # Truncate long tasks
            },
            "what_i_did": cls._summarize_work(work_completed),
            "what_you_need": cls._prepare_requirements(next_steps, dependencies),
            "where_to_find_more": cls._create_reference_map(work_completed),
        }

        return bundle

    @classmethod
    def _summarize_work(cls, work_completed: Dict) -> Dict:
        """
        Summarize completed work concisely.
        """
        summary = {
            "main_accomplishment": work_completed.get("output", "")[:300],
            "files_modified": [],
            "apis_created": [],
            "tests_written": [],
            "decisions_made": [],
        }

        # Extract key accomplishments by category
        if "artifacts_created" in work_completed:
            for artifact in work_completed["artifacts_created"]:
                if any(ext in artifact for ext in [".py", ".js", ".ts"]):
                    summary["files_modified"].append(artifact)
                elif "api" in artifact.lower() or "endpoint" in artifact.lower():
                    summary["apis_created"].append(artifact)
                elif "test" in artifact.lower():
                    summary["tests_written"].append(artifact)

        # Limit lists to most important items
        summary["files_modified"] = summary["files_modified"][:5]
        summary["apis_created"] = summary["apis_created"][:3]
        summary["tests_written"] = summary["tests_written"][:3]

        # Include key decisions
        if "decisions_made" in work_completed:
            for decision in work_completed["decisions_made"][-3:]:  # Last 3 decisions
                summary["decisions_made"].append(
                    {
                        "decision": decision.get("decision", "")[:100],
                        "impact": decision.get("rationale", "")[:50],
                    }
                )

        return summary

    @classmethod
    def _prepare_requirements(
        cls, next_steps: List[str], dependencies: List[str] = None
    ) -> Dict:
        """
        Prepare clear requirements for next agent.
        """
        requirements = {
            "immediate_tasks": next_steps[:5],  # Top 5 priority tasks
            "dependencies": dependencies[:5] if dependencies else [],
            "prerequisites_met": [],
            "blockers": [],
        }

        # Analyze tasks for prerequisites
        for task in next_steps:
            task_lower = task.lower()
            if "test" in task_lower:
                requirements["prerequisites_met"].append("Code implementation complete")
            elif "deploy" in task_lower:
                requirements["prerequisites_met"].append("Tests passing")
            elif "document" in task_lower:
                requirements["prerequisites_met"].append("Features implemented")

        return requirements

    @classmethod
    def _create_reference_map(cls, work_completed: Dict) -> Dict:
        """
        Create map of where to find additional information.
        """
        reference_map = {
            "detailed_context": {},
            "code_locations": {},
            "documentation": {},
            "external_resources": [],
        }

        # Map artifacts to categories
        if "artifacts_created" in work_completed:
            for artifact in work_completed["artifacts_created"]:
                # Categorize by file type
                if artifact.endswith(".md"):
                    reference_map["documentation"][artifact] = "Documentation"
                elif any(artifact.endswith(ext) for ext in [".py", ".js", ".ts"]):
                    # Extract module/component name
                    name = artifact.split("/")[-1].split(".")[0]
                    reference_map["code_locations"][name] = artifact

        # Add structural pointers if available
        if "structural_pointers" in work_completed:
            for key, location in list(work_completed["structural_pointers"].items())[
                :5
            ]:
                reference_map["detailed_context"][key] = location

        return reference_map

    @classmethod
    def validate_handoff(cls, bundle: Dict) -> Tuple[bool, List[str]]:
        """
        Validate that handoff bundle contains required information.
        """
        errors = []
        required_fields = ["handoff_metadata", "what_i_did", "what_you_need"]

        # Check required fields
        for field in required_fields:
            if field not in bundle:
                errors.append(f"Missing required field: {field}")

        # Check metadata completeness
        if "handoff_metadata" in bundle:
            metadata = bundle["handoff_metadata"]
            for key in ["from_agent", "to_agent", "timestamp", "task"]:
                if key not in metadata:
                    errors.append(f"Missing metadata field: {key}")

        # Check for actual content
        if "what_i_did" in bundle:
            if not bundle["what_i_did"].get("main_accomplishment"):
                errors.append("No accomplishments documented")

        if "what_you_need" in bundle:
            if not bundle["what_you_need"].get("immediate_tasks"):
                errors.append("No next steps defined")

        return len(errors) == 0, errors

    @classmethod
    def create_delegation_chain(cls, tasks: List[str]) -> List[Dict]:
        """
        Create a chain of delegations for sequential tasks.
        """
        chain = []

        for i, task in enumerate(tasks):
            delegation = {
                "sequence": i + 1,
                "task": task,
                "depends_on": i if i > 0 else None,
                "estimated_handoffs": 1,
                "parallel_possible": False,
            }

            # Analyze for parallelization opportunities
            task_lower = task.lower()
            if i > 0:
                prev_task_lower = tasks[i - 1].lower()
                # Check if tasks can be parallelized
                if not any(
                    dep in task_lower for dep in ["then", "after", "using", "from"]
                ):
                    if ("frontend" in task_lower and "backend" in prev_task_lower) or (
                        "backend" in task_lower and "frontend" in prev_task_lower
                    ):
                        delegation["parallel_possible"] = True

            chain.append(delegation)

        return chain

    @classmethod
    def optimize_parallel_delegations(cls, delegations: List[Dict]) -> List[List[Dict]]:
        """
        Optimize delegations for parallel execution where possible.
        """
        groups = []
        current_group = []

        for delegation in delegations:
            if delegation.get("parallel_possible") and current_group:
                # Can be parallelized with current group
                current_group.append(delegation)
            else:
                # Start new group
                if current_group:
                    groups.append(current_group)
                current_group = [delegation]

        if current_group:
            groups.append(current_group)

        return groups

    @classmethod
    def create_integration_handoff(
        cls, agent_results: List[Dict], integration_agent: str
    ) -> Dict:
        """
        Create special handoff for integration of multiple agent results.
        """
        integration_bundle = {
            "handoff_metadata": {
                "from_agents": [r.get("agent_id", "") for r in agent_results],
                "to_agent": integration_agent,
                "timestamp": datetime.now().isoformat(),
                "task": "Integrate results from multiple agents",
            },
            "components_to_integrate": [],
            "integration_points": [],
            "potential_conflicts": [],
            "suggested_approach": "",
        }

        # Analyze results for integration needs
        for result in agent_results:
            component = {
                "agent": result.get("agent_role", ""),
                "artifacts": result.get("artifacts_created", [])[:3],
                "status": result.get("status", ""),
            }
            integration_bundle["components_to_integrate"].append(component)

            # Identify integration points
            if "api" in str(result).lower():
                integration_bundle["integration_points"].append("API endpoints")
            if "database" in str(result).lower():
                integration_bundle["integration_points"].append("Database schema")
            if "ui" in str(result).lower() or "component" in str(result).lower():
                integration_bundle["integration_points"].append("UI components")

        # Remove duplicates
        integration_bundle["integration_points"] = list(
            set(integration_bundle["integration_points"])
        )

        # Suggest integration approach
        if len(agent_results) > 2:
            integration_bundle["suggested_approach"] = (
                "Incremental integration with testing at each step"
            )
        else:
            integration_bundle["suggested_approach"] = (
                "Direct integration with comprehensive testing"
            )

        return integration_bundle

    @classmethod
    def calculate_handoff_efficiency(cls, bundle: Dict) -> Dict[str, float]:
        """
        Calculate efficiency metrics for a handoff.
        """
        # Estimate token usage
        bundle_str = json.dumps(bundle)
        estimated_tokens = len(bundle_str) // 4  # Rough estimate

        # Count information density
        accomplishments = 0
        next_tasks = 0
        references = 0

        if "what_i_did" in bundle:
            work = bundle["what_i_did"]
            accomplishments = (
                len(work.get("files_modified", []))
                + len(work.get("apis_created", []))
                + len(work.get("tests_written", []))
            )

        if "what_you_need" in bundle:
            needs = bundle["what_you_need"]
            next_tasks = len(needs.get("immediate_tasks", []))

        if "where_to_find_more" in bundle:
            refs = bundle["where_to_find_more"]
            references = len(refs.get("code_locations", {})) + len(
                refs.get("documentation", {})
            )

        # Calculate efficiency scores
        information_density = (accomplishments + next_tasks + references) / max(
            estimated_tokens / 100, 1
        )

        return {
            "estimated_tokens": estimated_tokens,
            "information_items": accomplishments + next_tasks + references,
            "information_density": information_density,
            "efficiency_score": min(information_density * 10, 100),  # Scale to 0-100
        }
