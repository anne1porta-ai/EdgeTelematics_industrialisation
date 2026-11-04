"""Détecter les freinages brusques à partir d'un flux de mesures."""

import csv
import json
import os
from pathlib import Path

HARSH_BRAKING_THRESHOLD = -2.5
HARSH_BRAKING_RESET_THRESHOLD = -2.3


def parse_timestamp(value):
    """Lire un timestamp entier ou décimal sans perdre sa précision."""
    timestamp = float(value)
    if timestamp.is_integer():
        return int(timestamp)
    return timestamp


def iter_accelerometer_data(file_path):
    """Lire le CSV une mesure à la fois, sans garder tout le signal en mémoire."""
    path = Path(file_path)
    if not path.exists():
        raise FileNotFoundError(f"File not found: {file_path}")

    with path.open("r", encoding="utf-8", newline="") as file:
        reader = csv.DictReader(file)

        for row in reader:
            sample = {
                "timestamp": parse_timestamp(row["timestamp"]),
                "acc_x": float(row["acc_x"]),
                "acc_y": float(row["acc_y"]),
                "acc_z": float(row["acc_z"]),
            }
            yield sample


def analyze_accelerometer_stream(samples, on_event=None, retain_events=True):
    """Émettre un seul événement par épisode de freinage brusque.

    Le seuil de réarmement évite de compter plusieurs fois une série de mesures
    fortes. Les mesures sont traitées une par une et ne sont pas lissées.
    """
    total_samples = 0
    event_count = 0
    events = []
    armed = True

    for sample in samples:
        total_samples += 1
        acc_y = sample["acc_y"]

        # Une valeur revenue au-dessus de -2,3 m/s² autorise un futur événement.
        if acc_y > HARSH_BRAKING_RESET_THRESHOLD:
            armed = True
            continue

        if armed and is_harsh_braking(float(acc_y)):
            armed = False
            event = {
                "timestamp": sample["timestamp"],
                "acc_y": acc_y,
            }

            if on_event is not None:
                on_event(event.copy())

            if retain_events:
                events.append(event)

            event_count += 1

    return {
        "total_samples": total_samples,
        "harsh_braking_events": event_count,
        "events": events,
    }


def is_harsh_braking(acc_y):
    """Retourner True lorsque la décélération est strictement sous le seuil."""
    return acc_y < HARSH_BRAKING_THRESHOLD


def write_daily_score(score, output_path):
    """Remplacer le bilan seulement lorsque le nouveau JSON est complet."""
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary_path = path.with_name(path.name + ".tmp")

    try:
        with temporary_path.open("w", encoding="utf-8") as file:
            json.dump(score, file, indent=2)
            file.write("\n")
            file.flush()
            os.fsync(file.fileno())

        # os.replace remplace l'ancien fichier en une seule opération.
        os.replace(temporary_path, path)
    finally:
        if temporary_path.exists():
            temporary_path.unlink()
