"""Suspendre temporairement les appels reseau apres plusieurs echecs."""

import time

CLOSED = "CLOSED"
OPEN = "OPEN"
HALF_OPEN = "HALF_OPEN"


class CircuitBreaker:
    """Petit circuit breaker adapte au worker reseau du POC."""

    def __init__(
        self,
        failure_threshold: int = 3,
        recovery_timeout: float = 5.0,
    ) -> None:
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.failure_count = 0
        self.opened_at = 0.0
        self.state = CLOSED
        self.has_opened = False

    def allow_request(self) -> bool:
        """Autoriser un appel normal ou une seule sonde de reprise."""
        if self.state == CLOSED:
            return True

        if self.state == OPEN:
            elapsed = time.monotonic() - self.opened_at
            if elapsed >= self.recovery_timeout:
                self.state = HALF_OPEN
                return True
            return False

        return False

    def record_success(self) -> None:
        """Refermer le circuit apres un appel reussi."""
        self.failure_count = 0
        self.opened_at = 0.0
        self.state = CLOSED

    def record_failure(self) -> None:
        """Compter un echec et ouvrir le circuit au seuil defini."""
        if self.state == HALF_OPEN:
            self._open()
            return

        self.failure_count += 1
        if self.failure_count >= self.failure_threshold:
            self._open()

    def _open(self) -> None:
        self.state = OPEN
        self.opened_at = time.monotonic()
        self.has_opened = True
