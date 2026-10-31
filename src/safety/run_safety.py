import csv

from src.safety.safety_engine import (
    analyze_accelerometer_stream,
    iter_accelerometer_data,
    write_daily_score,
)


INPUT_FILE = "data/accelerometer_data.csv"
OUTPUT_FILE = "daily_score.json"


def run_safety_engine(
    input_file: str = INPUT_FILE,
    output_file: str = OUTPUT_FILE,
) -> None:
    """Run harsh braking detection and generate the daily safety report."""
    try:
        samples = iter_accelerometer_data(input_file)
        score = analyze_accelerometer_stream(samples)
        events = score["events"]

        for event in events:
            print(
                f'[HARSH BRAKING] timestamp={event["timestamp"]} '
                f'acc_y={event["acc_y"]} m/s²'
            )

        write_daily_score(score, output_file)

        print(
            f'[SAFETY SUMMARY] samples={score["total_samples"]} '
            f'harsh_braking_events={score["harsh_braking_events"]}'
        )
        print(f"[OUTPUT] {output_file}")

    except FileNotFoundError as error:
        print(f"[ERROR] {error}")
    except (csv.Error, KeyError, TypeError, ValueError) as error:
        print(f"[ERROR] Invalid Safety input data: {error}")


if __name__ == "__main__":
    run_safety_engine()