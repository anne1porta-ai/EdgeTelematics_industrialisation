import argparse

from scripts.generate_demo_data import OUTPUT_FILE as STRESS_INPUT_FILE
from scripts.generate_demo_data import generate_demo_data
from src.geo.run_geo import run_geo_engine
from src.safety.run_safety import run_safety_engine


def run_demo(use_stress_dataset: bool = False) -> None:
    """Run the complete GreenMove Edge POC demonstration."""
    print("=== GREENMOVE EDGE POC ===")
    print()

    print("=== GEO ENGINE ===")
    run_geo_engine()

    print()
    print("=== SAFETY ENGINE ===")

    if use_stress_dataset:
        generate_demo_data()
        print("[DEMO] Processing 1000 samples at simulated 100 Hz")
        run_safety_engine(input_file=str(STRESS_INPUT_FILE))
    else:
        run_safety_engine()

    print()
    print("=== DEMO COMPLETE ===")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Run the GreenMove Edge POC demonstration."
    )
    parser.add_argument(
        "--stress",
        action="store_true",
        help="Process 1000 simulated accelerometer samples at 100 Hz.",
    )

    args = parser.parse_args()
    run_demo(use_stress_dataset=args.stress)