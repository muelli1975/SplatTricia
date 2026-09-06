# SplatTricia source snapshot

This directory contains the SplatTricia source state corresponding to the
release in whose `source` folder it appears.

The snapshot is intentionally limited to files required to understand and
rebuild SplatTricia. It is not a copy of the developer workstation.

Included are:

- application source and translation files;
- launch, build and release-verification scripts;
- the PyInstaller specification;
- build notes and the release checklist;
- the SplatTricia MIT license;
- original project assets used by the application;
- the package/version lock generated for the release environment.

Not included are:

- the SHARP model checkpoint;
- virtual environments;
- previous builds and archives;
- settings, logs or user images;
- local third-party source checkouts and build caches.

## License boundary

The MIT License in `LICENSE.txt` covers SplatTricia source code and original
project documentation created by Christoph Müller. It does not relicense
Apple SHARP, the SHARP checkpoint, gsplat, PyTorch, ExifTool or any other
third-party component. Those components remain under their respective licenses.
