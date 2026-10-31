from pathlib import Path


OUTPUT_FILE = Path("data/demo_accelerometer_1000.csv")
SAMPLE_COUNT = 1000
HARSH_BRAKING_INDEX = 549


def generate_demo_data() -> None:
    """Generate deterministic accelerometer demo data."""
    lines = ["timestamp,acc_x,acc_y,acc_z"]

    for index in range(SAMPLE_COUNT):
        timestamp = 1678881000 + (index / 100)

        acc_x = 0.10 + (index % 5) * 0.01
        acc_y = -0.20 + (index % 7) * 0.03
        acc_z = 9.78 + (index % 4) * 0.01

        if index == HARSH_BRAKING_INDEX:
            acc_y = -3.45

        lines.append(
            f"{timestamp:.2f},{acc_x:.2f},{acc_y:.2f},{acc_z:.2f}"
        )

    OUTPUT_FILE.write_text(
        "\n".join(lines) + "\n",
        encoding="utf-8",
    )

    print(
        f"Generated {SAMPLE_COUNT} samples in {OUTPUT_FILE}"
    )


if __name__ == "__main__":
    generate_demo_data()