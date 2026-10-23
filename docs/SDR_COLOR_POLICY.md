# SDR photo and video export policy

Authorized by Christoph on 23 October 2026. Preserve the agreed renderer,
anaglyph mathematics, precision, sizing, codecs and quality settings.

Finished sRGB photographs retain their encoded tone values when exported to
ordinary SDR video. Convert RGB/YCbCr matrices, primaries where required, and
full/limited range explicitly. Mark the final conventional HD SDR signal as
BT.709 primaries/matrix/transfer, limited range. Do not add the previous
sRGB-to-BT.1886 tone remapping at the photo output boundary.

Ordinary BT.709 and SMPTE170M SDR video uses the same display-value convention
on input. Input and output adapters must agree; changing output alone would
darken existing video. Other explicitly supported transfer functions keep their
separate conversion. Do not turn this into a rule for HDR or scene-linear data.

Anaglyph methods retain their own required sRGB/linear transformations.
The frame-rate-only path retains source interpretation. Native limited-range
BT.709 YUV420 Blu-ray input keeps its existing bypass. RGB photo/intermediate
input to Blu-ray uses the same conventional SDR tone-value policy.

DiaDoris keeps photo rendering, preview, VideoReader, embedded TransCora and
export consistent. Its embedded engine is a separate checked-in copy; updating
the TransCora repository does not update DiaDoris automatically.

Reference implementation (source inspection, not an assertion about every editor):
- Shotcut: src/settings.cpp, Native8Cpu default; src/docks/encodedock.cpp.
  https://github.com/mltframework/shotcut
- MLT: src/modules/qt/qimage_wrapper.cpp;
  src/modules/avformat/filter_avcolour_space.c (matrix/range via swscale);
  src/modules/avformat/consumer_avformat.c (output color metadata).
  https://github.com/mltframework/mlt
- Chromium: ui/gfx/color_space.cc, GetTransferFunction groups BT709 and
  SMPTE170M with sRGB for display.
  https://github.com/chromium/chromium/blob/main/ui/gfx/color_space.cc

Regression checks use actual encoded and decoded gray/color patches, RGB photo
exports, limited/full-range SDR video round trips, frame-rate-only output,
native and RGB Blu-ray preparation, and (DiaDoris) matching photo/video slides.
Decode comparison uses matrix/range reconstruction, independently of the export
graph. Flat-patch tolerances allow codec/quantization error, not a systematic
tone curve. Packaging smoke tests and GPU inference tests are different evidence.
No claim of identical appearance in every player or calibrated display follows.
