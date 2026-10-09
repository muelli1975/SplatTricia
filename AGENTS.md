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
