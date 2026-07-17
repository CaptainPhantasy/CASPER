"""
CASPER Prime Terminal Session Management - SIGMA Agent Component
Manages terminal sessions with persistence and context tracking.
PRODUCTION GRADE - Full implementation of ISession interface.
"""

import asyncio
import json
import os
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, Any, List, Optional
from uuid import uuid4
import aiofiles
import logging

from ..interfaces import ISession, SessionState, SessionError

logger = logging.getLogger(__name__)


class SessionManager(ISession):
    """
    Production-grade session management for CASPER Prime Terminal.
    Handles session lifecycle, persistence, and context management.
    """

    def __init__(self, persistence_path: str = ".casper/terminal_sessions", session_timeout: int = 30):
        """Initialize session manager with persistence and configuration."""
        self.persistence_path = Path(persistence_path)
        self.session_timeout = session_timeout  # minutes
        self.current_session: Optional[SessionState] = None
        self.sessions_cache: Dict[str, SessionState] = {}

        # Ensure persistence directory exists
        self.persistence_path.mkdir(parents=True, exist_ok=True)

        # Session file paths
        self.sessions_index_file = self.persistence_path / "sessions_index.json"
        self.sessions_data_dir = self.persistence_path / "data"
        self.sessions_data_dir.mkdir(exist_ok=True)

    async def start_session(self, session_id: str) -> SessionState:
        """Initialize a new coding session with full state management."""
        try:
            # Check if session already exists
            if session_id in self.sessions_cache:
                logger.info(f"Resuming existing session: {session_id}")
                return self.sessions_cache[session_id]

            # Create new session
            now = datetime.now()
            session_state = SessionState(
                session_id=session_id,
                started_at=now,
                last_activity=now,
                context_tokens=0,
                files_modified=[],
                conversation_history=[],
                knowledge_base_id=f"kb_{session_id}",
                active=True
            )

            # Set as current session
            self.current_session = session_state
            self.sessions_cache[session_id] = session_state

            # Initialize session data directory
            session_data_dir = self.sessions_data_dir / session_id
            session_data_dir.mkdir(exist_ok=True)

            # Create session metadata file
            await self._save_session_metadata(session_state)

            # Update sessions index
            await self._update_sessions_index(session_id, "created")

            logger.info(f"Started new session: {session_id}")
            return session_state

        except Exception as e:
            logger.error(f"Failed to start session {session_id}: {e}")
            raise SessionError(f"Session creation failed: {e}")

    async def add_interaction(self, user_input: str, response: str) -> None:
        """Add an interaction to session history with token tracking."""
        if not self.current_session:
            raise SessionError("No active session")

        try:
            interaction = {
                "timestamp": datetime.now().isoformat(),
                "user_input": user_input,
                "response": response,
                "tokens_used": self._estimate_tokens(user_input + response)
            }

            self.current_session.conversation_history.append(interaction)
            self.current_session.last_activity = datetime.now()

            # Update token count
            self.current_session.context_tokens += interaction["tokens_used"]

            # Manage context size - rotate old conversations if needed
            await self._manage_context_size()

            logger.debug(f"Added interaction to session {self.current_session.session_id}")

        except Exception as e:
            logger.error(f"Failed to add interaction: {e}")
            raise SessionError(f"Interaction logging failed: {e}")

    async def get_context(self) -> Dict[str, Any]:
        """Get current session context with comprehensive information."""
        if not self.current_session:
            return {"session": None, "context": "No active session"}

        try:
            # Get recent conversation history (last 20 interactions)
            recent_history = self.current_session.conversation_history[-20:]

            # Get modified files information
            files_info = await self._get_files_info()

            # Calculate session metrics
            session_duration = (
                datetime.now() - self.current_session.started_at
            ).total_seconds() / 60  # minutes

            context = {
                "session_id": self.current_session.session_id,
                "started_at": self.current_session.started_at.isoformat(),
                "duration_minutes": round(session_duration, 2),
                "last_activity": self.current_session.last_activity.isoformat(),
                "total_interactions": len(self.current_session.conversation_history),
                "context_tokens": self.current_session.context_tokens,
                "files_modified": self.current_session.files_modified,
                "files_info": files_info,
                "recent_history": recent_history,
                "knowledge_base_id": self.current_session.knowledge_base_id,
                "session_active": self.current_session.active
            }

            return context

        except Exception as e:
            logger.error(f"Failed to get context: {e}")
            return {"error": f"Context retrieval failed: {e}"}

    async def persist(self) -> None:
        """Save session to persistent storage with data integrity."""
        if not self.current_session:
            logger.warning("No active session to persist")
            return

        try:
            # Save session metadata
            await self._save_session_metadata(self.current_session)

            # Save conversation history
            await self._save_conversation_history(self.current_session)

            # Update last persistence time
            self.current_session.last_activity = datetime.now()

            logger.debug(f"Persisted session {self.current_session.session_id}")

        except Exception as e:
            logger.error(f"Failed to persist session: {e}")
            raise SessionError(f"Session persistence failed: {e}")

    async def recover(self, session_id: str) -> SessionState:
        """Recover session from storage with full state restoration."""
        try:
            # Check cache first
            if session_id in self.sessions_cache:
                return self.sessions_cache[session_id]

            # Load from persistent storage
            session_file = self.sessions_data_dir / session_id / "metadata.json"
            if not session_file.exists():
                raise SessionError(f"Session {session_id} not found")

            # Load session metadata
            async with aiofiles.open(session_file, 'r') as f:
                session_data = json.loads(await f.read())

            # Reconstruct SessionState
            session_state = SessionState(
                session_id=session_data["session_id"],
                started_at=datetime.fromisoformat(session_data["started_at"]),
                last_activity=datetime.fromisoformat(session_data["last_activity"]),
                context_tokens=session_data["context_tokens"],
                files_modified=session_data["files_modified"],
                conversation_history=[],  # Will be loaded separately
                knowledge_base_id=session_data["knowledge_base_id"],
                active=session_data["active"]
            )

            # Load conversation history
            session_state.conversation_history = await self._load_conversation_history(session_id)

            # Cache and activate session
            self.sessions_cache[session_id] = session_state
            self.current_session = session_state

            logger.info(f"Recovered session: {session_id}")
            return session_state

        except Exception as e:
            logger.error(f"Failed to recover session {session_id}: {e}")
            raise SessionError(f"Session recovery failed: {e}")

    async def cleanup_old_sessions(self, days: int = 30) -> int:
        """Clean up sessions older than specified days."""
        try:
            cutoff_date = datetime.now() - timedelta(days=days)
            cleaned_count = 0

            # Load sessions index
            sessions_index = await self._load_sessions_index()

            sessions_to_remove = []
            for session_id, session_info in sessions_index.items():
                last_activity = datetime.fromisoformat(session_info["last_activity"])
                if last_activity < cutoff_date:
                    sessions_to_remove.append(session_id)

            # Remove old sessions
            for session_id in sessions_to_remove:
                await self._remove_session(session_id)
                cleaned_count += 1

            # Update index
            await self._save_sessions_index(sessions_index)

            logger.info(f"Cleaned up {cleaned_count} old sessions")
            return cleaned_count

        except Exception as e:
            logger.error(f"Failed to cleanup old sessions: {e}")
            return 0

    async def _save_session_metadata(self, session_state: SessionState) -> None:
        """Save session metadata to persistent storage."""
        session_dir = self.sessions_data_dir / session_state.session_id
        session_dir.mkdir(exist_ok=True)

        metadata = {
            "session_id": session_state.session_id,
            "started_at": session_state.started_at.isoformat(),
            "last_activity": session_state.last_activity.isoformat(),
            "context_tokens": session_state.context_tokens,
            "files_modified": session_state.files_modified,
            "knowledge_base_id": session_state.knowledge_base_id,
            "active": session_state.active
        }

        metadata_file = session_dir / "metadata.json"
        async with aiofiles.open(metadata_file, 'w') as f:
            await f.write(json.dumps(metadata, indent=2))

    async def _save_conversation_history(self, session_state: SessionState) -> None:
        """Save conversation history to separate file for efficiency."""
        session_dir = self.sessions_data_dir / session_state.session_id
        history_file = session_dir / "conversation_history.json"

        async with aiofiles.open(history_file, 'w') as f:
            await f.write(json.dumps(session_state.conversation_history, indent=2))

    async def _load_conversation_history(self, session_id: str) -> List[Dict[str, str]]:
        """Load conversation history from persistent storage."""
        history_file = self.sessions_data_dir / session_id / "conversation_history.json"

        if not history_file.exists():
            return []

        async with aiofiles.open(history_file, 'r') as f:
            return json.loads(await f.read())

    async def _update_sessions_index(self, session_id: str, action: str) -> None:
        """Update the sessions index with session information."""
        sessions_index = await self._load_sessions_index()

        sessions_index[session_id] = {
            "action": action,
            "timestamp": datetime.now().isoformat(),
            "last_activity": datetime.now().isoformat() if self.current_session else None
        }

        await self._save_sessions_index(sessions_index)

    async def _load_sessions_index(self) -> Dict[str, Any]:
        """Load sessions index from persistent storage."""
        if not self.sessions_index_file.exists():
            return {}

        try:
            async with aiofiles.open(self.sessions_index_file, 'r') as f:
                return json.loads(await f.read())
        except Exception:
            return {}

    async def _save_sessions_index(self, sessions_index: Dict[str, Any]) -> None:
        """Save sessions index to persistent storage."""
        async with aiofiles.open(self.sessions_index_file, 'w') as f:
            await f.write(json.dumps(sessions_index, indent=2))

    async def _remove_session(self, session_id: str) -> None:
        """Remove session from storage and cache."""
        # Remove from cache
        if session_id in self.sessions_cache:
            del self.sessions_cache[session_id]

        # Remove session directory
        session_dir = self.sessions_data_dir / session_id
        if session_dir.exists():
            import shutil
            shutil.rmtree(session_dir)

    async def _get_files_info(self) -> List[Dict[str, Any]]:
        """Get information about modified files."""
        if not self.current_session:
            return []

        files_info = []
        for file_path in self.current_session.files_modified:
            try:
                if os.path.exists(file_path):
                    stat = os.stat(file_path)
                    files_info.append({
                        "path": file_path,
                        "size": stat.st_size,
                        "modified": datetime.fromtimestamp(stat.st_mtime).isoformat()
                    })
            except Exception as e:
                logger.warning(f"Could not get info for file {file_path}: {e}")

        return files_info

    async def _manage_context_size(self) -> None:
        """Manage context size to prevent token limit overflow."""
        if not self.current_session:
            return

        # If context is too large, rotate old conversations
        MAX_CONTEXT_TOKENS = 150000  # Leave room for new content

        if self.current_session.context_tokens > MAX_CONTEXT_TOKENS:
            # Keep only recent conversations
            recent_conversations = self.current_session.conversation_history[-50:]

            # Recalculate token count
            new_token_count = sum(
                self._estimate_tokens(conv.get("user_input", "") + conv.get("response", ""))
                for conv in recent_conversations
            )

            self.current_session.conversation_history = recent_conversations
            self.current_session.context_tokens = new_token_count

            logger.info(f"Rotated context for session {self.current_session.session_id}")

    def _estimate_tokens(self, text: str) -> int:
        """Estimate token count for text (approximate)."""
        # Rough estimation: 1 token ≈ 4 characters
        return len(text) // 4