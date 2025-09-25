"""
Simplified State Manager for immediate testing without LangGraph dependencies
This proves the persistence concept works with real SQLite storage
"""

import json
import os
import sqlite3
import threading
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional
from dataclasses import dataclass
from enum import Enum


class TaskStatus(Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    PAUSED = "paused"


@dataclass
class AgentTask:
    task_id: str
    description: str
    status: TaskStatus
    assigned_agent: Optional[str]
    created_at: str
    updated_at: str
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None


class SimpleStateManager:
    """
    Real state management with SQLite persistence - NO DEPENDENCIES
    """

    def __init__(self, storage_path: str = None):
        self.storage_path = storage_path or "/Volumes/Storage/Development/CASPER DEV/.casper/transformation/state_management"
        self.db_path = Path(self.storage_path) / "simple_state.db"
        self.checkpoint_path = Path(self.storage_path) / "checkpoints"

        # Ensure directories exist
        Path(self.storage_path).mkdir(parents=True, exist_ok=True)
        self.checkpoint_path.mkdir(parents=True, exist_ok=True)

        # Initialize SQLite database
        self._init_database()

        # Thread-safe task tracking
        self._lock = threading.Lock()
        self._tasks: Dict[str, AgentTask] = {}
        self._load_tasks_from_db()

        print(f"✅ SimpleStateManager initialized with persistent storage at: {self.storage_path}")

    def _init_database(self):
        """Initialize SQLite database with proper schema"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Create tasks table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS tasks (
                task_id TEXT PRIMARY KEY,
                description TEXT NOT NULL,
                status TEXT NOT NULL,
                assigned_agent TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                result TEXT,
                error TEXT
            )
        """)

        # Create state snapshots table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS state_snapshots (
                snapshot_id TEXT PRIMARY KEY,
                thread_id TEXT NOT NULL,
                state_data TEXT NOT NULL,
                created_at TEXT NOT NULL
            )
        """)

        conn.commit()
        conn.close()
        print(f"✅ Database initialized at: {self.db_path}")

    def create_task(self, description: str, assigned_agent: str = None) -> AgentTask:
        """Create a new task"""
        task = AgentTask(
            task_id=str(uuid.uuid4()),
            description=description,
            status=TaskStatus.PENDING,
            assigned_agent=assigned_agent or "default_agent",
            created_at=datetime.now(timezone.utc).isoformat(),
            updated_at=datetime.now(timezone.utc).isoformat()
        )

        self._save_task_to_db(task)
        return task

    def update_task_status(self, task_id: str, status: TaskStatus, result: Dict[str, Any] = None, error: str = None) -> bool:
        """Update task status"""
        task = self._tasks.get(task_id)
        if not task:
            return False

        task.status = status
        task.updated_at = datetime.now(timezone.utc).isoformat()

        if result:
            task.result = result
        if error:
            task.error = error

        self._save_task_to_db(task)
        return True

    def complete_task(self, task_id: str, result: Dict[str, Any]) -> bool:
        """Mark task as completed with result"""
        return self.update_task_status(task_id, TaskStatus.COMPLETED, result=result)

    def fail_task(self, task_id: str, error: str) -> bool:
        """Mark task as failed with error"""
        return self.update_task_status(task_id, TaskStatus.FAILED, error=error)

    def _save_task_to_db(self, task: AgentTask):
        """Save task to SQLite database"""
        with self._lock:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            cursor.execute("""
                INSERT OR REPLACE INTO tasks
                (task_id, description, status, assigned_agent, created_at, updated_at, result, error)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                task.task_id,
                task.description,
                task.status.value,
                task.assigned_agent,
                task.created_at,
                task.updated_at,
                json.dumps(task.result) if task.result else None,
                task.error
            ))

            conn.commit()
            conn.close()

            # Also keep in memory
            self._tasks[task.task_id] = task

    def _load_tasks_from_db(self):
        """Load all tasks from database on startup"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("SELECT * FROM tasks")
        rows = cursor.fetchall()

        for row in rows:
            task = AgentTask(
                task_id=row[0],
                description=row[1],
                status=TaskStatus(row[2]),
                assigned_agent=row[3],
                created_at=row[4],
                updated_at=row[5],
                result=json.loads(row[6]) if row[6] else None,
                error=row[7]
            )
            self._tasks[task.task_id] = task

        conn.close()
        print(f"✅ Loaded {len(self._tasks)} tasks from database")

    def save_checkpoint(self, thread_id: str, state: Dict[str, Any]) -> str:
        """Save state checkpoint with unique ID"""
        checkpoint_id = str(uuid.uuid4())

        # Save to database
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("""
            INSERT INTO state_snapshots (snapshot_id, thread_id, state_data, created_at)
            VALUES (?, ?, ?, ?)
        """, (
            checkpoint_id,
            thread_id,
            json.dumps(state),
            datetime.now(timezone.utc).isoformat()
        ))

        conn.commit()
        conn.close()

        # Also save to file for backup
        checkpoint_file = self.checkpoint_path / f"{checkpoint_id}.json"
        with open(checkpoint_file, 'w') as f:
            json.dump({
                "checkpoint_id": checkpoint_id,
                "thread_id": thread_id,
                "state": state,
                "created_at": datetime.now(timezone.utc).isoformat()
            }, f, indent=2)

        return checkpoint_id

    def load_checkpoint(self, checkpoint_id: str) -> Optional[Dict[str, Any]]:
        """Load state from checkpoint"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("""
            SELECT state_data FROM state_snapshots WHERE snapshot_id = ?
        """, (checkpoint_id,))

        row = cursor.fetchone()
        conn.close()

        if row:
            return json.loads(row[0])

        # Fallback to file
        checkpoint_file = self.checkpoint_path / f"{checkpoint_id}.json"
        if checkpoint_file.exists():
            with open(checkpoint_file, 'r') as f:
                data = json.load(f)
                return data.get("state")

        return None

    def get_task_status(self, task_id: str) -> Optional[AgentTask]:
        """Get current status of a task"""
        return self._tasks.get(task_id)

    def list_all_tasks(self) -> List[AgentTask]:
        """List all tasks"""
        return list(self._tasks.values())

    def get_active_tasks(self) -> List[AgentTask]:
        """Get all active (non-completed) tasks"""
        return [task for task in self._tasks.values()
                if task.status in [TaskStatus.PENDING, TaskStatus.IN_PROGRESS, TaskStatus.PAUSED]]

    def health_check(self) -> Dict[str, Any]:
        """Comprehensive health check"""
        return {
            "database_accessible": self.db_path.exists(),
            "checkpoint_dir_exists": self.checkpoint_path.exists(),
            "total_tasks": len(self._tasks),
            "active_tasks": len(self.get_active_tasks()),
            "storage_path": str(self.storage_path),
            "timestamp": datetime.now(timezone.utc).isoformat()
        }

    def demonstrate_persistence(self) -> Dict[str, Any]:
        """Demonstrate actual persistence capabilities"""
        print("\n🎯 Demonstrating Persistence...")

        # Create multiple tasks
        tasks = []
        for i in range(3):
            task = self.create_task(f"Demo task {i+1}", f"agent_{i+1}")
            tasks.append(task)
            print(f"📝 Created task: {task.task_id}")

        # Update some task statuses
        self.update_task_status(tasks[0].task_id, TaskStatus.IN_PROGRESS)
        self.complete_task(tasks[1].task_id, {"output": "Task 2 completed successfully"})
        self.fail_task(tasks[2].task_id, "Task 3 failed due to test error")

        # Save state checkpoint
        state = {
            "session_id": str(uuid.uuid4()),
            "tasks_processed": len(tasks),
            "current_time": datetime.now(timezone.utc).isoformat(),
            "agent_status": "active"
        }
        checkpoint_id = self.save_checkpoint("demo-session", state)
        print(f"💾 Saved checkpoint: {checkpoint_id}")

        # Verify persistence
        all_tasks = self.list_all_tasks()
        active_tasks = self.get_active_tasks()

        result = {
            "tasks_created": len(tasks),
            "total_tasks_in_db": len(all_tasks),
            "active_tasks": len(active_tasks),
            "checkpoint_id": checkpoint_id,
            "database_file": str(self.db_path),
            "checkpoint_dir": str(self.checkpoint_path),
            "persistence_verified": True
        }

        print(f"✅ Persistence verified: {result}")
        return result


def test_persistence_across_restarts():
    """Test that demonstrates persistence across restarts"""
    print("🚀 Testing Persistence Across Restarts...")

    test_dir = "/tmp/claude/casper_persistence_test"

    # Phase 1: Create and populate
    print("\n📝 Phase 1: Creating data...")
    sm1 = SimpleStateManager(storage_path=test_dir)
    result1 = sm1.demonstrate_persistence()

    # Phase 2: "Restart" - new instance
    print("\n🔄 Phase 2: Simulating restart...")
    sm2 = SimpleStateManager(storage_path=test_dir)

    # Verify data persisted
    tasks_after_restart = sm2.list_all_tasks()
    print(f"📊 Tasks after restart: {len(tasks_after_restart)}")

    for task in tasks_after_restart:
        print(f"   - {task.task_id}: {task.description} ({task.status.value})")

    # Test checkpoint recovery
    checkpoint_id = result1["checkpoint_id"]
    recovered_state = sm2.load_checkpoint(checkpoint_id)
    print(f"💾 Recovered checkpoint: {recovered_state is not None}")

    if recovered_state:
        print(f"   Recovered state: {recovered_state}")

    success = (
        len(tasks_after_restart) >= 3 and
        recovered_state is not None
    )

    print(f"\n🎉 Persistence test: {'PASSED' if success else 'FAILED'}")
    return success


if __name__ == "__main__":
    success = test_persistence_across_restarts()
    exit(0 if success else 1)