"""Lire les mesures, signaler les freinages et ecrire le bilan."""

import csv
from collections import deque
from collections.abc import Callable, Iterable, Iterator

from src.safety.safety_engine import (
    analyze_accelerometer_stream,
    iter_accelerometer_data,
    write_daily_score,
)

INPUT_FILE = "data/accelerometer_data.csv"
OUTPUT_FILE = "daily_score.json"

Sample = dict[str, int | float]
EventCallback = Callable[[dict[str, int | float]], None]


def remember_samples(
    samples: Iterable[Sample],
    sample_buffer: deque[Sample],
) -> Iterator[Sample]:
    """Ajouter chaque mesure au buffer borne avant de la traiter."""
    for sample in samples:
        sample_buffer.append(sample)
        yield sample


def run_safety_engine(
    input_file: str = INPUT_FILE,
    output_file: str = OUTPUT_FILE,
    *,
    on_event: EventCallback | None = None,
    raise_on_error: bool = False,
    samples: Iterable[Sample] | None = None,
    sample_buffer: deque[Sample] | None = None,
    verbose: bool = True,
) -> dict | None:
    """Detecter les freinages et appeler on_event pour chaque episode."""
    try:
        source: Iterable[Sample]
        source = iter_accelerometer_data(input_file) if samples is None else samples

        if sample_buffer is not None:
            source = remember_samples(source, sample_buffer)

        score = analyze_accelerometer_stream(source, on_event=on_event)

        if verbose:
            print("\n[BILAN SAFETY] Collecte terminee.")
            for event in score["events"]:
                print(
                    f"[HARSH BRAKING] timestamp={event['timestamp']} "
                    f"acc_y={event['acc_y']} m/s²"
                )

        write_daily_score(score, output_file)

        if verbose:
            print(
                f"[SAFETY SUMMARY] samples={score['total_samples']} "
                f"harsh_braking_events={score['harsh_braking_events']}"
            )
            print(f"[OUTPUT] {output_file}")

        return score

    except (FileNotFoundError, csv.Error, KeyError, TypeError, ValueError) as error:
        if raise_on_error:
            raise
        print(f"[ERROR] {error}")
        return None


if __name__ == "__main__":
    run_safety_engine()
