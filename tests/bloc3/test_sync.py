import threading

import requests

import src.storage.event_repository as database
import src.sync.sync_service as network


def test_network_failure_keeps_event(tmp_path, monkeypatch):
    monkeypatch.setattr(database, "DB_PATH", str(tmp_path / "events.db"))
    database.initialize_database()
    database.save_alert({"acc_y": -3.45, "timestamp": 1})
    monkeypatch.setattr(network, "STOP_EVENT", threading.Event())
    monkeypatch.setattr(network, "FIRST_FAILURE", threading.Event())

    def failing_sender(_alert_id, _payload):
        network.STOP_EVENT.set()
        raise requests.ConnectionError("offline")

    monkeypatch.setattr(network, "send_alert", failing_sender)
    network.network_worker()

    assert database.pending_count() == 1
    assert network.FIRST_FAILURE.is_set()


def test_network_recovery_syncs_event(tmp_path, monkeypatch):
    monkeypatch.setattr(database, "DB_PATH", str(tmp_path / "events.db"))
    database.initialize_database()
    alert_id = database.save_alert({"acc_y": -3.45, "timestamp": 1})
    monkeypatch.setattr(network, "STOP_EVENT", threading.Event())
    monkeypatch.setattr(network, "FIRST_FAILURE", threading.Event())
    sent = []

    def sender(received_id, _payload):
        sent.append(received_id)
        network.STOP_EVENT.set()

    monkeypatch.setattr(network, "send_alert", sender)
    network.network_worker()

    assert sent == [alert_id]
    assert database.pending_count() == 0
