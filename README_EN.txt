SplatTricia 1.0
=================

SplatTricia is a local Windows tool for automatically converting individual 2D
images or complete image folders into stereo 3D. Each image produces a parallel
side-by-side stereo image (SBS) and either a colour or grayscale anaglyph.

The 3D reconstruction is based on Apple SHARP. SplatTricia processes images
locally, performs no automatic model downloads, and does not require cloud or
online services for normal use.

Requirements
------------
- Windows 10 or 11
- compatible NVIDIA graphics card with a current driver
- locally supplied SHARP checkpoint:

    models\sharp_2572gikvuh.pt

The SHARP checkpoint is not part of SplatTricia and must be supplied by the user
in the models folder. Apple's model license terms apply; see LICENSES.txt.

Basic use
---------
1. Select a single image or an image folder.
2. Use an output folder beside the input or select a custom output folder.
3. Set the desired deviation and stereo-window position.
4. Add floating-window curtains when required.
5. Select colour or grayscale anaglyph output.
6. Click “Start”.

Stereo controls
---------------
Deviation controls the horizontal depth range of the generated stereo scene.
Stereo-window position determines how that depth is distributed relative to the
picture plane. The additional window backshift is available only at a window
position of 100%. Floating-window curtains mask edge areas without changing the
scene geometry itself.

Automatic 2D-to-3D conversion remains a geometric estimate. For projection or
other demanding uses, deviation, window placement and image edges should be
checked visually.

Output
------
The selected output location contains:

- sbs: parallel side-by-side stereo images
- anaglyph: colour or grayscale anaglyphs
- _temp: cached PLY point clouds and validation data

Valid PLY files can be reused, allowing stereo settings to be rendered again
without running SHARP a second time. “Delete temporary files” removes only
_temp; finished images remain untouched.

Existing output images are replaced without prompting. “Append settings to
filename” can be used to keep deliberately created variants side by side.

Metadata
--------
Where technically possible, SplatTricia copies metadata from suitable source
files to the finished JPEG outputs. Image orientation is already applied during
processing.

Source code and long-term use
-----------------------------
The portable folder contains, under source, the exact SplatTricia source state
for this version together with build notes and a release checklist. This is
intended to keep the program understandable, maintainable and usable for future
development. SplatTricia source code and original documentation created by
Christoph Müller are licensed under the MIT License. Third-party components and
SHARP remain subject solely to their respective licenses.

Licenses
--------
LICENSE.txt contains the MIT License for SplatTricia itself. LICENSES.txt contains
license terms and notices for SHARP and the third-party components used by
SplatTricia.

Error log
---------
For technical failures, SplatTricia writes details to splattricia_error.log
beside the EXE.
