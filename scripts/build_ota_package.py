from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile

ROOT = Path(__file__).resolve().parents[1]

INCLUDE = [
    "src",
    "data",
    "run_demo.py",
    "run_bloc3_demo.py",
    "requirements.txt",
]

def iter_files():
    for item in INCLUDE:
        path = ROOT / item
        if path.is_dir():
            for child in path.rglob("*"):
                if child.is_file() and "__pycache__" not in child.parts:
                    yield child
        elif path.is_file():
            yield path

def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--version", required=True)
    parser.add_argument("--commit", required=True)
    args = parser.parse_args()

    dist = ROOT / "dist"
    dist.mkdir(exist_ok=True)
    package = dist / f"edge-telematics-{args.version}.zip"

    with ZipFile(package, "w", ZIP_DEFLATED) as archive:
        for path in iter_files():
            archive.write(path, path.relative_to(ROOT))

    sha256 = hashlib.sha256(package.read_bytes()).hexdigest()
    manifest = {
        "version": args.version,
        "commit": args.commit,
        "package": package.name,
        "sha256": sha256,
    }
    (dist / "manifest.json").write_text(
        json.dumps(manifest, indent=2),
        encoding="utf-8",
    )

    print(f"[BUILD] {package.name}")
    print(f"[SHA-256] {sha256}")
    print("[OK] Immutable OTA package created")

if __name__ == "__main__":
    main()
