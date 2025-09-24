"""
Backend Prime Agent - Specialized for backend development tasks.
Handles APIs, databases, authentication, and server-side logic.
"""

import asyncio
import json
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


class BackendPrimeAgent(BaseAgent):
    """
    Prime agent specialized in backend development.
    Expertise: APIs, databases, authentication, server architecture.
    """

    def __init__(self):
        super().__init__(role=AgentRole.BACKEND_PRIME)
        self.expertise = [
            "REST APIs", "GraphQL", "Database Design",
            "Authentication", "Authorization", "Microservices",
            "Message Queues", "Caching", "Performance Optimization"
        ]
        self.supported_frameworks = [
            "FastAPI", "Django", "Flask", "Express", "NestJS",
            "Spring Boot", "Rails", "Laravel"
        ]
        self.database_systems = [
            "PostgreSQL", "MySQL", "MongoDB", "Redis",
            "Elasticsearch", "DynamoDB", "Cassandra"
        ]

    async def analyze_task(self, task: str, context: ContextBundle) -> Tuple[bool, str]:
        """
        Analyze if this agent can handle the backend task.
        """
        task_lower = task.lower()

        # Keywords indicating backend work
        backend_keywords = [
            "api", "endpoint", "database", "db", "schema", "model",
            "authentication", "auth", "jwt", "oauth", "server",
            "backend", "crud", "rest", "graphql", "microservice",
            "queue", "cache", "redis", "sql", "migration"
        ]

        # Check if task contains backend keywords
        can_handle = any(keyword in task_lower for keyword in backend_keywords)

        if can_handle:
            return True, "Task involves backend development"
        else:
            return False, "Task does not require backend expertise"

    async def execute_task(self, task: str, context: ContextBundle) -> AgentResult:
        """
        Execute backend development task.
        """
        try:
            self.current_context = context

            # Start execution
            await self._update_progress(AgentStatus.PLANNING, 10, "Analyzing backend requirements...")

            # Analyze the specific backend task
            task_type = self._categorize_backend_task(task)

            # Plan the implementation
            implementation_plan = await self._create_implementation_plan(task, task_type)
            await self._update_progress(AgentStatus.PLANNING, 25, f"Planning {task_type} implementation...")

            # Execute based on task type
            if task_type == "api_development":
                result = await self._implement_api(task, implementation_plan)
            elif task_type == "database_design":
                result = await self._implement_database(task, implementation_plan)
            elif task_type == "authentication":
                result = await self._implement_auth(task, implementation_plan)
            elif task_type == "integration":
                result = await self._implement_integration(task, implementation_plan)
            else:
                result = await self._implement_generic_backend(task, implementation_plan)

            # Complete
            await self._update_progress(AgentStatus.COMPLETED, 100, f"Backend {task_type} completed")

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

    def _categorize_backend_task(self, task: str) -> str:
        """
        Categorize the type of backend task.
        """
        task_lower = task.lower()

        if any(keyword in task_lower for keyword in ["api", "endpoint", "rest", "graphql"]):
            return "api_development"
        elif any(keyword in task_lower for keyword in ["database", "db", "schema", "migration", "model"]):
            return "database_design"
        elif any(keyword in task_lower for keyword in ["auth", "jwt", "oauth", "login", "security"]):
            return "authentication"
        elif any(keyword in task_lower for keyword in ["integrate", "connect", "webhook", "external"]):
            return "integration"
        else:
            return "general_backend"

    async def _create_implementation_plan(self, task: str, task_type: str) -> Dict:
        """
        Create detailed implementation plan for backend task.
        """
        plan = {
            "task_type": task_type,
            "components": [],
            "technologies": [],
            "steps": [],
            "testing_strategy": "",
            "security_considerations": []
        }

        # Determine technologies based on context
        if "python" in task.lower() or "fastapi" in task.lower():
            plan["technologies"].extend(["Python", "FastAPI", "SQLAlchemy"])
        elif "node" in task.lower() or "express" in task.lower():
            plan["technologies"].extend(["Node.js", "Express", "Sequelize"])
        else:
            # Default to Python/FastAPI for now
            plan["technologies"].extend(["Python", "FastAPI", "SQLAlchemy"])

        # Plan steps based on task type
        if task_type == "api_development":
            plan["components"] = ["Routes", "Controllers", "Services", "DTOs", "Middleware"]
            plan["steps"] = [
                "Define API specifications",
                "Create route handlers",
                "Implement business logic",
                "Add validation and error handling",
                "Configure middleware",
                "Document endpoints"
            ]
            plan["testing_strategy"] = "Unit tests for services, integration tests for endpoints"

        elif task_type == "database_design":
            plan["components"] = ["Models", "Migrations", "Seeders", "Indexes", "Relationships"]
            plan["steps"] = [
                "Design database schema",
                "Create models/entities",
                "Define relationships",
                "Create migrations",
                "Add indexes for performance",
                "Create seed data"
            ]
            plan["testing_strategy"] = "Test migrations, validate constraints, check query performance"

        elif task_type == "authentication":
            plan["components"] = ["Auth Service", "JWT Handler", "Password Utils", "Session Manager"]
            plan["steps"] = [
                "Implement user model",
                "Create authentication endpoints",
                "Implement JWT generation/validation",
                "Add password hashing",
                "Implement session management",
                "Add rate limiting"
            ]
            plan["security_considerations"] = [
                "Use bcrypt for password hashing",
                "Implement refresh tokens",
                "Add CSRF protection",
                "Validate all inputs",
                "Use HTTPS only"
            ]
            plan["testing_strategy"] = "Test auth flow, token validation, password reset"

        # Log the plan
        self._log_decision(
            f"Backend implementation plan for {task_type}",
            f"Using {', '.join(plan['technologies'])} with {len(plan['steps'])} steps",
            plan["technologies"]
        )

        return plan

    async def _implement_api(self, task: str, plan: Dict) -> str:
        """Generate production-ready API endpoints."""
        await self._update_progress(AgentStatus.BUILDING, 40, "Generating API routes...")

        artifacts = ["backend/api.py", "backend/schemas.py"]
        guidance = (
            "Produce FastAPI code with request/response models, dependency injection,"
            " and clear error handling."
        )
        generated = await self._generate_files(task, plan, artifacts, guidance)

        await self._update_progress(AgentStatus.BUILDING, 72, "Registering API artifacts...")
        summary = self._summarize_generation(generated, "API")
        return summary

    async def _implement_database(self, task: str, plan: Dict) -> str:
        """
        Implement database schema and models.
        """
        await self._update_progress(AgentStatus.BUILDING, 40, "Designing database schema...")

        artifacts = ["database/models.py", "database/migrations/001_initial.sql"]
        guidance = (
            "Model relational entities with SQLAlchemy and emit a migration script"
            " compatible with Alembic."
        )
        generated = await self._generate_files(task, plan, artifacts, guidance)

        await self._update_progress(AgentStatus.BUILDING, 72, "Linking database assets...")
        return self._summarize_generation(generated, "database schema")

    async def _implement_auth(self, task: str, plan: Dict) -> str:
        """
        Implement authentication system.
        """
        await self._update_progress(AgentStatus.BUILDING, 40, "Setting up authentication...")

        artifacts = [
            "auth/jwt_handler.py",
            "auth/password_utils.py",
            "auth/routes.py",
        ]
        guidance = (
            "Provide secure JWT issuance/verification, password hashing using bcrypt,"
            " and FastAPI routes for login/register/reset."
        )
        generated = await self._generate_files(task, plan, artifacts, guidance)

        self._log_decision(
            "Implemented JWT-based authentication",
            "Stateless authentication chosen for scalability",
            ["Cookie-based sessions", "OAuth2"],
        )

        await self._update_progress(AgentStatus.BUILDING, 72, "Documenting auth workflow...")
        return self._summarize_generation(generated, "authentication system")

    async def _implement_integration(self, task: str, plan: Dict) -> str:
        """
        Implement external integrations.
        """
        await self._update_progress(AgentStatus.BUILDING, 40, "Setting up integrations...")

        artifacts = ["integrations/client.py", "integrations/webhooks.py"]
        guidance = (
            "Write robust HTTP client wrappers with retries/timeouts and webhook handlers"
            " including signature validation."
        )
        generated = await self._generate_files(task, plan, artifacts, guidance)

        await self._update_progress(AgentStatus.BUILDING, 72, "Recording integration outputs...")
        return self._summarize_generation(generated, "external integration")

    async def _implement_generic_backend(self, task: str, plan: Dict) -> str:
        """
        Implement generic backend functionality.
        """
        await self._update_progress(AgentStatus.BUILDING, 40, "Implementing backend logic...")

        artifacts = ["services/service.py", "services/utils.py"]
        guidance = (
            "Create modular business logic functions with dependency injection"
            " and clear docstrings."
        )
        generated = await self._generate_files(task, plan, artifacts, guidance)

        await self._update_progress(AgentStatus.BUILDING, 72, "Registering service layer outputs...")
        return self._summarize_generation(generated, "backend services")

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
            return f"No {label} artifacts generated; please refine the task."
        files = "\n".join(f"- {value}" for value in generated.values())
        return f"Generated {len(generated)} {label} artifact(s):\n{files}"

    def _build_prompt(self, task: str, plan: Dict, artifacts: List[str], guidance: str) -> str:
        artifact_lines = "\n".join(f"- {artifact}" for artifact in artifacts)
        steps = "\n".join(f"  • {step}" for step in plan.get("steps", []))
        tech = ", ".join(plan.get("technologies", []))
        return (
            "You are Backend Prime within CASPER."
            f"\nTask: {task}\n"
            f"Technologies: {tech or 'FastAPI, Python, SQLAlchemy'}\n"
            f"Execution steps:\n{steps}\n"
            f"Artifacts to emit, each delimited by '=== <path> ===':\n{artifact_lines}\n"
            f"Guidance: {guidance}\n"
            "Produce production-ready code with docstrings and basic tests or inline examples where appropriate."
        )

    async def _call_llm(self, prompt: str) -> str:
        if llm_service.available():
            try:
                result = await llm_service.complete(prompt, max_tokens=1500)
                if result:
                    return result
            except Exception:  # pragma: no cover
                pass
        return (
            "=== backend/api.py ===\n"
            "from fastapi import APIRouter\n\nrouter = APIRouter()\n\n"
            "@router.get('/health')\nasync def health_check():\n    return {'status': 'ok'}\n"
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
                if line.strip() in ["```python", "```", "```typescript", "```javascript"]:
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

    async def identify_dependencies(self, task: str) -> List[str]:
        """
        Identify external dependencies needed for the task.
        """
        dependencies = []
        task_lower = task.lower()

        # Database dependencies
        if "postgres" in task_lower:
            dependencies.append("psycopg2-binary")
        if "mysql" in task_lower:
            dependencies.append("mysqlclient")
        if "mongo" in task_lower:
            dependencies.append("pymongo")
        if "redis" in task_lower:
            dependencies.append("redis")

        # Framework dependencies
        if "fastapi" in task_lower:
            dependencies.extend(["fastapi", "uvicorn", "pydantic"])
        if "django" in task_lower:
            dependencies.append("django")
        if "flask" in task_lower:
            dependencies.append("flask")

        # Auth dependencies
        if any(keyword in task_lower for keyword in ["jwt", "auth"]):
            dependencies.extend(["python-jose", "passlib", "bcrypt"])

        return dependencies
