from __future__ import annotations

import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parent
DEST = ROOT / "source"

ROOT_FILES = [
    "run_splattricia.py",
    "run_core.py",
    "launcher.py",
    "README_DE.txt",
    "README_EN.txt",
    "LICENSE.txt",
    "BUILD.md",
    "RELEASE_CHECKLIST.md",
    "SOURCE_README.md",
    "requirements-lock.txt",
    "SplatTricia.spec",
    "build_portable.bat",
    "cleanup_project.bat",
    "freeze_requirements.bat",
    "prepare_gsplat_native.py",
    "prepare_source_bundle.py",
    "collect_licenses.py",
    "verify_release.py",
    "DESIGN_STANDARD_STEREOTOOLS.txt",
]

ASSET_FILES = [
    "assets/splattricia.ico",
    "assets/ready.wav",
]


def copy_file(relative: str) -> None:
    src = ROOT / relative
    if not src.is_file():
        raise FileNotFoundError(f"Source-Snapshot: Datei fehlt: {src}")
    dst = DEST / relative
    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src, dst)


def main() -> int:
    if DEST.exists():
        shutil.rmtree(DEST)
    DEST.mkdir(parents=True)

    for rel in ROOT_FILES:
        copy_file(rel)

    src_pkg = ROOT / "src" / "splattricia"
    if not src_pkg.is_dir():
        raise FileNotFoundError(f"Source-Snapshot: Paket fehlt: {src_pkg}")
    shutil.copytree(src_pkg, DEST / "src" / "splattricia")

    for rel in ASSET_FILES:
        copy_file(rel)

    print(f"Source-Snapshot erstellt: {DEST}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
