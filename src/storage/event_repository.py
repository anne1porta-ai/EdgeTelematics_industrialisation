"""Fonctions SQLite du POC : stocker les alertes et les reprendre après une panne."""

import json
import sqlite3
import time
import uuid
from contextlib import closing

DB_PATH = "greenmove.db"
MAX_RETRY_DELAY = 300


def connect_database():
    """Ouvrir une connexion à la base locale."""
    return sqlite3.connect(DB_PATH)


def initialize_database():
    """Préparer la file persistante sans modifier les anciennes tables."""
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
    """Créer l'identité une seule fois et enregistrer avant tout appel HTTP."""
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
    print(f"[STOCKEE] Alerte {alert_id} enregistree dans SQLite.")
    return alert_id


def get_pending_alerts(limit=20):
    """Lire les alertes dont le délai de reprise est écoulé."""
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
    """Espacer les essais : 2, 4, 8 secondes, jusqu'à 300 secondes."""
    attempts = attempts + 1
    next_attempt_at = time.time() + min(2**attempts, MAX_RETRY_DELAY)
    with closing(connect_database()) as connection:
        connection.execute(
            """
            UPDATE pending_alerts SET attempts = ?, next_attempt_at = ?
            WHERE alert_id = ?
            """,
            (attempts, next_attempt_at, alert_id),
        )
        connection.commit()


def delete_alert(alert_id):
    """Supprimer l'alerte après la confirmation de son envoi."""
    with closing(connect_database()) as connection:
        connection.execute("DELETE FROM pending_alerts WHERE alert_id = ?", (alert_id,))
        connection.commit()


def pending_count():
    """Compter toutes les alertes conservées, y compris les essais différés."""
    with closing(connect_database()) as connection:
        row = connection.execute("SELECT COUNT(*) FROM pending_alerts").fetchone()
    return row[0]
