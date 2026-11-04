"""Suspendre temporairement les appels réseau après plusieurs échecs."""

import time

CLOSED = "CLOSED"
OPEN = "OPEN"
HALF_OPEN = "HALF_OPEN"


class CircuitBreaker:
    """Protéger le serveur et le worker lorsque le réseau reste indisponible."""

    def __init__(self, failure_threshold=3, recovery_timeout=5.0):
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.failure_count = 0
        self.opened_at = 0.0
        self.state = CLOSED
        self.has_opened = False

    def allow_request(self):
        """Autoriser un appel normal ou un seul essai après le délai de pause."""
        if self.state == CLOSED:
            return True

        if self.state == OPEN:
            elapsed = time.monotonic() - self.opened_at
            if elapsed >= self.recovery_timeout:
                self.state = HALF_OPEN
                return True
            return False

        # En HALF_OPEN, une sonde est déjà en cours.
        return False

    def record_success(self):
        """Refermer le circuit après un appel réussi."""
        self.failure_count = 0
        self.opened_at = 0.0
        self.state = CLOSED

    def record_failure(self):
        """Compter un échec et ouvrir le circuit lorsque le seuil est atteint."""
        if self.state == HALF_OPEN:
            self._open()
            return

        self.failure_count += 1
        if self.failure_count >= self.failure_threshold:
            self._open()

    def _open(self):
        """Passer à l'état OPEN et mémoriser l'heure d'ouverture."""
        self.state = OPEN
        self.opened_at = time.monotonic()
        self.has_opened = True
