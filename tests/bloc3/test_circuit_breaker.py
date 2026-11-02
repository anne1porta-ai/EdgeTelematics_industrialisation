"""Tests du circuit breaker reseau."""

import src.storage.event_repository as database
import src.sync.circuit_breaker as circuit
import src.sync.sync_service as network
from src.domain.telemetry_event import TelemetryEvent
from src.sync.circuit_breaker import CLOSED, HALF_OPEN, OPEN, CircuitBreaker


def test_circuit_starts_closed():
    breaker = CircuitBreaker()

    assert breaker.state == CLOSED
    assert breaker.allow_request() is True
    assert breaker.failure_count == 0


def test_circuit_opens_after_three_failures(monkeypatch):
    monkeypatch.setattr(circuit.time, "monotonic", lambda: 100.0)
    breaker = CircuitBreaker(failure_threshold=3)

    breaker.record_failure()
    breaker.record_failure()
    assert breaker.state == CLOSED

    breaker.record_failure()

    assert breaker.state == OPEN
    assert breaker.allow_request() is False
    assert breaker.has_opened is True


def test_open_circuit_allows_one_half_open_probe(monkeypatch):
    clock = [100.0]
    monkeypatch.setattr(circuit.time, "monotonic", lambda: clock[0])
    breaker = CircuitBreaker(failure_threshold=1, recovery_timeout=5.0)

    breaker.record_failure()
    clock[0] = 104.9
    assert breaker.allow_request() is False

    clock[0] = 105.0
    assert breaker.allow_request() is True
    assert breaker.state == HALF_OPEN
    assert breaker.allow_request() is False


def test_successful_half_open_probe_closes_circuit(monkeypatch):
    clock = [100.0]
    monkeypatch.setattr(circuit.time, "monotonic", lambda: clock[0])
    breaker = CircuitBreaker(failure_threshold=1, recovery_timeout=5.0)

    breaker.record_failure()
    clock[0] = 105.0
    assert breaker.allow_request() is True

    breaker.record_success()

    assert breaker.state == CLOSED
    assert breaker.failure_count == 0
    assert breaker.allow_request() is True


def test_failed_half_open_probe_reopens_circuit(monkeypatch):
    clock = [100.0]
    monkeypatch.setattr(circuit.time, "monotonic", lambda: clock[0])
    breaker = CircuitBreaker(failure_threshold=1, recovery_timeout=5.0)

    breaker.record_failure()
    clock[0] = 105.0
    assert breaker.allow_request() is True

    clock[0] = 106.0
    breaker.record_failure()

    assert breaker.state == OPEN
    assert breaker.opened_at == 106.0
    assert breaker.allow_request() is False


def test_worker_does_not_call_sender_while_circuit_is_open(tmp_path, monkeypatch):
    monkeypatch.setattr(database, "DB_PATH", str(tmp_path / "events.db"))
    database.initialize_database()
    database.save_alert(TelemetryEvent.harsh_braking(-3.45, 1.0))

    breaker = CircuitBreaker(failure_threshold=1, recovery_timeout=60.0)
    breaker.record_failure()
    calls = []

    class StopAfterWait:
        stopped = False

        def is_set(self):
            return self.stopped

        def wait(self, _timeout):
            self.stopped = True

    def sender(_alert_id, _payload):
        calls.append("called")

    network.network_worker(
        sender=sender,
        stop_event=StopAfterWait(),
        circuit_breaker=breaker,
    )

    assert calls == []
    assert database.pending_count() == 1
