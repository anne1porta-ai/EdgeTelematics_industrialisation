"""Définir les événements métier créés sur la tablette."""


class TelemetryEvent:
    """Représenter un événement avant son stockage ou son envoi réseau."""

    def __init__(self, event_type, payload):
        self.event_type = event_type
        self.payload = dict(payload)

    @classmethod
    def harsh_braking(cls, acc_y, timestamp):
        """Créer un événement de freinage brusque."""
        payload = {
            "timestamp": timestamp,
            "acc_y": acc_y,
        }
        return cls("harsh_braking", payload)

    @classmethod
    def zfe_entry(cls, point):
        """Créer un événement d'entrée dans la ZFE."""
        payload = {
            "id": point["id"],
            "timestamp": point["timestamp"],
            "lat": point["lat"],
            "lon": point["lon"],
        }
        return cls("zfe_entry", payload)

    def to_payload(self):
        """Préparer le dictionnaire commun au stockage et à l'envoi réseau."""
        result = {"event_type": self.event_type}
        result.update(self.payload)
        return result
