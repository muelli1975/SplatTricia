# Repository guidance

Before changing GUI appearance, labels, interaction, previews, output paths,
or supplied assets, read [DESIGN_STANDARD_STEREOTOOLS.txt](DESIGN_STANDARD_STEREOTOOLS.txt).
It defines the shared Stereo-Tool standard and explicit per-project differences.

Check the actual current implementation and distinguish agreed targets from
implemented and verified behavior. Preserve this project's processing math and
working workflows; documentation changes do not authorize unrelated runtime changes.
Keep user-supplied assets byte-for-byte unless the user explicitly requests conversion.
When revising the shared standard, synchronize the identical version in all five
repositories: StereoFine, SplatTricia, AnaChroma, Freeda, and AnaglyphBatch.

## Agreed decisions and application startup

Treat Christoph's explicit decisions as requirements for implementation, test builds and releases. Preserve their intent when choosing tools or languages. Before editing, check the relevant agreements. Before building, check the actual diff, entry point and build command against them. If a concrete technical obstacle requires a departure, explain the conflict and obtain Christoph's agreement before implementing it.

Follow the existing Windows application build in `build_portable.bat` and `SplatTricia.spec`, and the existing preview workflow where applicable. Introducing an additional application starter, wrapper or bootstrap process requires Christoph's prior agreement in any language.
