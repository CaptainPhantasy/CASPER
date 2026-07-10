"""
Production-ready persistent coding session manager for CASPER Prime.
Implements complete ISession interface with SQLite persistence and 200k token context accumulation.
"""

import json
import sqlite3
import uuid
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
from dataclasses import dataclass, asdict
import threading
import logging
from contextlib import asynccontextmanager

from ..interfaces import ISession, SessionState, SessionError, MAX_CONTEXT_TOKENS
from ...context.manager import ContextManager


logger = logging.getLogger(__name__)


@dataclass
class TokenizedInteraction:
    """Single interaction with token counting"""
    timestamp: str
    user_input: str
    response: str
    token_count: int
    metadata: Dict[str, Any]


@dataclass
class SessionMetrics:
    """Session performance and usage metrics"""
    total_interactions: int
    total_tokens: int
    files_modified_count: int
    avg_response_time: float
    last_active: str
    session_duration: float  # minutes


class CodingSession(ISession):
    """
    Complete coding session manager with SQLite persistence and context accumulation.
    Implements full ISession interface - ZERO TOLERANCE for incomplete implementation.
    """

    def __init__(self, storage_path: str = None, context_manager: ContextManager = None):
        """Initialize session manager with persistent storage"""
        self.storage_path = Path(storage_path or "/Volumes/Storage/Development/CASPER DEV/.casper/sessions")
        self.db_path = self.storage_path / "sessions.db"
        self.context_manager = context_manager or ContextManager()

        # Thread safety
        self._lock = threading.RLock()

        # In-memory session cache
        self._active_sessions: Dict[str, SessionState] = {}
        self._interaction_buffers: Dict[str, List[TokenizedInteraction]] = {}

        # Setup storage
        self._ensure_directories()
        self._init_database()
        self._load_active_sessions()

        logger.info(f"CodingSession initialized with storage at: {self.storage_path}")

    def _ensure_directories(self) -> None:
        """Ensure required directories exist"""
        self.storage_path.mkdir(parents=True, exist_ok=True)

    def _init_database(self) -> None:
        """Initialize SQLite database with complete schema"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()

            # Main sessions table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS sessions (
                    session_id TEXT PRIMARY KEY,
                    started_at TEXT NOT NULL,
                    last_activity TEXT NOT NULL,
                    context_tokens INTEGER DEFAULT 0,
                    files_modified TEXT DEFAULT '[]',
                    knowledge_base_id TEXT,
                    active INTEGER DEFAULT 1,
                    metadata TEXT DEFAULT '{}'
                )
            """)

            # Interactions table for detailed history
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS interactions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id TEXT NOT NULL,
                    timestamp TEXT NOT NULL,
                    user_input TEXT NOT NULL,
                    response TEXT NOT NULL,
                    token_count INTEGER NOT NULL,
                    metadata TEXT DEFAULT '{}',
                    FOREIGN KEY (session_id) REFERENCES sessions (session_id)
                )
            """)

            # Session snapshots for recovery
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS session_snapshots (
                    snapshot_id TEXT PRIMARY KEY,
                    session_id TEXT NOT NULL,
                    snapshot_data TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    FOREIGN KEY (session_id) REFERENCES sessions (session_id)
                )
            """)

            # Create indexes for performance
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_sessions_active ON sessions(active)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_interactions_session ON interactions(session_id)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_interactions_timestamp ON interactions(timestamp)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_snapshots_session ON session_snapshots(session_id)")

            conn.commit()

    def _load_active_sessions(self) -> None:
        """Load active sessions from database on startup"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT session_id, started_at, last_activity, context_tokens,
                       files_modified, knowledge_base_id, metadata
                FROM sessions WHERE active = 1
            """)

            rows = cursor.fetchall()

            for row in rows:
                session_id, started_at, last_activity, context_tokens, files_modified, kb_id, metadata = row

                # Load conversation history
                cursor.execute("""
                    SELECT user_input, response FROM interactions
                    WHERE session_id = ? ORDER BY timestamp DESC LIMIT 50
                """, (session_id,))

                history_rows = cursor.fetchall()
                conversation_history = [
                    {"user": user_input, "assistant": response}
                    for user_input, response in history_rows
                ]

                # Create session state
                session_state = SessionState(
                    session_id=session_id,
                    started_at=datetime.fromisoformat(started_at),
                    last_activity=datetime.fromisoformat(last_activity),
                    context_tokens=context_tokens,
                    files_modified=json.loads(files_modified) if files_modified else [],
                    conversation_history=conversation_history,
                    knowledge_base_id=kb_id or f"kb_{session_id}",
                    active=True
                )

                self._active_sessions[session_id] = session_state
                self._interaction_buffers[session_id] = []

        logger.info(f"Loaded {len(self._active_sessions)} active sessions from database")

    async def start_session(self, session_id: str = None) -> SessionState:
        """Initialize a new coding session"""
        if not session_id:
            session_id = str(uuid.uuid4())

        with self._lock:
            if session_id in self._active_sessions:
                raise SessionError(f"Session {session_id} already exists")

            now = datetime.now(timezone.utc)

            # Create session state
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

            # Store in database
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT INTO sessions
                    (session_id, started_at, last_activity, context_tokens,
                     files_modified, knowledge_base_id, active, metadata)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    session_id,
                    now.isoformat(),
                    now.isoformat(),
                    0,
                    json.dumps([]),
                    f"kb_{session_id}",
                    1,
                    json.dumps({})
                ))
                conn.commit()

            # Add to active sessions
            self._active_sessions[session_id] = session_state
            self._interaction_buffers[session_id] = []

            # Create initial context
            await self._initialize_session_context(session_id)

            logger.info(f"Started new coding session: {session_id}")
            return session_state

    async def _initialize_session_context(self, session_id: str) -> None:
        """Initialize context for new session"""
        initial_context = {
            "session_id": session_id,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "context_tokens": 0,
            "structural_pointers": {},
            "artifacts_created": [],
            "decisions_made": [],
            "parent_task": f"Coding session {session_id}"
        }

        # Store context
        session_uuid = uuid.UUID(session_id)
        self.context_manager.store_context(session_uuid, initial_context)

    async def add_interaction(self, session_id: str, user_input: str, response: str, metadata: Dict[str, Any] = None) -> None:
        """Add an interaction to session history with token counting"""
        if session_id not in self._active_sessions:
            raise SessionError(f"Session {session_id} not found")

        with self._lock:
            now = datetime.now(timezone.utc)

            # Estimate token count (roughly 4 chars per token)
            token_count = (len(user_input) + len(response)) // 4

            # Create interaction
            interaction = TokenizedInteraction(
                timestamp=now.isoformat(),
                user_input=user_input,
                response=response,
                token_count=token_count,
                metadata=metadata or {}
            )

            # Add to buffer
            self._interaction_buffers[session_id].append(interaction)

            # Update session state
            session_state = self._active_sessions[session_id]
            session_state.last_activity = now
            session_state.context_tokens += token_count
            session_state.conversation_history.append({
                "user": user_input,
                "assistant": response
            })

            # Keep only recent history in memory (last 100 interactions)
            if len(session_state.conversation_history) > 100:
                session_state.conversation_history = session_state.conversation_history[-100:]

            # Check token limit and reduce if needed
            await self._manage_token_limit(session_id)

            # Store in database
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()

                # Insert interaction
                cursor.execute("""
                    INSERT INTO interactions
                    (session_id, timestamp, user_input, response, token_count, metadata)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (
                    session_id,
                    now.isoformat(),
                    user_input,
                    response,
                    token_count,
                    json.dumps(metadata or {})
                ))

                # Update session
                cursor.execute("""
                    UPDATE sessions
                    SET last_activity = ?, context_tokens = ?
                    WHERE session_id = ?
                """, (now.isoformat(), session_state.context_tokens, session_id))

                conn.commit()

    async def _manage_token_limit(self, session_id: str) -> None:
        """Manage context token limit by reducing oldest interactions"""
        session_state = self._active_sessions[session_id]

        if session_state.context_tokens <= MAX_CONTEXT_TOKENS:
            return

        # Calculate how many tokens to remove (remove 20% when limit exceeded)
        tokens_to_remove = session_state.context_tokens - int(MAX_CONTEXT_TOKENS * 0.8)

        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()

            # Get oldest interactions to remove
            cursor.execute("""
                SELECT id, token_count FROM interactions
                WHERE session_id = ? ORDER BY timestamp ASC
            """, (session_id,))

            rows = cursor.fetchall()
            tokens_removed = 0
            interactions_to_delete = []

            for interaction_id, token_count in rows:
                if tokens_removed >= tokens_to_remove:
                    break
                interactions_to_delete.append(interaction_id)
                tokens_removed += token_count

            # Remove old interactions
            if interactions_to_delete:
                placeholders = ','.join('?' * len(interactions_to_delete))
                cursor.execute(f"""
                    DELETE FROM interactions WHERE id IN ({placeholders})
                """, interactions_to_delete)

                # Update session token count
                session_state.context_tokens -= tokens_removed
                cursor.execute("""
                    UPDATE sessions SET context_tokens = ? WHERE session_id = ?
                """, (session_state.context_tokens, session_id))

                conn.commit()

                logger.info(f"Removed {len(interactions_to_delete)} old interactions "
                           f"({tokens_removed} tokens) from session {session_id}")

    async def get_context(self, session_id: str) -> Dict[str, Any]:
        """Get current session context with recent interactions"""
        if session_id not in self._active_sessions:
            raise SessionError(f"Session {session_id} not found")

        session_state = self._active_sessions[session_id]

        # Load context from context manager
        session_uuid = uuid.UUID(session_id)
        stored_context = self.context_manager.load_context(session_uuid) or {}

        # Get recent interactions
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT user_input, response, timestamp, token_count
                FROM interactions
                WHERE session_id = ?
                ORDER BY timestamp DESC LIMIT 20
            """, (session_id,))

            recent_interactions = [
                {
                    "user_input": row[0],
                    "response": row[1],
                    "timestamp": row[2],
                    "token_count": row[3]
                }
                for row in cursor.fetchall()
            ]

        # Build comprehensive context
        context = {
            "session_id": session_id,
            "session_state": asdict(session_state),
            "recent_interactions": recent_interactions,
            "stored_context": stored_context,
            "metrics": await self._calculate_session_metrics(session_id),
            "timestamp": datetime.now(timezone.utc).isoformat()
        }

        return context

    async def _calculate_session_metrics(self, session_id: str) -> Dict[str, Any]:
        """Calculate session performance metrics"""
        session_state = self._active_sessions[session_id]

        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()

            # Get interaction count and total tokens
            cursor.execute("""
                SELECT COUNT(*), SUM(token_count)
                FROM interactions WHERE session_id = ?
            """, (session_id,))

            interaction_count, total_tokens = cursor.fetchone()
            interaction_count = interaction_count or 0
            total_tokens = total_tokens or 0

        # Calculate session duration
        duration = (session_state.last_activity - session_state.started_at).total_seconds() / 60

        return {
            "total_interactions": interaction_count,
            "total_tokens": total_tokens,
            "files_modified_count": len(session_state.files_modified),
            "session_duration_minutes": duration,
            "avg_tokens_per_interaction": total_tokens / max(interaction_count, 1),
            "tokens_per_minute": total_tokens / max(duration, 1)
        }

    def _serialize_for_json(self, obj):
        """Helper to serialize objects for JSON storage"""
        if isinstance(obj, datetime):
            return obj.isoformat()
        elif isinstance(obj, dict):
            return {key: self._serialize_for_json(value) for key, value in obj.items()}
        elif isinstance(obj, list):
            return [self._serialize_for_json(item) for item in obj]
        elif hasattr(obj, '__dict__'):
            return self._serialize_for_json(obj.__dict__)
        else:
            return obj

    async def persist(self, session_id: str) -> None:
        """Save session to persistent storage with context snapshot"""
        if session_id not in self._active_sessions:
            raise SessionError(f"Session {session_id} not found")

        session_state = self._active_sessions[session_id]

        with self._lock:
            # Create snapshot of current state - serialize datetimes properly
            snapshot_data = {
                "session_state": self._serialize_for_json(asdict(session_state)),
                "recent_context": self._serialize_for_json(await self.get_context(session_id)),
                "timestamp": datetime.now(timezone.utc).isoformat()
            }

            snapshot_id = str(uuid.uuid4())

            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()

                # Update session record
                cursor.execute("""
                    UPDATE sessions
                    SET last_activity = ?, context_tokens = ?, files_modified = ?
                    WHERE session_id = ?
                """, (
                    session_state.last_activity.isoformat(),
                    session_state.context_tokens,
                    json.dumps(session_state.files_modified),
                    session_id
                ))

                # Save snapshot
                cursor.execute("""
                    INSERT INTO session_snapshots
                    (snapshot_id, session_id, snapshot_data, created_at)
                    VALUES (?, ?, ?, ?)
                """, (
                    snapshot_id,
                    session_id,
                    json.dumps(snapshot_data),
                    datetime.now(timezone.utc).isoformat()
                ))

                conn.commit()

        # Update context manager
        session_uuid = uuid.UUID(session_id)
        context_update = {
            "session_id": session_id,
            "last_persisted": datetime.now(timezone.utc).isoformat(),
            "context_tokens": session_state.context_tokens,
            "artifacts_created": session_state.files_modified,
            "decisions_made": [f"Session persisted at {snapshot_id}"]
        }

        existing_context = self.context_manager.load_context(session_uuid) or {}
        existing_context.update(context_update)
        self.context_manager.store_context(session_uuid, existing_context)

        logger.info(f"Session {session_id} persisted with snapshot {snapshot_id}")

    async def recover(self, session_id: str) -> SessionState:
        """Recover session from storage with full context restoration"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()

            # Get session record
            cursor.execute("""
                SELECT session_id, started_at, last_activity, context_tokens,
                       files_modified, knowledge_base_id, metadata
                FROM sessions WHERE session_id = ?
            """, (session_id,))

            row = cursor.fetchone()
            if not row:
                raise SessionError(f"Session {session_id} not found in storage")

            session_id, started_at, last_activity, context_tokens, files_modified, kb_id, metadata = row

            # Load conversation history
            cursor.execute("""
                SELECT user_input, response FROM interactions
                WHERE session_id = ? ORDER BY timestamp DESC LIMIT 100
            """, (session_id,))

            history_rows = cursor.fetchall()
            conversation_history = [
                {"user": user_input, "assistant": response}
                for user_input, response in history_rows
            ]

        # Create recovered session state
        recovered_state = SessionState(
            session_id=session_id,
            started_at=datetime.fromisoformat(started_at),
            last_activity=datetime.fromisoformat(last_activity),
            context_tokens=context_tokens,
            files_modified=json.loads(files_modified) if files_modified else [],
            conversation_history=conversation_history,
            knowledge_base_id=kb_id or f"kb_{session_id}",
            active=True
        )

        # Add back to active sessions
        with self._lock:
            self._active_sessions[session_id] = recovered_state
            self._interaction_buffers[session_id] = []

        # Reactivate in database
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE sessions SET active = 1 WHERE session_id = ?
            """, (session_id,))
            conn.commit()

        logger.info(f"Successfully recovered session {session_id}")
        return recovered_state

    async def cleanup_old_sessions(self, days: int = 30) -> int:
        """Clean up sessions older than specified days"""
        cutoff_date = datetime.now(timezone.utc) - timedelta(days=days)

        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()

            # Find old sessions to archive
            cursor.execute("""
                SELECT session_id FROM sessions
                WHERE last_activity < ? AND active = 1
            """, (cutoff_date.isoformat(),))

            old_sessions = [row[0] for row in cursor.fetchall()]

            if not old_sessions:
                return 0

            # Archive old sessions (mark as inactive)
            placeholders = ','.join('?' * len(old_sessions))
            cursor.execute(f"""
                UPDATE sessions SET active = 0
                WHERE session_id IN ({placeholders})
            """, old_sessions)

            # Remove from active memory
            with self._lock:
                for session_id in old_sessions:
                    if session_id in self._active_sessions:
                        del self._active_sessions[session_id]
                    if session_id in self._interaction_buffers:
                        del self._interaction_buffers[session_id]

            conn.commit()

        logger.info(f"Cleaned up {len(old_sessions)} old sessions")
        return len(old_sessions)

    # Additional utility methods for complete functionality

    def get_active_session_ids(self) -> List[str]:
        """Get list of active session IDs"""
        return list(self._active_sessions.keys())

    async def get_session_stats(self) -> Dict[str, Any]:
        """Get comprehensive session statistics"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()

            # Total sessions
            cursor.execute("SELECT COUNT(*) FROM sessions")
            total_sessions = cursor.fetchone()[0]

            # Active sessions
            cursor.execute("SELECT COUNT(*) FROM sessions WHERE active = 1")
            active_sessions = cursor.fetchone()[0]

            # Total interactions
            cursor.execute("SELECT COUNT(*) FROM interactions")
            total_interactions = cursor.fetchone()[0]

            # Total tokens
            cursor.execute("SELECT SUM(context_tokens) FROM sessions WHERE active = 1")
            total_tokens = cursor.fetchone()[0] or 0

        return {
            "total_sessions": total_sessions,
            "active_sessions": active_sessions,
            "sessions_in_memory": len(self._active_sessions),
            "total_interactions": total_interactions,
            "total_context_tokens": total_tokens,
            "storage_path": str(self.storage_path),
            "database_path": str(self.db_path)
        }

    async def add_file_modification(self, session_id: str, file_path: str) -> None:
        """Track file modification in session"""
        if session_id not in self._active_sessions:
            raise SessionError(f"Session {session_id} not found")

        session_state = self._active_sessions[session_id]

        if file_path not in session_state.files_modified:
            session_state.files_modified.append(file_path)

            # Update database
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    UPDATE sessions SET files_modified = ? WHERE session_id = ?
                """, (json.dumps(session_state.files_modified), session_id))
                conn.commit()

    async def close_session(self, session_id: str) -> None:
        """Gracefully close a session"""
        if session_id not in self._active_sessions:
            return

        # Final persist
        await self.persist(session_id)

        # Mark as inactive
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE sessions SET active = 0 WHERE session_id = ?
            """, (session_id,))
            conn.commit()

        # Remove from memory
        with self._lock:
            if session_id in self._active_sessions:
                del self._active_sessions[session_id]
            if session_id in self._interaction_buffers:
                del self._interaction_buffers[session_id]

        logger.info(f"Closed session {session_id}")

    def health_check(self) -> Dict[str, Any]:
        """Comprehensive health check"""
        return {
            "database_accessible": self.db_path.exists(),
            "storage_directory_exists": self.storage_path.exists(),
            "active_sessions": len(self._active_sessions),
            "context_manager_available": self.context_manager is not None,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "storage_path": str(self.storage_path),
            "max_context_tokens": MAX_CONTEXT_TOKENS
        }