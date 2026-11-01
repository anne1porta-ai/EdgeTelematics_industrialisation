import src.storage.event_repository as database


def test_event_is_persisted_locally(tmp_path, monkeypatch):
    monkeypatch.setattr(database, "DB_PATH", str(tmp_path / "events.db"))
    database.initialize_database()
    database.save_alert({"acc_y": -3.45, "timestamp": 1})

    assert database.pending_count() == 1


def test_delete_alert(tmp_path, monkeypatch):
    monkeypatch.setattr(database, "DB_PATH", str(tmp_path / "events.db"))
    database.initialize_database()
    alert_id = database.save_alert({"acc_y": -3.45, "timestamp": 1})
    database.delete_alert(alert_id)

    assert database.pending_count() == 0
