# SplatTricia 1.0

Convert individual 2D photographs or image folders into stereo 3D using Apple SHARP.

- Export parallel SBS and colour or grayscale anaglyph JPEGs.
- Adjust deviation, stereo-window position and floating-window curtains.
- Reuse cached reconstructions when changing stereo settings.
- German and English interface.

## Installation

Windows and a compatible NVIDIA graphics card are required. Download all three ZIP files and extract them into the same destination, merging their `SplatTricia` folders. Start `SplatTricia.exe`.

Obtain `sharp_2572gikvuh.pt` from [Apple's official SHARP project](https://github.com/apple-aiml-research/ml-sharp), read and accept Apple's model terms before downloading, and place the file in `SplatTricia/models`. The checkpoint is not included. Processing works offline after setup.
