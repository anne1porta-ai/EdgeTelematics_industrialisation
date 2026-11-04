"""Envoyer les alertes SQLite sans bloquer la collecte des capteurs."""

import json
import os
import threading

import requests

from src.storage.event_repository import (
    get_pending_alerts,
    mark_alert_synced,
    schedule_retry,
)
from src.sync.circuit_breaker import HALF_OPEN, OPEN, CircuitBreaker

API_URL = os.environ.get("GML_API_URL", "")
API_TOKEN = os.environ.get("GML_API_TOKEN", "")
STOP_EVENT = threading.Event()


def configure_api(url, token=None):
    """Choisir l'API distante et, si besoin, son jeton d'authentification."""
    global API_URL, API_TOKEN
    API_URL = url
    if token is not None:
        API_TOKEN = token


def send_alert(alert_id, payload):
    """Envoyer une alerte avec un timeout et une clé d'idempotence stable."""
    if not API_URL:
        raise ValueError("L'URL de l'API n'est pas configurée.")

    headers = {
        "Authorization": f"Bearer {API_TOKEN}",
        "Idempotency-Key": alert_id,
    }

    with requests.post(
        API_URL,
        json=json.loads(payload),
        headers=headers,
        timeout=(3, 10),
    ) as response:
        if response.status_code < 200 or response.status_code >= 300:
            raise requests.HTTPError(f"HTTP {response.status_code}")


def network_worker(sender=None, stop_event=None, circuit_breaker=None):
    """Envoyer les alertes avec retry, backoff et circuit breaker."""
    send = sender or send_alert

    if stop_event is None:
        stop = STOP_EVENT
    else:
        stop = stop_event

    if circuit_breaker is None:
        breaker = CircuitBreaker()
    else:
        breaker = circuit_breaker

    open_message_shown = False

    while not stop.is_set():
        pending_alerts = get_pending_alerts()

        if not pending_alerts:
            stop.wait(0.2)
            continue

        for alert_id, payload, attempts in pending_alerts:
            # Le circuit OPEN suspend les appels, mais la collecte reste active.
            if not breaker.allow_request():
                if not open_message_shown:
                    print("[CIRCUIT] OPEN - appels réseau suspendus temporairement.")
                    open_message_shown = True
                stop.wait(0.2)
                break

            if breaker.state == HALF_OPEN:
                print("[CIRCUIT] HALF_OPEN - essai de reprise du réseau.")

            open_message_shown = False

            try:
                send(alert_id, payload)
            except requests.RequestException:
                # L'alerte reste dans SQLite. Seule la date du prochain essai change.
                breaker.record_failure()
                delay = schedule_retry(alert_id, attempts)
                print(f"[ECHEC] Alerte {alert_id} conservée dans SQLite.")
                print(f"[RETRY] Nouvelle tentative dans {delay} s.")

                if breaker.state == OPEN:
                    print(
                        "[CIRCUIT] OPEN après "
                        f"{breaker.failure_count} échecs consécutifs."
                    )
                    break
            else:
                was_half_open = breaker.state == HALF_OPEN
                breaker.record_success()
                mark_alert_synced(alert_id)

                if was_half_open:
                    print("[CIRCUIT] CLOSED - le réseau répond de nouveau.")

                print(
                    f"[SYNCHRONISEE] Alerte {alert_id} archivée avec synced=1 "
                    "et retirée de la file."
                )
