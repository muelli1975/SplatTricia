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
    @staticmethod
    def view(weight):
        rgb = np.zeros((47, 65, 3), dtype=np.uint8)
        rgb[..., 1] = np.arange(65, dtype=np.uint8) * 3
        rgb[:, round(weight * 50):round(weight * 50) + 10, 0] = 255
        return rgb

    def test_new_settings_keep_old_defaults_and_remember_each_format(self):
        old = WiggleOptions.from_settings(dict(format='mp4', video_height=1080, video_fps=60))
        self.assertEqual((old.video_height, old.video_fps), (1080, 60))
        self.assertEqual(old.avif_height, 1080)
        options = replace(old, format='avif', avif_height=2160, avif_fps=60)
        self.assertEqual(WiggleOptions.from_settings(options.to_settings()), options)
        for fmt in ('avif',):
            for height in (720, 1080, 2160):
                option = replace(old, format=fmt, **{fmt + '_height': height})
                option.validate()
                self.assertEqual(option.output_size(3840, 2160), (round(height * 16 / 9), height))
                self.assertEqual(option.output_size(65, 47), (65, 47))
            with self.assertRaises(ValueError):
                replace(old, **{fmt + '_height': 800}).validate()

    def test_removed_saved_format_preserves_other_preferences(self):
        saved = dict(format='webp', webp_height=2160, webp_fps=60,
                     video_height=2160, video_fps=60, gif_fps=25,
                     avif_height=720, avif_fps=60, cycle_seconds=3.0)
        original = saved.copy()
        restored = WiggleOptions.from_settings(saved)
        self.assertEqual(restored.format, 'mp4')
        self.assertEqual((restored.video_height, restored.video_fps), (2160, 60))
        self.assertEqual((restored.avif_height, restored.avif_fps), (720, 60))
        self.assertEqual((restored.gif_fps, restored.cycle_seconds), (25, 3.0))
        self.assertEqual(saved, original)
        self.assertNotIn('webp_height', restored.to_settings())
        self.assertNotIn('webp_fps', restored.to_settings())
        with self.assertRaises(ValueError):
            WiggleOptions(format='webp').validate()

    def test_animation_timing_return_path_and_odd_edges(self):
        for fmt in ('avif',):
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
        for fmt in ('avif',):
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
