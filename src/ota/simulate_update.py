"""Simuler une mise à jour et un rollback avec des fichiers JSON locaux.

Cette simulation n'installe aucun logiciel Android et ne contacte aucun serveur.
"""

import argparse
import json
from pathlib import Path

from src.ota.check_manifest import verify_package

STATE_PATH = Path("ota_state.json")
STATUS_PATH = Path("ota_status.json")
DEFAULT_VERSION = "2.2.0"


def read_current_version():
    """Lire la version simulée ou retourner la version initiale."""
    if not STATE_PATH.exists():
        return DEFAULT_VERSION

    content = STATE_PATH.read_text(encoding="utf-8")
    state = json.loads(content)
    return state["current_version"]


def write_current_version(version):
    """Écrire la version simulée dans le répertoire choisi."""
    STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
    content = json.dumps({"current_version": version}, indent=2) + "\n"
    STATE_PATH.write_text(content, encoding="utf-8")


def write_status(status):
    """Conserver le résultat de la simulation dans un fichier local."""
    STATUS_PATH.parent.mkdir(parents=True, exist_ok=True)
    content = json.dumps(status, indent=2) + "\n"
    STATUS_PATH.write_text(content, encoding="utf-8")


def simulate_update(version=None, fail_install=False, manifest_path=None):
    """Vérifier le paquet, puis simuler son installation ou son rollback."""
    metadata = {}

    if manifest_path is not None:
        manifest = verify_package(manifest_path)
        version = manifest["version"]
        metadata = {
            "commit": manifest["commit"],
            "checksum": manifest["checksum"],
        }

    if version is None:
        raise ValueError("Indiquer une version ou un manifeste.")

    previous_version = read_current_version()
    print(f"[OTA SIMULATION] Tentative locale version={version}")

    if fail_install:
        write_current_version(previous_version)
        status = {
            "status": "rolled_back",
            "attempted_version": version,
            "current_version": previous_version,
            "previous_version": previous_version,
        }
        print(
            "[OTA SIMULATION] Installation échouée ; "
            f"version conservée={previous_version}"
        )
    else:
        write_current_version(version)
        status = {
            "status": "success",
            "previous_version": previous_version,
            "current_version": version,
        }
        print(
            "[OTA SIMULATION] Installation réussie : "
            f"{previous_version} -> {version}"
        )

    status.update(metadata)
    write_status(status)
    print(f"[OTA SIMULATION] Statut écrit dans {STATUS_PATH}")
    return status


def main():
    """Lire les options puis exécuter la simulation."""
    global STATE_PATH, STATUS_PATH

    parser = argparse.ArgumentParser(description=__doc__)
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument("--version")
    source.add_argument("--manifest", type=Path)
    parser.add_argument("--state-dir", type=Path, default=Path("."))
    parser.add_argument("--fail-install", action="store_true")
    args = parser.parse_args()

    STATE_PATH = args.state_dir / "ota_state.json"
    STATUS_PATH = args.state_dir / "ota_status.json"

    try:
        status = simulate_update(
            args.version,
            fail_install=args.fail_install,
            manifest_path=args.manifest,
        )
    except (OSError, ValueError, KeyError) as error:
        raise SystemExit(f"[OTA SIMULATION] Échec : {error}") from error

    if status["status"] == "rolled_back":
        raise SystemExit(1)


if __name__ == "__main__":
    main()
