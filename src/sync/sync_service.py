"""Deferred synchronization service for locally persisted telemetry events.

Network transmission is injected through a sender callable. This keeps network
I/O outside the business model and makes the retry behavior easy to test.
"""

from collections.abc import Callable
from typing import Any

from src.storage.event_repository import EventRepository


Sender = Callable[
    [dict[str, Any], float],
    None,
]


class SyncService:
    """Synchronize pending events without losing them on network failure."""

    def __init__(
        self,
        repository: EventRepository,
        sender: Sender,
        timeout_seconds: float = 2.0,
        max_attempts: int = 3,
    ) -> None:
        self.repository = repository
        self.sender = sender
        self.timeout_seconds = timeout_seconds
        self.max_attempts = max_attempts

    def sync_pending(
        self,
        limit: int = 100,
    ) -> dict[str, int]:
        """Try to send a bounded batch of pending events.

        An event is marked as synchronized only after a successful send.
        Temporary transport failures leave the event pending for a later retry.
        """
        synced_ids: list[int] = []
        failed = 0

        for event in self.repository.pending(limit):
            delivered = False

            for _ in range(self.max_attempts):
                try:
                    self.sender(
                        event,
                        self.timeout_seconds,
                    )
                    delivered = True
                    break

                except (
                    ConnectionError,
                    TimeoutError,
                    OSError,
                ):
                    # Transport errors are expected during connectivity loss.
                    # The event remains pending instead of being discarded.
                    continue

            if delivered:
                synced_ids.append(event["id"])
            else:
                failed += 1

        self.repository.mark_synced(
            synced_ids
        )

        return {
            "synced": len(synced_ids),
            "failed": failed,
        }