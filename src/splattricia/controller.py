from __future__ import annotations

import traceback
from collections.abc import Callable
from pathlib import Path

import torch

from .cache import (
    build_cache_identity,
    cache_paths,
    checkpoint_signature,
    is_valid_cache,
    write_cache_record,
)
from .config import ProcessingConfig
from .cuda_utils import release_cuda_cache, require_cuda
from .image_input import collect_images, make_item_key
from .metadata import copy_metadata_to_outputs
from .models import ProcessingItem, ProgressEvent
from .naming import build_suffix
from .renderer import render_ply_to_outputs
from .sharp_backend import SharpSession


EventCallback = Callable[[ProgressEvent], None]
CancelCallback = Callable[[], bool]


class ProcessingCancelled(RuntimeError):
    pass


class ProcessingController:
    def __init__(
        self,
        config: ProcessingConfig,
        event_callback: EventCallback | None = None,
        cancel_callback: CancelCallback | None = None,
    ) -> None:
        self.config = config
        self.event_callback = event_callback
        self.cancel_callback = cancel_callback

    def _emit(
        self,
        stage: str,
        message_key: str,
        fallback_message: str,
        current: int = 0,
        total: int = 0,
        item_key: str = "",
        **details,
    ) -> None:
        if self.event_callback is not None:
            self.event_callback(
                ProgressEvent(
                    stage=stage,
                    message_key=message_key,
                    fallback_message=fallback_message,
                    current=current,
                    total=total,
                    item_key=item_key,
                    details=details,
                )
            )

    def _check_cancelled(self) -> None:
        if self.cancel_callback is not None and self.cancel_callback():
            raise ProcessingCancelled("Verarbeitung wurde abgebrochen.")

    def run(
        self,
        input_path: Path,
        output_dir: Path,
        recursive: bool = False,
        rebuild_ply: bool = False,
        limit: int = 0,
    ) -> list[ProcessingItem]:
        self.config.validate()
        if limit < 0:
            raise ValueError("limit darf nicht negativ sein.")

        device = require_cuda()
        temp_dir = output_dir / "_temp"
        sbs_dir = output_dir / "sbs"
        anaglyph_dir = output_dir / "anaglyph"
        for directory in (temp_dir, sbs_dir, anaglyph_dir):
            directory.mkdir(parents=True, exist_ok=True)

        images = collect_images(input_path, recursive, output_dir)
        if limit > 0:
            images = images[:limit]
        if not images:
            raise RuntimeError(f"Keine Bilder gefunden: {input_path}")

        self._emit(
            "start",
            "progress.start",
            f"{len(images)} Bild(er)",
            total=len(images),
            count=len(images),
            device=torch.cuda.get_device_name(0),
        )

        suffix = ""
        if self.config.append_settings_to_filename:
            suffix = build_suffix(
                self.config.deviation_permille,
                self.config.window_position_percent,
                self.config.window_back_permille,
                self.config.float_left_permille,
                self.config.float_right_permille,
                self.config.float_top_permille,
                self.config.float_bottom_permille,
            )

        model_signature = checkpoint_signature(self.config.checkpoint_path)
        items: list[ProcessingItem] = []

        for index, image_path in enumerate(images, start=1):
            self._check_cancelled()
            self._emit(
                "preparing",
                "progress.preparing",
                f"Prüfe Cache: {image_path.name}",
                index,
                len(images),
                filename=image_path.name,
            )
            key = make_item_key(image_path, input_path)
            identity = build_cache_identity(
                source_path=image_path,
                checkpoint=model_signature,
                target_height=self.config.target_height,
                fixed_focal_length_mm=self.config.fixed_focal_length_mm,
            )
            ply_path, cache_metadata_path = cache_paths(temp_dir, key, identity)
            output_stem = f"{key}{suffix}"
            sbs_path = sbs_dir / f"{output_stem}_sbs.jpg"
            anaglyph_path = anaglyph_dir / f"{output_stem}_anaglyph.jpg"
            item = ProcessingItem(
                source_path=image_path,
                key=key,
                ply_path=ply_path,
                cache_metadata_path=cache_metadata_path,
                sbs_path=sbs_path,
                anaglyph_path=anaglyph_path,
                cache_identity=identity,
                cache_valid=False,
            )
            cache_valid = is_valid_cache(
                item.ply_path,
                item.cache_metadata_path,
                identity,
            )
            item.cache_valid = cache_valid
            items.append(item)

        pending = [
            item
            for item in items
            if rebuild_ply or not item.cache_valid
        ]

        if pending:
            self._emit(
                "model_loading",
                "progress.model_loading",
                "Lade SHARP-Modell …",
                total=len(pending),
            )
            try:
                with SharpSession(self.config.checkpoint_path, device) as session:
                    self._emit(
                        "model_ready",
                        "progress.model_ready",
                        f"SHARP-Modell geladen ({session.load_seconds:.2f} s)",
                        total=len(pending),
                        load_seconds=session.load_seconds,
                    )
                    for position, item in enumerate(pending, start=1):
                        self._check_cancelled()
                        self._emit(
                            "inference",
                            "progress.inference",
                            f"Erzeuge PLY: {item.source_path.name}",
                            position,
                            len(pending),
                            item.key,
                            filename=item.source_path.name,
                        )
                        try:
                            metrics = session.infer_to_ply(
                                item.source_path,
                                item.ply_path,
                                self.config.target_height,
                                self.config.fixed_focal_length_mm,
                            )
                            try:
                                write_cache_record(
                                    item.cache_metadata_path,
                                    item.ply_path,
                                    item.source_path,
                                    item.cache_identity,
                                )
                            except Exception as cache_exc:
                                self._emit(
                                    "item_warning",
                                    "progress.cache_warning",
                                    f"Cache-Hinweis bei {item.key}: {cache_exc}",
                                    position,
                                    len(pending),
                                    item.key,
                                    filename=item.source_path.name,
                                    error=str(cache_exc),
                                )

                            item.status = "ply_ok"
                            self._emit(
                                "inference_done",
                                "progress.inference_done",
                                f"PLY fertig: {item.key}",
                                position,
                                len(pending),
                                item.key,
                                filename=item.source_path.name,
                                seconds=metrics.inference_seconds,
                            )
                        except Exception as exc:
                            item.status = "fehler_inferenz"
                            self._emit(
                                "item_error",
                                "progress.item_error",
                                f"Inferenzfehler bei {item.key}: {exc}",
                                position,
                                len(pending),
                                item.key,
                                error=str(exc),
                                traceback=traceback.format_exc(),
                            )
                        finally:
                            release_cuda_cache()
            finally:
                release_cuda_cache()

            self._emit(
                "model_released",
                "progress.model_released",
                "SHARP-Modell freigegeben.",
            )
        else:
            self._emit(
                "inference_skipped",
                "progress.cache_used",
                "Alle benötigten PLY-Dateien sind vorhanden.",
                total=len(items),
            )

        render_messages = {
            "loading_ply": ("progress.loading_ply", "Lade 3D-Punktwolke …"),
            "geometry": ("progress.geometry", "Berechne Stereo-Geometrie …"),
            "render_left": ("progress.render_left", "Rendere linke Ansicht …"),
            "render_right": ("progress.render_right", "Rendere rechte Ansicht …"),
            "save_sbs": ("progress.save_sbs", "Speichere SBS …"),
            "anaglyph": ("progress.anaglyph", "Berechne Anaglyphe …"),
            "save_anaglyph": ("progress.save_anaglyph", "Speichere Anaglyphe …"),
        }

        for position, item in enumerate(items, start=1):
            self._check_cancelled()
            if not item.ply_path.is_file():
                if not item.status.startswith("fehler"):
                    item.status = "fehler_ply_fehlt"
                    error = f"3D-Punktwolke fehlt: {item.ply_path}"
                    self._emit(
                        "item_error",
                        "progress.item_error",
                        f"Fehler bei {item.key}: {error}",
                        position,
                        len(items),
                        item.key,
                        filename=item.source_path.name,
                        error=error,
                    )
                continue

            self._emit(
                "rendering",
                "progress.rendering",
                f"Rendere Stereo-SBS: {item.key}",
                position,
                len(items),
                item.key,
                filename=item.source_path.name,
            )

            def render_progress(step: str, fraction: float) -> None:
                key, fallback = render_messages[step]
                self._emit(
                    "render_step",
                    key,
                    fallback,
                    position,
                    len(items),
                    item.key,
                    filename=item.source_path.name,
                    step_fraction=fraction,
                )

            try:
                metrics = render_ply_to_outputs(
                    ply_path=item.ply_path,
                    sbs_path=item.sbs_path,
                    anaglyph_path=item.anaglyph_path,
                    device=device,
                    deviation_permille=self.config.deviation_permille,
                    window_position_percent=self.config.window_position_percent,
                    window_back_permille=self.config.window_back_permille,
                    float_left_permille=self.config.float_left_permille,
                    float_right_permille=self.config.float_right_permille,
                    float_top_permille=self.config.float_top_permille,
                    float_bottom_permille=self.config.float_bottom_permille,
                    gray_anaglyph=self.config.gray_anaglyph,
                    jpeg_quality_sbs=self.config.jpeg_quality_sbs,
                    jpeg_quality_anaglyph=self.config.jpeg_quality_anaglyph,
                    progress_callback=render_progress,
                )
                item.status = "ok"

                if self.config.copy_metadata:
                    self._emit(
                        "metadata",
                        "progress.metadata",
                        f"Übertrage Metadaten: {item.key}",
                        position,
                        len(items),
                        item.key,
                        filename=item.source_path.name,
                    )
                    metadata_result = copy_metadata_to_outputs(
                        self.config.exiftool_path,
                        item.source_path,
                        (item.sbs_path, item.anaglyph_path),
                    )
                    if metadata_result.error:
                        self._emit(
                            "item_warning",
                            "progress.metadata_warning",
                            f"Metadaten-Hinweis bei {item.key}: {metadata_result.error}",
                            position,
                            len(items),
                            item.key,
                            filename=item.source_path.name,
                            error=metadata_result.error,
                        )

                self._emit(
                    "rendering_done",
                    "progress.rendering_done",
                    f"Ausgaben fertig: {item.key}",
                    position,
                    len(items),
                    item.key,
                    filename=item.source_path.name,
                    deviation=metrics.measured_deviation_permille,
                    anaglyph_seconds=metrics.anaglyph_seconds,
                )
            except Exception as exc:
                item.status = "fehler_rendering"
                self._emit(
                    "item_error",
                    "progress.item_error",
                    f"Renderfehler bei {item.key}: {exc}",
                    position,
                    len(items),
                    item.key,
                    error=str(exc),
                    traceback=traceback.format_exc(),
                )
            finally:
                release_cuda_cache()

        ok_count = sum(1 for item in items if item.status == "ok")
        self._emit(
            "finished",
            "progress.finished",
            f"Fertig: {ok_count}/{len(items)} erfolgreich.",
            ok_count,
            len(items),
            ok=ok_count,
            total_count=len(items),
        )
        return items
