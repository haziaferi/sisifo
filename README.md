# Sisifo

A variable typeface carved from [Ortica Linear](https://github.com/collletttivo/ortica), made for SisyphusFit, an offline workout tracker. Small text is plain Ortica; titles and set numbers are cut like stone. SIL Open Font License 1.1.

The font is two files: `Sisifo[CARV,wght].ttf` (255 KB) and its oblique, `Sisifo-Italic[CARV,wght].ttf` (12°, 263 KB), with the same axes and features.

## Axes

| Axis | Range | Default | What it does |
|---|---|---|---|
| `wght` | 300–700 | 400 | Weight: Light 300, Regular 400, Medium 500, SemiBold 600, Bold 700 (the named instances). |
| `CARV` | 0–100 | 0 | Carve. At 0 it is Ortica Linear's outline, glyph for glyph (the gate checks this). At 100 curves become chiselled cuts, after Ortica Angular's own cuts, gentler at Light (half the carve) than at Bold (the full carve). |

The app ties carve to text size: small text stays at 0, while titles and set numbers sit at or near 100.

## Features

- **`tnum`:** tabular lining figures, so a set weight such as 62.5 keeps its width as it changes. Default digits are proportional, as in Ortica.
- **`ss01`:** inscriptional capitals for titles set in capitals: Cinzel's capitals with Roman proportions, carved like the rest. Accented capitals follow (À, É, Ì, Ò, Ù, …).
- **`ss01` off is the GL release.** With `ss01` off, Sisifo is the GL carve with its own capitals, identical glyph for glyph (a test checks every glyph's outline and advance). There's no separate GL file: switch the feature instead.
- **Ortica's own features** are kept: `onum`, `lnum`, `case`, `frac`, `sups`, `ordn`, `liga`, `dlig`.

In Jetpack Compose, one `FontFamily` holds both files: the italic one as `FontStyle.Italic`. Set carve and weight with `FontVariation.Settings`, and add `fontFeatureSettings = "ss01"` to the text styles whose titles are set in capitals. Leave it off to get GL's capitals.

## Building

```bash
pip install -r requirements.txt
python tools/build.py release
python tools/gate.py "fonts/variable/Sisifo[CARV,wght].ttf" "fonts/variable/Sisifo-Italic[CARV,wght].ttf"
python -m pytest
```

- **The build** writes `fonts/variable/Sisifo[CARV,wght].ttf` and `Sisifo-Italic[CARV,wght].ttf`. It is reproducible: the font's build time is the last commit's (`SOURCE_DATE_EPOCH`), so a commit always gives byte-identical files.
- **The gate:**
  - compares Ortica's 394 glyphs at CARV 0 with the original fonts;
  - checks the outlines at CARV 0, 50 and 100, and that carving never cuts through a stroke;
  - checks the tabular figures and the shaped widths.
- **The browser checks:** the gate's shaping checks, a few tests and the specimen tools render text in a headless Chromium-family browser, through a small helper outside this repository. The build itself needs none of it.

`sources/` holds the plain masters: Ortica Linear Light, Regular and Bold, renamed, made compatible, with tabular figures. The carve and the `ss01` capitals are generated at build time by `tools/carve.py`, `tools/angular_fit.py` and `tools/ss01.py`. `docs/` holds the design, the plans, and every round's scores and judges' reasons. `FONTLOG.md` records each change.

## Credits and licence

- **Ortica:** © 2021 Benedetta Bovani & Collletttivo; © 2023 Collletttivo. The base of every glyph, and Ortica Angular's cuts.
- **Cinzel:** © 2020 The Cinzel Project Authors. The `ss01` capitals.
- **Sisifo's modifications:** © 2026 haziaferi.

Everything is under the [SIL Open Font License 1.1](OFL.txt). The third-party sources are in `vendor/`, with their licences and origins. Sisifo is not Ortica or Cinzel, and isn't endorsed by their authors.
