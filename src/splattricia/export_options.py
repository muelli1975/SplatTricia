"""Settings for the optional animation export; independent of stereo geometry."""
from __future__ import annotations

from dataclasses import asdict, dataclass, fields
import math


@dataclass(frozen=True)
class WiggleOptions:
    format: str = "mp4"
    video_fps: int = 30
    gif_fps: int = 15
    png_fps: int = 30
    video_height: int = 1080
    gif_long_side: int = 800
    png_height: int = 1080
    cycle_seconds: float = 2.0

    @property
    def fps(self) -> int:
        return {"mp4": self.video_fps, "gif": self.gif_fps, "png": self.png_fps}[self.format]

    @property
    def frame_count(self) -> int:
        return round(self.cycle_seconds * self.fps)

    def validate(self) -> None:
        if self.format not in {"mp4", "gif", "png"}:
            raise ValueError("Ungültiges Wiggle-Format / invalid wiggle format.")
        for value in (self.video_fps, self.png_fps):
            if type(value) is not int or value not in (30, 60):
                raise ValueError("MP4/PNG: 30 oder 60 fps wählen / choose 30 or 60 fps.")
        if type(self.gif_fps) is not int or self.gif_fps not in (10, 15, 20, 25):
            raise ValueError("GIF: 10, 15, 20 oder 25 fps wählen / choose 10, 15, 20 or 25 fps.")
        if type(self.video_height) is not int or self.video_height not in (720, 1080, 2160):
            raise ValueError("MP4: 720, 1080 oder 2160 Pixel Bildhöhe wählen.")
        if type(self.png_height) is not int or self.png_height not in (1080, 2160):
            raise ValueError("PNG: 1080 oder 2160 Pixel Bildhöhe wählen.")
        if type(self.gif_long_side) is not int or not 64 <= self.gif_long_side <= 2160:
            raise ValueError("GIF: Lange Bildseite von 64 bis 2160 Pixeln wählen.")
        if not isinstance(self.cycle_seconds, (int, float)) or not math.isfinite(self.cycle_seconds) or not 0.5 <= self.cycle_seconds <= 30:
            raise ValueError("Zyklusdauer: 0,5 bis 30 Sekunden / cycle duration: 0.5 to 30 seconds.")
        if not math.isclose(self.cycle_seconds * self.fps, self.frame_count, abs_tol=1e-6):
            raise ValueError("Dauer muss eine ganze Bildanzahl ergeben / duration must give a whole number of frames.")

    def to_settings(self) -> dict:
        return asdict(self)

    @classmethod
    def from_settings(cls, value) -> "WiggleOptions":
        try:
            result = cls(**{f.name: value[f.name] for f in fields(cls) if f.name in value})
            result.validate()
            return result
        except (TypeError, ValueError, KeyError):
            return cls()

    def output_size(self, width: int, height: int) -> tuple[int, int]:
        if self.format == "gif":
            scale = min(1.0, self.gif_long_side / max(width, height))
        else:
            limit = self.video_height if self.format == "mp4" else self.png_height
            scale = min(1.0, limit / height)
        w, h = max(1, round(width * scale)), max(1, round(height * scale))
        # MP4 encoding pads odd dimensions by one pixel; never crop the image.
        return w, h


def cycle_index(index: int, count: int) -> int:
    """Reuse the identical camera view for the return half of the cycle."""
    return min(index, count - index)


def gif_frame_durations(count: int, fps: int) -> list[int]:
    """Round cumulative timestamps to GIF's 10-ms grid without timing drift."""
    ticks = [(index * 100 + fps // 2) // fps for index in range(count + 1)]
    return [(end - start) * 10 for start, end in zip(ticks, ticks[1:])]


def camera_weight(index: int, count: int) -> float:
    """One periodic sinusoidal movement, no duplicated final endpoint."""
    return 0.5 - 0.5 * math.cos(2.0 * math.pi * index / count)
