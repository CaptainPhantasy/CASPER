"""SQLite-backed run, event, and checkpoint persistence."""

from __future__ import annotations

import json
import sqlite3
import time
from pathlib import Path
from typing import Any, Optional

from .models import RunEvent, RunState


class RunStore:
    def __init__(self, state_root: Path | str) -> None:
        self.root = Path(state_root).expanduser().resolve()
        self.root.mkdir(parents=True, exist_ok=True, mode=0o700)
        self.path = self.root / "runs.sqlite3"
        self._initialize()

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.path)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        connection.execute("PRAGMA journal_mode = WAL")
        return connection

    def _initialize(self) -> None:
        with self._connect() as connection:
            connection.executescript("""
                CREATE TABLE IF NOT EXISTS runs (
                    run_id TEXT PRIMARY KEY,
                    objective TEXT NOT NULL,
                    status TEXT NOT NULL,
                    state_json TEXT NOT NULL,
                    created_at REAL NOT NULL,
                    updated_at REAL NOT NULL
                );
                CREATE TABLE IF NOT EXISTS events (
                    run_id TEXT NOT NULL,
                    sequence INTEGER NOT NULL,
                    type TEXT NOT NULL,
                    payload_json TEXT NOT NULL,
                    created_at REAL NOT NULL,
                    PRIMARY KEY (run_id, sequence),
                    FOREIGN KEY (run_id) REFERENCES runs(run_id) ON DELETE CASCADE
                );
                CREATE TABLE IF NOT EXISTS checkpoints (
                    run_id TEXT NOT NULL,
                    name TEXT NOT NULL,
                    state_json TEXT NOT NULL,
                    created_at REAL NOT NULL,
                    PRIMARY KEY (run_id, name),
                    FOREIGN KEY (run_id) REFERENCES runs(run_id) ON DELETE CASCADE
                );
            """)

    def save(self, state: RunState) -> RunState:
        state.updated_at = time.time()
        payload = json.dumps(state.to_dict(), sort_keys=True)
        with self._connect() as connection:
            connection.execute(
                """INSERT INTO runs(run_id, objective, status, state_json, created_at, updated_at)
                   VALUES (?, ?, ?, ?, ?, ?)
                   ON CONFLICT(run_id) DO UPDATE SET
                     objective=excluded.objective, status=excluded.status,
                     state_json=excluded.state_json, updated_at=excluded.updated_at""",
                (state.run_id, state.objective, state.status.value, payload, state.created_at, state.updated_at),
            )
        return state

    def load(self, run_id: str) -> Optional[RunState]:
        with self._connect() as connection:
            row = connection.execute("SELECT state_json FROM runs WHERE run_id = ?", (run_id,)).fetchone()
        return RunState.from_dict(json.loads(row["state_json"])) if row else None

    def list_runs(self, limit: int = 50) -> list[dict[str, Any]]:
        with self._connect() as connection:
            rows = connection.execute(
                "SELECT run_id, objective, status, created_at, updated_at FROM runs ORDER BY updated_at DESC LIMIT ?",
                (max(1, min(limit, 500)),),
            ).fetchall()
        return [dict(row) for row in rows]

    def append_event(self, event: RunEvent) -> RunEvent:
        with self._connect() as connection:
            connection.execute(
                "INSERT INTO events(run_id, sequence, type, payload_json, created_at) VALUES (?, ?, ?, ?, ?)",
                (event.run_id, event.sequence, event.type, json.dumps(event.payload, sort_keys=True), event.created_at),
            )
        return event

    def events(self, run_id: str) -> list[RunEvent]:
        with self._connect() as connection:
            rows = connection.execute(
                "SELECT sequence, type, payload_json, created_at FROM events WHERE run_id = ? ORDER BY sequence",
                (run_id,),
            ).fetchall()
        return [RunEvent(run_id, row["sequence"], row["type"], json.loads(row["payload_json"]), row["created_at"]) for row in rows]

    def checkpoint(self, state: RunState, name: str) -> None:
        if not name or not name.replace("-", "").replace("_", "").isalnum():
            raise ValueError("checkpoint names must be non-empty and filesystem-safe")
        with self._connect() as connection:
            connection.execute(
                """INSERT INTO checkpoints(run_id, name, state_json, created_at) VALUES (?, ?, ?, ?)
                   ON CONFLICT(run_id, name) DO UPDATE SET state_json=excluded.state_json, created_at=excluded.created_at""",
                (state.run_id, name, json.dumps(state.to_dict(), sort_keys=True), time.time()),
            )

    def restore_checkpoint(self, run_id: str, name: str) -> Optional[RunState]:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT state_json FROM checkpoints WHERE run_id = ? AND name = ?", (run_id, name),
            ).fetchone()
        return RunState.from_dict(json.loads(row["state_json"])) if row else None
