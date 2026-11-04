"""Construire le ZIP du projet et son manifeste SHA-256."""

import argparse
import json
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile

from src.ota.check_manifest import sha256_file

PROJECT_ROOT = Path(__file__).resolve().parents[1]
IGNORED_DIRECTORIES = {
    "__pycache__",
    ".pytest_cache",
    ".mypy_cache",
    ".ruff_cache",
    ".venv",
    "venv",
    "dist",
    "resultats",
    "resultats_demo",
}


def collect_project_files():
    """Lister les fichiers nécessaires au paquet OTA."""
    files = []

    for name in ("lancer.py", "run_demo.py", "run_bloc3_demo.py", "requirements.txt"):
        files.append(PROJECT_ROOT / name)

    for directory_name in ("src", "data", "scripts"):
        directory = PROJECT_ROOT / directory_name
        for path in directory.rglob("*"):
            if path.is_file():
                files.append(path)

    for launcher_name in ("INSTALLER.bat", "LANCER_DEMO_CRISE.bat"):
        launcher = PROJECT_ROOT / launcher_name
        if launcher.is_file():
            files.append(launcher)

    return files


def should_ignore(path, output_paths):
    """Retourner True si le fichier ne doit pas être ajouté au ZIP."""
    relative_path = path.relative_to(PROJECT_ROOT)

    for part in relative_path.parts:
        if part in IGNORED_DIRECTORIES:
            return True

    if path.suffix in (".pyc", ".pyo"):
        return True

    if path.resolve() in output_paths:
        return True

    return False


def build_package(output_dir=Path("dist"), version="demo-local", commit="local"):
    """Construire le ZIP, puis écrire son manifeste avec le checksum."""
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    package_path = output_dir / "greenmove.zip"
    manifest_path = output_dir / "manifest.json"
    output_paths = {package_path.resolve(), manifest_path.resolve()}

    files = collect_project_files()

    with ZipFile(package_path, "w", compression=ZIP_DEFLATED) as archive:
        for path in sorted(files):
            if should_ignore(path, output_paths):
                continue

            relative_path = path.relative_to(PROJECT_ROOT)
            archive.write(path, relative_path.as_posix())

    manifest = {
        "version": version,
        "commit": commit,
        "package": package_path.name,
        "checksum": sha256_file(package_path),
    }
    manifest_text = json.dumps(manifest, indent=2, ensure_ascii=False) + "\n"
    manifest_path.write_text(manifest_text, encoding="utf-8")

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
