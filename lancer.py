"""Point d'entrée unique pour lancer et vérifier le projet."""

import argparse
import subprocess  # nosec B404 - commandes Python construites sans shell
import sys
import tempfile
from pathlib import Path

from run_demo import DEFAULT_DB, DEFAULT_SCORE, run_demo
from scripts.build_package import build_package
from scripts.demo_ota_rollout import rollout, staging as show_ota_staging
from scripts.staging_demo import demonstrate as demonstrate_staging

PROJECT_ROOT = Path(__file__).resolve().parent


def run_tests():
    """Exécuter les tests avec l'interpréteur Python courant."""
    command = [sys.executable, "-m", "pytest", "-q"]
    result = subprocess.run(  # nosec B603
        command,
        cwd=PROJECT_ROOT,
        check=False,
    )
    return result.returncode


def run_resilience(data_dir):
    """Lancer la démonstration de crise dans un dossier dédié."""
    from run_bloc3_demo import demonstrate

    data_dir.mkdir(parents=True, exist_ok=True)
    folder = Path(tempfile.mkdtemp(prefix="essai-", dir=data_dir))
    demonstrate(folder)


def create_parser():
    """Construire les commandes disponibles dans le terminal."""
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)

    demo = commands.add_parser("demo", help="Lancer les moteurs GEO et Safety")
    demo.add_argument("--db", type=Path, default=DEFAULT_DB)
    demo.add_argument("--score-file", type=Path, default=DEFAULT_SCORE)
    demo.add_argument("--url")
    demo.add_argument("--wait-seconds", type=float, default=5)

    stress = commands.add_parser("stress", help="Traiter 1 000 mesures simulées")
    stress.add_argument("--db", type=Path, default=DEFAULT_DB)
    stress.add_argument("--score-file", type=Path, default=DEFAULT_SCORE)

    crisis = commands.add_parser("resilience", help="Démontrer la résilience réseau")
    crisis.add_argument(
        "--data-dir",
        type=Path,
        default=PROJECT_ROOT / "resultats_demo",
    )

    commands.add_parser("tests", help="Exécuter les tests automatisés")

    build = commands.add_parser("build", help="Construire le paquet et son manifeste")
    build.add_argument("--version", default="demo-local")
    build.add_argument("--commit", default="local")
    build.add_argument("--output-dir", type=Path, default=PROJECT_ROOT / "dist")

    stage = commands.add_parser("staging", help="Tester le paquet et le rollback")
    stage.add_argument(
        "--manifest",
        type=Path,
        default=PROJECT_ROOT / "dist" / "manifest.json",
    )
    stage.add_argument("--output-dir", type=Path, default=PROJECT_ROOT / "staging")

    ota = commands.add_parser("ota", help="Afficher le staging ou le rollout OTA")
    ota.add_argument("--mode", choices=("staging", "rollout"), required=True)

    return parser


def main():
    """Lancer la commande choisie par l'utilisateur."""
    parser = create_parser()
    args = parser.parse_args()

    if args.command == "demo":
        run_demo(
            db_path=args.db,
            api_url=args.url,
            score_file=args.score_file,
            wait_seconds=args.wait_seconds,
        )
        return 0

    if args.command == "stress":
        run_demo(
            use_stress_dataset=True,
            db_path=args.db,
            score_file=args.score_file,
        )
        return 0

    if args.command == "resilience":
        run_resilience(args.data_dir)
        return 0

    if args.command == "tests":
        return run_tests()

    if args.command == "build":
        manifest = build_package(args.output_dir, args.version, args.commit)
        print(f"[BUILD] {manifest.parent / 'greenmove.zip'}")
        print(f"[MANIFEST] {manifest}")
        return 0

    if args.command == "staging":
        demonstrate_staging(args.manifest, args.output_dir)
        return 0

    if args.command == "ota":
        if args.mode == "staging":
            show_ota_staging()
        else:
            rollout()
        return 0

    return 1


if __name__ == "__main__":
    raise SystemExit(main())
