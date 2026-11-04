"""Simuler le staging et le déploiement progressif d'une version OTA."""

import argparse

WAVES = [
    ("INTERNE", 10, 100.0),
    ("PILOTE", 50, 100.0),
    ("5 %", 250, 99.8),
    ("MULTI-PAYS", 1000, 98.9),
    ("RESTE", 3690, 99.9),
]

MIN_STABILITY = 99.5


def staging():
    """Afficher les contrôles réalisés avant un déploiement."""
    print("=" * 62)
    print("        STAGING OTA SIMULÉ - ARTEFACT SIGNÉ")
    print("=" * 62)
    print("[OK] Signature vérifiée")
    print("[OK] SHA-256 vérifié")
    print("[OK] Tests de crise disponibles")
    print("[INFO] Zebra réelle / reboot / endurance 8 h : validation terrain")
    print("=" * 62)


def rollout():
    """Déployer par vagues et arrêter la campagne si la stabilité baisse."""
    print("=" * 62)
    print("        DÉPLOIEMENT OTA PROGRESSIF - DÉMO")
    print("=" * 62)

    deployed = 0

    for name, count, stability in WAVES:
        print(f"\nVague {name}")
        print(f"Terminaux cibles : {count}")
        print(f"Stabilité        : {stability:.1f} %")

        if stability < MIN_STABILITY:
            print("Décision         : NO-GO")
            print("\n[ALERTE] Seuil rouge détecté")
            print("[ROLLBACK] Campagne gelée")
            print("[ROLLBACK] Version N-1 devient la cible")
            print("[VERIFY] Capteurs : OK")
            print("[VERIFY] Mémoire  : OK")
            print("[VERIFY] SQLite   : OK")
            print("[VERIFY] Télémétrie : OK")
            return

        deployed += count
        print("Décision         : GO")
        print(f"Déploiement cumulé : {deployed}")

    print("\n[OK] Toutes les vagues sont passées au vert")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mode", choices=["staging", "rollout"], required=True)
    args = parser.parse_args()

    if args.mode == "staging":
        staging()
    else:
        rollout()


if __name__ == "__main__":
    main()
