from __future__ import annotations

import time
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import torch
from sharp.utils.gaussians import load_ply
from sharp.utils.gsplat import GSplatRenderer

from .anaglyph import make_anaglyph
from .floating_window import apply_floating_window
from .output_writer import save_anaglyph_jpeg, save_sbs_jpeg
from .stereo_geometry import create_stereo_setup


RenderProgressCallback = Callable[[str, float], None]


@dataclass(frozen=True)
class RenderMetrics:
    measured_deviation_permille: float
    anaglyph_seconds: float



def _tensor_to_rgb8(color: torch.Tensor) -> np.ndarray:
    return (
        color.permute(1, 2, 0)
        .clamp(0.0, 1.0)
        .mul(255.0)
        .round()
        .to(torch.uint8)
        .cpu()
        .numpy()
    )


def _notify(
    callback: RenderProgressCallback | None,
    step: str,
    fraction: float,
) -> None:
    if callback is not None:
        callback(step, fraction)


def render_ply_to_outputs(
    ply_path: Path,
    sbs_path: Path,
    anaglyph_path: Path,
    device: torch.device,
    deviation_permille: float,
    window_position_percent: float,
    window_back_permille: float,
    float_left_permille: float,
    float_right_permille: float,
    float_top_permille: float,
    float_bottom_permille: float,
    gray_anaglyph: bool,
    jpeg_quality_sbs: int,
    jpeg_quality_anaglyph: int,
    progress_callback: RenderProgressCallback | None = None,
) -> RenderMetrics:
    _notify(progress_callback, "loading_ply", 0.05)
    gaussians_cpu, metadata = load_ply(ply_path)

    width, height = metadata.resolution_px
    focal_length_px = float(metadata.focal_length_px)
    gaussians = gaussians_cpu.to(device)
    del gaussians_cpu

    try:
        _notify(progress_callback, "geometry", 0.14)
        points = gaussians.mean_vectors
        if points.ndim == 3:
            points = points[0]
        if points.ndim != 2 or points.shape[1] != 3:
            raise RuntimeError(
                f"Unerwartete Form der Gaussian-Zentren: {tuple(points.shape)}"
            )

        setup = create_stereo_setup(
            points=points,
            width=width,
            height=height,
            focal_length_px=focal_length_px,
            deviation_permille=deviation_permille,
            window_position_percent=window_position_percent,
            window_back_permille=window_back_permille,
            device=device,
        )
        renderer = GSplatRenderer(
            color_space=metadata.color_space,
            background_color="black",
        ).to(device)

        _notify(progress_callback, "render_left", 0.25)
        with torch.inference_mode():
            left_rendering = renderer(
                gaussians,
                extrinsics=setup.left_extrinsics[None],
                intrinsics=setup.left_intrinsics[None],
                image_width=width,
                image_height=height,
            )
        torch.cuda.synchronize()
        left_rgb = _tensor_to_rgb8(left_rendering.color[0])
        del left_rendering

        _notify(progress_callback, "render_right", 0.43)
        with torch.inference_mode():
            right_rendering = renderer(
                gaussians,
                extrinsics=setup.right_extrinsics[None],
                intrinsics=setup.right_intrinsics[None],
                image_width=width,
                image_height=height,
            )
        torch.cuda.synchronize()
        right_rgb = _tensor_to_rgb8(right_rendering.color[0])
        del right_rendering

        left_rgb, right_rgb = apply_floating_window(
            left_rgb,
            right_rgb,
            left_permille=float_left_permille,
            right_permille=float_right_permille,
            top_permille=float_top_permille,
            bottom_permille=float_bottom_permille,
        )

        _notify(progress_callback, "save_sbs", 0.60)
        save_sbs_jpeg(left_rgb, right_rgb, sbs_path, jpeg_quality_sbs)

        _notify(progress_callback, "anaglyph", 0.72)
        anaglyph_start = time.perf_counter()
        anaglyph = make_anaglyph(left_rgb, right_rgb, gray=gray_anaglyph)
        anaglyph_seconds = time.perf_counter() - anaglyph_start

        _notify(progress_callback, "save_anaglyph", 0.90)
        save_anaglyph_jpeg(anaglyph, anaglyph_path, jpeg_quality_anaglyph)

        final = setup.final_measurement
        del renderer, left_rgb, right_rgb, anaglyph
        return RenderMetrics(
            measured_deviation_permille=final.range_px / width * 1000.0,
            anaglyph_seconds=anaglyph_seconds,
        )
    finally:
        del gaussians
