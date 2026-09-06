from __future__ import annotations

import json
from pathlib import Path
from typing import Any


DEFAULT_SETTINGS: dict[str, Any] = {
    "language": "de",
    "last_input_file": "",
    "last_input_folder": "",
    "last_output_folder": "",
    "use_input_subfolder": True,
}


def load_settings(path: Path) -> dict[str, Any]:
    result = dict(DEFAULT_SETTINGS)
    try:
        loaded = json.loads(path.read_text(encoding="utf-8"))
        if isinstance(loaded, dict):
            result.update(loaded)
    except (FileNotFoundError, OSError, json.JSONDecodeError):
        pass
    return result


def save_settings(path: Path, settings: dict[str, Any]) -> None:
    temporary = path.with_name(path.name + ".partial")
    temporary.write_text(
        json.dumps(settings, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    temporary.replace(path)
