"""Conserver les alertes localement avant leur envoi au serveur."""

import json
import sqlite3
import time
import uuid
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DB_PATH = str(PROJECT_ROOT / "greenmove.db")
MAX_RETRY_DELAY = 300


def configure_database(path):
    """Choisir le fichier SQLite utilisé par le projet."""
    global DB_PATH
    DB_PATH = str(Path(path))


def configure_retry_delay(max_delay):
    """Fixer le délai maximal entre deux tentatives d'envoi."""
    if max_delay < 1:
        raise ValueError("Le délai maximal doit être supérieur à zéro.")

    global MAX_RETRY_DELAY
    MAX_RETRY_DELAY = max_delay


def connect_database():
    """Ouvrir une connexion vers la base SQLite locale."""
    return sqlite3.connect(DB_PATH)


def initialize_database():
    """Créer la file d'attente et l'historique s'ils n'existent pas."""
    path = Path(DB_PATH)
    path.parent.mkdir(parents=True, exist_ok=True)

    connection = connect_database()
    try:
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
    finally:
        connection.close()


def save_alert(event):
    """Enregistrer l'événement avant tout appel réseau."""
    alert_id = str(uuid.uuid4())
    captured_at = time.time()

    payload = event.to_payload()
    payload["alert_id"] = alert_id
    payload["captured_at"] = captured_at
    payload_text = json.dumps(payload)

    connection = connect_database()
    try:
        connection.execute(
            """
            INSERT INTO pending_alerts(alert_id, payload, created_at)
            VALUES (?, ?, ?)
            """,
            (alert_id, payload_text, captured_at),
        )
        connection.commit()
    finally:
        connection.close()

    print(f"[STOCKEE] Alerte {alert_id} enregistrée dans SQLite.")
    return alert_id


def get_pending_alerts(limit=20):
    """Lire les alertes dont le délai avant le prochain essai est écoulé."""
    connection = connect_database()
    try:
        rows = connection.execute(
            """
            SELECT alert_id, payload, attempts
            FROM pending_alerts
            WHERE next_attempt_at <= ?
            ORDER BY created_at
            LIMIT ?
            """,
            (time.time(), limit),
        ).fetchall()
    finally:
        connection.close()

    alerts = []
    for alert_id, payload, attempts in rows:
        alerts.append((str(alert_id), str(payload), int(attempts)))
    return alerts


def schedule_retry(alert_id, attempts):
    """Programmer le prochain essai avec un délai de 2, 4, 8 secondes, etc."""
    next_attempt = attempts + 1
    delay = min(2 ** next_attempt, MAX_RETRY_DELAY)
    next_attempt_at = time.time() + delay

    connection = connect_database()
    try:
        connection.execute(
            """
            UPDATE pending_alerts
            SET attempts = ?, next_attempt_at = ?
            WHERE alert_id = ?
            """,
            (next_attempt, next_attempt_at, alert_id),
        )
        connection.commit()
    finally:
        connection.close()

    return delay


def mark_alert_synced(alert_id):
    """Archiver une alerte confirmée, puis la retirer de la file d'attente."""
    connection = connect_database()
    try:
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
        connection.commit()
        return True
    finally:
        connection.close()


def pending_count():
    """Compter les alertes qui attendent encore une confirmation du serveur."""
    connection = connect_database()
    try:
        row = connection.execute("SELECT COUNT(*) FROM pending_alerts").fetchone()
        return int(row[0])
    finally:
        connection.close()


def synced_count():
    """Compter les alertes confirmées et conservées dans l'historique."""
    connection = connect_database()
    try:
        row = connection.execute(
            "SELECT COUNT(*) FROM event_history WHERE synced = 1"
        ).fetchone()
        return int(row[0])
    finally:
        connection.close()


def get_synced_events(limit=100):
    """Lire les alertes synchronisées, des plus récentes aux plus anciennes."""
    connection = connect_database()
    try:
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
    finally:
        connection.close()

    events = []
    for alert_id, event_type, payload, captured_at, synced_at in rows:
        event = {
            "alert_id": str(alert_id),
            "event_type": str(event_type),
            "payload": json.loads(payload),
            "captured_at": float(captured_at),
            "synced": 1,
            "synced_at": float(synced_at),
        }
        events.append(event)

    return events
