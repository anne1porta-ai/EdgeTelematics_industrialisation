"""Fonctions SQLite du POC : stocker les alertes et les reprendre apres une panne."""

import json
import sqlite3
import time
import uuid
from contextlib import closing

DB_PATH = "greenmove.db"
MAX_RETRY_DELAY = 300


def connect_database():
    return sqlite3.connect(DB_PATH)


def initialize_database():
    with closing(connect_database()) as connection:
        connection.execute("PRAGMA journal_mode = WAL")
        connection.execute("""
            CREATE TABLE IF NOT EXISTS pending_alerts (
                alert_id TEXT PRIMARY KEY,
                payload TEXT NOT NULL,
                created_at REAL NOT NULL,
                attempts INTEGER DEFAULT 0,
                next_attempt_at REAL DEFAULT 0
            )
        """)
        connection.commit()


def save_alert(sample):
    """Enregistrer l'alerte avant toute tentative reseau."""
    alert_id = str(uuid.uuid4())
    captured_at = time.time()
    payload = {"event_type": "harsh_braking", **sample}
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

    print("\n[ALERTE] Freinage detecte")
    print("[SQLITE] Alerte sauvegardee localement avant l'envoi")
    return alert_id


def get_pending_alerts(limit=20):
    with closing(connect_database()) as connection:
        rows = connection.execute(
            """
            SELECT alert_id, payload, attempts FROM pending_alerts
            WHERE next_attempt_at <= ?
            ORDER BY created_at LIMIT ?
            """,
            (time.time(), limit),
        ).fetchall()
    return rows


def schedule_retry(alert_id, attempts):
    attempts = attempts + 1
    delay = min(2**attempts, MAX_RETRY_DELAY)
    next_attempt_at = time.time() + delay
    with closing(connect_database()) as connection:
        connection.execute(
            """
            UPDATE pending_alerts SET attempts = ?, next_attempt_at = ?
            WHERE alert_id = ?
            """,
            (attempts, next_attempt_at, alert_id),
        )
        connection.commit()
    return delay


def delete_alert(alert_id):
    with closing(connect_database()) as connection:
        connection.execute("DELETE FROM pending_alerts WHERE alert_id = ?", (alert_id,))
        connection.commit()


def pending_count():
    with closing(connect_database()) as connection:
        row = connection.execute("SELECT COUNT(*) FROM pending_alerts").fetchone()
    return row[0]
