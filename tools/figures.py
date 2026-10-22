"""Add tabular lining figures (zero.tf ... nine.tf) and a tnum feature to Sisifo's sources.

Usage:  python tools/figures.py      (edits sources/Sisifo-{Light,Regular,Bold}.ufo in place; safe to rerun)

Each .tf glyph is one component of its digit, shifted into a common advance W per master:
  W = widest digit ink + 2 x the median over digits of the smaller sidebearing
so the widest digit keeps a typical sidebearing and no digit is squeezed. Inside W each digit keeps its own left/right
balance (Ortica's optical spacing), not a plain centring. The default digits are untouched; tnum opts in.
"""
import pathlib
import re
import statistics

import ufoLib2
from fontTools.pens.boundsPen import BoundsPen

ROOT = pathlib.Path(__file__).resolve().parent.parent
DIGITS = ["zero", "one", "two", "three", "four", "five", "six", "seven", "eight", "nine"]


def _sides(font, name):
    b = BoundsPen(font)
    font[name].draw(b)
    x0, _, x1, _ = b.bounds
    return x1 - x0, x0, font[name].width - x1


def tabular_width(font) -> int:
    s = [_sides(font, d) for d in DIGITS]
    return round(max(ink for ink, _, _ in s) + 2 * statistics.median(min(l, r) for _, l, r in s))


def apply(ufo_path) -> int:
    f = ufoLib2.Font.open(ufo_path)
    W = tabular_width(f)
    order = [n for n in f.lib.get("public.glyphOrder", list(f.keys())) if not n.endswith(".tf")]
    for d in DIGITS:
        ink, L, R = _sides(f, d)
        name = d + ".tf"
        if name in f:
            del f[name]
        g = f.newGlyph(name)
        g.width = W
        g.components.append(ufoLib2.objects.Component(d, (1, 0, 0, 1, round((W - ink) * L / (L + R)) - round(L), 0)))
        order.append(name)
    f.lib["public.glyphOrder"] = order
    sub = "\n".join(f"sub {d} by {d}.tf;" for d in DIGITS)
    text = re.sub(r"\n?feature tnum \{.*?\} tnum;\n?", "\n", f.features.text, flags=re.S).rstrip("\n")
    f.features.text = f"{text}\n\nfeature tnum {{\n{sub}\n}} tnum;\n"
    f.save(overwrite=True)
    return W


if __name__ == "__main__":
    for s in ("Light", "Regular", "Bold"):
        print(s, "tabular width", apply(ROOT / "sources" / f"Sisifo-{s}.ufo"))
