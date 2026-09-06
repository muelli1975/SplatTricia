from __future__ import annotations

import numpy as np
from PIL import Image, ImageDraw


def _apply_black_mask(image: np.ndarray, mask: Image.Image) -> np.ndarray:
    mask_array = np.asarray(mask, dtype=np.float32) / 255.0
    output = image.astype(np.float32).copy()
    output *= 1.0 - mask_array[..., None]
    return np.clip(output, 0, 255).astype(np.uint8)


def _make_triangle_mask(
    width: int,
    height: int,
    side: str,
    direction: str,
    max_px: int,
    scale: int = 4,
) -> Image.Image:
    if max_px <= 0:
        return Image.new("L", (width, height), 0)
    scaled_width = width * scale
    scaled_height = height * scale
    scaled_max = max_px * scale
    mask = Image.new("L", (scaled_width, scaled_height), 0)
    draw = ImageDraw.Draw(mask)

    if side == "left" and direction == "bottom":
        points = [(0, 0), (0, scaled_height), (scaled_max, scaled_height)]
    elif side == "right" and direction == "bottom":
        points = [
            (scaled_width, 0),
            (scaled_width, scaled_height),
            (scaled_width - scaled_max, scaled_height),
        ]
    elif side == "left" and direction == "top":
        points = [(0, 0), (scaled_max, 0), (0, scaled_height)]
    elif side == "right" and direction == "top":
        points = [
            (scaled_width, 0),
            (scaled_width - scaled_max, 0),
            (scaled_width, scaled_height),
        ]
    else:
        raise ValueError(f"Ungültige Vorhangrichtung: {side}/{direction}")

    draw.polygon(points, fill=255)
    return mask.resize((width, height), Image.Resampling.LANCZOS)


def apply_floating_window(
    left: np.ndarray,
    right: np.ndarray,
    left_permille: float = 0.0,
    right_permille: float = 0.0,
    top_permille: float = 0.0,
    bottom_permille: float = 0.0,
) -> tuple[np.ndarray, np.ndarray]:
    height, width = left.shape[:2]
    left_permille = max(0.0, float(left_permille))
    right_permille = max(0.0, float(right_permille))
    top_permille = max(0.0, float(top_permille))
    bottom_permille = max(0.0, float(bottom_permille))

    if top_permille > 0.0 and bottom_permille > 0.0:
        raise ValueError("Oben und unten können nicht gleichzeitig aktiv sein.")

    if top_permille > 0.0 or bottom_permille > 0.0:
        value = top_permille if top_permille > 0.0 else bottom_permille
        direction = "top" if top_permille > 0.0 else "bottom"
        max_px = round(width * value / 1000.0)
        if max_px > 0:
            left = _apply_black_mask(
                left, _make_triangle_mask(width, height, "left", direction, max_px)
            )
            right = _apply_black_mask(
                right, _make_triangle_mask(width, height, "right", direction, max_px)
            )
        return left, right

    left_px = round(width * left_permille / 1000.0)
    right_px = round(width * right_permille / 1000.0)
    if left_px > 0:
        left = left.copy()
        left[:, :left_px, :] = 0
    if right_px > 0:
        right = right.copy()
        right[:, -right_px:, :] = 0
    return left, right
