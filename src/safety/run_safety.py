"""Lire les mesures du projet, signaler les freinages et ecrire le bilan."""

import csv

from src.safety.safety_engine import (
    analyze_accelerometer_stream,
    iter_accelerometer_data,
    write_daily_score,
)

INPUT_FILE = "data/accelerometer_data.csv"
OUTPUT_FILE = "daily_score.json"


def run_safety_engine(
    input_file=INPUT_FILE,
    output_file=OUTPUT_FILE,
    *,
    on_event=None,
    raise_on_error=False,
    samples=None,
    verbose=True,
):
    """Traiter les mesures en flux et appeler on_event pour chaque freinage."""
    try:
        if samples is None:
            samples = iter_accelerometer_data(input_file)

        score = analyze_accelerometer_stream(samples, on_event=on_event)

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

    except (FileNotFoundError, csv.Error, KeyError, TypeError, ValueError) as error:
        if raise_on_error:
            raise
        print(f"[ERROR] {error}")


if __name__ == "__main__":
    run_safety_engine()
