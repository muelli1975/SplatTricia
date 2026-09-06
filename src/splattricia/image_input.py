from __future__ import annotations

from pathlib import Path

import numpy as np
import pillow_heif
from PIL import Image, ImageOps


SUPPORTED_EXTENSIONS = {
    ".jpg",
    ".jpeg",
    ".png",
    ".webp",
    ".tif",
    ".tiff",
    ".bmp",
    ".heic",
    ".heif",
}

pillow_heif.register_heif_opener()


def _is_inside(path: Path, directory: Path) -> bool:
    try:
        path.resolve().relative_to(directory.resolve())
        return True
    except ValueError:
        return False


def collect_images(
    input_path: Path,
    recursive: bool,
    exclude_directory: Path,
) -> list[Path]:
    if input_path.is_file():
        if input_path.suffix.lower() not in SUPPORTED_EXTENSIONS:
            raise ValueError(
                f"Nicht unterstützte Bilddatei: {input_path}"
            )
        return [input_path]

    if not input_path.is_dir():
        raise FileNotFoundError(input_path)

    iterator = (
        input_path.rglob("*")
        if recursive
        else input_path.iterdir()
    )
    images = [
        path
        for path in iterator
        if (
            path.is_file()
            and path.suffix.lower() in SUPPORTED_EXTENSIONS
            and not _is_inside(path, exclude_directory)
        )
    ]
    return sorted(images, key=lambda path: str(path).lower())


def make_item_key(source_path: Path, input_path: Path) -> str:
    if input_path.is_file():
        return source_path.stem

    relative = source_path.relative_to(input_path).with_suffix("")
    return "__".join(relative.parts)


def load_work_image(
    path: Path,
    target_height: int,
) -> np.ndarray:
    """
    Lädt das Bild, berücksichtigt ausschließlich die EXIF-Orientierung
    und skaliert nur dann, wenn die Höhe über target_height liegt.

    EXIF-Brennweiten werden hier bewusst nicht gelesen.
    """
    with Image.open(path) as source:
        image = ImageOps.exif_transpose(source).convert("RGB")
        width, height = image.size

        if target_height > 0 and height > target_height:
            scale = target_height / height
            new_width = max(1, round(width * scale))
            image = image.resize(
                (new_width, target_height),
                Image.Resampling.LANCZOS,
            )

        return np.asarray(image).copy()
