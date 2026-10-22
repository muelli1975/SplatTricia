# SplatTricia 1.1

- Add optional 16-bit depth-map PNG export.
- Add wiggle animations as MP4, looping GIF, WebP, AVIF or PNG frame sequences.
- Improve animated WebP compression and reduce block artifacts in smooth areas.
- Save animation size and frame rate separately for each format.
- Fix window resizing when enabling wiggle export or starting processing.

## Installation

Windows 10/11 and a compatible NVIDIA graphics card are required. Download all three ZIP files and extract them into the same destination, merging their `SplatTricia` folders. Start `SplatTricia.exe`.

The SHARP checkpoint is supplied separately. Obtain `sharp_2572gikvuh.pt` from [Apple's official SHARP project](https://github.com/apple-aiml-research/ml-sharp), read and accept Apple's model terms before downloading, and place the file in `SplatTricia/models`. Processing works offline after setup.

Existing 1.1 installations need only the updated `SplatTricia_1.1.zip`; the two runtime ZIPs are unchanged. Keep `settings.json` and your model file when updating.
