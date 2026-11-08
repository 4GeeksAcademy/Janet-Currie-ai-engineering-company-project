"""Ordered step records. A trace stores what ran, not the staff member's question."""

from __future__ import annotations

import json
import os
import sqlite3
import threading
from pathlib import Path


def store_paths() -> tuple[str, str]:
    """Checkpoint file and trace file. Tests can point both at temporary paths."""

    default_dir = Path(__file__).resolve().parents[2] / "data"
    data_dir = Path(os.environ.get("AGENT_DATA_DIR", default_dir))
    checkpoint = os.environ.get(
        "AGENT_CHECKPOINT_PATH", str(data_dir / "agent_checkpoints.sqlite")
    )
    trace = os.environ.get("AGENT_TRACE_PATH", str(data_dir / "agent_traces.sqlite"))
    Path(checkpoint).parent.mkdir(parents=True, exist_ok=True)
    Path(trace).parent.mkdir(parents=True, exist_ok=True)
    return checkpoint, trace


class MemoryTraceStore:
    """One store per test, so two runs cannot see each other's steps."""

    def __init__(self) -> None:
        self._events: dict[str, list[dict]] = {}

    def append(self, run_id: str, event: dict) -> None:
        self._events.setdefault(run_id, []).append(dict(event))

    def list(self, run_id: str) -> list[dict]:
        return [dict(event) for event in self._events.get(run_id, [])]


class SqliteTraceStore:
    """A small table beside the checkpoint file. Printing to the terminal is not the trace."""

    def __init__(self, path: str) -> None:
        self.path = path
        self._lock = threading.Lock()
        with self._connect() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS agent_trace (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    run_id TEXT NOT NULL,
                    position INTEGER NOT NULL,
                    node TEXT NOT NULL,
                    status TEXT NOT NULL,
                    passage_count INTEGER NOT NULL,
                    source_documents TEXT NOT NULL,
                    answer TEXT NOT NULL
                )
                """
            )

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.path, check_same_thread=False)
        connection.row_factory = sqlite3.Row
        return connection

    def append(self, run_id: str, event: dict) -> None:
        with self._lock, self._connect() as connection:
            position = connection.execute(
                "SELECT COALESCE(MAX(position), 0) + 1 FROM agent_trace WHERE run_id = ?",
                (run_id,),
            ).fetchone()[0]
            connection.execute(
                """
                INSERT INTO agent_trace (
                    run_id, position, node, status, passage_count, source_documents, answer
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    run_id,
                    position,
                    event["node"],
                    event["status"],
                    int(event["passage_count"]),
                    json.dumps(event["source_documents"]),
                    event.get("answer") or "",
                ),
            )

    def list(self, run_id: str) -> list[dict]:
        with self._lock, self._connect() as connection:
            rows = connection.execute(
                """
                SELECT run_id, node, status, passage_count, source_documents, answer
                FROM agent_trace
                WHERE run_id = ?
                ORDER BY position
                """,
                (run_id,),
            ).fetchall()
        return [
            {
                "run_id": row["run_id"],
                "node": row["node"],
                "status": row["status"],
                "passage_count": row["passage_count"],
                "source_documents": json.loads(row["source_documents"]),
                "answer": row["answer"],
            }
            for row in rows
        ]
