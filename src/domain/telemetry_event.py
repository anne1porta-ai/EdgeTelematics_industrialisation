"""Modeles metier simples des evenements produits sur la tablette."""

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class TelemetryEvent:
    """Evenement metier independant de SQLite et du reseau."""

    event_type: str
    payload: dict[str, Any]

    @classmethod
    def harsh_braking(cls, acc_y: float, timestamp: float) -> "TelemetryEvent":
        """Creer un evenement de freinage brusque."""
        return cls(
            event_type="harsh_braking",
            payload={"timestamp": timestamp, "acc_y": acc_y},
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
        )

    def to_payload(self) -> dict[str, Any]:
        """Retourner le JSON commun a SQLite et au reseau."""
        return {"event_type": self.event_type, **self.payload}
