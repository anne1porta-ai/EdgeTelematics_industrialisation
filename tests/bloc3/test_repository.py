import src.storage.event_repository as database
from src.domain.telemetry_event import TelemetryEvent


def test_event_is_persisted_locally(tmp_path, monkeypatch):
    monkeypatch.setattr(database, "DB_PATH", str(tmp_path / "events.db"))
    database.initialize_database()
    database.save_alert({"acc_y": -3.45, "timestamp": 1})

    assert database.pending_count() == 1
    assert database.synced_count() == 0


def test_delete_alert_moves_event_to_synced_history(tmp_path, monkeypatch):
    monkeypatch.setattr(database, "DB_PATH", str(tmp_path / "events.db"))
    database.initialize_database()
    alert_id = database.save_alert({"acc_y": -3.45, "timestamp": 1})
    database.delete_alert(alert_id)

    assert database.pending_count() == 0
    assert database.synced_count() == 1

    history = database.get_synced_events()
    assert history[0]["alert_id"] == alert_id
    assert history[0]["event_type"] == "harsh_braking"
    assert history[0]["synced"] == 1


def test_repository_accepts_telemetry_event_model(tmp_path, monkeypatch):
    monkeypatch.setattr(database, "DB_PATH", str(tmp_path / "events.db"))
    database.initialize_database()

    event = TelemetryEvent.harsh_braking(acc_y=-3.45, timestamp=1.0)
    alert_id = database.save_alert(event)

    pending = database.get_pending_alerts()
    assert pending[0][0] == alert_id
    assert database.pending_count() == 1
