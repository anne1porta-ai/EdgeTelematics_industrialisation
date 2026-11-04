"""Vérifier l'intégrité des paquets utilisés par les démonstrations OTA.

Le projet conserve deux exemples :
- un ancien manifeste avec une signature pédagogique ;
- un ZIP construit par la CI et vérifié avec son SHA-256.
"""

import argparse
import hashlib
import json
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
MANIFEST_PATH = PROJECT_ROOT / "src" / "ota" / "manifest.json"
PACKAGE_PATH = PROJECT_ROOT / "src" / "ota" / "packages" / "greenmove-2.3.0.pkg"
DEMO_PUBLIC_MARKER = "greenmove-demo-public-marker"


def sha256_file(path):
    """Calculer le SHA-256 d'un fichier."""
    digest = hashlib.sha256()
    digest.update(Path(path).read_bytes())
    return digest.hexdigest()


def expected_demo_signature(checksum):
    """Calculer la signature déterministe de l'ancien exemple pédagogique."""
    value = f"{checksum}:{DEMO_PUBLIC_MARKER}"
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def validate_manifest():
    """Vérifier l'ancien manifeste et sa signature pédagogique."""
    manifest_text = MANIFEST_PATH.read_text(encoding="utf-8")
    manifest = json.loads(manifest_text)
    checksum = sha256_file(PACKAGE_PATH)

    signature = expected_demo_signature(checksum)

    return {
        "version": manifest["version"],
        "checksum_valid": checksum == manifest["checksum"],
        "signature_valid": manifest["demo_signature"] == signature,
    }


def verify_package(manifest_path):
    """Vérifier le SHA-256 du ZIP construit par la CI."""
    manifest_path = Path(manifest_path)
    manifest_text = manifest_path.read_text(encoding="utf-8")
    manifest = json.loads(manifest_text)

    package_name = manifest["package"]
    if Path(package_name).name != package_name:
        raise ValueError("Le paquet doit être un fichier voisin du manifeste.")

    package_path = manifest_path.parent / package_name
    actual_checksum = sha256_file(package_path)

    if actual_checksum != manifest["checksum"]:
        raise ValueError("Le checksum du paquet est invalide.")

    return manifest


def main():
    """Vérifier soit le paquet CI, soit l'ancien paquet de démonstration."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, help="Manifeste du paquet ZIP")
    args = parser.parse_args()

    if args.manifest is not None:
        try:
            result = verify_package(args.manifest)
        except (OSError, ValueError, KeyError) as error:
            raise SystemExit(f"[PACKAGE] {error}") from error

        print(
            f'[PACKAGE] version={result["version"]} '
            f'commit={result["commit"]} checksum=valid'
        )
        return

    result = validate_manifest()

    if not result["checksum_valid"]:
        raise SystemExit("[OTA] checksum invalid")

    if not result["signature_valid"]:
        raise SystemExit("[OTA] signature invalid")

    print(
        "[OTA] manifest "
        f'version={result["version"]} '
        "signature=valid checksum=valid"
    )


if __name__ == "__main__":
    main()
