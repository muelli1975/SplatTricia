from __future__ import annotations

import numpy as np


SRGB_DECODE_THRESHOLD = np.float32(0.04045)
SRGB_ENCODE_THRESHOLD = np.float32(0.0031308)


def srgb_to_linear(values: np.ndarray) -> np.ndarray:
    """
    Wandelt normierte sRGB-Werte (0..1) in lineares RGB um.

    Die standardisierte stückweise sRGB-Transferfunktion wird direkt mit
    NumPy berechnet. Die Funktion erzeugt ein float32-Ergebnis und verändert
    das Eingabearray nicht.
    """
    source = np.asarray(values, dtype=np.float32)
    result = np.empty_like(source, dtype=np.float32)
    low = source <= SRGB_DECODE_THRESHOLD

    result[low] = source[low] / np.float32(12.92)
    high = ~low
    result[high] = np.power(
        (source[high] + np.float32(0.055)) / np.float32(1.055),
        np.float32(2.4),
    )
    return result


def linear_to_srgb(values: np.ndarray) -> np.ndarray:
    """
    Wandelt lineares RGB in normierte sRGB-Werte (0..1) um.

    Werte außerhalb des darstellbaren Bereichs werden vor der Rückwandlung
    auf 0..1 begrenzt. Das Ergebnis ist float32; die 8-Bit-Quantisierung
    bleibt bewusst Aufgabe des aufrufenden Bildverfahrens.
    """
    source = np.clip(np.asarray(values, dtype=np.float32), 0.0, 1.0)
    result = np.empty_like(source, dtype=np.float32)
    low = source <= SRGB_ENCODE_THRESHOLD

    result[low] = source[low] * np.float32(12.92)
    high = ~low
    result[high] = (
        np.float32(1.055)
        * np.power(source[high], np.float32(1.0 / 2.4))
        - np.float32(0.055)
    )
    return result
