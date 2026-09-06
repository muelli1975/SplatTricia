from __future__ import annotations

from dataclasses import dataclass

import torch


@dataclass(frozen=True)
class StereoMeasurement:
    visible_count: int
    near_depth_m: float
    far_depth_m: float
    near_disparity_px: float
    far_disparity_px: float
    range_px: float


@dataclass(frozen=True)
class StereoSetup:
    left_extrinsics: torch.Tensor
    right_extrinsics: torch.Tensor
    left_intrinsics: torch.Tensor
    right_intrinsics: torch.Tensor
    source_near_depth_m: float
    source_far_depth_m: float
    baseline_m: float
    target_range_px: float
    final_measurement: StereoMeasurement


def make_intrinsics(
    width: int,
    height: int,
    focal_length_px: float,
    cx_shift_px: float,
    device: torch.device,
) -> torch.Tensor:
    return torch.tensor(
        [
            [
                focal_length_px,
                0.0,
                width * 0.5 + cx_shift_px,
                0.0,
            ],
            [
                0.0,
                focal_length_px,
                height * 0.5,
                0.0,
            ],
            [0.0, 0.0, 1.0, 0.0],
            [0.0, 0.0, 0.0, 1.0],
        ],
        dtype=torch.float32,
        device=device,
    )


def make_parallel_extrinsics(
    camera_x_m: float,
    device: torch.device,
) -> torch.Tensor:
    extrinsics = torch.eye(
        4,
        dtype=torch.float32,
        device=device,
    )
    extrinsics[0, 3] = -camera_x_m
    return extrinsics


def project_points(
    points: torch.Tensor,
    extrinsics: torch.Tensor,
    intrinsics: torch.Tensor,
) -> tuple[torch.Tensor, torch.Tensor, torch.Tensor]:
    points_camera = (
        points @ extrinsics[:3, :3].T
        + extrinsics[:3, 3]
    )
    depth = points_camera[:, 2]
    x = (
        points_camera[:, 0] / depth
        * intrinsics[0, 0]
        + intrinsics[0, 2]
    )
    y = (
        points_camera[:, 1] / depth
        * intrinsics[1, 1]
        + intrinsics[1, 2]
    )
    return x, y, depth


def visible_depth_extrema_from_source(
    points: torch.Tensor,
    intrinsics: torch.Tensor,
    width: int,
    height: int,
) -> tuple[float, float, int]:
    identity = torch.eye(
        4,
        dtype=torch.float32,
        device=points.device,
    )
    x, y, depth = project_points(
        points,
        identity,
        intrinsics,
    )

    visible = (
        (depth > 0.0)
        & torch.isfinite(depth)
        & torch.isfinite(x)
        & torch.isfinite(y)
        & (x >= 0.0)
        & (x < width)
        & (y >= 0.0)
        & (y < height)
    )
    visible_depth = depth[visible]
    if visible_depth.numel() == 0:
        raise RuntimeError(
            "Keine sichtbaren Gaussian-Zentren gefunden."
        )

    return (
        float(visible_depth.min().item()),
        float(visible_depth.max().item()),
        int(visible_depth.numel()),
    )


def measure_stereo_range(
    points: torch.Tensor,
    left_extrinsics: torch.Tensor,
    right_extrinsics: torch.Tensor,
    left_intrinsics: torch.Tensor,
    right_intrinsics: torch.Tensor,
    width: int,
    height: int,
) -> StereoMeasurement:
    left_x, left_y, left_depth = project_points(
        points,
        left_extrinsics,
        left_intrinsics,
    )
    right_x, right_y, right_depth = project_points(
        points,
        right_extrinsics,
        right_intrinsics,
    )

    visible = (
        (left_depth > 0.0)
        & (right_depth > 0.0)
        & torch.isfinite(left_depth)
        & torch.isfinite(right_depth)
        & torch.isfinite(left_x)
        & torch.isfinite(left_y)
        & torch.isfinite(right_x)
        & torch.isfinite(right_y)
        & (left_x >= 0.0)
        & (left_x < width)
        & (left_y >= 0.0)
        & (left_y < height)
        & (right_x >= 0.0)
        & (right_x < width)
        & (right_y >= 0.0)
        & (right_y < height)
    )

    depth = left_depth[visible]
    disparity = (left_x - right_x)[visible]
    if depth.numel() == 0:
        raise RuntimeError(
            "Keine Gaussian-Zentren sind in beiden "
            "Stereoansichten sichtbar."
        )

    near_depth = depth.min()
    far_depth = depth.max()
    near_disparity = disparity[
        depth == near_depth
    ].median()
    far_disparity = disparity[
        depth == far_depth
    ].median()

    return StereoMeasurement(
        visible_count=int(depth.numel()),
        near_depth_m=float(near_depth.item()),
        far_depth_m=float(far_depth.item()),
        near_disparity_px=float(
            near_disparity.item()
        ),
        far_disparity_px=float(
            far_disparity.item()
        ),
        range_px=float(
            torch.abs(
                near_disparity - far_disparity
            ).item()
        ),
    )


def create_stereo_setup(
    points: torch.Tensor,
    width: int,
    height: int,
    focal_length_px: float,
    deviation_permille: float,
    window_position_percent: float,
    window_back_permille: float,
    device: torch.device,
) -> StereoSetup:
    """
    Bewährter SplatTricia-Stereokern:

    - sichtbare Tiefenextreme 0/100
    - analytische Basis
    - parallele Kameras
    - Kontrollmessung über Gaussian-Zentren
    - Scheinfensterlage über symmetrischen Principal-Point-Shift
    """
    target_range_px = (
        width * deviation_permille / 1000.0
    )

    source_intrinsics = make_intrinsics(
        width,
        height,
        focal_length_px,
        cx_shift_px=0.0,
        device=device,
    )
    source_near_m, source_far_m, _ = (
        visible_depth_extrema_from_source(
            points,
            source_intrinsics,
            width,
            height,
        )
    )

    denominator = focal_length_px * (
        1.0 / source_near_m
        - 1.0 / source_far_m
    )
    if denominator <= 0.0:
        raise RuntimeError(
            "Ungültige Nah-/Ferntiefe für "
            "die Basisberechnung."
        )

    baseline_m = target_range_px / denominator

    raw_measurement: StereoMeasurement | None = None
    for _ in range(3):
        left_extrinsics = make_parallel_extrinsics(
            camera_x_m=-baseline_m * 0.5,
            device=device,
        )
        right_extrinsics = make_parallel_extrinsics(
            camera_x_m=baseline_m * 0.5,
            device=device,
        )

        raw_measurement = measure_stereo_range(
            points,
            left_extrinsics,
            right_extrinsics,
            source_intrinsics,
            source_intrinsics,
            width,
            height,
        )
        if raw_measurement.range_px <= 0.0:
            raise RuntimeError(
                "Gemessene Deviation ist 0."
            )

        if (
            abs(
                raw_measurement.range_px
                - target_range_px
            )
            <= 0.01
        ):
            break

        baseline_m *= (
            target_range_px
            / raw_measurement.range_px
        )

    if raw_measurement is None:
        raise RuntimeError(
            "Keine Stereo-Messung erzeugt."
        )

    scene_range_px = (
        raw_measurement.far_disparity_px
        - raw_measurement.near_disparity_px
    )
    front_ratio = (
        100.0 - window_position_percent
    ) / 100.0
    window_back_px = (
        width * window_back_permille / 1000.0
    )

    effective_shift_px = (
        raw_measurement.near_disparity_px
        + scene_range_px * front_ratio
        + window_back_px
    )

    left_intrinsics = make_intrinsics(
        width,
        height,
        focal_length_px,
        cx_shift_px=-effective_shift_px * 0.5,
        device=device,
    )
    right_intrinsics = make_intrinsics(
        width,
        height,
        focal_length_px,
        cx_shift_px=effective_shift_px * 0.5,
        device=device,
    )

    final_measurement = measure_stereo_range(
        points,
        left_extrinsics,
        right_extrinsics,
        left_intrinsics,
        right_intrinsics,
        width,
        height,
    )

    return StereoSetup(
        left_extrinsics=left_extrinsics,
        right_extrinsics=right_extrinsics,
        left_intrinsics=left_intrinsics,
        right_intrinsics=right_intrinsics,
        source_near_depth_m=source_near_m,
        source_far_depth_m=source_far_m,
        baseline_m=baseline_m,
        target_range_px=target_range_px,
        final_measurement=final_measurement,
    )
