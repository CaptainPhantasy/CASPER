import pytest

from core.agents.worker import WorkerAgent
from core.agents.base import ContextBundle, AgentStatus


@pytest.mark.asyncio
async def test_worker_generates_patch(project_root, _mock_llm_service):
    _mock_llm_service.available.return_value = False
    agent = WorkerAgent()
    context = ContextBundle()
    result = await agent.execute_task("Fix typo in README documentation", context)

    assert result.status == AgentStatus.COMPLETED
    patch_files = list((project_root / ".casper" / "output").glob("**/*.diff"))
    assert patch_files, "Expected worker to generate a diff artifact"
    content = patch_files[0].read_text()
    assert "Worker Recovery Plan" in content
    assert "Fix typo in README documentation" in content
