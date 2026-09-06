from __future__ import annotations

import argparse
import ast
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent
SRC = ROOT / "src"


def fail(message: str) -> None:
    raise SystemExit(f"RELEASE CHECK FAILED: {message}")


def check_python_syntax() -> None:
    for path in [ROOT / "launcher.py", ROOT / "run_splattricia.py", ROOT / "run_core.py"]:
        ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    for path in sorted((SRC / "splattricia").glob("*.py")):
        ast.parse(path.read_text(encoding="utf-8"), filename=str(path))


def check_locales() -> None:
    de_path = SRC / "splattricia" / "locales" / "de.json"
    en_path = SRC / "splattricia" / "locales" / "en.json"
    de = json.loads(de_path.read_text(encoding="utf-8"))
    en = json.loads(en_path.read_text(encoding="utf-8"))
    if set(de) != set(en):
        fail("Sprachdateien haben unterschiedliche Schluessel.")


def check_version() -> None:
    init_text = (SRC / "splattricia" / "__init__.py").read_text(encoding="utf-8")
    if '__version__ = "1.0"' not in init_text:
        fail("Version in __init__.py ist nicht 1.0.")
    for rel in ["README_DE.txt", "README_EN.txt", "BUILD.md", "RELEASE_CHECKLIST.md"]:
        if "1.0" not in (ROOT / rel).read_text(encoding="utf-8"):
            fail(f"Versionsangabe 1.0 fehlt in {rel}.")


def check_metadata_no_console() -> None:
    text = (SRC / "splattricia" / "metadata.py").read_text(encoding="utf-8")
    required = ["CREATE_NO_WINDOW", "creationflags=creationflags"]
    for marker in required:
        if marker not in text:
            fail(f"Fensterloser ExifTool-Aufruf fehlt: {marker}")


def check_release_naming() -> None:
    text = (ROOT / "build_portable.bat").read_text(encoding="utf-8")
    required = [
        'set "VERSION=1.0"',
        'set "ZIP_PATH=%CD%\\dist\\%APP_NAME%_%VERSION%.zip"',
    ]
    for marker in required:
        if marker not in text:
            fail(f"Release-Namensregel fehlt in build_portable.bat: {marker}")


def check_source_definition() -> None:
    text = (ROOT / "prepare_source_bundle.py").read_text(encoding="utf-8")
    for marker in [
        '"LICENSE.txt"',
        '"requirements-lock.txt"',
        '"assets/splattricia.ico"',
        '"assets/ready.wav"',
    ]:
        if marker not in text:
            fail(f"Source-Snapshot-Regel fehlt: {marker}")


def check_license_boundary() -> None:
    license_text = (ROOT / "LICENSE.txt").read_text(encoding="utf-8")
    if "MIT License" not in license_text or "Copyright (c) 2026 Christoph Müller" not in license_text:
        fail("LICENSE.txt ist nicht die erwartete SplatTricia-MIT-Lizenz.")
    for rel in ["README_DE.txt", "README_EN.txt", "SOURCE_README.md"]:
        text = (ROOT / rel).read_text(encoding="utf-8").lower()
        if "mit" not in text or "sharp" not in text:
            fail(f"Lizenztrennung ist in {rel} nicht ausreichend dokumentiert.")


def check_dist(dist: Path) -> None:
    expected = [
        dist / "SplatTricia.exe",
        dist / "README_DE.txt",
        dist / "README_EN.txt",
        dist / "LICENSE.txt",
        dist / "LICENSES.txt",
        dist / "source" / "LICENSE.txt",
        dist / "source" / "requirements-lock.txt",
        dist / "source" / "src" / "splattricia" / "gui.py",
    ]
    missing = [str(path) for path in expected if not path.is_file()]
    if missing:
        fail("Release-Dateien fehlen:\n  " + "\n  ".join(missing))
    if (dist / "models" / "sharp_2572gikvuh.pt").exists():
        fail("SHARP-Checkpoint darf nicht Bestandteil des Releases sein.")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dist", type=Path)
    args = parser.parse_args()

    check_python_syntax()
    check_locales()
    check_version()
    check_metadata_no_console()
    check_release_naming()
    check_source_definition()
    check_license_boundary()

    if args.dist:
        check_dist(args.dist.resolve())

    print("Release-Pruefung erfolgreich.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
