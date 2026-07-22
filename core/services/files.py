import os
from pathlib import Path


def write_artifact(base_dir: str, session_id: str, rel_path: str, content: str) -> str:
    """Write an artifact under base_dir/session_id/rel_path inside the project root."""
    project_root = Path(os.environ.get("CASPER_PROJECT_ROOT", Path.cwd()))
    base = (project_root / base_dir / str(session_id)).resolve()
    target = (base / rel_path).resolve()

    if project_root not in target.parents and target != project_root:
        raise ValueError("Attempted to write artifact outside project root")

    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(content)
    return str(target)
