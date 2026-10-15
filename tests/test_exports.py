from dataclasses import replace
import json
from pathlib import Path
import subprocess

import numpy as np
from PIL import Image, ImageSequence
import pytest

from splattricia.depth_export import depth_pixels, save_depth_png
from splattricia.export_options import WiggleOptions, camera_weight, cycle_index, gif_frame_durations
from splattricia.wiggle_export import export_wiggle, ffmpeg_path, ExportCancelled


def view(weight):
    image = np.zeros((47, 64, 3), dtype=np.uint8)
    image[..., 1] = np.arange(64, dtype=np.uint8) * 4
    image[:, round(weight * 50):round(weight * 50) + 10, 0] = 255
    return image


def test_depth_is_inverse_and_invalid_background_stays_far(tmp_path):
    depth = np.array([[1, 2, 4], [0, np.nan, .001]])
    alpha = np.array([[1, 1, 1], [1, 1, 0]])
    pixels = depth_pixels(depth, alpha)
    assert pixels.tolist() == [[65535, 21845, 0], [0, 0, 0]]
    target = tmp_path / 'depth.png'
    save_depth_png(depth, alpha, target)
    with Image.open(target) as im:
        assert im.size == (3, 2)
        assert np.asarray(im).tolist() == pixels.tolist()
        assert 'gamma' not in im.info


def test_cycle_has_no_duplicated_endpoint_and_reuses_return_views():
    count = 60
    assert [cycle_index(i, count) for i in (0, 1, 29, 30, 31, 59)] == [0, 1, 29, 30, 29, 1]
    assert camera_weight(0, count) == 0
    assert camera_weight(30, count) == 1
    assert camera_weight(59, count) == pytest.approx(camera_weight(1, count))


def test_options_preserve_settings_per_format_and_do_not_upscale():
    assert WiggleOptions().gif_fps == 15
    o = WiggleOptions(video_fps=60, gif_fps=10, png_height=2160)
    assert WiggleOptions.from_settings(o.to_settings()) == o
    assert o.output_size(640, 480) == (640, 480)
    assert o.output_size(3000, 4000) == (810, 1080)
    assert replace(o, format='gif').output_size(3000, 4000) == (600, 800)
    assert WiggleOptions.from_settings({'video_fps': 'bad'}) == WiggleOptions()
    mp4 = WiggleOptions(video_height=720)
    mp4.validate()
    assert mp4.output_size(3840, 2160) == (1280, 720)
    assert mp4.output_size(480, 640) == (480, 640)
    with pytest.raises(ValueError):
        WiggleOptions(format='png', png_height=720).validate()


def test_png_sequence_replaces_whole_previous_cycle(tmp_path):
    output = tmp_path / 'wiggle' / 'photo_30fps_frames'
    output.mkdir(parents=True)
    (output / '999999.png').write_bytes(b'old frame')
    o = WiggleOptions(format='png', cycle_seconds=.5)
    rendered = []
    def render(w):
        rendered.append(w)
        return view(w)
    export_wiggle(render, (64, 47), o, output, tmp_path / '_temp')
    frames = sorted(output.glob('*.png'))
    assert len(frames) == 15
    assert len(rendered) == 8
    assert frames[0].name == '000001.png' and frames[-1].name == '000015.png'
    with Image.open(frames[1]) as a, Image.open(frames[-1]) as b:
        assert a.tobytes() == b.tobytes()
    assert not list((tmp_path / '_temp').iterdir())


@pytest.mark.parametrize('fps', [10, 15, 20, 25])
def test_gif_loop_and_timing(tmp_path, fps):
    o = WiggleOptions(format='gif', gif_fps=fps, cycle_seconds=1)
    output = tmp_path / f'{fps}.gif'
    export_wiggle(view, (64, 47), o, output, tmp_path / '_temp')
    with Image.open(output) as im:
        assert im.info['loop'] == 0
        assert im.size == (64, 47)
        assert sum(frame.info['duration'] for frame in ImageSequence.Iterator(im)) == 1000


def test_15fps_timing_has_no_cumulative_drift():
    durations = gif_frame_durations(450, 15)
    assert set(durations) == {60, 70}
    assert sum(durations) == 30000
    elapsed = 0
    for index, duration in enumerate(durations, start=1):
        elapsed += duration
        assert abs(elapsed - index * 1000 / 15) <= 5
    for fps in (10, 20, 25):
        assert gif_frame_durations(fps, fps) == [1000 // fps] * fps


@pytest.mark.parametrize('fps', [30, 60])
def test_mp4_has_five_cycles_and_keeps_odd_image_edges(tmp_path, fps):
    o = WiggleOptions(video_fps=fps, cycle_seconds=.5)
    output = tmp_path / f'{fps}.mp4'
    export_wiggle(view, (64, 47), o, output, tmp_path / '_temp')
    result = subprocess.run([ffmpeg_path(), '-hide_banner', '-loglevel', 'error', '-i', str(output),
                             '-f', 'rawvideo', '-pix_fmt', 'rgb24', 'pipe:1'], capture_output=True, check=True)
    assert len(result.stdout) == o.frame_count * 5 * 64 * 48 * 3


def test_cancel_keeps_existing_output_and_removes_work_files(tmp_path):
    output = tmp_path / 'photo.gif'
    output.write_bytes(b'previous')
    calls = 0
    def cancel():
        nonlocal calls
        calls += 1
        return calls > 3
    with pytest.raises(ExportCancelled):
        export_wiggle(view, (64, 47), WiggleOptions(format='gif'), output, tmp_path / '_temp', cancel=cancel)
    assert output.read_bytes() == b'previous'
    assert not list((tmp_path / '_temp').iterdir())
