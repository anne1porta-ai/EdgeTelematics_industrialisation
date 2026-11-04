"""Créer un jeu déterministe de 1 000 mesures pour le mode stress."""

from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
OUTPUT_FILE = PROJECT_ROOT / "data" / "demo_accelerometer_1000.csv"
SAMPLE_COUNT = 1000
HARSH_BRAKING_INDEX = 549


def generate_demo_data():
    """Générer 1 000 mesures à 100 Hz, avec un freinage connu."""
    lines = ["timestamp,acc_x,acc_y,acc_z"]

    for index in range(SAMPLE_COUNT):
        timestamp = 1678881000 + index / 100
        acc_x = 0.10 + (index % 5) * 0.01
        acc_y = -0.20 + (index % 7) * 0.03
        acc_z = 9.78 + (index % 4) * 0.01

        if index == HARSH_BRAKING_INDEX:
            acc_y = -3.45

        line = f"{timestamp:.2f},{acc_x:.2f},{acc_y:.2f},{acc_z:.2f}"
        lines.append(line)

    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_FILE.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"{SAMPLE_COUNT} mesures créées dans {OUTPUT_FILE}")


if __name__ == "__main__":
    generate_demo_data()
