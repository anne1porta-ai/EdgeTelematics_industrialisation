"""Simuler une mise à jour et un rollback avec des fichiers JSON locaux.

Cette simulation n'installe aucun logiciel Android et ne contacte pas de backend.
"""

import argparse
import json
from pathlib import Path

from src.ota.check_manifest import verify_package

STATE_PATH = Path("ota_state.json")
STATUS_PATH = Path("ota_status.json")
DEFAULT_VERSION = "2.2.0"


def read_current_version() -> str:
    """Lire la version simulée, ou la version initiale si aucun état n'existe."""
    if not STATE_PATH.exists():
        return DEFAULT_VERSION
    return json.loads(STATE_PATH.read_text(encoding="utf-8"))["current_version"]


def write_current_version(version: str) -> None:
    """Écrire la version simulée dans le répertoire choisi."""
    STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
    STATE_PATH.write_text(
        json.dumps({"current_version": version}, indent=2) + "\n", encoding="utf-8"
    )


def write_status(status: dict) -> None:
    """Conserver le résultat de la simulation dans un fichier local."""
    STATUS_PATH.parent.mkdir(parents=True, exist_ok=True)
    STATUS_PATH.write_text(json.dumps(status, indent=2) + "\n", encoding="utf-8")


def simulate_update(
    version: str | None = None,
    fail_install: bool = False,
    manifest_path: str | Path | None = None,
) -> dict:
    """Vérifier le paquet avant toute écriture, puis simuler son installation."""
    metadata = {}
    if manifest_path is not None:
        manifest = verify_package(manifest_path)
        version = manifest["version"]
        metadata = {"commit": manifest["commit"], "checksum": manifest["checksum"]}
    if version is None:
        raise ValueError("Indiquer une version ou un manifeste.")

    previous = read_current_version()
    print(f"[OTA SIMULATION] Tentative locale version={version}")

    if fail_install:
        write_current_version(previous)
        status = {
            "status": "rolled_back",
            "attempted_version": version,
            "current_version": previous,
            "previous_version": previous,
        }
        print(f"[OTA SIMULATION] Installation échouée ; version conservée={previous}")
    else:
        write_current_version(version)
        status = {
            "status": "success",
            "previous_version": previous,
            "current_version": version,
        }
        print(f"[OTA SIMULATION] Installation réussie : {previous} -> {version}")

    status.update(metadata)
    write_status(status)
    print(f"[OTA SIMULATION] Statut écrit dans {STATUS_PATH}")
    return status


def main() -> None:
    """Exécuter la simulation et bloquer la chaîne en cas d'échec."""
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
