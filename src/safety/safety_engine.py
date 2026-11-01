import csv
import json
from collections.abc import Callable
from pathlib import Path

HARSH_BRAKING_THRESHOLD = -2.5
HARSH_BRAKING_RESET_THRESHOLD = -2.3


def parse_timestamp(value: str) -> int | float:
    """Parse integer or fractional timestamps without losing precision."""
    timestamp = float(value)

    if timestamp.is_integer():
        return int(timestamp)

    return timestamp


def iter_accelerometer_data(file_path: str):
    """Yield accelerometer samples one by one from a CSV file."""
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
    on_event: Callable[[dict], None] | None = None,
    retain_events: bool = True,
) -> dict:
    """Count all samples and emit one event per harsh braking episode.

    Detection rearms only above the reset threshold. Events are delivered
    immediately and counted even when they are not retained in the result.
    """
    total_samples = 0
    harsh_braking_events = 0
    events = []
    armed = True

    for sample in samples:
        total_samples += 1

        acc_y = sample["acc_y"]
        if acc_y > HARSH_BRAKING_RESET_THRESHOLD:
            armed = True
        elif armed and is_harsh_braking(acc_y):
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
    """Return True when longitudinal deceleration exceeds the threshold."""
    return acc_y < HARSH_BRAKING_THRESHOLD


def detect_harsh_braking_events(samples: list[dict]) -> list[dict]:
    """Return the complete first sample of each harsh braking episode."""
    events = []
    armed = True

    for sample in samples:
        acc_y = sample["acc_y"]
        if acc_y > HARSH_BRAKING_RESET_THRESHOLD:
            armed = True
        elif armed and is_harsh_braking(acc_y):
            armed = False
            events.append(sample)

    return events


def build_daily_score(samples: list[dict], events: list[dict]) -> dict:
    """Build a daily safety summary from accelerometer samples."""
    return {
        "total_samples": len(samples),
        "harsh_braking_events": len(events),
        "events": [
            {
                "timestamp": event["timestamp"],
                "acc_y": event["acc_y"],
            }
            for event in events
        ],
    }


def write_daily_score(score: dict, output_path: str) -> None:
    """Write the daily safety summary to a JSON file."""
    path = Path(output_path)

    with path.open("w", encoding="utf-8") as file:
        json.dump(score, file, indent=2)
