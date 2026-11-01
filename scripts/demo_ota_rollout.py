"""Simuler le staging, les vagues OTA et un rollback N-1."""

import argparse

WAVES = [
    ("INTERNE", 10, 100.0),
    ("PILOTE", 50, 100.0),
    ("5 %", 250, 99.8),
    ("MULTI-PAYS", 1000, 98.9),  # Seuil rouge volontaire pour la demo.
    ("RESTE", 3690, 99.9),
]
MIN_STABILITY = 99.5


def show_staging() -> None:
    print("=" * 62)
    print("        STAGING OTA SIMULE - ARTEFACT SIGNE")
    print("=" * 62)
    print("[OK] Signature verifiee")
    print("[OK] SHA-256 verifie")
    print("[OK] Tests de crise disponibles")
    print("[INFO] Zebra / reboot / endurance 8 h : validation terrain")
    print("=" * 62)


def show_rollout() -> None:
    print("=" * 62)
    print("        DEPLOIEMENT OTA PROGRESSIF - DEMO")
    print("=" * 62)

    deployed = 0
    for name, count, stability in WAVES:
        print(f"\nVague {name}")
        print(f"Terminaux cibles : {count}")
        print(f"Stabilite        : {stability:.1f} %")

        if stability < MIN_STABILITY:
            print("Decision         : NO-GO")
            print("\n[ALERTE] Seuil rouge detecte")
            print("[ROLLBACK] Campagne gelee")
            print("[ROLLBACK] Version N-1 devient la cible")
            print("[VERIFY] Capteurs   : OK")
            print("[VERIFY] Memoire    : OK")
            print("[VERIFY] SQLite     : OK")
            print("[VERIFY] Telemetrie : OK")
            return

        deployed += count
        print("Decision         : GO")
        print(f"Deploiement cumule : {deployed}")

    print("\n[OK] Toutes les vagues sont passees au vert")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mode", choices=["staging", "rollout"], required=True)
    args = parser.parse_args()

    if args.mode == "staging":
        show_staging()
    else:
        show_rollout()


if __name__ == "__main__":
    main()
