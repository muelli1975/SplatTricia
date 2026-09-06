# SplatTricia 1.0

SplatTricia is a local Windows tool for experimental conversion of individual 2D images or complete image folders into stereoscopic 3D. For each image it generates a parallel side-by-side stereo image (SBS) and, optionally, a color or grayscale anaglyph.

The 3D reconstruction is based on **Apple SHARP**. SplatTricia processes images locally, performs no automatic model downloads, and does not require cloud services or an online connection during use.

**Deutsch:** [README_DE.md](README_DE.md)

## Requirements

- Windows 10 or 11
- compatible NVIDIA GPU with a current driver
- a locally provided SHARP checkpoint at `models\sharp_2572gikvuh.pt`

The SHARP checkpoint is **not part of SplatTricia** and is not provided in this repository. SHARP and the model remain subject to Apple's own license terms.

## Basic concept

SplatTricia creates two parallel views from the scene reconstructed by SHARP. **Deviation** controls the horizontal depth range of the generated stereo scene. **Window position** determines how that depth is placed relative to the stereo window. **Floating-window curtains** can mask edge regions without changing the geometry of the scene itself.

Automatic 2D-to-3D conversion remains a geometric estimate. For projection or other demanding uses, deviation, window position, and image borders should be checked visually.

## Output

SplatTricia generates:

- parallel side-by-side stereo images
- optional color or grayscale anaglyphs
- a reusable PLY cache for fast re-rendering with different stereo settings

Where technically possible, metadata from suitable source files is copied to the final JPEG outputs.

## Source code

This repository exists to publish and preserve the SplatTricia source code. Build notes, a release checklist, and documented design, state, and folder rules are included as well.

Active maintenance, support, or the handling of issues and pull requests cannot be guaranteed.

The SplatTricia code and original documentation created by Christoph Müller are released under the **MIT License**. SHARP and all other third-party components retain their respective licenses; the SplatTricia MIT License does not alter those terms.

## Windows version

The current 1.0 release is available here:

https://traumnarben.de/download/SplatTricia_1.0.zip

The download link may later move to the StereoFine website.
