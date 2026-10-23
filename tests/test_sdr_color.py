"""Actual photo-to-MP4 regression, independent matrix/range-only decoding."""
import subprocess
import tempfile
import unittest
from pathlib import Path

import numpy as np
from PIL import Image
from splattricia.export_options import WiggleOptions
from splattricia.wiggle_export import export_wiggle, ffmpeg_path


class SDRPhotoExportTests(unittest.TestCase):
    def test_mp4_preserves_gray_and_color_patch_values(self):
        grays = [0, 16, 32, 64, 96, 128, 192, 255]
        colors = [(64,96,128),(160,64,96),(96,160,64),(64,96,160),
                  (192,128,64),(128,64,192),(64,192,128),(160,160,96)]
        image = Image.new("RGB", (256, 128))
        for i, value in enumerate(grays):
            image.paste((value,value,value), (32*i,0,32*(i+1),64))
            image.paste(colors[i], (32*i,64,32*(i+1),128))
        rgb = np.array(image)
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            output = root / "chart.mp4"
            export_wiggle(lambda weight: rgb, image.size,
                          WiggleOptions(cycle_seconds=.5), output, root / "_temp")
            result = subprocess.run(
                [ffmpeg_path(), "-v", "error", "-i", str(output), "-frames:v", "1",
                 "-vf", "scale=in_color_matrix=bt709:in_range=limited:out_range=full",
                 "-f", "rawvideo", "-pix_fmt", "rgb24", "-"],
                check=True, capture_output=True)
            decoded = np.frombuffer(result.stdout, np.uint8).reshape(128,256,3)
            for i, value in enumerate(grays):
                sample = decoded[24:40,32*i+8:32*i+24].astype(float).mean(axis=(0,1))
                self.assertLessEqual(float(np.max(np.abs(sample-value))), 2.1, (value,sample))
                sample = decoded[88:104,32*i+8:32*i+24].astype(float).mean(axis=(0,1))
                self.assertLessEqual(float(np.max(np.abs(sample-colors[i]))), 4.1, (colors[i],sample))


if __name__ == "__main__":
    unittest.main()
