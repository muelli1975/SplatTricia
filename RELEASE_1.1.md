## Animation export update — 22 October 2026

- Add animated **WebP**, fixed quality **85**, without a quality selector or lossless option.
- Add animated **AVIF**, fixed quality **60**, **4:4:4**, encoder speed **6**.
- Both formats offer maximum image heights **720/1080/2160 pixels** and **30/60 fps**, preserve the aspect ratio and never enlarge smaller images. Default: **1080p/30 fps**.
- One complete pendulum cycle repeats indefinitely; existing motion and cycle duration are retained.
- Existing GIF, MP4 and PNG-sequence encoding, stereo processing and application defaults are unchanged. The version remains **1.1**.

SplatTricia 1.1 adds optional depth maps and wiggle animations.

- 16-bit grayscale depth PNGs in depth_maps (white near, black far), independent of stereo settings and floating-window curtains.
- Wiggle MP4: H.264 CRF18/slow, 8-bit 4:2:0, 30/60 fps, maximum height 720/1080/2160 pixels; defaults to 1080p/30 fps and contains five cycles.
- Wiggle GIF: 10/15/20/25 fps, default 15 fps, maximum long edge 800 pixels by default, continuous looping.
- PNG frame sequence: 30/60 fps, maximum height 1080/2160 pixels, one cycle in a numbered folder per source image.
- Themed wiggle settings with saved per-format size/frame rate; smaller images are never enlarged.
- Stable GUI geometry when enabling wiggle and starting processing, including long status messages.

Existing stereo geometry, slider behavior and image processing are preserved. Existing saved choices are retained.

Download all three ZIPs and extract each into the same destination directory, merging their SplatTricia folder. The two runtime ZIPs are unchanged by this export update. Existing 1.1 installations need only the updated SplatTricia_1.1.zip.

All runtime libraries and tools are included. A compatible NVIDIA GPU is required. The SHARP checkpoint is not included. Obtain sharp_2572gikvuh.pt separately from https://github.com/apple-aiml-research/ml-sharp, read and accept Apple's model terms before downloading, and place the file in SplatTricia/models. Processing works offline after setup. The previous 1.0 release remains available.
