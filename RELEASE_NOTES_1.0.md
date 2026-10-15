# SplatTricia 1.0

SplatTricia 1.0 is the first stable public release of the local Windows tool for converting individual 2D images or complete image folders into stereo 3D.

Depth reconstruction is based on **Apple SHARP** and runs locally on the user's own computer. SplatTricia produces parallel side-by-side stereo images (SBS) together with either colour or grayscale anaglyphs. Deviation, stereo-window position and Floating Window masks can be adjusted, and cached PLY point clouds can be reused for later re-rendering without running SHARP again.

## Windows download and setup

Download all three ZIP files from the [SplatTricia 1.0 release](https://github.com/muelli1975/SplatTricia/releases/tag/v1.0):

- `SplatTricia_1.0.zip` — application, tools, documentation and licenses
- `SplatTricia_1.0_Runtime_1.zip` — runtime libraries, part 1
- `SplatTricia_1.0_Runtime_2.zip` — runtime libraries, part 2

1. Extract **every ZIP into the same destination directory**, merging their shared `SplatTricia` subfolder. Do not extract them into separate folders named after each archive.
2. Obtain the SHARP checkpoint yourself from [Apple's official project](https://github.com/apple-aiml-research/ml-sharp). Read and accept Apple's model terms before downloading.
3. Place `sharp_2572gikvuh.pt` in `SplatTricia\models`.
4. Start `SplatTricia\SplatTricia.exe`.

All runtime libraries are included. No separate Python installation, CUDA toolkit or build tools are required. Processing works offline after setup.

The application and runtime files are unchanged from the original 1.0 distribution. A bilingual `INSTALLATION.txt` is included. `SplatTricia_1.0_SHA256SUMS.txt` provides download checksums; the accompanying manifest records the unchanged original files.

## SHARP checkpoint

The Apple SHARP checkpoint is **not included** in the portable package and is not part of this repository. Users must obtain the checkpoint from [Apple's official project](https://github.com/apple-aiml-research/ml-sharp), read and accept the model terms, and provide it separately at:

`models\sharp_2572gikvuh.pt`

Apple's own model license terms apply to SHARP and the checkpoint.

## License

SplatTricia source code and original documentation created by Christoph Müller are released under the **MIT License**. Apple SHARP and all other third-party components remain subject solely to their respective original licenses and are treated separately from the SplatTricia MIT license.
