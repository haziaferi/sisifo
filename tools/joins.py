"""Deepen joins that only rest on an overshoot, so the carve cannot separate them.

Usage:  python tools/joins.py      (edits sources/Sisifo-{Light,Regular,Bold}.ufo in place; safe to rerun)

cent: Ortica draws the two bars as rectangles ending on the c's overshoot (bottom bar up to y 2, top bar down from
y 500). At CARV 100 the c's flats snap onto the baseline and x-height, leaving the bars touching or 2 units in. Each bar
is run DEPTH units into the c's stroke instead; the added part lies inside the ink (the c's stroke is 28-37 units), so
the plain outline is unchanged, which the gate's merged-area comparison checks.
"""
import pathlib

import ufoLib2

ROOT = pathlib.Path(__file__).resolve().parent.parent
DEPTH = 12


def deepen_cent(font) -> None:
    g, xh = font["cent"], font.info.xHeight
    for c in g.contours:
        ys = [p.y for p in c]
        if min(ys) >= xh - 2 * DEPTH:        # top bar: its foot goes DEPTH below the x-height
            foot = min(ys)
            for p in c:
                if p.y == foot:
                    p.y = min(foot, xh - DEPTH)
        elif max(ys) <= 2 * DEPTH:           # bottom bar: its head goes DEPTH above the baseline
            head = max(ys)
            for p in c:
                if p.y == head:
                    p.y = max(head, DEPTH)


if __name__ == "__main__":
    for s in ("Light", "Regular", "Bold"):
        f = ufoLib2.Font.open(ROOT / "sources" / f"Sisifo-{s}.ufo")
        deepen_cent(f)
        f.save(overwrite=True)
        print(s, [sorted({p.y for p in c}) for c in f["cent"].contours])
