import src.storage.event_repository as database
from src.domain.telemetry_event import TelemetryEvent


def test_event_is_persisted_locally(tmp_path, monkeypatch):
    monkeypatch.setattr(database, "DB_PATH", str(tmp_path / "events.db"))
    database.initialize_database()

    event = TelemetryEvent.harsh_braking(acc_y=-3.45, timestamp=1.0)
    database.save_alert(event)

    assert database.pending_count() == 1
    assert database.synced_count() == 0


def test_mark_alert_synced_moves_event_to_history(tmp_path, monkeypatch):
    monkeypatch.setattr(database, "DB_PATH", str(tmp_path / "events.db"))
    database.initialize_database()

    event = TelemetryEvent.harsh_braking(acc_y=-3.45, timestamp=1.0)
    alert_id = database.save_alert(event)
    database.mark_alert_synced(alert_id)

    assert database.pending_count() == 0
    assert database.synced_count() == 1

    history = database.get_synced_events()
    assert history[0]["alert_id"] == alert_id
    assert history[0]["event_type"] == "harsh_braking"
    assert history[0]["synced"] == 1


def test_repository_preserves_zfe_event_type(tmp_path, monkeypatch):
    monkeypatch.setattr(database, "DB_PATH", str(tmp_path / "events.db"))
    database.initialize_database()

    event = TelemetryEvent.zfe_entry(
        {"id": "truck-1", "timestamp": 2, "lat": 45.75, "lon": 4.85}
    )
    alert_id = database.save_alert(event)

    database.mark_alert_synced(alert_id)
    history = database.get_synced_events()

    assert history[0]["event_type"] == "zfe_entry"
    assert history[0]["payload"]["id"] == "truck-1"
