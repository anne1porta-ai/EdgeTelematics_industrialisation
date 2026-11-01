"""Envoi des alertes SQLite : les fonctions et le try/except/else des PPT."""

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

# Ces variables servent uniquement a la demonstration de panne 4G.
DEMO_MODE = True
NETWORK_AVAILABLE = False
FIRST_FAILURE = threading.Event()


def send_alert(alert_id, payload):
    """Simuler la 4G ou envoyer la meme alerte a l'API."""
    if DEMO_MODE:
        if not NETWORK_AVAILABLE:
            raise requests.ConnectionError("4G coupee")
        print(f"[RECU] Alerte {alert_id} recue par le serveur simule.")
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
    """Relire SQLite, envoyer, puis supprimer uniquement apres succes."""
    while not STOP_EVENT.is_set():
        pending_alerts = get_pending_alerts()
        if not pending_alerts:
            STOP_EVENT.wait(0.2)
            continue

        for alert_id, payload, attempts in pending_alerts:
            try:
                send_alert(alert_id, payload)
            except requests.RequestException:
                schedule_retry(alert_id, attempts)
                print(f"[ECHEC] Alerte {alert_id} conservee ; nouvel essai programme.")
                FIRST_FAILURE.set()
            else:
                delete_alert(alert_id)
                print(f"[SUPPRIMEE] Alerte {alert_id} retiree de SQLite apres succes.")
