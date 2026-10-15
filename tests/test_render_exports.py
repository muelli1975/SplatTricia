"""Exercise the real camera setup and export integration with a deterministic rasterizer.

This checks data flow without claiming a CUDA/inference quality test.
"""
from dataclasses import replace
from pathlib import Path
from types import SimpleNamespace

import numpy as np
from PIL import Image
import pytest
import torch

from splattricia.export_options import WiggleOptions


def test_render_exports_preserve_stereo_and_use_original_depth_camera(tmp_path, monkeypatch):
    from splattricia import renderer as module
    points = torch.tensor([[-.1, -.1, 2.], [.1, .1, 3.], [0., 0., 5.]])
    class Gaussians:
        mean_vectors = points
        def to(self, device):
            return self
    monkeypatch.setattr(module, 'load_ply', lambda path: (Gaussians(), SimpleNamespace(
        resolution_px=(64, 48), focal_length_px=50., color_space='sRGB')))
    monkeypatch.setattr(torch.cuda, 'synchronize', lambda: None)
    cameras = []
    class Renderer:
        def __init__(self, **kwargs):
            pass
        def to(self, device):
            return self
        def __call__(self, g, *, extrinsics, intrinsics, image_width, image_height):
            cameras.append((extrinsics.clone(), intrinsics.clone()))
            return SimpleNamespace(color=torch.full((1,3,48,64), .5),
                                   depth=torch.linspace(1,5,64).expand(1,1,48,64),
                                   alpha=torch.ones(1,1,48,64))
    monkeypatch.setattr(module, 'GSplatRenderer', Renderer)
    common = dict(ply_path=tmp_path/'fake.ply', device=torch.device('cpu'), deviation_permille=15,
                  window_position_percent=100, window_back_permille=2,
                  float_left_permille=5, float_right_permille=5, float_top_permille=0, float_bottom_permille=0,
                  gray_anaglyph=False, jpeg_quality_sbs=95, jpeg_quality_anaglyph=90)
    module.render_ply_to_outputs(**common, sbs_path=tmp_path/'before.jpg', anaglyph_path=tmp_path/'before_a.jpg')
    original_cameras = cameras[:]
    cameras.clear()
    module.render_ply_to_outputs(**common, sbs_path=tmp_path/'after.jpg', anaglyph_path=tmp_path/'after_a.jpg',
                                 depth_path=tmp_path/'depth.png', wiggle_path=tmp_path/'frames',
                                 wiggle_options=WiggleOptions(format='png', cycle_seconds=.5), temp_root=tmp_path/'_temp')
    assert (tmp_path/'before.jpg').read_bytes() == (tmp_path/'after.jpg').read_bytes()
    assert (tmp_path/'before_a.jpg').read_bytes() == (tmp_path/'after_a.jpg').read_bytes()
    for before, after in zip(original_cameras, cameras[:2]):
        assert torch.equal(before[0], after[0]) and torch.equal(before[1], after[1])
    assert torch.equal(cameras[2][0][0], torch.eye(4))
    assert cameras[2][1][0,0,2].item() == 32
    with Image.open(tmp_path/'depth.png') as image:
        assert image.size == (64,48)
    with Image.open(tmp_path/'frames/000001.png') as image:
        # Curtains remain in the stereo JPGs but are never applied to wiggle.
        assert np.asarray(image)[0,0].tolist() == [128,128,128]
