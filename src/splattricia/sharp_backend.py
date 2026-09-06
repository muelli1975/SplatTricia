from __future__ import annotations

import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import torch

from sharp.cli.predict import predict_image
from sharp.models import PredictorParams, create_predictor
from sharp.utils.gaussians import save_ply
from sharp.utils.io import convert_focallength

from .image_input import load_work_image


@dataclass(frozen=True)
class InferenceMetrics:
    inference_seconds: float


class SharpSession:
    """
    Hält das SHARP-Modell für mehrere Bilder einmalig im VRAM.

    Das Modell wird bewusst vor dem späteren PLY-Rendering wieder
    freigegeben. So liegen SHARP und der Stereo-Renderer nicht
    gleichzeitig im Speicher.
    """

    def __init__(
        self,
        checkpoint_path: Path,
        device: torch.device,
    ) -> None:
        self.checkpoint_path = checkpoint_path
        self.device = device
        self.predictor: Any | None = None
        self.load_seconds = 0.0

    def __enter__(self) -> "SharpSession":
        start = time.perf_counter()
        state_dict = torch.load(
            self.checkpoint_path,
            map_location="cpu",
            weights_only=True,
        )
        predictor = create_predictor(PredictorParams())
        predictor.load_state_dict(state_dict)
        del state_dict

        predictor.eval()
        predictor.to(self.device)
        torch.cuda.synchronize()

        self.predictor = predictor
        self.load_seconds = time.perf_counter() - start
        return self

    def __exit__(self, exc_type, exc, traceback) -> None:
        if self.predictor is not None:
            del self.predictor
            self.predictor = None

    def infer_to_ply(
        self,
        source_path: Path,
        ply_path: Path,
        target_height: int,
        fixed_focal_length_mm: float,
    ) -> InferenceMetrics:
        if self.predictor is None:
            raise RuntimeError("SHARP-Modell ist nicht geladen.")

        image = load_work_image(source_path, target_height)
        height, width = image.shape[:2]
        focal_length_px = float(
            convert_focallength(
                width,
                height,
                fixed_focal_length_mm,
            )
        )

        inference_start = time.perf_counter()
        gaussians = predict_image(
            self.predictor,
            image,
            focal_length_px,
            self.device,
        )
        torch.cuda.synchronize()
        inference_seconds = time.perf_counter() - inference_start

        ply_path.parent.mkdir(parents=True, exist_ok=True)
        temporary_path = ply_path.with_name(ply_path.stem + ".partial.ply")
        save_ply(
            gaussians,
            focal_length_px,
            (height, width),
            temporary_path,
        )
        temporary_path.replace(ply_path)

        del gaussians
        del image

        return InferenceMetrics(inference_seconds=inference_seconds)
