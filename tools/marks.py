"""Give Sisifo's combining marks zero advance width and the 'mark' category, as Ortica's exported OTFs have them.

Usage:  python tools/marks.py      (edits sources/Sisifo-{Light,Regular,Bold}.ufo in place)

Glyphs (the editor Ortica was exported from) zeroes mark widths at export; fontmake building from UFOs does not.
The set is read from the original OTF, not guessed: glyphs that its GDEF glyph-class table marks as class 3 (mark).
"""
import pathlib

import ufoLib2
from fontTools.ttLib import TTFont

ROOT = pathlib.Path(__file__).resolve().parent.parent
ORIGINAL = ROOT / "vendor" / "ortica" / "fonts" / "OrticaLinear-Regular.otf"


def zero_width_glyphs(otf: pathlib.Path = ORIGINAL) -> list[str]:
    """Glyphs with zero advance in the original (the combining accents and their .case/.alt forms)."""
    t = TTFont(otf)
    return sorted(n for n, (adv, _) in t["hmtx"].metrics.items() if adv == 0 and n != ".notdef")


def mark_glyphs(otf: pathlib.Path = ORIGINAL) -> list[str]:
    """Glyphs the original's GDEF glyph-class table declares as marks (class 3)."""
    defs = TTFont(otf)["GDEF"].table.GlyphClassDef.classDefs
    return sorted(n for n, c in defs.items() if c == 3)


def apply(ufo_path: pathlib.Path, zero: list[str], marks: list[str]) -> int:
    f = ufoLib2.Font.open(ufo_path)
    # the OTF uses production names (uni0308); the sources use friendly names, mapped in public.postscriptNames
    prod = {v: k for k, v in f.lib.get("public.postscriptNames", {}).items()}
    zero, marks = [prod.get(n, n) for n in zero], [prod.get(n, n) for n in marks]
    cats = dict(f.lib.get("public.openTypeCategories", {}))
    n = 0
    for name in zero:
        if name in f:
            f[name].width = 0
            n += 1
    for name in marks:
        if name in f:
            cats[name] = "mark"
    f.lib["public.openTypeCategories"] = cats
    f.save(overwrite=True)
    return n


if __name__ == "__main__":
    z, m = zero_width_glyphs(), mark_glyphs()
    for s in ("Light", "Regular", "Bold"):
        print(s, apply(ROOT / "sources" / f"Sisifo-{s}.ufo", z, m), "glyphs set to zero width;", len(m), "declared marks")
