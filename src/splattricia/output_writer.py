from __future__ import annotations

import time
from pathlib import Path

import numpy as np
from PIL import Image


REPLACE_ATTEMPTS = 8
REPLACE_DELAY_SECONDS = 0.25


def _replace_with_retry(temporary: Path, destination: Path) -> None:
    last_error: PermissionError | None = None
    for attempt in range(REPLACE_ATTEMPTS):
        try:
            temporary.replace(destination)
            return
        except PermissionError as exc:
            last_error = exc
            if attempt + 1 < REPLACE_ATTEMPTS:
                time.sleep(REPLACE_DELAY_SECONDS)

    try:
        temporary.unlink(missing_ok=True)
    except OSError:
        pass

    raise PermissionError(
        "Ausgabedatei ist gesperrt und konnte nicht ersetzt werden / "
        f"output file is locked: {destination}"
    ) from last_error


def _save_jpeg(image: np.ndarray, path: Path, quality: int) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.stem + ".partial.jpg")
    try:
        Image.fromarray(np.ascontiguousarray(image)).save(
            temporary,
            format="JPEG",
            quality=quality,
            subsampling=0,
        )
        _replace_with_retry(temporary, path)
    except Exception:
        try:
            temporary.unlink(missing_ok=True)
        except OSError:
            pass
        raise


def save_sbs_jpeg(
    left_rgb: np.ndarray,
    right_rgb: np.ndarray,
    output_path: Path,
    quality: int,
) -> None:
    _save_jpeg(np.concatenate([left_rgb, right_rgb], axis=1), output_path, quality)


def save_anaglyph_jpeg(image: np.ndarray, output_path: Path, quality: int) -> None:
    _save_jpeg(image, output_path, quality)
