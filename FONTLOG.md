# Sisifo FONTLOG

Sisifo is a modified version of **Ortica Linear** by Benedetta Bovani and Collletttivo (SIL OFL 1.1),
taken from https://github.com/collletttivo/ortica at commit 27bf44d (sources `source/Ortica Linear-{Light,Regular,Bold}.ufo`).
It is made for SisyphusFit, an offline workout tracker: plain Ortica Linear where text is small, carved where it is
large. Sisifo is not Ortica and is not endorsed by its authors.

## 0.1 (2026-10-22), stage 1: variable Ortica
- Renamed to Sisifo; copyright lines kept and Sisifo's added.
- Masters made compatible (25 glyphs): Light and Regular curves split where Bold has extra points, at the same
  arc-length fractions (shapes unchanged); f_k contours reordered; zero.dnom, empty in Ortica's Regular, drawn by
  interpolating Light and Bold (a helper glyph; not exported).
- Combining marks set to zero width, as in Ortica's exported fonts (Glyphs does this at export; fontmake does not).
- Variable font, wght 300-700 (Light, Regular, Medium, SemiBold, Bold), 88 KB.
- Gate against the original Ortica Linear OTFs: 394 glyphs at 300, 400 and 700 match (advance equal, merged-overlap
  area within 1 %, bounds within 3 units); no outline errors or direction flips at 300-700; kerning-shaped widths equal.
- Specimen at the 6T density (build/specimen.png): 300, 400 and 700 look identical to the originals; 500 and 600 sit
  evenly between.
