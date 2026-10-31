from src.domain.telemetry_event import (
    TelemetryEvent,
)

from src.storage.event_repository import (
    EventRepository,
)

from src.sync.sync_service import (
    SyncService,
)


def test_network_failure_keeps_event(
    tmp_path,
):
    repository = EventRepository(
        tmp_path / "events.db"
    )

    repository.add(
        TelemetryEvent.harsh_braking(
            acc_y=-3.45,
            timestamp=1,
        )
    )

    def failing_sender(
        _event,
        _timeout,
    ):
        raise ConnectionError(
            "offline"
        )

    result = SyncService(
        repository,
        failing_sender,
        max_attempts=3,
    ).sync_pending()

    assert result == {
        "synced": 0,
        "failed": 1,
    }

    assert (
        repository.pending_count()
        == 1
    )


def test_network_recovery_syncs_event(
    tmp_path,
):
    repository = EventRepository(
        tmp_path / "events.db"
    )

    repository.add(
        TelemetryEvent.harsh_braking(
            acc_y=-3.45,
            timestamp=1,
        )
    )

    sent = []

    def sender(
        event,
        timeout,
    ):
        sent.append(
            (
                event["id"],
                timeout,
            )
        )

    result = SyncService(
        repository,
        sender,
    ).sync_pending()

    assert result == {
        "synced": 1,
        "failed": 0,
    }

    assert (
        repository.pending_count()
        == 0
    )