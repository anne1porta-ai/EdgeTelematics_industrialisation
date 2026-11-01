"""Construire un ZIP du POC et son manifeste SHA-256 pour la chaîne CI/CD."""

import argparse
import json
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile

from src.ota.check_manifest import sha256_file

PROJECT_ROOT = Path(__file__).resolve().parents[1]
IGNORED_DIRECTORIES = {
    "__pycache__", ".pytest_cache", ".mypy_cache", ".ruff_cache",
    ".venv", "venv", "dist", "resultats", "resultats_demo",
}


def build_package(output_dir=Path("dist"), version="demo-local", commit="local"):
    """Assembler les fichiers du projet, puis calculer le checksum du ZIP fermé."""
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    package_path = output_dir / "greenmove.zip"
    manifest_path = output_dir / "manifest.json"

    files = [
        PROJECT_ROOT / name
        for name in ("run_demo.py", "run_bloc3_demo.py", "requirements.txt")
    ]
    for directory in ("src", "data", "scripts"):
        files.extend(path for path in (PROJECT_ROOT / directory).rglob("*") if path.is_file())
    for launcher in ("INSTALLER.bat", "LANCER_PROJET.bat"):
        if (PROJECT_ROOT / launcher).is_file():
            files.append(PROJECT_ROOT / launcher)

    outputs = {package_path.resolve(), manifest_path.resolve()}
    with ZipFile(package_path, "w", compression=ZIP_DEFLATED) as archive:
        for path in sorted(files):
            relative_path = path.relative_to(PROJECT_ROOT)
            if any(part in IGNORED_DIRECTORIES for part in relative_path.parts):
                continue
            if path.suffix in {".pyc", ".pyo"} or path.resolve() in outputs:
                continue
            archive.write(path, relative_path.as_posix())

    manifest = {
        "version": version,
        "commit": commit,
        "package": package_path.name,
        "checksum": sha256_file(package_path),
    }
    manifest_path.write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    return manifest_path


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--version", default="demo-local")
    parser.add_argument("--commit", default="local")
    parser.add_argument("--output-dir", type=Path, default=Path("dist"))
    args = parser.parse_args()
    manifest_path = build_package(args.output_dir, args.version, args.commit)
    print(f"[BUILD] {manifest_path.parent / 'greenmove.zip'}")
    print(f"[MANIFEST] {manifest_path}")


if __name__ == "__main__":
    main()
