"""File SQLite persistante et historique des alertes synchronisees."""

import json
import sqlite3
import time
import uuid
from contextlib import closing
from typing import Any

from src.domain.telemetry_event import TelemetryEvent

DB_PATH = "greenmove.db"
MAX_RETRY_DELAY = 300


def connect_database() -> sqlite3.Connection:
    """Ouvrir une connexion a la base locale."""
    return sqlite3.connect(DB_PATH)


def initialize_database() -> None:
    """Creer la file d'attente et l'historique d'audit."""
    with closing(connect_database()) as connection:
        connection.execute("PRAGMA journal_mode = WAL")
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS pending_alerts (
                alert_id TEXT PRIMARY KEY,
                payload TEXT NOT NULL,
                created_at REAL NOT NULL,
                attempts INTEGER DEFAULT 0,
                next_attempt_at REAL DEFAULT 0
            )
            """
        )
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS event_history (
                alert_id TEXT PRIMARY KEY,
                event_type TEXT NOT NULL,
                payload TEXT NOT NULL,
                created_at REAL NOT NULL,
                synced INTEGER NOT NULL DEFAULT 1,
                synced_at REAL NOT NULL
            )
            """
        )
        connection.commit()


def save_alert(event: TelemetryEvent) -> str:
    """Donner un identifiant a l'alerte et la stocker avant le reseau."""
    alert_id = str(uuid.uuid4())
    captured_at = time.time()
    payload = event.to_payload()
    payload["alert_id"] = alert_id
    payload["captured_at"] = captured_at

    with closing(connect_database()) as connection:
        connection.execute(
            """
            INSERT INTO pending_alerts(alert_id, payload, created_at)
            VALUES (?, ?, ?)
            """,
            (alert_id, json.dumps(payload), captured_at),
        )
        connection.commit()

    print(f"[STOCKEE] Alerte {alert_id} enregistree dans SQLite.")
    return alert_id


def get_pending_alerts(limit: int = 20) -> list[tuple[str, str, int]]:
    """Lire les alertes dont le delai de reprise est ecoule."""
    with closing(connect_database()) as connection:
        rows = connection.execute(
            """
            SELECT alert_id, payload, attempts FROM pending_alerts
            WHERE next_attempt_at <= ?
            ORDER BY created_at LIMIT ?
            """,
            (time.time(), limit),
        ).fetchall()

    return [
        (str(alert_id), str(payload), int(attempts))
        for alert_id, payload, attempts in rows
    ]


def schedule_retry(alert_id: str, attempts: int) -> int:
    """Espacer les essais : 2, 4, 8 secondes, jusqu'a 300 secondes."""
    next_attempt = attempts + 1
    delay = min(2**next_attempt, MAX_RETRY_DELAY)
    next_attempt_at = time.time() + delay

    with closing(connect_database()) as connection:
        connection.execute(
            """
            UPDATE pending_alerts SET attempts = ?, next_attempt_at = ?
            WHERE alert_id = ?
            """,
            (next_attempt, next_attempt_at, alert_id),
        )
        connection.commit()

    return delay


def mark_alert_synced(alert_id: str) -> bool:
    """Archiver l'alerte avec synced=1 puis la retirer de la file active."""
    with closing(connect_database()) as connection, connection:
        row = connection.execute(
            """
            SELECT payload, created_at
            FROM pending_alerts
            WHERE alert_id = ?
            """,
            (alert_id,),
        ).fetchone()

        if row is None:
            return False

        payload_text, captured_at = row
        payload = json.loads(payload_text)
        event_type = str(payload.get("event_type", "unknown"))

        connection.execute(
            """
            INSERT OR REPLACE INTO event_history(
                alert_id,
                event_type,
                payload,
                created_at,
                synced,
                synced_at
            )
            VALUES (?, ?, ?, ?, 1, ?)
            """,
            (alert_id, event_type, payload_text, captured_at, time.time()),
        )
        connection.execute(
            "DELETE FROM pending_alerts WHERE alert_id = ?",
            (alert_id,),
        )

    return True


def pending_count() -> int:
    """Compter les alertes encore en attente."""
    with closing(connect_database()) as connection:
        row = connection.execute("SELECT COUNT(*) FROM pending_alerts").fetchone()
    return int(row[0])


def synced_count() -> int:
    """Compter les alertes envoyees conservees dans l'historique."""
    with closing(connect_database()) as connection:
        row = connection.execute(
            "SELECT COUNT(*) FROM event_history WHERE synced = 1"
        ).fetchone()
    return int(row[0])


def get_synced_events(limit: int = 100) -> list[dict[str, Any]]:
    """Lire l'historique des alertes synchronisees, plus recentes d'abord."""
    with closing(connect_database()) as connection:
        rows = connection.execute(
            """
            SELECT alert_id, event_type, payload, created_at, synced_at
            FROM event_history
            WHERE synced = 1
            ORDER BY synced_at DESC
            LIMIT ?
            """,
            (limit,),
        ).fetchall()

    return [
        {
            "alert_id": str(alert_id),
            "event_type": str(event_type),
            "payload": json.loads(payload),
            "captured_at": float(captured_at),
            "synced": 1,
            "synced_at": float(synced_at),
        }
        for alert_id, event_type, payload, captured_at, synced_at in rows
    ]
