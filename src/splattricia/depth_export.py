"""Relative, linear inverse-depth data, not a colourized preview."""
from __future__ import annotations

from pathlib import Path
import numpy as np
from PIL import Image, PngImagePlugin

from .output_writer import _replace_with_retry


def depth_pixels(depth: np.ndarray, alpha: np.ndarray) -> np.ndarray:
    depth = np.asarray(depth, dtype=np.float64)
    alpha = np.asarray(alpha)
    if depth.shape != alpha.shape or depth.ndim != 2:
        raise ValueError("Depth and alpha must be equally sized single-channel images.")
    valid = np.isfinite(depth) & (depth > 0) & np.isfinite(alpha) & (alpha > 1e-8)
    inverse = np.zeros_like(depth)
    np.divide(1.0, depth, out=inverse, where=valid)
    pixels = np.zeros(depth.shape, dtype=np.uint16)
    if valid.any():
        near, far = inverse[valid].max(), inverse[valid].min()
        if near > far:
            pixels[valid] = np.rint(np.clip((inverse[valid] - far) / (near - far), 0, 1) * 65535).astype(np.uint16)
    return pixels


def save_depth_png(depth: np.ndarray, alpha: np.ndarray, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.stem + ".partial.png")
    info = PngImagePlugin.PngInfo()
    info.add_text("Description", "Relative inverse depth; white=near, black=far; unobserved pixels=black")
    try:
        Image.fromarray(depth_pixels(depth, alpha)).save(temporary, format="PNG", pnginfo=info)
        _replace_with_retry(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)
