# Vendored fonts

Third-party font sources that Sisifo is built from or checked against. They are included unchanged, with their licences, so the repository builds and tests on its own. Both are under the SIL Open Font License 1.1, which allows redistribution with the licence.

## `ortica/`: Ortica, by Benedetta Bovani and Collletttivo

- **Source:** https://github.com/collletttivo/ortica at commit `27bf44d3ea5057b7abcd09a8922d43d0b37a4f06` (2024-03-14).
- **Licence:** `LICENSE.txt` (SIL OFL 1.1), copied from that repository.
- **`source/Ortica Linear-{Light,Regular,Bold}.ufo`:** the drawings Sisifo starts from. `sources/` holds Sisifo's renamed and modified copies. The tests use these untouched ones to check that the compatibility fixes kept every shape.
- **`source/Ortica Angular.ufo`:** Angular's own cuts. `tools/angular_fit.py` fits them onto Linear's outlines to make the carve.
- **`fonts/OrticaLinear-{Light,Regular,Bold}.otf`:** the published fonts the gate compares against, at CARV 0. The gate checks every glyph's outline, plus kerning and widths.
- **`fonts/OrticaAngular-Bold.otf`:** the reference shown to the panel in the carve rounds.

## `cinzel/`: Cinzel, by The Cinzel Project Authors

- **Source:** the Google Fonts copy (`github.com/google/fonts`, `ofl/cinzel`). That's where the licence of the font search's copy is recorded. File SHA-256: `f4d83d34d1f6c741193e4acf4b3dff9531e5a67b6aa65228d00a7db72a4e0f34`.
- **Licence:** `OFL.txt` (SIL OFL 1.1, Copyright 2020 The Cinzel Project Authors, https://github.com/NDISCOVER/Cinzel). No Reserved Font Name is declared.
- **Use:** `tools/ss01.py` takes Cinzel's capitals for Sisifo's inscriptional set (`ss01`, stage 4).

`tools/search_measure.py` is the measuring script from the typeface search that chose Ortica, copied here because the carve scoring reuses its axes.
