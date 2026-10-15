# SplatTricia 1.1 development build notes

SplatTricia is developed and built on Windows. The release is intentionally a
portable onedir application; users do not need a Python installation.

## Reference environment

- Windows 10/11, 64 bit
- Python 3.12
- PyTorch with CUDA support
- NVIDIA CUDA-capable GPU
- Microsoft C++ build tools and a compatible CUDA toolkit are required only to
  compile the native gsplat extension for a release build.

The build script writes `requirements-lock.txt` with `pip list --format=freeze`
so that the Python package environment of the release remains documented.

## Local directories

The development root contains these relevant directories:

- `src/splattricia` - application source
- `assets` - application icon and completion sound
- `models` - locally supplied model checkpoint; never distributed
- `tools` - locally supplied ExifTool files; not part of the source snapshot
- `_src` - local third-party source trees used only while building native
  components; not part of the source snapshot

## SHARP

The application expects the SHARP checkpoint at:

`models\sharp_2572gikvuh.pt`

The checkpoint is not distributed with SplatTricia. Apple's own model license
applies.

SHARP is integrated locally through the project's backend and must not be
silently downloaded at runtime.

## Native gsplat extension

The release build prepares a native gsplat CUDA extension for multiple NVIDIA
architectures. This is required so that the finished onedir build can render
without requiring Ninja, Visual Studio or a CUDA toolkit on the target system.

`prepare_gsplat_native.py` performs this build preparation. The exact supported
architecture list is defined there and in `build_portable.bat`.

## Building

Create and activate a suitable virtual environment, install the dependencies,
provide the required local third-party source/build components, and run:

`build_portable.bat`

The script:

1. removes old build output;
2. records the Python environment in `requirements-lock.txt`;
3. builds/prepares the multi-architecture gsplat extension;
4. runs PyInstaller in onedir mode;
5. copies runtime assets and required local tools;
6. generates the aggregated third-party `LICENSES.txt`;
7. creates the `source` snapshot from an explicit allow-list;
8. runs release verification;
9. creates `SplatTricia_1.0.zip`.

## Source snapshot

`prepare_source_bundle.py` copies the exact relevant project source into the
release `source` directory. The snapshot contains application code, build and
verification scripts, documentation, original project assets and the generated
requirements lock, but not the virtual environment, build directories, local
models, user settings, logs, output images or local third-party source trees.

The source snapshot is therefore meant as a reproducible reference for the
corresponding release, not as a complete backup of the developer workstation.

The archive contains a single `SplatTricia` application folder. Application folders and executable names remain independent of version and architecture; those belong in the download archive name.

## GitHub packaging of the existing 1.0 release

The GitHub release distributes the existing portable application as
`SplatTricia_1.0.zip` plus two `SplatTricia_1.0_Runtime_*.zip` files.
Extract all three into the same destination directory, merging their shared
`SplatTricia` folder.

`scripts/package_existing_release.py` performs the one-time migration from the
previously hosted archive. It requires the independently audited original
SHA-256 checksum, copies compressed ZIP entries without rebuilding the program,
adds a bilingual installation note, and verifies every original file by SHA-256.
No SHARP checkpoint is included. The publication workflow downloads every
uploaded asset again and verifies its checksum before updating the release notes.

The original Windows build script still produces the complete monolithic
archive; the migration script describes the packaging of this existing build,
not a new application build.


## 1.1 test application

The preview preserves the independently verified 1.0 runtime libraries,
third-party Python code, native CUDA extension and frozen runtime hooks.
`Preview.spec` reads the published dependency archive, replaces only the
SplatTricia application modules, and rebuilds a normal frozen Windows EXE
with PyInstaller 6.22.0 and Python 3.12. No source-path override is used.
The JSON language resources are copied into the application's resource folder.

`scripts/assemble_preview.py` checks every base ZIP before extraction and
verifies every preserved original runtime file. The exact new source and
build scripts are included in the source snapshot. The Windows workflow
requires the rebuilt EXE to report version 1.1 and complete its GUI/encoder
self-test. This checks German/English layout and widget scaling, the themed
dialog, saved settings, 16-bit PNG and actual MP4/GIF/PNG-sequence encoding.
It does not claim a CUDA rendering or SHARP inference test. Camera/export
integration is tested separately with a deterministic rasterizer.

Only after these checks does the workflow publish a separately marked
prerelease with three ordinary ZIP files. The stable 1.0 remains unchanged.
A final 1.1 release requires visual assessment on an NVIDIA GPU.
