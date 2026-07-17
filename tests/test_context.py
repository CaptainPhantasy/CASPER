import json
from pathlib import Path
from uuid import uuid4

from core.context.manager import ContextManager
from core.context.reducer import ContextReducer


def test_context_reducer_limits_tokens():
    bundle = {
        "parent_task": "a" * 5000,
        "decisions_made": [
            {"decision": f"decision-{i}", "rationale": "r" * 50, "timestamp": "2020-01-01T00:00:00"}
            for i in range(20)
        ],
        "artifacts_created": [f"file_{i}.py" for i in range(30)],
        "token_count": 10_000,
    }
    reduced = ContextReducer.reduce_to_token_limit(bundle, limit=200)
    assert len(reduced.get("decisions_made", [])) <= 5
    assert len(reduced.get("artifacts_created", [])) <= 10
    assert ContextReducer.estimate_tokens(str(reduced)) <= 200 * 1.2  # allow small overhead


def test_context_manager_persists_reduced_bundle(project_root):
    manager = ContextManager(Path(".casper"))
    session_id = uuid4()
    context = {
        "parent_task": "demo" * 500,
        "artifacts_created": [f"artifact_{i}.py" for i in range(20)],
    }
    path = manager.store_context(session_id, context)
    with open(path, "r" if path.endswith(".ctx") else "rb") as fh:
        if path.endswith(".ctx"):
            data = json.load(fh)
        else:
            import zlib
            data = json.loads(zlib.decompress(fh.read()).decode())
    assert Path(path).exists()
    assert "parent_task" in data
