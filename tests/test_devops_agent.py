import pytest

from core.agents.devops_prime import DevOpsPrimeAgent
from core.agents.base import ContextBundle, AgentStatus


@pytest.mark.asyncio
async def test_devops_agent_generates_artifacts(project_root):
    agent = DevOpsPrimeAgent()
    context = ContextBundle()
    result = await agent.execute_task("Set up CI pipeline with build and deploy stages", context)

    assert result.status == AgentStatus.COMPLETED
    output_path = project_root / ".casper" / "output"
    session_dirs = list(output_path.glob("*")) if output_path.exists() else []
    files = []
    for session_dir in session_dirs:
        files.extend(session_dir.rglob("*"))
    assert files, "DevOps agent should emit artifacts"
