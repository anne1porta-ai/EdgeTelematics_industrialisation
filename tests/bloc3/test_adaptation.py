"""Neuf verifications des ajouts du POC, sans serveur externe."""

import json
import socket
import threading
from contextlib import closing
from uuid import UUID

import pytest
import requests

import src.storage.event_repository as database
import src.sync.sync_service as network
from run_demo import acquisition_loop, collect_events, recent_samples
from src.safety.run_safety import run_safety_engine
from src.safety.safety_engine import analyze_accelerometer_stream


@pytest.fixture(autouse=True)
def local_database(tmp_path, monkeypatch):
    monkeypatch.setattr(database, "DB_PATH", str(tmp_path / "events.db"))
    database.initialize_database()
    monkeypatch.setattr(network, "STOP_EVENT", threading.Event())
    monkeypatch.setattr(network, "FIRST_FAILURE", threading.Event())


def add_alert(timestamp=1):
    return database.save_alert({"timestamp": timestamp, "acc_y": -3.45})


def stored_alerts():
    """Read even postponed alerts to check their durable state."""
    with closing(database.connect_database()) as connection:
        rows = connection.execute(
            "SELECT alert_id, payload, attempts, next_attempt_at FROM pending_alerts"
        ).fetchall()
    return {
        alert_id: {
            "payload": json.loads(payload),
            "attempts": attempts,
            "next_attempt_at": next_attempt_at,
        }
        for alert_id, payload, attempts, next_attempt_at in rows
    }


def test_queue_keeps_identity_after_reopening_and_deletes_only_selected_alert():
    first = add_alert(1)
    second = add_alert(2)
    original = stored_alerts()
    identifiers = [UUID(alert_id) for alert_id in (first, second)]
    assert len(set(identifiers)) == 2
    assert all(identifier.version == 4 for identifier in identifiers)
    for alert_id, timestamp in ((first, 1), (second, 2)):
        payload = original[alert_id]["payload"]
        assert payload["alert_id"] == alert_id
        assert payload["timestamp"] == timestamp
        assert payload["acc_y"] == -3.45
        assert isinstance(payload["captured_at"], float)
        assert payload["captured_at"] > 0

    database.initialize_database()
    assert stored_alerts() == original
    database.delete_alert(first)
    assert stored_alerts() == {second: original[second]}
    assert database.pending_count() == 1


def test_worker_commits_each_ack_and_schedules_failed_alert_without_loss(monkeypatch):
    first, second, third = [add_alert(timestamp) for timestamp in (1, 2, 3)]
    original_payload = stored_alerts()[second]["payload"]
    calls = []

    def sender(alert_id, payload):
        calls.append(alert_id)
        assert stored_alerts()[alert_id]["payload"] == json.loads(payload)
        if alert_id == second:
            assert first not in stored_alerts()
            raise requests.ConnectionError("offline")
        if alert_id == third:
            network.STOP_EVENT.set()

    monkeypatch.setattr(network, "send_alert", sender)
    network.network_worker()
    assert calls == [first, second, third]
    assert network.FIRST_FAILURE.is_set()
    remaining = stored_alerts()
    assert set(remaining) == {second}
    assert remaining[second]["payload"] == original_payload
    assert remaining[second]["attempts"] == 1
    assert remaining[second]["next_attempt_at"] > 0
    database.initialize_database()
    assert stored_alerts() == remaining


def test_retry_backoff_is_persisted_and_only_due_alerts_are_selected(monkeypatch):
    clock = [1_000.0]

    def now():
        return clock[0]

    monkeypatch.setattr(database.time, "time", now)
    alert_id = add_alert()
    payload = database.get_pending_alerts()[0][1]
    for attempts, delay in enumerate((2, 4, 8, 16, 32, 64, 128, 256, 300, 300)):
        assert database.get_pending_alerts() == [(alert_id, payload, attempts)]
        database.schedule_retry(alert_id, attempts)
        deadline = clock[0] + delay
        saved = stored_alerts()[alert_id]
        assert saved["attempts"] == attempts + 1
        assert saved["next_attempt_at"] == deadline
        database.initialize_database()
        assert database.pending_count() == 1
        clock[0] = deadline - 0.001
        assert database.get_pending_alerts() == []
        clock[0] = deadline
        assert database.get_pending_alerts() == [(alert_id, payload, attempts + 1)]

    database.delete_alert(alert_id)
    next_id = add_alert(2)
    database.schedule_retry(next_id, 0)
    assert stored_alerts()[next_id]["next_attempt_at"] == clock[0] + 2


def test_background_network_does_not_block_business_persistence(tmp_path, monkeypatch):
    network_started = threading.Event()
    release_network = threading.Event()
    collected_during_outage = threading.Event()
    business_finished = threading.Event()
    errors = []
    report = tmp_path / "stream_report.json"

    def blocked_sender(_alert_id, _payload):
        network_started.set()
        if not release_network.wait(timeout=3):
            raise requests.Timeout("Test duration guard")

    def run_network():
        try:
            network.network_worker()
        except (AssertionError, OSError, RuntimeError, ValueError, requests.RequestException) as error:
            errors.append(error)

    def sample_stream():
        yield {"timestamp": 0, "acc_y": -3.45}
        assert network_started.wait(timeout=2)
        for timestamp in range(1, 6):
            yield {"timestamp": timestamp, "acc_y": 0.02}
        collected_during_outage.set()
        assert release_network.wait(timeout=3)
        for timestamp in range(6, 11):
            yield {"timestamp": timestamp, "acc_y": 0.02}

    def produce_events():
        try:
            acquisition_loop(output_file=str(report), samples=sample_stream())
            business_finished.set()
        except (AssertionError, OSError, RuntimeError, ValueError, requests.RequestException) as error:
            errors.append(error)

    monkeypatch.setattr(network, "send_alert", blocked_sender)
    worker = threading.Thread(target=run_network)
    acquisition = threading.Thread(target=produce_events)
    worker.start()
    acquisition.start()
    try:
        assert network_started.wait(timeout=2)
        assert collected_during_outage.wait(timeout=2)
        assert errors == []
        assert database.pending_count() == 1
        release_network.set()
        assert business_finished.wait(timeout=2)
    finally:
        network.STOP_EVENT.set()
        release_network.set()
        if acquisition.ident is not None:
            acquisition.join(timeout=3)
        worker.join(timeout=3)
    assert not worker.is_alive()
    assert not acquisition.is_alive()
    assert errors == []
    assert database.pending_count() == 0
    score = json.loads(report.read_text(encoding="utf-8"))
    assert score["total_samples"] == 11
    assert score["harsh_braking_events"] == 1
    assert score["events"] == [{"timestamp": 0, "acc_y": -3.45}]


def test_collection_commits_both_engine_events_before_any_send(tmp_path, monkeypatch):
    def deny_network(*_args, **_kwargs):
        raise AssertionError("Collection must not use the network")

    monkeypatch.setattr(socket, "socket", deny_network)
    collect_events(score_file=str(tmp_path / "daily_score.json"))
    pending = database.get_pending_alerts(limit=1000)
    payloads = [json.loads(payload) for _alert_id, payload, _attempts in pending]
    assert len(pending) == database.pending_count()
    assert any(payload.get("event_type") == "zfe_entry" for payload in payloads)
    assert any(payload.get("acc_y", 0) < -2.5 for payload in payloads)
    sent = []

    def sender(alert_id, payload):
        assert stored_alerts()[alert_id]["payload"] == json.loads(payload)
        sent.append(alert_id)
        if len(sent) == len(pending):
            network.STOP_EVENT.set()

    monkeypatch.setattr(network, "send_alert", sender)
    network.network_worker()
    assert set(sent) == {alert_id for alert_id, _payload, _attempts in pending}
    assert database.pending_count() == 0


def test_streaming_callback_emits_before_next_sample_without_retaining_a_list():
    emitted = []

    def samples():
        yield {"timestamp": 1, "acc_y": -3.45}
        assert emitted == [{"timestamp": 1, "acc_y": -3.45}]
        yield {"timestamp": 2, "acc_y": -2.5}

    score = analyze_accelerometer_stream(
        samples(), on_event=emitted.append, retain_events=False
    )
    assert score == {"total_samples": 2, "harsh_braking_events": 1, "events": []}


def test_report_counts_1000_samples_as_one_episode_and_survives_bad_input(tmp_path):
    samples = tmp_path / "accelerometer.csv"
    samples.write_text(
        "timestamp,acc_x,acc_y,acc_z\n"
        + "".join(f"{index},0,-3,0\n" for index in range(1000)),
        encoding="utf-8",
    )
    report = tmp_path / "daily_score.json"
    emitted = []
    run_safety_engine(
        str(samples), str(report), on_event=emitted.append, raise_on_error=True
    )
    previous_report = report.read_bytes()
    score = json.loads(previous_report)
    assert score["total_samples"] == 1000
    assert score["harsh_braking_events"] == 1
    assert emitted == [{"timestamp": 0, "acc_y": -3.0}]
    assert score["events"] == emitted

    samples.write_text(
        "timestamp,acc_x,acc_y,acc_z\n1,0,-3,0\n2,0,invalid,0\n", encoding="utf-8"
    )
    with pytest.raises(ValueError):
        run_safety_engine(str(samples), str(report), raise_on_error=True)
    assert report.read_bytes() == previous_report


def test_collection_reports_missing_input_and_keeps_the_previous_report(tmp_path):
    report = tmp_path / "daily_score.json"
    previous_report = '{"previous_report": true}'
    report.write_text(previous_report, encoding="utf-8")
    with pytest.raises(FileNotFoundError):
        collect_events(
            score_file=str(report),
            accelerometer_file=str(tmp_path / "absent.csv"),
        )
    assert report.read_text(encoding="utf-8") == previous_report


def test_http_sends_stable_identity_and_leaves_old_table_untouched(monkeypatch):
    class Response:
        def __init__(self, status_code):
            self.status_code = status_code
            self.closed = False

        def __enter__(self):
            return self

        def __exit__(self, *_args):
            self.closed = True

    responses = [Response(204), Response(503)]
    calls = []

    def post(url, **kwargs):
        calls.append((url, kwargs))
        return responses[len(calls) - 1]

    monkeypatch.setattr(network, "DEMO_MODE", False)
    monkeypatch.setattr(network, "API_URL", "https://example.invalid/alert")
    monkeypatch.setattr(network, "API_TOKEN", "test-token")
    monkeypatch.setattr(network.requests, "post", post)
    alert_id = "05be8884-b222-4791-a4a3-4c055737154f"
    payload = {
        "timestamp": 1,
        "acc_y": -3.45,
        "alert_id": alert_id,
        "captured_at": 1_700_000_000.5,
    }
    network.send_alert(alert_id, json.dumps(payload))
    url, request = calls[0]
    assert url == "https://example.invalid/alert"
    assert request["headers"]["Authorization"] == "Bearer test-token"
    assert request["headers"]["Idempotency-Key"] == alert_id
    assert request["json"] == payload
    assert request["timeout"] == (3, 10)
    assert responses[0].closed

    with pytest.raises(requests.HTTPError):
        network.send_alert(alert_id, json.dumps(payload))
    assert calls[1][1]["headers"]["Idempotency-Key"] == alert_id
    assert calls[1][1]["json"] == payload
    assert responses[1].closed

    # The old table is preserved; this flow intentionally performs no migration.
    old_payload = json.dumps({"timestamp": 1, "acc_y": -3.45})
    with closing(database.connect_database()) as connection, connection:
        connection.execute(
            "CREATE TABLE events (id INTEGER PRIMARY KEY, event_type TEXT, "
            "payload TEXT, created_at TEXT, synced INTEGER)"
        )
        connection.execute(
            "INSERT INTO events VALUES (1, 'harsh_braking', ?, 'original-date', 0)",
            (old_payload,),
        )
    database.initialize_database()
    assert database.get_pending_alerts() == []
    assert database.pending_count() == 0
    with closing(database.connect_database()) as connection:
        assert connection.execute("SELECT * FROM events").fetchall() == [
            (1, "harsh_braking", old_payload, "original-date", 0)
        ]


def test_memory_buffer_is_bounded():
    recent_samples.clear()
    for index in range(1000):
        recent_samples.append({"timestamp": index, "acc_y": 0.0})
    assert len(recent_samples) == 600
    assert recent_samples.maxlen == 600
    assert recent_samples[0]["timestamp"] == 400
    recent_samples.clear()
