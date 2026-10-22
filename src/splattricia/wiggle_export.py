"""Bounded-memory animation encoding from rendered camera views."""
from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
import shutil
import subprocess
import tempfile
import time

import numpy as np
from PIL import Image

from .export_options import WiggleOptions, cycle_index, camera_weight, gif_frame_durations
from .output_writer import _replace_with_retry


class ExportCancelled(RuntimeError):
    pass


def check_cancelled(callback) -> None:
    if callback is not None and callback():
        raise ExportCancelled("Verarbeitung wurde abgebrochen / processing cancelled.")


def ffmpeg_path() -> str:
    # imageio-ffmpeg ships its executable. No download or PATH lookup at runtime.
    from imageio_ffmpeg import get_ffmpeg_exe
    executable = get_ffmpeg_exe()
    if not Path(executable).is_file():
        raise FileNotFoundError("Die mitgelieferte FFmpeg-Datei fehlt / bundled FFmpeg is missing.")
    return executable


def _run_ffmpeg(arguments: list[str], log: Path, cancel, write=None) -> None:
    flags = getattr(subprocess, "CREATE_NO_WINDOW", 0)
    with log.open("wb") as errors:
        process = subprocess.Popen([ffmpeg_path(), "-hide_banner", "-loglevel", "error", "-nostdin", "-y", *arguments],
                                   stdin=subprocess.PIPE if write else subprocess.DEVNULL,
                                   stdout=subprocess.DEVNULL, stderr=errors, creationflags=flags)
        try:
            if write:
                write(process.stdin)
                process.stdin.close()
            while process.poll() is None:
                check_cancelled(cancel)
                time.sleep(0.05)
            if process.returncode:
                raise RuntimeError("FFmpeg: " + log.read_text(errors="replace")[-3000:])
        except BrokenPipeError as exc:
            if process.poll() is None:
                process.kill()
            process.wait()
            raise RuntimeError("FFmpeg: " + log.read_text(errors="replace")[-3000:]) from exc
        except BaseException:
            if process.poll() is None:
                process.kill()
            process.wait()
            raise


def export_wiggle(render_view: Callable[[float], np.ndarray], source_size: tuple[int, int],
                  options: WiggleOptions, output: Path, temp_root: Path,
                  progress: Callable[[float], None] | None = None, cancel=None) -> None:
    """Render each distinct view once, mirror the return path, then encode."""
    options.validate()
    output.parent.mkdir(parents=True, exist_ok=True)
    temp_root.mkdir(parents=True, exist_ok=True)
    size = options.output_size(*source_size)
    count = options.frame_count
    with tempfile.TemporaryDirectory(prefix="wiggle_", dir=temp_root) as directory:
        work = Path(directory)
        paths = []
        for index in range(count // 2 + 1):
            check_cancelled(cancel)
            rgb = render_view(camera_weight(index, count))
            with Image.fromarray(rgb) as image:
                if image.size != size:
                    image = image.resize(size, Image.Resampling.LANCZOS)
                path = work / f"view_{index:06d}.png"
                image.save(path, format="PNG")
            paths.append(path)
            if progress:
                progress(0.7 * (index + 1) / (count // 2 + 1))
        sequence = [paths[cycle_index(i, count)] for i in range(count)]
        if options.format == "mp4":
            cycle = work / "cycle.mp4"
            # Match TransCora: sRGB -> Rec.709, H.264 CRF18/slow, 8-bit 4:2:0.
            # Padding is at most one pixel and never removes source image edges.
            video_filter = ("pad=ceil(iw/2)*2:ceil(ih/2)*2:0:0:black,format=gbrp,"
                            "zscale=matrixin=gbr:primariesin=709:transferin=iec61966-2-1:rangein=full:"
                            "matrix=709:primaries=709:transfer=709:range=limited,format=yuv420p")
            def write(stream):
                for index, path in enumerate(sequence):
                    check_cancelled(cancel)
                    with Image.open(path) as frame:
                        stream.write(frame.convert("RGB").tobytes())
                    if progress:
                        progress(0.7 + 0.2 * (index + 1) / count)
            _run_ffmpeg(["-f", "rawvideo", "-pixel_format", "rgb24", "-video_size", f"{size[0]}x{size[1]}",
                         "-framerate", str(options.fps), "-i", "pipe:0", "-an", "-vf", video_filter,
                         "-c:v", "libx264", "-crf", "18", "-preset", "slow", "-pix_fmt", "yuv420p",
                         "-colorspace", "bt709", "-color_primaries", "bt709", "-color_trc", "bt709",
                         "-color_range", "tv", str(cycle)], work / "encode.log", cancel, write)
            temporary = work / "finished.mp4"
            try:
                _run_ffmpeg(["-stream_loop", "4", "-i", str(cycle), "-map", "0:v:0", "-an", "-c:v", "copy",
                             "-movflags", "+faststart", str(temporary)], work / "repeat.log", cancel)
                check_cancelled(cancel)
                _replace_with_retry(temporary, output)
            finally:
                temporary.unlink(missing_ok=True)
        elif options.format in {"webp", "avif"}:
            from .animated_image import encode_animation
            temporary = work / ("finished." + options.format)
            try:
                encode_animation(sequence, temporary, options.format, options.fps,
                                 lambda: check_cancelled(cancel), progress)
                check_cancelled(cancel)
                _replace_with_retry(temporary, output)
            finally:
                temporary.unlink(missing_ok=True)
        elif options.format == "gif":
            # A shared palette prevents per-frame palette changes. Construct it
            # from small samples of all distinct views, not just the first image.
            samples = []
            for path in paths:
                with Image.open(path) as image:
                    image.thumbnail((128, 128), Image.Resampling.LANCZOS)
                    samples.append(np.asarray(image.convert("RGB")).reshape(-1, 3))
            atlas = Image.fromarray(np.concatenate(samples).reshape(-1, 1, 3))
            palette = atlas.quantize(colors=256, method=Image.Quantize.MEDIANCUT)
            frames = []
            try:
                for index, path in enumerate(sequence):
                    check_cancelled(cancel)
                    with Image.open(path) as image:
                        frames.append(image.convert("RGB").quantize(palette=palette, dither=Image.Dither.FLOYDSTEINBERG))
                    if progress:
                        progress(0.7 + 0.2 * (index + 1) / count)
                temporary = work / "finished.gif"
                try:
                    frames[0].save(temporary, format="GIF", save_all=True, append_images=frames[1:],
                                   loop=0, duration=gif_frame_durations(count, options.fps), disposal=2, optimize=False)
                    check_cancelled(cancel)
                    _replace_with_retry(temporary, output)
                finally:
                    temporary.unlink(missing_ok=True)
            finally:
                palette.close()
                atlas.close()
                for frame in frames:
                    frame.close()
        else:
            # The caller places _temp beside wiggle in the selected output root.
            staged = work / "new_frames"
            backup = work / "previous_frames"
            staged.mkdir()
            try:
                for index, path in enumerate(sequence, start=1):
                    check_cancelled(cancel)
                    shutil.copyfile(path, staged / f"{index:06d}.png")
                    if progress:
                        progress(0.7 + 0.2 * index / count)
                if output.exists():
                    output.replace(backup)
                try:
                    staged.replace(output)
                except BaseException:
                    if backup.exists():
                        backup.replace(output)
                    raise
            finally:
                if staged.exists():
                    shutil.rmtree(staged)
                if backup.exists() and output.exists():
                    shutil.rmtree(backup)
        if progress:
            progress(1.0)
