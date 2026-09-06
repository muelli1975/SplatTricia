# SplatTricia 1.0 release checklist

This checklist is intentionally short. It verifies the behaviours that matter
for a stable release rather than repeating every development experiment.

## Source and build

- `verify_release.py` passes.
- `requirements-lock.txt` is regenerated from the release environment.
- The portable build is produced by `build_portable.bat`.
- The final ZIP is named `SplatTricia_1.0.zip`.
- The ZIP contains the `source` directory for the same source state.
- `source\LICENSE.txt` is present and contains the SplatTricia MIT License.
- `source\requirements-lock.txt` is present.
- No model checkpoint is contained in the release.
- No virtual environment, build directory, log, settings or user output is in
  the source snapshot.

## Start-up

- Start the development version once.
- Start the freshly extracted portable version once.
- Verify application icon, language selection and saved settings.
- Verify that a missing model produces a clear local error and no download is
  attempted.

## Processing

Test at least:

- one JPEG input;
- one PNG input;
- one folder/batch input;
- custom output directory;
- output subdirectory beside the input;
- colour anaglyph;
- grayscale anaglyph;
- reusable PLY cache;
- rerender with changed stereo settings;
- EXIF/metadata transfer for a suitable JPEG;
- cancellation.

## GUI state

- Custom output path stays stored and visible when the input-subfolder mode is
  active.
- Inactive dependent controls lose their gold accent.
- Window backshift is active only at 100% window position.
- Floating-window exclusions and symmetry behave consistently.
- While processing, only Cancel remains available among processing controls.
- After success, cancellation or error, dependent controls return to the
  correct states.
- No terminal window flashes during normal image processing.

## Output and cleanup

- Existing final output files are overwritten as documented.
- Appending settings to the filename keeps intentional variants separate.
- `_temp` can be deleted completely.
- Deleting temporary files does not remove finished images.
- A reused PLY is accepted only when its validation data matches.

## Documentation and licenses

- `README_DE.txt`, `README_EN.txt`, `LICENSE.txt` and `LICENSES.txt` are present.
- `LICENSE.txt` is the MIT License for SplatTricia code and original
  documentation.
- README explains the purpose, prerequisites, stereo concepts, output, offline
  behaviour, model separation and source availability.
- SHARP checkpoint is not distributed.
- Third-party licenses remain separate from the SplatTricia MIT License.
