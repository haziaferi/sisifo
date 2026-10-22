# Sisifo: design (2026-10-22)

A custom typeface for SisyphusFit, derived from Ortica Linear (Benedetta Bovani & Collletttivo, 2021, SIL OFL 1.1).
Status: proposed, awaiting the owner's approval. Nothing is built yet.

## Intent and why

SisyphusFit is built on Camus's reading of the myth: the boulder, the repeated climb, the measured walk back down,
"one must imagine Sisyphus happy". The app relies on habit, not motivation, and never shows failure. The owner fears
that the app, like their other projects, will end up looking "stock". A calm, non-judgemental register still needs a
bold, energizing presentation, in greyscale for now. Type is the first visual element to settle; the rest follows it.

The search (twenty free faces, scored on harmony, stone character, numbers, calm and technical fit) and the 13 px
test showed:
- carved texture only survives at display sizes: Ortica Angular's facets vanish at 13 px;
- Ortica Linear is the one candidate that works as small text unaided (x-height 6.5 dp at 13 px, close to IBM Plex
  Sans's 6.7);
- the strongest "stone" faces (Avara, Cinzel, Daubenton) are display-only.

So Sisifo is one face that is plain where text is small and carved where it is large.

## Goals

1. **One variable font, `Sisifo`**, with two axes:
   - `wght` 300–700, from Ortica Linear's Light, Regular and Bold sources;
   - `CARV` (carve) 0–100: 0 is Ortica Linear unchanged, 100 is fully carved. The app ties it to text size through
     its type tokens (decided: "carve tied to size"): small text sits at 0, titles and set numbers at or near 100.
     The size→carve mapping is set during the token step and checked on the phone.
2. **Carved traits at `CARV` 100** (owner's choice):
   - **facets**: curves broken into a few straight cuts, with Ortica Angular as the visual reference, extended to
     every weight;
   - **flat-cut bowls**: round shapes trimmed flat where a chisel would stop (Avara's idea);
   - **inscriptional capitals**: alternate capitals with Roman-inscription proportions (Cinzel's idea), in a
     stylistic set (`ss01`) for titles only, so running text keeps Ortica's capitals.
3. **Scripted obliques**: an oblique for every weight, slanted about 9° with corrections for stroke weight and
   spacing. Delivered as a second variable file `Sisifo-Italic` (same axes), or a `slnt` axis if that measures better.
4. **Numbers for the set screen**: a `tnum` feature with equal-width lining figures (Ortica's digits range from 465 to
   627 units wide today, so 62.5 would shift as it changes), plus `lnum`/`onum` as Ortica has them. The decimal point
   and × stay clearly visible at arm's length.
5. **Coverage at least Ortica's**: its 405 glyphs, including every Italian accent, × · – ’ « », and 99 of the 128
   Latin Extended-A letters.

## Non-goals

- No hand-made irregularity or wobble (Bagnard's trait was left out by the owner).
- No true, redrawn italics in this version (a possible later stage).
- No new scripts (Greek, Cyrillic) or colour layers.
- No change to Ortica's spacing or kerning at `CARV` 0, beyond what the compatibility fixes need.

## Anti-goals (failure even if it builds)

- Aggressive or shouting display text; carving should read as chiselled stone, not as broken or glitchy letters.
- A "ransom note": traits that look pasted on rather than one design across all letters.
- Small text worse than Ortica Linear: 13 px must be at least as sharp and readable as the original.
- Digits that are harder to tell apart (1/7, 3/8, 0/O, 5/6) once faceted.

## Constraints

- **Licence**: SIL OFL 1.1. Sisifo stays OFL; Ortica's copyright line stays in the font, with Sisifo's added; the
  name differs from Ortica's (no reserved font name is declared, but a new name is the rule for modified versions).
  The licence file ships with the font.
- **Source**: github.com/collletttivo/ortica at 27bf44d (UFOs under `source/`, Glyphs files under `backup/`),
  cloned into `research/type-2026-10-22/ortica-src`.
- **Tools**: fontmake 3.12.2, glyphsLib, ufo2ft, fontTools, all open source. The transformations are scripts over the
  UFO sources, so every build is reproducible from source.
- **Compatibility work found** (25 glyphs): Bold adds 3–9 points to A I M Q V W X Y & b d h k l m n p r u v w x y;
  these get matched by inserting the same points in Light and Regular without changing their shapes. `f_k` lists its
  contours in a different order (reorder). `zero.dnom` has no outline in Regular, so it is drawn there from Light and
  Bold. Accented glyphs are components and follow.
- **App**: Android, Jetpack Compose `FontVariation` settings per text style; bundled offline; one file (two with the
  oblique). Target size ≤ 400 KB per file. The app's minSdk is 30, so a custom `CARV` axis works on every supported
  device and no static fallback fonts are needed.
- **Screens**: 384 dp wide on the 6T (density 450); the mockups were drawn at 360 dp. Reviewed on the phone as
  1:1 images, because its browser blocks web fonts.

## How quality is judged (owner's axes)

Each build is scored on, at equal weight unless noted:
1. harmony (measured): even spacing, even x-height, ascender against descender;
2. stone character (blind panel of three judges, coded specimens);
3. numbers at arm's length (measured);
4. calm (half blind panel, half measured stroke contrast and colour);
5. technical fit (measured: licence, coverage, weights, size);
6. carving at display size (blind panel, specimens at 22–56 px at 6T density);
7. small text unharmed (measured at 13 px against Ortica Linear: x-height, width, pixel sharpness);
8. faithful to Ortica, **at half weight** (measured: spacing, proportions and kerning against the original).
A gap under 0.02 between versions is reported as a tie, not a ranking.

- **The panel** is three independent model judges (the method of the font search): each sees coded specimens only,
  scores 0–4 with a reason, and the scores are averaged. The owner's own review on the phone comes at stages 3 and 6.
- **The scales** are absolute 0–1, as in `tools/measure.py`, not relative to the best candidate. Ortica Linear is the
  1.0 reference for "small text unharmed" and "faithful to Ortica".
- **Versions per stage**: a handful of variants (about 3–6, from a small grid of the main parameters), not an
  open-ended search; the best one moves on to the next stage.

Gates, before any scoring: the font builds from source; every master is compatible; no outline errors (open or
self-intersecting contours, wrong direction); coverage ≥ Ortica's; `tnum` digits all one width; at `CARV` 0 the
outlines equal Ortica Linear's within a small tolerance (proves the base was not damaged).

## Stages, in dependency order

1. **Variable Ortica**: fix the 25 incompatible glyphs, build `wght` 300–700, gate that each instance matches the
   original font.
2. **Figures**: tabular lining digits and `tnum`; numbers re-measured.
3. **Carve masters**: generate `CARV` 100 for each weight (facets + flat-cut bowls), build the two-axis font, panel
   and measures. **Owner review on the phone** (display sizes and 13 px).
4. **Inscriptional capitals** (`ss01`).
5. **Obliques**.
6. **Full scoring and owner sign-off**, then the size→carve mapping goes into the type tokens.

## Left to the builder

The facet algorithm (how many cuts per curve, by curve length and weight), where bowls get flattened and by how
much, the inscriptional proportions, the oblique corrections, and which glyphs need hand fixes after the scripts.
Each of these is judged by the axes above, not by preference.

## Where it lives (owner, 2026-10-22)

Its own public repository, `github.com/haziaferi/sisifo`: sources, build script, OFL and notices, its own CI. The app
takes released font files and does not run Python font tooling in its Gradle CI. Creating the repository and pushing
to it wait for the owner's go-ahead at the end of stage 1.
