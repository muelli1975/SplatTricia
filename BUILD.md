# SplatTricia 1.0 build notes

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
