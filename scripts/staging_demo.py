"""Valider le paquet construit : collecte, echec OTA, rollback, puis succes."""

import argparse
import json
import sqlite3
import subprocess  # nosec B404
import sys
import tempfile
from pathlib import Path
from zipfile import ZipFile

from src.ota.check_manifest import verify_package


def demonstrate(manifest_path, output_dir):
    manifest_path = Path(manifest_path).resolve()
    output_dir = Path(output_dir).resolve()
    manifest = verify_package(manifest_path)
    package = manifest_path.parent / manifest["package"]
    output_dir.mkdir(parents=True, exist_ok=True)
    session = Path(tempfile.mkdtemp(prefix="essai-", dir=output_dir))
    application = session / "application"
    device = session / "tablette-simulee"
    capture = session / "capteurs"

    # 1. Executer le code contenu dans le paquet, apres verification de son hash.
    with ZipFile(package) as archive:
        archive.extractall(application)
    command = [sys.executable, "run_bloc3_demo.py", "--data-dir", str(capture)]
    # Interpreteur fixe ; le paquet execute est celui construit par cette CI.
    demo = subprocess.run(  # nosec B603
        command,
        cwd=application,
        stdin=subprocess.DEVNULL,
        text=True,
        capture_output=True,
        check=True,
        timeout=30,
    )
    print(demo.stdout)
    (output_dir / "demo.log").write_text(demo.stdout, encoding="utf-8")
    report_path = next(capture.glob("essai-*/daily_score.json"))
    score = json.loads(report_path.read_text(encoding="utf-8"))
    with sqlite3.connect(report_path.parent / "events.sqlite") as connection:
        pending = connection.execute(
            "SELECT COUNT(*) FROM pending_alerts"
        ).fetchone()[0]
        synced = connection.execute(
            "SELECT COUNT(*) FROM event_history WHERE synced = 1"
        ).fetchone()[0]

    result = (score["total_samples"], score["harsh_braking_events"], pending, synced)
    if result != (160, 1, 0, 1):
        raise RuntimeError(
            "Scenario attendu : 160 mesures, 1 freinage, "
            "0 alerte en attente et 1 alerte historisee."
        )

    # 2. Un echec volontaire doit conserver la version precedente.
    install = [
        sys.executable,
        "-m",
        "src.ota.simulate_update",
        "--manifest",
        str(manifest_path),
        "--state-dir",
        str(device),
    ]
    # Module du meme paquet, execute sans shell.
    failure = subprocess.run(  # nosec B603
        install + ["--fail-install"], cwd=application, check=False, timeout=10
    )
    rollback = json.loads((device / "ota_status.json").read_text(encoding="utf-8"))
    if failure.returncode != 1 or rollback["status"] != "rolled_back":
        raise RuntimeError("Le rollback simule n'a pas ete observe.")
    if rollback["current_version"] != rollback["previous_version"]:
        raise RuntimeError("La version precedente n'a pas ete conservee.")

    # 3. Installer avec succes exactement le meme paquet, sans le reconstruire.
    subprocess.run(  # nosec B603
        install, cwd=application, check=True, timeout=10
    )
    installed = json.loads((device / "ota_status.json").read_text(encoding="utf-8"))
    if (
        installed["status"] != "success"
        or installed["checksum"] != manifest["checksum"]
    ):
        raise RuntimeError("Le paquet confirme ne correspond pas au paquet verifie.")
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
    destination.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(f"[STAGING DEMO] Collecte et rollback valides. Rapport : {destination}")
    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, default=Path("dist/manifest.json"))
    parser.add_argument("--output-dir", type=Path, default=Path("staging"))
    args = parser.parse_args()
    demonstrate(args.manifest, args.output_dir)
