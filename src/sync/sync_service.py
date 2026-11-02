"""Envoi des alertes SQLite dans un worker separe de la collecte."""

import json
import os
import threading
from collections.abc import Callable

import requests

from src.storage.event_repository import (
    get_pending_alerts,
    mark_alert_synced,
    schedule_retry,
)

API_URL = os.environ.get("GML_API_URL", "")
API_TOKEN = os.environ.get("GML_API_TOKEN", "")
STOP_EVENT = threading.Event()

Sender = Callable[[str, str], None]


def send_alert(alert_id: str, payload: str) -> None:
    """Envoyer une alerte a l'API avec timeout et cle d'idempotence."""
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


def network_worker(
    sender: Sender | None = None,
    stop_event: threading.Event | None = None,
) -> None:
    """Relire SQLite, envoyer, historiser puis retirer de la file active."""
    send = sender or send_alert
    stop = stop_event if stop_event is not None else STOP_EVENT

    while not stop.is_set():
        pending_alerts = get_pending_alerts()
        if not pending_alerts:
            stop.wait(0.2)
            continue

        for alert_id, payload, attempts in pending_alerts:
            try:
                send(alert_id, payload)
            except requests.RequestException:
                delay = schedule_retry(alert_id, attempts)
                print(f"[ECHEC] Alerte {alert_id} conservee dans SQLite.")
                print(f"[RETRY] Nouvelle tentative dans {delay} s.")
            else:
                mark_alert_synced(alert_id)
                print(
                    f"[SYNCHRONISEE] Alerte {alert_id} archivee avec synced=1 "
                    "et retiree de la file."
                )
