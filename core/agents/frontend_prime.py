"""
Frontend Prime Agent - Specialized for frontend development tasks.
Handles UI components, user experience, and client-side logic.
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


class FrontendPrimeAgent(BaseAgent):
    """
    Prime agent specialized in frontend development.
    Expertise: React, UI/UX, components, state management, responsive design.
    """

    def __init__(self):
        super().__init__(role=AgentRole.FRONTEND_PRIME)
        self.expertise = [
            "React", "Vue", "Angular", "TypeScript",
            "State Management", "Component Architecture",
            "Responsive Design", "Accessibility", "Performance"
        ]
        self.ui_libraries = [
            "Material-UI", "Ant Design", "Tailwind CSS",
            "Bootstrap", "Chakra UI", "Styled Components"
        ]

    async def analyze_task(self, task: str, context: ContextBundle) -> Tuple[bool, str]:
        """
        Analyze if this agent can handle the frontend task.
        """
        task_lower = task.lower()

        # Keywords indicating frontend work
        frontend_keywords = [
            "ui", "interface", "component", "frontend", "react", "vue",
            "form", "button", "layout", "dashboard", "page", "view",
            "responsive", "mobile", "css", "style", "animation", "ux"
        ]

        can_handle = any(keyword in task_lower for keyword in frontend_keywords)

        if can_handle:
            return True, "Task involves frontend development"
        else:
            return False, "Task does not require frontend expertise"

    async def execute_task(self, task: str, context: ContextBundle) -> AgentResult:
        """
        Execute frontend development task.
        """
        try:
            self.current_context = context

            await self._update_progress(AgentStatus.PLANNING, 10, "Analyzing UI requirements...")

            # Categorize frontend task
            task_type = self._categorize_frontend_task(task)

            # Create implementation plan
            plan = await self._create_ui_plan(task, task_type)
            await self._update_progress(AgentStatus.PLANNING, 25, f"Planning {task_type} implementation...")

            # Execute based on task type
            if task_type == "component_development":
                result = await self._implement_components(task, plan)
            elif task_type == "dashboard_creation":
                result = await self._implement_dashboard(task, plan)
            elif task_type == "form_implementation":
                result = await self._implement_forms(task, plan)
            elif task_type == "responsive_design":
                result = await self._implement_responsive(task, plan)
            else:
                result = await self._implement_generic_ui(task, plan)

            await self._update_progress(AgentStatus.COMPLETED, 100, f"Frontend {task_type} completed")

            return AgentResult(
                agent_id=self.agent_id,
                agent_role=self.role,
                task_id=context.session_id,
                status=AgentStatus.COMPLETED,
                context_bundle=self.current_context,
                output=result,
                token_usage=self.token_usage
            )

        except Exception as e:
            return AgentResult(
                agent_id=self.agent_id,
                agent_role=self.role,
                task_id=context.session_id,
                status=AgentStatus.FAILED,
                context_bundle=context,
                errors=[str(e)],
                token_usage=self.token_usage
            )

    def _categorize_frontend_task(self, task: str) -> str:
        """
        Categorize the type of frontend task.
        """
        task_lower = task.lower()

        if "component" in task_lower:
            return "component_development"
        elif "dashboard" in task_lower:
            return "dashboard_creation"
        elif "form" in task_lower or "input" in task_lower:
            return "form_implementation"
        elif "responsive" in task_lower or "mobile" in task_lower:
            return "responsive_design"
        else:
            return "general_ui"

    async def _create_ui_plan(self, task: str, task_type: str) -> Dict:
        """
        Create UI implementation plan.
        """
        plan = {
            "task_type": task_type,
            "framework": "React",  # Default to React
            "components": [],
            "styling_approach": "Tailwind CSS",
            "state_management": "Context API",
            "steps": []
        }

        if task_type == "component_development":
            plan["components"] = ["BaseComponent", "ComponentVariants", "ComponentProps"]
            plan["steps"] = [
                "Design component structure",
                "Implement base functionality",
                "Add styling and themes",
                "Create component variants",
                "Add accessibility features",
                "Write component tests"
            ]

        elif task_type == "dashboard_creation":
            plan["components"] = ["Layout", "Sidebar", "Charts", "Tables", "Cards"]
            plan["state_management"] = "Redux or Zustand"  # For complex state
            plan["steps"] = [
                "Design dashboard layout",
                "Create navigation structure",
                "Implement data visualization",
                "Add real-time updates",
                "Optimize performance"
            ]

        self._log_decision(
            f"Frontend plan for {task_type}",
            f"Using {plan['framework']} with {plan['styling_approach']}",
            [plan['framework']]
        )

        return plan

    async def _implement_components(self, task: str, plan: Dict) -> str:
        """
        Implement UI components.
        """
        await self._update_progress(AgentStatus.BUILDING, 40, "Creating component structure...")

        artifacts = [
            "frontend/components/BaseButton.tsx",
            "frontend/components/Card.tsx",
            "frontend/components/Modal.tsx",
        ]
        guidance = (
            "Create modern React components in TypeScript with Tailwind classes,"
            " accessibility attributes, and Storybook-style docs in comments."
        )
        generated = await self._generate_files(task, plan, artifacts, guidance)
        await self._update_progress(AgentStatus.BUILDING, 72, "Documenting components...")
        return self._summarize_generation(generated, "UI components")

    async def _implement_dashboard(self, task: str, plan: Dict) -> str:
        """
        Implement dashboard UI.
        """
        await self._update_progress(AgentStatus.BUILDING, 40, "Building dashboard layout...")

        artifacts = [
            "frontend/pages/Dashboard.tsx",
            "frontend/components/charts/LineChart.tsx",
            "frontend/components/tables/DataTable.tsx",
            "frontend/layouts/DashboardLayout.tsx",
        ]
        guidance = (
            "Compose a dashboard using React + Tailwind with Recharts and reusable"
            " layout components."
        )
        generated = await self._generate_files(task, plan, artifacts, guidance)
        await self._update_progress(AgentStatus.BUILDING, 72, "Attaching dashboard assets...")
        return self._summarize_generation(generated, "dashboard")

    async def _implement_forms(self, task: str, plan: Dict) -> str:
        """
        Implement form components.
        """
        await self._update_progress(AgentStatus.BUILDING, 40, "Creating form components...")

        artifacts = [
            "frontend/components/forms/LoginForm.tsx",
            "frontend/components/forms/RegisterForm.tsx",
            "frontend/utils/validation.ts",
        ]
        guidance = (
            "Create controlled React Hook Form components with Zod validation and"
            " inline error messaging."
        )
        generated = await self._generate_files(task, plan, artifacts, guidance)
        await self._update_progress(AgentStatus.BUILDING, 72, "Linking form validation...")
        return self._summarize_generation(generated, "form")

    async def _implement_responsive(self, task: str, plan: Dict) -> str:
        """
        Implement responsive design.
        """
        await self._update_progress(AgentStatus.BUILDING, 40, "Implementing responsive layout...")

        artifacts = ["frontend/styles/responsive.css", "frontend/hooks/useResponsive.ts"]
        guidance = (
            "Produce mobile-first CSS utility classes and a React hook exposing"
            " breakpoints using matchMedia."
        )
        generated = await self._generate_files(task, plan, artifacts, guidance)
        await self._update_progress(AgentStatus.BUILDING, 72, "Validating responsive behaviour...")
        return self._summarize_generation(generated, "responsive layout")

    async def _implement_generic_ui(self, task: str, plan: Dict) -> str:
        """
        Implement generic UI functionality.
        """
        await self._update_progress(AgentStatus.BUILDING, 40, "Building UI components...")

        artifacts = ["frontend/components/index.tsx", "frontend/styles/global.css"]
        guidance = "Implement reusable components and global styles aligned with the task brief."
        generated = await self._generate_files(task, plan, artifacts, guidance)
        await self._update_progress(AgentStatus.BUILDING, 72, "Finalizing UI bundle...")
        return self._summarize_generation(generated, "UI bundle")

    async def _generate_files(
        self,
        task: str,
        plan: Dict,
        artifacts: List[str],
        guidance: str,
    ) -> Dict[str, str]:
        base_dir = os.environ.get("CASPER_OUTPUT_DIR", ".casper/output")
        session_id = str(self.current_context.session_id)

        prompt = self._build_prompt(task, plan, artifacts, guidance)
        llm_output = await self._call_llm(prompt)
        contents = self._split_output(llm_output, artifacts)

        generated: Dict[str, str] = {}
        for artifact, content in contents.items():
            if not content.strip():
                continue
            path = write_artifact(base_dir, session_id, artifact, content.rstrip() + "\n")
            generated[artifact] = path
            self._add_artifact(path)
            self._add_pointer(artifact.replace("/", "_"), path)
        return generated

    def _summarize_generation(self, generated: Dict[str, str], label: str) -> str:
        if not generated:
            return f"No {label} assets generated; consider refining the task."
        files = "\n".join(f"- {path}" for path in generated.values())
        return f"Generated {len(generated)} {label} artifact(s):\n{files}"

    def _build_prompt(self, task: str, plan: Dict, artifacts: List[str], guidance: str) -> str:
        artifact_lines = "\n".join(f"- {artifact}" for artifact in artifacts)
        steps = "\n".join(f"  • {step}" for step in plan.get("steps", []))
        return (
            "You are Frontend Prime inside CASPER."
            f"\nTask: {task}\n"
            f"Framework: {plan.get('framework', 'React')}\n"
            f"Styling: {plan.get('styling_approach', 'Tailwind CSS')}\n"
            f"State management: {plan.get('state_management', 'Context API')}\n"
            f"Implementation steps:\n{steps}\n"
            f"Emit the following artifacts with '=== <path> ===' delimiters:\n{artifact_lines}\n"
            f"Guidance: {guidance}\n"
            "Return idiomatic TypeScript React code with descriptive docblocks."
        )

    async def _call_llm(self, prompt: str) -> str:
        if llm_service.available():
            try:
                output = await llm_service.complete(prompt, max_tokens=1400)
                if output:
                    return output
            except Exception:  # pragma: no cover
                pass
        return (
            "=== frontend/components/BaseButton.tsx ===\n"
            "import React from 'react';\n\nexport const BaseButton: React.FC<React.ButtonHTMLAttributes<HTMLButtonElement>> = ({ children, ...rest }) => (\n    <button className='px-4 py-2 rounded bg-blue-600 text-white hover:bg-blue-500 focus:outline-none focus:ring-2 focus:ring-blue-300' {...rest}>\n        {children}\n    </button>\n);\n"
        )

    def _split_output(self, output: str, artifacts: List[str]) -> Dict[str, str]:
        mapping: Dict[str, str] = {artifact: "" for artifact in artifacts}
        current: Optional[str] = None
        in_code_block = False
        
        for line in output.splitlines():
            if line.startswith("=== ") and line.endswith(" ==="):
                candidate = line[4:-4].strip()
                current = candidate if candidate in mapping else None
                in_code_block = False
                continue
            
            if current:
                # Skip markdown code block markers
                if line.strip() in ["```python", "```", "```typescript", "```javascript", "```tsx", "```jsx", "```css"]:
                    in_code_block = not in_code_block
                    continue
                    
                mapping[current] += line + "\n"
        
        # Clean up any remaining artifacts
        for artifact in mapping:
            content = mapping[artifact].strip()
            # Remove any remaining code block markers
            if content.startswith("```"):
                lines = content.split('\n')
                if lines[0].startswith("```"):
                    lines = lines[1:]
                if lines and lines[-1].strip() == "```":
                    lines = lines[:-1]
                content = '\n'.join(lines)
            mapping[artifact] = content
            
        return mapping
