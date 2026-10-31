"""Demonstrate local persistence and deferred network synchronization.

The scenario creates one harsh-braking event, simulates a 4G outage, verifies
that the event remains pending locally, then simulates network recovery and
verifies that the event is finally synchronized.
"""

from pathlib import Path

from src.domain.telemetry_event import TelemetryEvent
from src.storage.event_repository import EventRepository
from src.sync.sync_service import SyncService


DB_PATH = Path("bloc3_demo_events.db")


def offline_sender(
    _event: dict,
    _timeout: float,
) -> None:
    """Simulate a network outage."""
    raise ConnectionError(
        "simulated 4G outage"
    )


def online_sender(
    event: dict,
    timeout: float,
) -> None:
    """Simulate a successful backend transmission."""
    print(
        f'[SYNC] sent id={event["id"]} '
        f'type={event["event_type"]} '
        f"timeout={timeout}s"
    )


def main() -> None:
    """Run the complete offline-then-online demonstration scenario."""
    if DB_PATH.exists():
        DB_PATH.unlink()

    repository = EventRepository(DB_PATH)

    event = TelemetryEvent.harsh_braking(
        acc_y=-3.45,
        timestamp=1678880005,
    )

    repository.add(event)

    print(
        "[LOCAL] pending before sync="
        f"{repository.pending_count()}"
    )

    # First attempt: connectivity is unavailable.
    offline = SyncService(
        repository,
        offline_sender,
        max_attempts=2,
    )

    result = offline.sync_pending()

    print(
        "[OFFLINE] "
        f'synced={result["synced"]} '
        f'failed={result["failed"]} '
        f"pending={repository.pending_count()}"
    )

    # Second attempt: connectivity has returned.
    online = SyncService(
        repository,
        online_sender,
    )

    result = online.sync_pending()

    print(
        "[ONLINE] "
        f'synced={result["synced"]} '
        f'failed={result["failed"]} '
        f"pending={repository.pending_count()}"
    )

    DB_PATH.unlink(missing_ok=True)


if __name__ == "__main__":
    main()