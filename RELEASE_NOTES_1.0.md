# SplatTricia 1.0

SplatTricia 1.0 is the first stable public release of the local Windows tool for converting individual 2D images or complete image folders into stereo 3D.

Depth reconstruction is based on **Apple SHARP** and runs locally on the user's own computer. SplatTricia produces parallel side-by-side stereo images (SBS) together with either colour or grayscale anaglyphs. Deviation, stereo-window position and Floating Window masks can be adjusted, and cached PLY point clouds can be reused for later re-rendering without running SHARP again.

## Windows download

The complete portable Windows package is hosted on the project website because its size exceeds GitHub's per-file Release asset limit:

https://traumnarben.de/download/SplatTricia_1.0.zip

No installation is required; extract the archive and keep the supplied folder structure together.

## SHARP checkpoint

The Apple SHARP checkpoint is **not included** in the portable package and is not part of this repository. Users must provide the checkpoint separately at:

`models\sharp_2572gikvuh.pt`

Apple's own model license terms apply to SHARP and the checkpoint.

## License

SplatTricia source code and original documentation created by Christoph Müller are released under the **MIT License**. Apple SHARP and all other third-party components remain subject solely to their respective original licenses and are treated separately from the SplatTricia MIT license.
