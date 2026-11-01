"""Six preuves de non-regression directement reliees a la crise du pilote."""

import json
import threading
from contextlib import closing

import pytest
import requests

import run_demo
import src.storage.event_repository as database
import src.sync.sync_service as network


@pytest.fixture(autouse=True)
def isolated_crisis_test(tmp_path, monkeypatch):
    """Chaque test travaille avec sa propre base SQLite et ses propres events."""
    monkeypatch.setattr(database, "DB_PATH", str(tmp_path / "crisis.db"))
    database.initialize_database()
    monkeypatch.setattr(network, "STOP_EVENT", threading.Event())
    monkeypatch.setattr(network, "FIRST_FAILURE", threading.Event())
    run_demo.recent_samples.clear()
    yield
    run_demo.recent_samples.clear()


def _one_braking_sample():
    return [{"timestamp": 1, "acc_y": -3.45}]


def _stored_row(alert_id):
    with closing(database.connect_database()) as connection:
        return connection.execute(
            "SELECT alert_id, payload, attempts, next_attempt_at "
            "FROM pending_alerts WHERE alert_id = ?",
            (alert_id,),
        ).fetchone()


def test_memory_buffer_is_bounded():
    """Crise RAM : 1 000 mesures ne doivent jamais faire depasser 600 en memoire."""
    for index in range(1000):
        run_demo.recent_samples.append({"timestamp": index, "acc_y": 0.0})

    assert run_demo.recent_samples.maxlen == 600
    assert len(run_demo.recent_samples) == 600
    assert run_demo.recent_samples[0]["timestamp"] == 400


def test_acquisition_loop_has_no_network_call(tmp_path, monkeypatch):
    """Crise 4G : la boucle capteur doit fonctionner sans aucun appel HTTP."""

    def forbidden_post(*_args, **_kwargs):
        raise AssertionError("La collecte ne doit jamais appeler le reseau")

    monkeypatch.setattr(requests, "post", forbidden_post)

    run_demo.acquisition_loop(
        output_file=str(tmp_path / "score.json"), samples=_one_braking_sample()
    )

    assert database.pending_count() == 1


def test_critical_alert_is_persisted_before_network(tmp_path, monkeypatch):
    """Crise perte de donnees : l'alerte doit exister dans SQLite avant l'envoi."""
    network_calls = []

    def forbidden_send(*args, **kwargs):
        network_calls.append((args, kwargs))
        raise AssertionError("Aucun envoi ne doit avoir lieu pendant l'acquisition")

    monkeypatch.setattr(network, "send_alert", forbidden_send)

    run_demo.acquisition_loop(
        output_file=str(tmp_path / "score.json"), samples=_one_braking_sample()
    )

    pending = database.get_pending_alerts()
    assert len(pending) == 1
    alert_id, payload, attempts = pending[0]
    assert json.loads(payload)["alert_id"] == alert_id
    assert attempts == 0
    assert network_calls == []


def test_failed_send_keeps_alert_and_schedules_retry(monkeypatch):
    """Crise reseau : un echec conserve l'alerte et programme le prochain essai."""
    alert_id = database.save_alert({"timestamp": 1, "acc_y": -3.45})

    def offline_sender(_alert_id, _payload):
        network.STOP_EVENT.set()
        raise requests.ConnectionError("4G coupee")

    monkeypatch.setattr(network, "send_alert", offline_sender)
    network.network_worker()

    row = _stored_row(alert_id)
    assert row is not None
    assert row[2] == 1
    assert row[3] > 0


def test_successful_send_removes_alert(monkeypatch):
    """Crise perte de donnees : la purge n'arrive qu'apres un envoi reussi."""
    alert_id = database.save_alert({"timestamp": 1, "acc_y": -3.45})
    sent = []

    def successful_sender(current_alert_id, payload):
        sent.append((current_alert_id, json.loads(payload)))
        network.STOP_EVENT.set()

    monkeypatch.setattr(network, "send_alert", successful_sender)
    network.network_worker()

    assert sent[0][0] == alert_id
    assert database.pending_count() == 0
    assert _stored_row(alert_id) is None


def test_http_client_uses_https_auth_idempotency_and_timeouts(monkeypatch):
    """Crise appel bloquant/doublon : HTTPS, auth, idempotence et timeout sont imposes."""

    class Response:
        status_code = 204

        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return False

    calls = []

    def fake_post(url, **kwargs):
        calls.append((url, kwargs))
        return Response()

    monkeypatch.setattr(network, "DEMO_MODE", False)
    monkeypatch.setattr(network, "API_URL", "https://api.example.invalid/alerts")
    monkeypatch.setattr(network, "API_TOKEN", "demo-token")
    monkeypatch.setattr(network.requests, "post", fake_post)

    alert_id = "demo-alert-123"
    payload = json.dumps(
        {
            "event_type": "harsh_braking",
            "alert_id": alert_id,
            "timestamp": 1,
            "acc_y": -3.45,
        }
    )

    network.send_alert(alert_id, payload)

    url, request = calls[0]
    assert url.startswith("https://")
    assert request["headers"]["Authorization"] == "Bearer demo-token"
    assert request["headers"]["Idempotency-Key"] == alert_id
    assert request["timeout"] == (3, 10)
    assert request["json"]["alert_id"] == alert_id
