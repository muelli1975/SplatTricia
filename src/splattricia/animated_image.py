"""Fixed-quality AVIF encoding through Pillow's animation writer."""
from __future__ import annotations

import os
from pathlib import Path

from PIL import Image


class _RenderedSequence(Image.Image):
    """Seekable RGB sequence retaining only one decoded rendered view.

    Pillow's writers accept a multi-frame image. Feeding this sequence avoids
    keeping every uncompressed frame alive in an append_images list.
    """

    def __init__(self, paths, check, progress):
        super().__init__()
        self.paths = paths
        self.n_frames = len(paths)
        self.is_animated = True
        self.check = check
        self.progress = progress
        self._frame = None
        self._position = -1
        self._reported = -1
        self.seek(0)

    def seek(self, frame):
        if not 0 <= frame < self.n_frames:
            raise EOFError("End of rendered sequence")
        self.check()
        if frame != self._position:
            if self._frame is not None:
                self._frame.close()
            with Image.open(self.paths[frame]) as image:
                self._frame = image.convert("RGB")
            self._mode = self._frame.mode
            self._size = self._frame.size
            self._im = self._frame.im
            self._position = frame
        if self.progress is not None and frame > self._reported:
            self._reported = frame
            self.progress(0.7 + 0.2 * (frame + 1) / self.n_frames)

    def tell(self):
        return self._position

    def load(self):
        return self._frame.load()

    def close(self):
        if self._frame is not None:
            self._frame.close()
            self._frame = None
        super().close()


def encode_animation(paths: list[Path], output: Path, kind: str, fps: int,
                     check, progress=None) -> None:
    """Write one infinitely repeated cycle, on a cumulative millisecond grid."""
    if kind != "avif":
        raise ValueError("Unsupported animated image format")
    # Rounding cumulative timestamps avoids 30/60-fps timing drift.
    ticks = [round(index * 1000 / fps) for index in range(len(paths) + 1)]
    durations = [end - start for start, end in zip(ticks, ticks[1:])]
    settings = dict(save_all=True, duration=durations)
    # libavif's sequence writer defaults to infinite repetition. Pillow
    # exposes no AVIF loop parameter; package tests inspect its BMFF flags.
    settings.update(quality=60, subsampling="4:2:0", speed=6, range="full", codec="aom",
                    max_threads=min(8, os.cpu_count() or 1))
    with _RenderedSequence(paths, check, progress) as sequence:
        sequence.save(output, format=kind.upper(), **settings)
    check()
