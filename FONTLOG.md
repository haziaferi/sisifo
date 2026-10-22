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

## 0.2 (2026-10-22), stage 2: figures
- Tabular lining figures zero.tf ... nine.tf, each one component of its digit, in one advance per master: widest digit
  ink + 2 x the median of the smaller sidebearings (Light 611, Regular 626, Bold 656; 641 at 550). Each digit keeps
  its own left/right balance inside the cell. `tnum` maps the ten lining digits; default digits are unchanged.
- Oldstyle digits stay proportional: with `onum` and `tnum` both on, `onum` wins.
- Gate: Ortica's 394 glyphs still match at 300/400/700; the ten tabular digits share one width at 300, 400, 550 and
  700; "0000" ... "9999" set with tnum by HarfBuzz spread 0.000 px at 100 px (without tnum they spread, as a control).
- Numbers axis (tools/measure.py): Ortica 0.639, Sisifo 0.894 (tabular 0 -> 1). Still weakest: the decimal point,
  0.58 (its ink against the stroke of "1"). 89 KB.
