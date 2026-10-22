from dataclasses import replace
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import numpy as np
from PIL import Image

from splattricia.export_options import WiggleOptions
from splattricia.wiggle_export import export_wiggle, ExportCancelled
from splattricia.animation_checks import check_animation


class AnimatedImageTests(unittest.TestCase):
    def test_webp_slow_gradient_does_not_accumulate_stale_blocks(self):
        """Small per-frame colour changes must not freeze a smooth background."""
        from splattricia.animated_image import encode_animation
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            paths, reference_means = [], []
            for index in range(60):
                ramp = np.linspace(75, 100, 320, dtype=np.float32)[None, :] + round(index / 3)
                rgb = np.zeros((192, 320, 3), dtype=np.uint8)
                rgb[:] = np.stack((ramp + 7, ramp + 1, ramp), axis=2).astype(np.uint8)
                # Keep every frame distinct while the unobstructed background
                # changes by less than one colour level per frame.
                rgb[5:16, 2 * index:2 * index + 10] = (220, 25, 15)
                reference_means.append(rgb[40:160, 160:300].mean(axis=(0, 1)))
                path = root / f'{index:03d}.png'
                with Image.fromarray(rgb) as image:
                    image.save(path)
                paths.append(path)
            output = root / 'gradient.webp'
            encode_animation(paths, output, 'webp', 30, lambda: None)
            check_animation(output, (320, 192), 2000, expected_frames=60)
            with Image.open(output) as animation:
                for index, reference in enumerate(reference_means):
                    animation.seek(index)
                    actual = np.asarray(animation.convert('RGB'))[40:160, 160:300].mean(axis=(0, 1))
                    # Permit ordinary lossy quantization, but not the roughly
                    # 20-level drift produced when keyframes are disabled.
                    self.assertLessEqual(float(np.abs(actual - reference).max()), 4.0,
                                         f'Background drift in frame {index}')

    @staticmethod
    def view(weight):
        rgb = np.zeros((47, 65, 3), dtype=np.uint8)
        rgb[..., 1] = np.arange(65, dtype=np.uint8) * 3
        rgb[:, round(weight * 50):round(weight * 50) + 10, 0] = 255
        return rgb

    def test_new_settings_keep_old_defaults_and_remember_each_format(self):
        old = WiggleOptions.from_settings(dict(format='mp4', video_height=1080, video_fps=60))
        self.assertEqual((old.video_height, old.video_fps), (1080, 60))
        self.assertEqual((old.webp_height, old.avif_height), (1080, 1080))
        options = replace(old, format='avif', avif_height=2160, avif_fps=60,
                          webp_height=1080, webp_fps=30)
        self.assertEqual(WiggleOptions.from_settings(options.to_settings()), options)
        for fmt in ('webp', 'avif'):
            for height in (720, 1080, 2160):
                option = replace(old, format=fmt, **{fmt + '_height': height})
                option.validate()
                self.assertEqual(option.output_size(3840, 2160), (round(height * 16 / 9), height))
                self.assertEqual(option.output_size(65, 47), (65, 47))
            with self.assertRaises(ValueError):
                replace(old, **{fmt + '_height': 800}).validate()

    def test_animation_timing_return_path_and_odd_edges(self):
        for fmt in ('webp', 'avif'):
            for fps in (30, 60):
                with self.subTest(fmt=fmt, fps=fps), tempfile.TemporaryDirectory() as temp:
                    root = Path(temp)
                    output = root / ('animation.' + fmt)
                    options = WiggleOptions(format=fmt, cycle_seconds=1, **{fmt + '_fps': fps})
                    calls = []
                    def render(weight):
                        calls.append(weight)
                        return self.view(weight)
                    export_wiggle(render, (65, 47), options, output, root / '_temp')
                    check_animation(output, (65, 47), 1000)
                    self.assertEqual(len(calls), fps // 2 + 1)
                    with Image.open(output) as image:
                        image.seek(0); image.load(); first = np.asarray(image.convert('RGB'))
                        image.seek(image.n_frames // 2); image.load(); middle = np.asarray(image.convert('RGB'))
                        self.assertGreater(np.abs(first.astype(float) - middle).mean(), 10)
                    self.assertFalse(list((root / '_temp').iterdir()))

    def test_cancel_during_image_encoding_preserves_existing_output(self):
        for fmt in ('webp', 'avif'):
            with self.subTest(fmt=fmt), tempfile.TemporaryDirectory() as temp:
                root = Path(temp); output = root / ('animation.' + fmt)
                output.write_bytes(b'previous completed animation')
                cancelled = False
                def progress(value):
                    nonlocal cancelled
                    cancelled = value > 0.75
                with self.assertRaises(ExportCancelled):
                    export_wiggle(self.view, (65, 47), WiggleOptions(format=fmt), output,
                                  root / '_temp', progress=progress, cancel=lambda: cancelled)
                self.assertEqual(output.read_bytes(), b'previous completed animation')
                self.assertFalse(list((root / '_temp').iterdir()))

    def test_encoder_failure_preserves_existing_output(self):
        original = Image.Image.save
        def fail(image, target, format=None, **settings):
            if format == 'AVIF':
                Path(target).write_bytes(b'incomplete output')
                raise OSError('test encoder failure')
            return original(image, target, format=format, **settings)
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp); output = root / 'animation.avif'; output.write_bytes(b'previous')
            with patch.object(Image.Image, 'save', fail), self.assertRaises(OSError):
                export_wiggle(self.view, (65, 47), WiggleOptions(format='avif'), output, root / '_temp')
            self.assertEqual(output.read_bytes(), b'previous')
            self.assertFalse(list((root / '_temp').iterdir()))


if __name__ == '__main__':
    unittest.main()
