"""SQLite repository used to persist telemetry events locally.

The repository replaces the unbounded in-memory buffer from the initial POC.
Events remain stored locally while connectivity is unavailable and are marked
as synchronized only after a successful transmission.
"""

import json
import sqlite3
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path
from typing import Iterable

from src.domain.telemetry_event import TelemetryEvent


class EventRepository:
    """Persist telemetry events and track their synchronization state."""

    def __init__(
        self,
        db_path: str | Path = "greenmove_events.db",
    ) -> None:
        self.db_path = str(db_path)
        self._initialize()

    @contextmanager
    def _connection(
        self,
    ) -> Iterator[sqlite3.Connection]:
        """Open and always close a SQLite connection safely.

        Explicit closure is important on Windows because an open connection
        may keep the database file locked after the operation has completed.
        """
        connection = sqlite3.connect(
            self.db_path
        )
        connection.row_factory = sqlite3.Row

        try:
            with connection:
                yield connection
        finally:
            connection.close()

    def _initialize(self) -> None:
        """Create the event table when the database is first used."""
        with self._connection() as connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    event_type TEXT NOT NULL,
                    payload TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    synced INTEGER NOT NULL DEFAULT 0
                )
                """
            )

    def add(
        self,
        event: TelemetryEvent,
    ) -> int:
        """Persist an event as pending and return its database identifier."""
        with self._connection() as connection:
            cursor = connection.execute(
                """
                INSERT INTO events(
                    event_type,
                    payload,
                    created_at,
                    synced
                )
                VALUES (?, ?, ?, 0)
                """,
                (
                    event.event_type,
                    json.dumps(event.payload),
                    event.created_at,
                ),
            )

            return int(cursor.lastrowid)

    def pending(
        self,
        limit: int = 100,
    ) -> list[dict]:
        """Return unsynchronized events, oldest first.

        A limit is used so synchronization happens in bounded batches rather
        than loading the whole local database in memory.
        """
        with self._connection() as connection:
            rows = connection.execute(
                """
                SELECT
                    id,
                    event_type,
                    payload,
                    created_at
                FROM events
                WHERE synced = 0
                ORDER BY id
                LIMIT ?
                """,
                (limit,),
            ).fetchall()

        return [
            {
                "id": int(row["id"]),
                "event_type": row["event_type"],
                "payload": json.loads(
                    row["payload"]
                ),
                "created_at": row["created_at"],
            }
            for row in rows
        ]

    def mark_synced(
        self,
        event_ids: Iterable[int],
    ) -> None:
        """Mark successfully transmitted events as synchronized."""
        ids = list(event_ids)

        if not ids:
            return

        placeholders = ",".join(
            "?" for _ in ids
        )

        with self._connection() as connection:
            connection.execute(
                f"""
                UPDATE events
                SET synced = 1
                WHERE id IN ({placeholders})
                """,
                ids,
            )

    def pending_count(self) -> int:
        """Return the number of events still waiting for synchronization."""
        with self._connection() as connection:
            row = connection.execute(
                """
                SELECT COUNT(*) AS count
                FROM events
                WHERE synced = 0
                """
            ).fetchone()

        return int(row["count"])