"""Gate Sisifo's variable font against the original Ortica Linear fonts.

Usage:  python tools/gate.py       -> build/gate.json + a table; exit 1 on any failure

compare_outlines  each glyph of the instance at 300/400/700 against the original OTF of that weight: advance width
                  equal, area within 1 %, bounds within 3 units (fontmake's cubic-to-quadratic conversion moves points
                  by about 1 unit); glyphs compared by name, or by character when `chars` is given
outline_errors    contours with fewer than 3 points, non-finite coordinates, or zero area, at any weight
direction_flips   a contour whose winding direction changes between weights (a sign that points were matched to the
                  wrong partners: the outline turns inside out on the way)
shaped_widths     text set by the browser's HarfBuzz (kerning on) in Sisifo at a weight and in the original; the
                  largest width difference in px at 100 px
No exemptions: zero.dnom, the one glyph drawn anew, is a helper glyph that neither font exports.
"""
import functools
import json
import math
import pathlib
import sys

from booleanOperations.booleanGlyph import BooleanGlyph
from fontTools.pens.areaPen import AreaPen
from fontTools.pens.basePen import BasePen
from fontTools.pens.pointPen import SegmentToPointPen
from fontTools.pens.boundsPen import BoundsPen
from fontTools.pens.recordingPen import DecomposingRecordingPen
from fontTools.ttLib import TTFont
from fontTools.varLib.instancer import instantiateVariableFont

ROOT = pathlib.Path(__file__).resolve().parent.parent
VF = ROOT / "fonts" / "variable" / "Sisifo[wght].ttf"
ORTICA = ROOT.parent / "ortica-src" / "fonts"
ORIGINAL = {s: ORTICA / f"OrticaLinear-{s}.otf" for s in ("Light", "Regular", "Bold")}
EXEMPT = {}   # zero.dnom (drawn for Sisifo) is a non-exported helper, so nothing needs exempting
sys.path.insert(0, str(pathlib.Path.home() / ".claude" / "tools"))


@functools.lru_cache(maxsize=None)
def instance(w):
    return instantiateVariableFont(TTFont(VF), {"wght": w}, static=True)


@functools.lru_cache(maxsize=None)
def original(style):
    return TTFont(ORIGINAL[style])


class _CubicPen(BasePen):
    """Records a glyph as cubic segments (quadratics elevated exactly), components decomposed."""
    def __init__(self, glyphSet):
        super().__init__(glyphSet)
        self.value = []

    def _moveTo(self, p):
        self.value.append(("moveTo", (p,)))

    def _lineTo(self, p):
        self.value.append(("lineTo", (p,)))

    def _curveToOne(self, a, b, c):
        self.value.append(("curveTo", (a, b, c)))

    def _qCurveToOne(self, a, b):
        p0 = self._getCurrentPoint()
        c1 = (p0[0] + 2 / 3 * (a[0] - p0[0]), p0[1] + 2 / 3 * (a[1] - p0[1]))
        c2 = (b[0] + 2 / 3 * (a[0] - b[0]), b[1] + 2 / 3 * (a[1] - b[1]))
        self.value.append(("curveTo", (c1, c2, b)))

    def _closePath(self):
        self.value.append(("closePath", ()))


def _measure(font, name):
    """Area after merging overlaps (a variable font keeps overlapping contours; the original OTF had them merged),
    bounds, and advance."""
    gs = font.getGlyphSet()
    rec = _CubicPen(gs)
    gs[name].draw(rec)
    bg = BooleanGlyph()
    seg = SegmentToPointPen(bg.getPointPen())
    for op, args in rec.value:
        getattr(seg, op)(*args)
    merged = bg.removeOverlap()
    a, b = AreaPen(), BoundsPen(gs)
    merged.draw(a)
    gs[name].draw(b)
    return abs(a.value), b.bounds, font["hmtx"].metrics[name][0]


def compare_outlines(w, style, chars=None):
    new, old = instance(w), original(style)
    if chars:
        nc, oc = new.getBestCmap(), old.getBestCmap()
        pairs = [(nc[ord(c)], oc[ord(c)]) for c in chars if ord(c) in nc and ord(c) in oc]
    else:
        names = set(new.getGlyphOrder())
        pairs = [(n, n) for n in old.getGlyphOrder() if n in names and n != ".notdef"]
    bad, exempt = [], []
    for nn, on in pairs:
        if (on, w) in EXEMPT:
            exempt.append(on)
            continue
        a1, b1, w1 = _measure(new, nn)
        a0, b0, w0 = _measure(old, on)
        why = []
        if w1 != w0:
            why.append(f"advance {w0}->{w1}")
        if abs(abs(a1) - abs(a0)) > 0.01 * max(1.0, abs(a0)):   # TrueType winds contours opposite to CFF
            why.append(f"area {abs(a0):.0f}->{abs(a1):.0f}")
        if (b0 is None) != (b1 is None) or (b0 and any(abs(x - y) > 3 for x, y in zip(b0, b1))):
            why.append(f"bounds {b0}->{b1}")
        if why:
            bad.append(f"{on}: " + ", ".join(why))
    return {"compared": len(pairs) - len(exempt), "mismatches": bad, "exempt": exempt}


def _contours(font, name):
    pen = DecomposingRecordingPen(font.getGlyphSet())
    font.getGlyphSet()[name].draw(pen)
    out, cur = [], []
    for op, args in pen.value:
        if op == "moveTo":
            cur = [args[0]]
        elif op in ("lineTo", "curveTo", "qCurveTo"):
            cur += [a for a in args if a is not None]
        elif op in ("closePath", "endPath"):
            out.append(cur)
            cur = []
    return out


def _signed_area(pts):
    return sum(pts[i][0] * pts[(i + 1) % len(pts)][1] - pts[(i + 1) % len(pts)][0] * pts[i][1]
               for i in range(len(pts))) / 2


def outline_errors(w):
    f = instance(w)
    errs = []
    for name in f.getGlyphOrder():
        for i, c in enumerate(_contours(f, name)):
            if len(c) < 3:
                errs.append(f"{name} contour {i}: {len(c)} points")
            elif not all(math.isfinite(v) for p in c for v in p):
                errs.append(f"{name} contour {i}: non-finite point")
            elif abs(_signed_area(c)) < 1:
                errs.append(f"{name} contour {i}: zero area")
    return errs


def direction_flips(weights):
    signs = {}
    for w in weights:
        f = instance(w)
        for name in f.getGlyphOrder():
            for i, c in enumerate(_contours(f, name)):
                if len(c) >= 3:
                    signs.setdefault((name, i), set()).add(_signed_area(c) > 0)
    return sorted(f"{n} contour {i}" for (n, i), s in signs.items() if len(s) > 1)


def shaped_widths_diff(texts, weights=(300, 400, 700)):
    import headless_browser as hb
    style = {300: "Light", 400: "Regular", 700: "Bold"}
    faces = (f"@font-face{{font-family:S;src:url('{VF.as_uri()}');font-weight:300 700}}"
             + "".join(f"@font-face{{font-family:O{w};src:url('{ORIGINAL[style[w]].as_uri()}')}}" for w in weights))
    spans = "".join(f'<span data-k="{w}|{t}|{fam}" style="font-family:{fam if fam != "S" else "S"};'
                    f'font-weight:{w if fam == "S" else 400};font-variation-settings:{chr(39)}wght{chr(39)} {w if fam == "S" else 400}">'
                    f"{t}</span><br>" for w in weights for t in texts for fam in ("S", f"O{w}"))
    page = ROOT / "build" / "shape.html"
    page.parent.mkdir(exist_ok=True)
    page.write_text(f"<!doctype html><meta charset=utf-8><style>{faces} body{{font-size:100px;white-space:nowrap;"
                    f"font-kerning:normal}}</style>{spans}", encoding="utf-8")
    js = ("(async()=>{await document.fonts.ready;const r={};for(const f of document.fonts){r['face:'+f.family]=f.status};"
          "document.querySelectorAll('span').forEach(s=>r[s.dataset.k]=s.getBoundingClientRect().width);"
          "return JSON.stringify(r)})()")
    try:
        res = json.loads(hb.evaluate(str(page), js, 4000, 3000))
    finally:
        hb.close_all()
    unloaded = [k for k, v in res.items() if k.startswith("face:") and v != "loaded"]
    if unloaded or len([k for k in res if k.startswith("face:")]) != 1 + len(weights):
        raise RuntimeError(f"fonts not loaded in the shaping page: {unloaded}")   # equal fallbacks would read as a match
    diffs = [abs(res[f"{w}|{t}|S"] - res[f"{w}|{t}|O{w}"]) for w in weights for t in texts]
    return max(diffs)


def run():
    out = {}
    for w, s in ((300, "Light"), (400, "Regular"), (700, "Bold")):
        out[f"outlines {w}"] = compare_outlines(w, s)
    out["outline errors"] = {w: outline_errors(w) for w in (300, 350, 400, 550, 650, 700)}
    out["direction flips"] = direction_flips((300, 350, 400, 550, 650, 700))
    out["shaped width diff px"] = shaped_widths_diff(["AVATAR", "To Ty Yo", "Wave LT", "Panca piana 62.5 kg"])
    return out


def main():
    r = run()
    ok = all(not r[f"outlines {w}"]["mismatches"] for w in (300, 400, 700)) \
        and not any(r["outline errors"].values()) and not r["direction flips"] and r["shaped width diff px"] <= 0.5
    for w in (300, 400, 700):
        x = r[f"outlines {w}"]
        print(f"outlines {w}: {x['compared']} compared, {len(x['mismatches'])} mismatched, exempt {x['exempt']}")
    print(f"outline errors: {sum(len(v) for v in r['outline errors'].values())}; direction flips: {len(r['direction flips'])}; "
          f"shaped width diff: {r['shaped width diff px']:.2f} px at 100 px")
    (ROOT / "build").mkdir(exist_ok=True)
    (ROOT / "build" / "gate.json").write_text(json.dumps(r, indent=1, default=str), encoding="utf-8")
    print("GATE PASS" if ok else "GATE FAIL")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
