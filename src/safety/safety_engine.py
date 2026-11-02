"""Detection des freinages brusques a partir d'un flux de mesures."""

import csv
import json
from collections.abc import Callable, Iterator
from pathlib import Path

HARSH_BRAKING_THRESHOLD = -2.5
HARSH_BRAKING_RESET_THRESHOLD = -2.3

Sample = dict[str, int | float]
BrakingEvent = dict[str, int | float]


def parse_timestamp(value: str) -> int | float:
    """Lire un timestamp entier ou decimal sans perdre sa precision."""
    timestamp = float(value)
    if timestamp.is_integer():
        return int(timestamp)
    return timestamp


def iter_accelerometer_data(file_path: str) -> Iterator[Sample]:
    """Lire le CSV une mesure a la fois."""
    path = Path(file_path)
    if not path.exists():
        raise FileNotFoundError(f"File not found: {file_path}")

    with path.open("r", encoding="utf-8", newline="") as file:
        reader = csv.DictReader(file)
        for row in reader:
            yield {
                "timestamp": parse_timestamp(row["timestamp"]),
                "acc_x": float(row["acc_x"]),
                "acc_y": float(row["acc_y"]),
                "acc_z": float(row["acc_z"]),
            }


def analyze_accelerometer_stream(
    samples,
    *,
    on_event: Callable[[BrakingEvent], None] | None = None,
    retain_events: bool = True,
) -> dict:
    """Emettre un seul evenement par episode de freinage brusque."""
    total_samples = 0
    harsh_braking_events = 0
    events: list[BrakingEvent] = []
    armed = True

    for sample in samples:
        total_samples += 1
        acc_y = sample["acc_y"]

        if acc_y > HARSH_BRAKING_RESET_THRESHOLD:
            armed = True
        elif armed and is_harsh_braking(float(acc_y)):
            armed = False
            event = {
                "timestamp": sample["timestamp"],
                "acc_y": acc_y,
            }
            if on_event is not None:
                on_event(dict(event))
            if retain_events:
                events.append(event)
            harsh_braking_events += 1

    return {
        "total_samples": total_samples,
        "harsh_braking_events": harsh_braking_events,
        "events": events,
    }


def is_harsh_braking(acc_y: float) -> bool:
    """Retourner True quand la deceleration depasse le seuil."""
    return acc_y < HARSH_BRAKING_THRESHOLD


def write_daily_score(score: dict, output_path: str) -> None:
    """Ecrire le bilan Safety dans un fichier JSON."""
    path = Path(output_path)
    with path.open("w", encoding="utf-8") as file:
        json.dump(score, file, indent=2)
