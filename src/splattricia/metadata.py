from __future__ import annotations

import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable


SUPPORTED_METADATA_SOURCES = {".jpg", ".jpeg", ".tif", ".tiff"}


@dataclass(frozen=True)
class MetadataCopyResult:
    copied: bool
    skipped: bool = False
    error: str = ""


def copy_metadata_to_outputs(
    exiftool_path: Path | None,
    source_path: Path,
    destination_paths: Iterable[Path],
) -> MetadataCopyResult:
    """
    Überträgt die Metadaten einer Quelle in einem ExifTool-Aufruf auf alle
    vorhandenen Zielbilder.

    Die ursprüngliche Brennweite bleibt erhalten. Nur eingebettete Vorschauen
    und Orientation werden nicht kopiert, weil die Ausgabepixel bereits fertig
    ausgerichtet und neu berechnet sind.
    """
    destinations = [path for path in destination_paths if path.is_file()]
    if not destinations:
        return MetadataCopyResult(copied=False, skipped=True)
    if exiftool_path is None or not exiftool_path.is_file():
        return MetadataCopyResult(copied=False, skipped=True)
    if source_path.suffix.lower() not in SUPPORTED_METADATA_SOURCES:
        return MetadataCopyResult(copied=False, skipped=True)

    try:
        completed = subprocess.run(
            [
                str(exiftool_path),
                "-overwrite_original",
                "-m",
                "-TagsFromFile",
                str(source_path),
                "--Preview:all",
                "--Orientation",
                *[str(path) for path in destinations],
            ],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            encoding="utf-8",
            errors="replace",
            check=False,
            timeout=120,
            # ExifTool ist ein Konsolenprogramm. Aus einer fensterlosen
            # PyInstaller-GUI heraus würde Windows sonst kurz ein Terminalfenster
            # einblenden. Auf anderen Plattformen ist der Wert schlicht 0.
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        return MetadataCopyResult(copied=False, error=str(exc))

    if completed.returncode == 0:
        return MetadataCopyResult(copied=True)

    error = completed.stderr.strip() or completed.stdout.strip()
    return MetadataCopyResult(
        copied=False,
        error=error or f"ExifTool-Rückgabecode {completed.returncode}",
    )
