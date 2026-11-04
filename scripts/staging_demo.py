"""Valider le paquet construit, le rollback et l'installation finale."""

import argparse
import json
import sqlite3
import subprocess  # nosec B404 - commandes Python construites sans shell
import sys
import tempfile
from pathlib import Path
from zipfile import ZipFile

from src.ota.check_manifest import verify_package


def read_event_counts(database_path):
    """Lire le nombre d'alertes en attente et synchronisées."""
    with sqlite3.connect(database_path) as connection:
        pending = connection.execute(
            "SELECT COUNT(*) FROM pending_alerts"
        ).fetchone()[0]
        synced = connection.execute(
            "SELECT COUNT(*) FROM event_history"
        ).fetchone()[0]
    return pending, synced


def demonstrate(manifest_path, output_dir):
    """Exécuter le paquet, tester un rollback, puis installer le même paquet."""
    manifest_path = Path(manifest_path).resolve()
    output_dir = Path(output_dir).resolve()

    manifest = verify_package(manifest_path)
    package_path = manifest_path.parent / manifest["package"]

    output_dir.mkdir(parents=True, exist_ok=True)
    session = Path(tempfile.mkdtemp(prefix="essai-", dir=output_dir))
    application_dir = session / "application"
    device_dir = session / "tablette-simulee"
    capture_dir = session / "capteurs"

    # Étape 1 : extraire et exécuter le paquet dont le hash a été vérifié.
    with ZipFile(package_path) as archive:
        archive.extractall(application_dir)

    demo_command = [
        sys.executable,
        "run_bloc3_demo.py",
        "--data-dir",
        str(capture_dir),
    ]
    demo = subprocess.run(  # nosec B603
        demo_command,
        cwd=application_dir,
        text=True,
        capture_output=True,
        check=True,
        timeout=30,
        stdin=subprocess.DEVNULL,
    )

    print(demo.stdout)
    (output_dir / "demo.log").write_text(demo.stdout, encoding="utf-8")

    report_paths = list(capture_dir.glob("essai-*/daily_score.json"))
    if not report_paths:
        raise RuntimeError("Le bilan Safety du paquet est introuvable.")

    report_path = report_paths[0]
    score = json.loads(report_path.read_text(encoding="utf-8"))
    pending, synced = read_event_counts(report_path.parent / "events.sqlite")

    observed = (
        score["total_samples"],
        score["harsh_braking_events"],
        pending,
        synced,
    )
    expected = (160, 1, 0, 1)

    if observed != expected:
        raise RuntimeError(
            "Le paquet ne reproduit pas le scénario attendu : "
            "160 mesures / 1 freinage / 0 attente / 1 historique."
        )

    # Étape 2 : simuler un échec et vérifier le retour à la version précédente.
    install_command = [
        sys.executable,
        "-m",
        "src.ota.simulate_update",
        "--manifest",
        str(manifest_path),
        "--state-dir",
        str(device_dir),
    ]
    failed_install = subprocess.run(  # nosec B603
        install_command + ["--fail-install"],
        cwd=application_dir,
        check=False,
        timeout=10,
    )

    rollback_path = device_dir / "ota_status.json"
    rollback = json.loads(rollback_path.read_text(encoding="utf-8"))

    if failed_install.returncode != 1 or rollback["status"] != "rolled_back":
        raise RuntimeError("Le rollback simulé n'a pas été observé.")

    if rollback["current_version"] != rollback["previous_version"]:
        raise RuntimeError("La version précédente n'a pas été conservée.")

    # Étape 3 : installer avec succès exactement le même paquet.
    subprocess.run(  # nosec B603
        install_command,
        cwd=application_dir,
        check=True,
        timeout=10,
    )

    installed_path = device_dir / "ota_status.json"
    installed = json.loads(installed_path.read_text(encoding="utf-8"))

    if installed["status"] != "success":
        raise RuntimeError("L'installation finale n'a pas réussi.")

    if installed["checksum"] != manifest["checksum"]:
        raise RuntimeError("Le paquet installé ne correspond pas au paquet vérifié.")

    verify_package(manifest_path)

    report = {
        "version": manifest["version"],
        "commit": manifest["commit"],
        "checksum": manifest["checksum"],
        "samples": score["total_samples"],
        "braking_events": score["harsh_braking_events"],
        "pending_alerts": pending,
        "synced_alerts": synced,
        "rollback": rollback,
        "installation": installed,
    }

    destination = output_dir / "report.json"
    destination.write_text(
        json.dumps(report, indent=2) + "\n",
        encoding="utf-8",
    )
    print(f"[STAGING DEMO] Collecte et rollback validés. Rapport : {destination}")
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, default=Path("dist/manifest.json"))
    parser.add_argument("--output-dir", type=Path, default=Path("staging"))
    args = parser.parse_args()

    demonstrate(args.manifest, args.output_dir)


if __name__ == "__main__":
    main()
