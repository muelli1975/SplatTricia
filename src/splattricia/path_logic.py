from __future__ import annotations

from pathlib import Path
from typing import Iterable


def resolve_output_dir(
    input_path: Path | None,
    use_input_subfolder: bool,
    custom_output_folder: str | Path,
) -> Path | None:
    """Ermittelt den tatsächlich verwendeten Ausgabeordner ohne GUI-Zustand."""
    if input_path is None:
        return None

    if use_input_subfolder:
        if input_path.is_file():
            return input_path.parent / "output"
        return input_path / "output"

    value = str(custom_output_folder).strip()
    return Path(value) if value else None


def _directory_from_candidate(candidate: str | Path) -> Path | None:
    text = str(candidate).strip()
    if not text:
        return None

    path = Path(text).expanduser()
    if path.is_dir():
        return path
    if path.is_file() and path.parent.is_dir():
        return path.parent
    if path.parent != path and path.parent.is_dir():
        return path.parent
    return None


def preferred_dialog_directory(
    *candidates: str | Path,
    fallback: Path | None = None,
) -> Path:
    """Wählt den ersten vorhandenen Ordner für einen Datei-/Ordnerdialog."""
    for candidate in candidates:
        directory = _directory_from_candidate(candidate)
        if directory is not None:
            return directory

    fallback = fallback or Path.home()
    return fallback if fallback.is_dir() else Path.cwd()
