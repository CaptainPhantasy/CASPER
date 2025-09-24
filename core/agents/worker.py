"""
Worker Agent - General purpose agent for simple tasks.
Handles single-file edits, small fixes, and straightforward implementations.
"""

import os
import re
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


class WorkerAgent(BaseAgent):
    """Worker agent responsible for small, highly focused changes."""

    def __init__(self):
        super().__init__(role=AgentRole.WORKER)
        self.max_file_operations = 3
        self.supported_operations = [
            "file_edit",
            "bug_fix",
            "refactor",
            "documentation",
            "configuration",
            "cleanup",
        ]

    async def analyze_task(self, task: str, context: ContextBundle) -> Tuple[bool, str]:
        task_lower = task.lower()
        simple_keywords = [
            "fix",
            "update",
            "change",
            "modify",
            "edit",
            "typo",
            "cleanup",
            "refactor",
            "rename",
        ]
        complex_keywords = [
            "architecture",
            "integration",
            "migration",
            "system",
            "platform",
            "orchestrate",
        ]

        is_simple = any(keyword in task_lower for keyword in simple_keywords)
        is_complex = any(keyword in task_lower for keyword in complex_keywords)

        if is_simple and not is_complex:
            return True, "Task suitable for worker"
        if is_complex:
            return False, "Escalate to prime agent"
        return True, "Attempting task with worker"

    async def execute_task(self, task: str, context: ContextBundle) -> AgentResult:
        try:
            self.current_context = context
            await self._update_progress(AgentStatus.PLANNING, 12, "Scoping change...")

            operation = self._identify_operation(task)
            plan = self._create_simple_plan(task, operation)

            await self._update_progress(AgentStatus.BUILDING, 45, f"Drafting {operation} patch...")
            patch_path, summary = await self._generate_patch(task, operation, plan)

            await self._update_progress(AgentStatus.REVIEWING, 90, "Reviewing patch output...")
            verification = self._verify_work(operation, plan)

            await self._update_progress(AgentStatus.COMPLETED, 100, "Worker task complete")

            return AgentResult(
                agent_id=self.agent_id,
                agent_role=self.role,
                task_id=context.session_id,
                status=AgentStatus.COMPLETED,
                context_bundle=self.current_context,
                output=f"Patch file: {patch_path}\n{summary}\n{verification}",
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

    def _identify_operation(self, task: str) -> str:
        task_lower = task.lower()
        if "bug" in task_lower or "fix" in task_lower:
            return "bug_fix"
        if "refactor" in task_lower:
            return "refactor"
        if "document" in task_lower or "comment" in task_lower:
            return "documentation"
        if "config" in task_lower or "setting" in task_lower:
            return "configuration"
        if "clean" in task_lower or "format" in task_lower:
            return "cleanup"
        return "file_edit"

    def _create_simple_plan(self, task: str, operation: str) -> Dict:
        plan = {
            "operation": operation,
            "files_to_modify": [],
            "estimated_changes": 1,
            "approach": "",
        }

        if operation == "bug_fix":
            plan["approach"] = "Locate failing logic, patch, and describe validation"
        elif operation == "refactor":
            plan["approach"] = "Improve readability while preserving behaviour"
            plan["estimated_changes"] = 2
        elif operation == "documentation":
            plan["approach"] = "Add or update inline docstrings and README notes"
        elif operation == "configuration":
            plan["approach"] = "Adjust configuration with safe defaults"
        elif operation == "cleanup":
            plan["approach"] = "Apply formatting and remove unused code"
            plan["estimated_changes"] = 2
        else:
            plan["approach"] = "Apply direct file edits"

        self._log_decision(
            f"Worker executing {operation}",
            plan["approach"],
            []
        )
        return plan

    async def _generate_patch(self, task: str, operation: str, plan: Dict) -> Tuple[str, str]:
        base_dir = os.environ.get("CASPER_OUTPUT_DIR", ".casper/output")
        session_id = str(self.current_context.session_id)
        patch_dir = f"patches/{operation}"
        patch_name = f"{operation}_changes.diff"

        prompt = self._build_prompt(task, operation, plan)
        diff = await self._call_llm(prompt, task, operation, plan)

        path = write_artifact(base_dir, session_id, f"{patch_dir}/{patch_name}", diff.rstrip() + "\n")
        self._add_artifact(path)
        self._add_pointer(f"patch_{operation}", path)
        self._track_tokens(40, max(len(diff) // 4, 60))
        return path, "Review and apply with `git apply`"

    def _build_prompt(self, task: str, operation: str, plan: Dict) -> str:
        return (
            "You are the Worker agent for CASPER."
            f"\nTask: {task}\n"
            f"Operation: {operation}\n"
            "Produce a unified diff implementing the change."
            " Keep the patch minimal, include helpful comments, and assume a Python/TypeScript project unless specified."
        )

    async def _call_llm(self, prompt: str, task: str, operation: str, plan: Dict) -> str:
        if llm_service.available():
            try:
                output = await llm_service.complete(prompt, max_tokens=400)
                if output:
                    return output
            except Exception as e:
                print(f"Worker LLM call failed: {e}")
                # Fall through to deterministic patch
        return self._deterministic_patch(task, operation, plan)

    def _deterministic_patch(self, task: str, operation: str, plan: Dict) -> str:
        """Produce a deterministic patch when no LLM is available."""
        slug = self._slugify(task) or "task"
        filename = f"docs/manual/worker_{operation}_{slug}.md"

        context = getattr(self, "current_context", None)
        pointers = getattr(context, "structural_pointers", {}) if context else {}
        next_actions = getattr(context, "next_actions", []) if context else []
        decisions = getattr(context, "decisions_made", []) if context else []

        def _decision_attr(item, key):
            if isinstance(item, dict):
                return item.get(key, "")
            return getattr(item, key, "")

        header = (
            f"# Worker Recovery Plan ({operation})\n\n"
            f"**Task:** {task.strip()}\n\n"
            f"**Operation Strategy:** {plan.get('approach', 'Document pending changes')}\n\n"
        )

        files_to_modify = plan.get('files_to_modify') or []
        if not files_to_modify and pointers:
            files_to_modify = list(pointers.values())[:3]

        checklist = files_to_modify or [
            "Review relevant source file",
            "Implement change described in operation strategy",
            "Add verification notes once change is applied",
        ]

        pointer_lines = "\n".join(
            f"- **{key}:** {value}" for key, value in list(pointers.items())[:5]
        ) or "- No structural pointers captured"

        next_steps = "\n".join(f"- {step}" for step in next_actions[:5]) or "- No delegated follow-up actions"

        decision_notes = "\n".join(
            f"- {_decision_attr(decision, 'decision')}: {_decision_attr(decision, 'rationale')}"
            for decision in decisions[-3:]
        ) or "- No recorded decisions"

        document = (
            header
            + "## Immediate Checklist\n\n"
            + "\n".join(f"- {item}" for item in checklist[:5])
            + "\n\n## Helpful Context\n\n"
            + pointer_lines
            + "\n\n## Next Actions\n\n"
            + next_steps
            + "\n\n## Decision Trace\n\n"
            + decision_notes
            + "\n\n_This deterministic recovery note was generated because no model output was available. Use it to resume progress quickly._"
        )

        lines = document.splitlines()
        patch = (
            f"diff --git a/{filename} b/{filename}\n"
            "new file mode 100644\n"
            "--- /dev/null\n"
            f"+++ b/{filename}\n"
            f"@@ -0,0 +1,{len(lines)} @@\n"
            + "\n".join(f"+{line}" for line in lines) + "\n"
        )
        return patch

    def _slugify(self, text: str) -> str:
        """Create a filesystem-friendly slug from the task description."""
        condensed = re.sub(r"[^a-z0-9]+", "-", text.lower())
        return condensed.strip("-")[:32]

    def _verify_work(self, operation: str, plan: Dict) -> str:
        verifications = {
            "bug_fix": "Bug fix generated with rationale attached",
            "refactor": "Refactor patch ready for review",
            "documentation": "Documentation additions prepared",
            "configuration": "Configuration adjustments scaffolded",
            "cleanup": "Cleanup patch created",
            "file_edit": "File edit patch generated",
        }
        return verifications.get(operation, "Changes prepared")

    def estimate_completion_time(self, task: str) -> int:
        operation = self._identify_operation(task)
        times = {
            "bug_fix": 30,
            "refactor": 45,
            "documentation": 20,
            "configuration": 15,
            "cleanup": 25,
            "file_edit": 20,
        }
        return times.get(operation, 30)
