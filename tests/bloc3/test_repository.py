from src.domain.telemetry_event import (
    TelemetryEvent,
)

from src.storage.event_repository import (
    EventRepository,
)


def test_event_is_persisted_locally(
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

    assert (
        repository.pending_count()
        == 1
    )


def test_mark_synced(
    tmp_path,
):
    repository = EventRepository(
        tmp_path / "events.db"
    )

    event_id = repository.add(
        TelemetryEvent.harsh_braking(
            acc_y=-3.45,
            timestamp=1,
        )
    )

    repository.mark_synced(
        [event_id]
    )

    assert (
        repository.pending_count()
        == 0
    )