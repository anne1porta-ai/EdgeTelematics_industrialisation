"""Modeles metier des evenements produits par l'application Edge."""

from collections.abc import Mapping
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any


@dataclass(frozen=True)
class TelemetryEvent:
    """Evenement metier immuable, independant de SQLite et du reseau."""

    event_type: str
    payload: dict[str, Any]
    created_at: str

    @classmethod
    def harsh_braking(cls, acc_y: float, timestamp: float) -> "TelemetryEvent":
        """Creer un evenement de freinage brusque."""
        return cls(
            event_type="harsh_braking",
            payload={"timestamp": timestamp, "acc_y": acc_y},
            created_at=datetime.now(timezone.utc).isoformat(),
        )

    @classmethod
    def zfe_entry(cls, point: Mapping[str, Any]) -> "TelemetryEvent":
        """Creer un evenement d'entree dans une ZFE."""
        return cls(
            event_type="zfe_entry",
            payload={
                "id": point["id"],
                "timestamp": point["timestamp"],
                "lat": point["lat"],
                "lon": point["lon"],
            },
            created_at=datetime.now(timezone.utc).isoformat(),
        )

    def to_payload(self) -> dict[str, Any]:
        """Retourner le contenu JSON commun a SQLite et au reseau."""
        return {
            "event_type": self.event_type,
            **self.payload,
            "created_at": self.created_at,
        }
