import threading

import requests

import src.storage.event_repository as database
import src.sync.sync_service as network
from src.domain.telemetry_event import TelemetryEvent


def test_network_failure_keeps_event(tmp_path, monkeypatch):
    monkeypatch.setattr(database, "DB_PATH", str(tmp_path / "events.db"))
    database.initialize_database()
    database.save_alert(TelemetryEvent.harsh_braking(-3.45, 1.0))

    stop_event = threading.Event()
    def failing_sender(_alert_id, _payload):
        stop_event.set()
        raise requests.ConnectionError("offline")

    network.network_worker(
        sender=failing_sender,
        stop_event=stop_event,
    )

    assert database.pending_count() == 1


def test_network_recovery_syncs_event(tmp_path, monkeypatch):
    monkeypatch.setattr(database, "DB_PATH", str(tmp_path / "events.db"))
    database.initialize_database()
    alert_id = database.save_alert(TelemetryEvent.harsh_braking(-3.45, 1.0))

    stop_event = threading.Event()
    sent = []

    def sender(received_id, _payload):
        sent.append(received_id)
        stop_event.set()

    network.network_worker(sender=sender, stop_event=stop_event)

    assert sent == [alert_id]
    assert database.pending_count() == 0
    assert database.synced_count() == 1
