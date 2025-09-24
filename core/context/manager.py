"""
Context Management System for CASPER Prime.
Implements efficient context bundling and transmission between agents.
"""

import json
import os
import zlib
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
from uuid import UUID

from .reducer import ContextReducer


class ContextManager:
    """
    Manages context storage, retrieval, and optimization.
    Central hub for all context operations in CASPER Prime.
    """

    def __init__(self, project_path: str = ".casper"):
        self.project_path = Path(project_path)
        self.context_path = self.project_path / "context"
        self.knowledge_path = self.project_path / "knowledge"
        self._ensure_directories()
        self.active_contexts: Dict[UUID, Dict] = {}
        self.context_cache: Dict[str, Any] = {}

    def _ensure_directories(self):
        """Ensure required directories exist."""
        self.context_path.mkdir(parents=True, exist_ok=True)
        self.knowledge_path.mkdir(parents=True, exist_ok=True)

    def store_context(self, session_id: UUID, context_data: Dict) -> str:
        """
        Store context data with compression if needed.
        Returns storage path.
        """
        reduced = ContextReducer.reduce_to_token_limit(context_data)
        if isinstance(context_data, dict) and context_data.get("root_task_id"):
            reduced["root_task_id"] = context_data.get("root_task_id")
        elif isinstance(context_data, dict) and context_data.get("session_id"):
            reduced.setdefault("root_task_id", context_data.get("session_id"))

        # Compress if large
        serialized = json.dumps(reduced)
        if len(serialized) > 10000:  # 10KB threshold
            compressed = zlib.compress(serialized.encode())
            file_path = self.context_path / f"{session_id}.ctx.gz"
            with open(file_path, 'wb') as f:
                f.write(compressed)
        else:
            file_path = self.context_path / f"{session_id}.ctx"
            with open(file_path, 'w') as f:
                json.dump(reduced, f)

        # Cache for quick access
        self.active_contexts[session_id] = reduced
        return str(file_path)

    def load_context(self, session_id: UUID) -> Optional[Dict]:
        """
        Load context data from storage.
        """
        # Check cache first
        if session_id in self.active_contexts:
            return self.active_contexts[session_id]

        # Try compressed file
        compressed_path = self.context_path / f"{session_id}.ctx.gz"
        if compressed_path.exists():
            with open(compressed_path, 'rb') as f:
                compressed = f.read()
                decompressed = zlib.decompress(compressed)
                context_data = json.loads(decompressed.decode())
                self.active_contexts[session_id] = context_data
                return context_data

        # Try regular file
        regular_path = self.context_path / f"{session_id}.ctx"
        if regular_path.exists():
            with open(regular_path, 'r') as f:
                context_data = json.load(f)
                self.active_contexts[session_id] = context_data
                return context_data

        return None

    def create_structural_awareness(self, project_root: str) -> Dict[str, Any]:
        """
        Create lightweight project map without loading file contents.
        Returns structural pointers to important locations.
        """
        structure = {
            "project_root": project_root,
            "file_map": {},
            "patterns": {},
            "dependencies": {},
            "created_at": datetime.now().isoformat()
        }

        project_path = Path(project_root)

        # Map file locations by type
        for ext in ['.py', '.js', '.ts', '.jsx', '.tsx', '.json', '.yaml', '.yml']:
            files = list(project_path.rglob(f"*{ext}"))
            if files:
                structure["file_map"][ext] = [str(f.relative_to(project_path)) for f in files[:100]]  # Limit

        # Identify common patterns
        if (project_path / "package.json").exists():
            structure["patterns"]["framework"] = "node/npm"
        if (project_path / "requirements.txt").exists() or (project_path / "setup.py").exists():
            structure["patterns"]["framework"] = "python"
        if (project_path / "Cargo.toml").exists():
            structure["patterns"]["framework"] = "rust"

        # Store in knowledge base
        knowledge_file = self.knowledge_path / "structure.json"
        with open(knowledge_file, 'w') as f:
            json.dump(structure, f, indent=2)

        return structure

    def archive_completed_work(self, session_id: UUID, summary: str) -> str:
        """
        Archive completed context with summary.
        Moves from active to archived with compression.
        """
        # Get current context
        context = self.load_context(session_id)
        if not context:
            return "No context to archive"

        # Create archive entry
        archive = {
            "session_id": str(session_id),
            "summary": summary,
            "original_task": context.get("parent_task", ""),
            "artifacts": context.get("artifacts_created", []),
            "decisions": len(context.get("decisions_made", [])),
            "archived_at": datetime.now().isoformat()
        }

        # Store archive summary
        archive_path = self.context_path / "archive" / f"{session_id}.summary.json"
        archive_path.parent.mkdir(exist_ok=True)
        with open(archive_path, 'w') as f:
            json.dump(archive, f)

        # Remove from active contexts
        if session_id in self.active_contexts:
            del self.active_contexts[session_id]

        # Delete original context file
        for ext in [".ctx", ".ctx.gz"]:
            file_path = self.context_path / f"{session_id}{ext}"
            if file_path.exists():
                file_path.unlink()

        return str(archive_path)

    def get_context_summary(self, session_id: UUID) -> Dict[str, Any]:
        """
        Get lightweight summary of context without loading full data.
        """
        # Check archive first
        archive_path = self.context_path / "archive" / f"{session_id}.summary.json"
        if archive_path.exists():
            with open(archive_path, 'r') as f:
                return json.load(f)

        # Load and summarize active context
        context = self.load_context(session_id)
        if context:
            return {
                "session_id": str(session_id),
                "parent_task": context.get("parent_task", ""),
                "token_count": context.get("token_count", 0),
                "artifacts_count": len(context.get("artifacts_created", [])),
                "decisions_count": len(context.get("decisions_made", [])),
                "status": "active"
            }

        return {"session_id": str(session_id), "status": "not_found"}

    def merge_contexts(self, contexts: List[Dict]) -> Dict:
        """
        Merge multiple contexts into one, maintaining efficiency.
        """
        merged = {
            "parent_task": "",
            "structural_pointers": {},
            "decisions_made": [],
            "artifacts_created": [],
            "token_count": 0
        }

        for context in contexts:
            # Merge structural pointers (last wins for conflicts)
            merged["structural_pointers"].update(context.get("structural_pointers", {}))

            # Combine artifacts (deduplicate)
            artifacts = context.get("artifacts_created", [])
            for artifact in artifacts:
                if artifact not in merged["artifacts_created"]:
                    merged["artifacts_created"].append(artifact)

            # Combine decisions (keep last 10)
            merged["decisions_made"].extend(context.get("decisions_made", []))
            if len(merged["decisions_made"]) > 10:
                merged["decisions_made"] = merged["decisions_made"][-10:]

            # Sum token counts
            merged["token_count"] += context.get("token_count", 0)

        return merged

    def clear_cache(self):
        """Clear in-memory context cache."""
        self.active_contexts.clear()
        self.context_cache.clear()

    def get_active_sessions(self) -> List[UUID]:
        """Get list of active session IDs."""
        return list(self.active_contexts.keys())

    def calculate_token_efficiency(self, session_id: UUID) -> Dict[str, float]:
        """
        Calculate token usage efficiency metrics.
        """
        context = self.load_context(session_id)
        if not context:
            return {"efficiency": 0.0}

        token_count = context.get("token_count", 0)
        artifacts_count = len(context.get("artifacts_created", []))
        decisions_count = len(context.get("decisions_made", []))

        # Calculate efficiency metrics
        if token_count > 0:
            artifacts_per_token = artifacts_count / token_count * 1000
            decisions_per_token = decisions_count / token_count * 1000
        else:
            artifacts_per_token = 0
            decisions_per_token = 0

        return {
            "total_tokens": token_count,
            "artifacts_created": artifacts_count,
            "decisions_made": decisions_count,
            "artifacts_per_1k_tokens": artifacts_per_token,
            "decisions_per_1k_tokens": decisions_per_token,
            "efficiency_score": (artifacts_per_token + decisions_per_token) / 2
        }
