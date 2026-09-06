from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class ProcessingConfig:
    checkpoint_path: Path
    exiftool_path: Path | None = None
    target_height: int = 2160
    fixed_focal_length_mm: float = 30.0
    deviation_permille: float = 20.0
    window_position_percent: float = 100.0
    window_back_permille: float = 0.0
    float_left_permille: float = 0.0
    float_right_permille: float = 0.0
    float_top_permille: float = 0.0
    float_bottom_permille: float = 0.0
    gray_anaglyph: bool = False
    append_settings_to_filename: bool = False
    jpeg_quality_sbs: int = 95
    jpeg_quality_anaglyph: int = 90
    copy_metadata: bool = True

    def validate(self) -> None:
        if not self.checkpoint_path.is_file():
            raise FileNotFoundError(
                f"SHARP-Checkpoint nicht gefunden: {self.checkpoint_path}"
            )
        if self.target_height < 0:
            raise ValueError("target_height darf nicht negativ sein.")
        if self.fixed_focal_length_mm <= 0.0:
            raise ValueError("fixed_focal_length_mm muss größer als 0 sein.")
        if self.deviation_permille <= 0.0:
            raise ValueError("deviation_permille muss größer als 0 sein.")
        if not 0.0 <= self.window_position_percent <= 100.0:
            raise ValueError(
                "window_position_percent muss zwischen 0 und 100 liegen."
            )
        for name, value in (
            ("window_back_permille", self.window_back_permille),
            ("float_left_permille", self.float_left_permille),
            ("float_right_permille", self.float_right_permille),
            ("float_top_permille", self.float_top_permille),
            ("float_bottom_permille", self.float_bottom_permille),
        ):
            if value < 0.0:
                raise ValueError(f"{name} darf nicht negativ sein.")
        if self.float_top_permille > 0.0 and self.float_bottom_permille > 0.0:
            raise ValueError("Oben und unten können nicht gleichzeitig aktiv sein.")
        if (self.float_top_permille > 0.0 or self.float_bottom_permille > 0.0) and (
            self.float_left_permille > 0.0 or self.float_right_permille > 0.0
        ):
            raise ValueError(
                "Seitliche und kippende Vorhänge können nicht kombiniert werden."
            )
        if not 1 <= self.jpeg_quality_sbs <= 100:
            raise ValueError("jpeg_quality_sbs muss zwischen 1 und 100 liegen.")
        if not 1 <= self.jpeg_quality_anaglyph <= 100:
            raise ValueError(
                "jpeg_quality_anaglyph muss zwischen 1 und 100 liegen."
            )
