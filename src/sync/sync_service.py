"""Envoi des alertes SQLite dans un worker separe de la collecte."""

import json
import os
import threading

import requests

from src.storage.event_repository import (
    delete_alert,
    get_pending_alerts,
    schedule_retry,
)

API_URL = os.environ.get("GML_API_URL", "")
API_TOKEN = os.environ.get("GML_API_TOKEN", "")
STOP_EVENT = threading.Event()

# Variables uniquement utilisees pour la demonstration de panne 4G.
DEMO_MODE = True
NETWORK_AVAILABLE = False
FIRST_FAILURE = threading.Event()


def send_alert(alert_id, payload):
    if DEMO_MODE:
        if not NETWORK_AVAILABLE:
            raise requests.ConnectionError("4G coupee")
        print("\n[ENVOI] Alerte envoyee au serveur simule")
        print("[ACK]   Reception confirmee")
        return

    with requests.post(
        API_URL,
        json=json.loads(payload),
        headers={
            "Authorization": f"Bearer {API_TOKEN}",
            "Idempotency-Key": alert_id,
        },
        timeout=(3, 10),
    ) as response:
        if not 200 <= response.status_code < 300:
            raise requests.HTTPError(f"HTTP {response.status_code}")


def network_worker():
    """Relire SQLite, reessayer apres panne, supprimer apres succes."""
    while not STOP_EVENT.is_set():
        pending_alerts = get_pending_alerts()
        if not pending_alerts:
            STOP_EVENT.wait(0.2)
            continue

        for alert_id, payload, attempts in pending_alerts:
            try:
                send_alert(alert_id, payload)
            except requests.RequestException:
                delay = schedule_retry(alert_id, attempts)
                print(f"[RETRY] Envoi impossible -> nouvel essai dans {delay} s")
                FIRST_FAILURE.set()
            else:
                delete_alert(alert_id)
                print("[SQLITE] Alerte supprimee apres confirmation")
