from __future__ import annotations

import numpy as np

from .color_transfer import linear_to_srgb, srgb_to_linear


# Farbmatrizen aus der bewährten Referenzpipeline der AnaglyphBatch.
M_LEFT = np.array(
    [
        [0.4561, 0.500484, 0.176381],
        [-0.0400822, -0.0378246, -0.0157589],
        [-0.0152161, -0.0205971, -0.00546856],
    ],
    dtype=np.float32,
)
M_RIGHT = np.array(
    [
        [-0.0434706, -0.0879388, -0.00155529],
        [0.378476, 0.73364, -0.0184503],
        [-0.0721527, -0.112961, 1.2264],
    ],
    dtype=np.float32,
)
LUMA = np.array([0.299, 0.587, 0.114], dtype=np.float32)

# Bewährte Rotkanal-Abstimmung aus derselben Referenzpipeline.
RED_CHANNEL_POWER = np.float32(0.75)
DEFAULT_BLOCK_ROWS = 128


def _validate_pair(left: np.ndarray, right: np.ndarray) -> None:
    if left.shape != right.shape:
        raise ValueError(
            f"Linkes und rechtes Bild müssen gleich groß sein: "
            f"{left.shape} != {right.shape}"
        )
    if left.ndim != 3 or left.shape[2] != 3:
        raise ValueError(f"RGB-Bild mit Form HxWx3 erwartet, erhalten: {left.shape}")
    if left.dtype != np.uint8 or right.dtype != np.uint8:
        raise TypeError("Anaglyphen-Eingaben müssen uint8-RGB-Bilder sein.")


def _make_gray_anaglyph(
    left: np.ndarray,
    right: np.ndarray,
    block_rows: int,
) -> np.ndarray:
    """Grey aus der Batch: direkte Luminanzberechnung in sRGB, ohne Linearisation."""
    height, width, _ = left.shape
    output = np.empty((height, width, 3), dtype=np.uint8)

    for y in range(0, height, block_rows):
        end = min(height, y + block_rows)
        left_block = left[y:end].astype(np.float32, copy=False)
        right_block = right[y:end].astype(np.float32, copy=False)
        left_luma = left_block @ LUMA
        right_luma = right_block @ LUMA

        output[y:end, :, 0] = np.clip(np.rint(left_luma), 0, 255).astype(np.uint8)
        right_gray = np.clip(np.rint(right_luma), 0, 255).astype(np.uint8)
        output[y:end, :, 1] = right_gray
        output[y:end, :, 2] = right_gray

    return output


def _make_color_anaglyph(
    left: np.ndarray,
    right: np.ndarray,
    block_rows: int,
) -> np.ndarray:
    """
    Farbanaglyphe nach der bewährten AnaglyphBatch-Referenzpipeline.

    Pipeline:
      sRGB -> linear -> Matrizen -> Addition -> sRGB -> Rotanpassung.

    Die Berechnung erfolgt streifenweise. Das reduziert lediglich den
    Speicherbedarf; Formel und Ergebnis bleiben gleich.
    """
    height, width, _ = left.shape
    output = np.empty((height, width, 3), dtype=np.uint8)
    scale = np.float32(1.0 / 255.0)

    for y in range(0, height, block_rows):
        end = min(height, y + block_rows)

        left_srgb = left[y:end].astype(np.float32) * scale
        right_srgb = right[y:end].astype(np.float32) * scale
        left_linear = srgb_to_linear(left_srgb)
        right_linear = srgb_to_linear(right_srgb)
        del left_srgb, right_srgb

        # Wie in der 16-Bit-FFmpeg-Pipeline werden die beiden Matrixbeiträge
        # getrennt auf den darstellbaren Bereich begrenzt und danach addiert.
        mixed = left_linear @ M_LEFT.T
        np.clip(mixed, 0.0, 1.0, out=mixed)
        right_mixed = right_linear @ M_RIGHT.T
        np.clip(right_mixed, 0.0, 1.0, out=right_mixed)
        mixed += right_mixed
        del left_linear, right_linear, right_mixed

        srgb = linear_to_srgb(mixed)
        del mixed
        srgb[..., 0] = np.power(srgb[..., 0], RED_CHANNEL_POWER)
        output[y:end] = np.clip(np.rint(srgb * 255.0), 0, 255).astype(np.uint8)

    return output


def make_anaglyph(
    left: np.ndarray,
    right: np.ndarray,
    gray: bool = False,
    block_rows: int = DEFAULT_BLOCK_ROWS,
) -> np.ndarray:
    _validate_pair(left, right)
    if block_rows < 1:
        raise ValueError("block_rows muss mindestens 1 sein.")
    if gray:
        return _make_gray_anaglyph(left, right, block_rows)
    return _make_color_anaglyph(left, right, block_rows)
