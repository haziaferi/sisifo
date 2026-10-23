"""Inscriptional capitals for Sisifo's ss01 stylistic set (stage 4), added to the masters at build time.

Two sources, both scored (owner, 2026-10-22):
- "P", proportions only: Sisifo's own capitals re-proportioned to Cinzel's measured widths (ink width over cap
  height, Cinzel 400 against Sisifo Regular). The width changes inside bands set per letter, between or beside the
  stems, so stems keep their thickness; points outside the bands keep their place.
- "Z", Cinzel's capitals: Cinzel's outlines (SIL OFL 1.1, Copyright 2020 The Cinzel Project Authors, no Reserved
  Font Name), quadratics made cubic exactly, scaled to Sisifo's cap height, at the Cinzel weight whose I stem matches
  Sisifo's I stem at each master (Light extrapolated below Cinzel's 400).
Accented capitals built only from components get .ss01 copies with the base swapped and the accent re-centred over
the new base. The ss01 feature maps every default glyph to its .ss01. The carve then cuts the new glyphs like any
other (chiselled rules: Angular has no inscriptional capitals).
"""
import copy
import functools
import pathlib
import statistics

import ufoLib2
from fontTools.pens.basePen import BasePen
from fontTools.pens.boundsPen import BoundsPen
from fontTools.pens.pointInsidePen import PointInsidePen
from fontTools.pens.pointPen import SegmentToPointPen
from fontTools.ttLib import TTFont
from fontTools.varLib.instancer import instantiateVariableFont

ROOT = pathlib.Path(__file__).resolve().parent.parent
CINZEL = ROOT / "vendor" / "cinzel" / "Cinzel-wght.ttf"
CINZEL_COPYRIGHT = "Copyright 2020 The Cinzel Project Authors (https://github.com/NDISCOVER/Cinzel)"
CAPS = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
# P: where each capital may stretch, as fractions of its ink width, with the share of the width change each band
# takes; outside the bands the outline moves rigidly (stems keep their thickness)
BANDS = {**{c: [(0.3, 0.7, 1)] for c in "OCDGQHNUAVXWZM"},
         **{c: [(0.3, 0.98, 1)] for c in "EFLK"},
         **{c: [(0.3, 0.75, 1)] for c in "BPR"},
         "S": [(0.1, 0.9, 1)],
         **{c: [(0.02, 0.38, 0.5), (0.62, 0.98, 0.5)] for c in "TY"}}
KEEP_WIDTH = {"I", "J"}     # their difference from Cinzel is serif length; stretching would squeeze the stem


def _ink(font, name):
    b = BoundsPen(font)
    font[name].draw(b)
    return b.bounds


def stem(font, name):
    """Thickness of the leftmost vertical stem: the first run of ink along a horizontal line at 45 % of cap height."""
    x0, _, x1, _ = _ink(font, name)
    y = 0.45 * font.info.capHeight
    inside = lambda x: (lambda pen: (font[name].draw(pen), pen.getResult())[1])(PointInsidePen(font, (x, y)))
    x = x0 - 1
    while x < x1 and not inside(x):
        x += 1
    start = x
    while x < x1 and inside(x):
        x += 1
    return x - start


@functools.lru_cache(maxsize=None)
def _cinzel_static(w):
    return instantiateVariableFont(TTFont(CINZEL), {"wght": w}, static=True)


class _Cubic(BasePen):
    """Draws into a point pen with quadratics elevated to cubics exactly."""
    def __init__(self, glyphSet, out):
        super().__init__(glyphSet)
        self.out = out

    def _moveTo(self, p):
        self.out.moveTo(p)

    def _lineTo(self, p):
        self.out.lineTo(p)

    def _curveToOne(self, a, b, c):
        self.out.curveTo(a, b, c)

    def _qCurveToOne(self, a, b):
        p0 = self._getCurrentPoint()
        self.out.curveTo((p0[0] + 2 / 3 * (a[0] - p0[0]), p0[1] + 2 / 3 * (a[1] - p0[1])),
                         (b[0] + 2 / 3 * (a[0] - b[0]), b[1] + 2 / 3 * (a[1] - b[1])), b)

    def _closePath(self):
        self.out.closePath()


def _cinzel_glyph(w, ch):
    """Cinzel's capital at weight w as a cubic ufoLib2 glyph (unscaled) and its advance."""
    t = _cinzel_static(w)
    name = t.getBestCmap()[ord(ch)]
    g = ufoLib2.objects.Glyph()
    t.getGlyphSet()[name].draw(_Cubic(t.getGlyphSet(), SegmentToPointPen(g.getPointPen())))
    return g, t["hmtx"].metrics[name][0]


def _blend(a, b, k):
    """a + k (b - a) point by point (same structure); k < 0 extrapolates."""
    out = copy.deepcopy(a)
    for ca, cb, co in zip(a.contours, b.contours, out.contours):
        for pa, pb, po in zip(ca, cb, co):
            po.x, po.y = pa.x + k * (pb.x - pa.x), pa.y + k * (pb.y - pa.y)
    return out


@functools.lru_cache(maxsize=None)
def _cinzel_stems():
    def s(w):
        g, _ = _cinzel_glyph(w, "I")
        f = ufoLib2.Font()
        f.info.capHeight = 700
        f.layers.defaultLayer.insertGlyph(g, "I")
        return stem(f, "I")
    return s(400), s(900)


PUNCT = ".,:;-–—'’‘\"“”«»!?()&/·"   # kerned against the ss01 capitals


def _cinzel_k(target, cap):
    """Where on Cinzel's weight axis Sisifo's stem `target` falls: k = 0 at 400, 1 at 900 (negative: below 400)."""
    s400, s900 = _cinzel_stems()
    return (target / (cap / 700) - s400) / (s900 - s400)


@functools.lru_cache(maxsize=None)
def _cinzel_pairs(w):
    """Cinzel's kern feature at weight w, resolved: {(left glyph, right glyph): x-advance adjustment}."""
    t = _cinzel_static(w)
    gpos = t["GPOS"].table
    out = {}
    idx = {i for fr in gpos.FeatureList.FeatureRecord if fr.FeatureTag == "kern" for i in fr.Feature.LookupListIndex}
    for i in sorted(idx):
        for st in gpos.LookupList.Lookup[i].SubTable:
            st = getattr(st, "ExtSubTable", st)
            if st.Format == 1:
                for left, ps in zip(st.Coverage.glyphs, st.PairSet):
                    for pv in ps.PairValueRecord:
                        v = getattr(pv.Value1, "XAdvance", 0) if pv.Value1 else 0
                        out.setdefault((left, pv.SecondGlyph), v)
            else:
                c1, c2 = st.ClassDef1.classDefs, st.ClassDef2.classDefs
                rights = {}
                for g, k in c2.items():
                    rights.setdefault(k, []).append(g)
                for left in st.Coverage.glyphs:
                    rec = st.Class1Record[c1.get(left, 0)]
                    for k2, c2rec in enumerate(rec.Class2Record):
                        v = getattr(c2rec.Value1, "XAdvance", 0) if c2rec.Value1 else 0
                        if v:
                            for right in rights.get(k2, []):
                                out.setdefault((left, right), v)   # pairs (format 1) come first and win
    return out


def _cinzel_kern_value(left_ch, right_ch, k, scale):
    """Cinzel's kerning between two characters at axis position k, scaled to Sisifo's cap height."""
    cm = _cinzel_static(400).getBestCmap()
    if ord(left_ch) not in cm or ord(right_ch) not in cm:
        return 0
    pair = (cm[ord(left_ch)], cm[ord(right_ch)])
    if k >= 0:
        v = _cinzel_pairs(round(400 + 500 * k)).get(pair, 0)
    else:
        v4, v5 = _cinzel_pairs(400).get(pair, 0), _cinzel_pairs(500).get(pair, 0)
        v = v4 + k * 5 * (v5 - v4)
    return round(v * scale)


def kern_z(f, names):
    """Z: Cinzel's own kerning for the ss01 capitals in this master, at the Cinzel weight its capitals came from.
    Each capital and its accented forms make one kerning group per side; pairs go between groups and against
    Sisifo's punctuation."""
    k, scale = _cinzel_k(stem(f, "I"), f.info.capHeight), f.info.capHeight / 700
    members = {ch: [n for n in names if n == f"{ch}.ss01" or (n.endswith(".ss01") and f[n].components
                                                                 and f[n].components[0].baseGlyph == f"{ch}.ss01")]
               for ch in CAPS}
    for ch, ms in members.items():
        f.groups[f"public.kern1.ss01_{ch}"] = ms
        f.groups[f"public.kern2.ss01_{ch}"] = list(ms)
    cmap = {u: g.name for g in f for u in g.unicodes}
    for a in CAPS:
        for b in CAPS:
            v = _cinzel_kern_value(a, b, k, scale)
            if v:
                f.kerning[(f"public.kern1.ss01_{a}", f"public.kern2.ss01_{b}")] = v
        for p in PUNCT:
            if ord(p) not in cmap:
                continue
            v1, v2 = _cinzel_kern_value(a, p, k, scale), _cinzel_kern_value(p, a, k, scale)
            if v1:
                f.kerning[(f"public.kern1.ss01_{a}", cmap[ord(p)])] = v1
            if v2:
                f.kerning[(cmap[ord(p)], f"public.kern2.ss01_{a}")] = v2


def _cinzel_at_stem(ch, target, cap):
    """Cinzel's capital at the weight whose I stem is `target` (Sisifo units), scaled to cap height `cap`."""
    scale = cap / 700
    s400, s900 = _cinzel_stems()
    k = (target / scale - s400) / (s900 - s400)
    if k >= 0:
        g, adv = _cinzel_glyph(round(400 + 500 * k), ch)
    else:                     # below Cinzel's lightest: extrapolate along its 400 -> 500 direction
        g4, adv = _cinzel_glyph(400, ch)
        g5, _ = _cinzel_glyph(500, ch)
        g = _blend(g4, g5, k * 5)
    for c in g.contours:
        for p in c:
            p.x, p.y = p.x * scale, p.y * scale
    g.width = round(adv * scale)
    return g


def _stretch(glyph, font, ch, ratio):
    """P: widen or narrow one capital's ink by `ratio`, inside its bands."""
    x0, _, x1, _ = _ink(font, ch)
    w = x1 - x0
    delta = w * (ratio - 1)
    bands = BANDS[ch]
    for a, b, share in bands:
        if 1 + delta * share / ((b - a) * w) < 0.4:
            raise ValueError(f"{ch}: band too narrow for a {ratio:.2f} change")

    def shift(x):
        f = (x - x0) / w
        return delta * sum(share * min(max((f - a) / (b - a), 0.0), 1.0) for a, b, share in bands)
    for c in glyph.contours:
        for p in c:
            p.x += shift(p.x)
    glyph.width = round(glyph.width + delta)
    return shift


BELOW_OVERLAP = 22   # Z: a mark below the letter (ogonek, cedilla) overlaps its bottom by this much, more than an
                     # overshoot, so the carve's flats (which lift overshoots onto the baseline) cannot part them


def _lowest_ink(font, name, x):
    """The lowest y with ink in glyph `name` along the vertical line at x (None if the line misses it)."""
    for y in range(-80, 400, 2):
        pen = PointInsidePen(font, (x, y))
        font[name].draw(pen)
        if pen.getResult():
            return y
    return None


def _stroke_above(font, name, x, bottom):
    """Thickness of the stroke at the bottom of glyph `name` along x, from its lowest ink upwards."""
    y = bottom
    while y < bottom + 300:
        pen = PointInsidePen(font, (x, y + 1))
        font[name].draw(pen)
        if not pen.getResult():
            break
        y += 1
    return y - bottom


def reseat_below_marks(f):
    """Z, after the carve: seat each mark that hangs below an .ss01 capital (cedilla, ogonek) on the carved letter, in
    this master: its top goes half the bottom stroke's thickness into the stroke (at least 4 units). Placed before
    the carve, a Cinzel stroke thinner than the overlap let the mark poke into the counter at Light, and the carve's
    lifted overshoots parted it elsewhere. TrueType composites take a different offset per master."""
    for g in f:
        if not g.name.endswith(".ss01") or not g.components or not g.components[0].baseGlyph.endswith(".ss01"):
            continue
        base = g.components[0].baseGlyph
        for c in g.components[1:]:
            mb = _ink(f, c.baseGlyph)
            if mb is None or mb[3] + c.transformation[5] >= 60:
                continue
            t = c.transformation
            top_pt = max((p for k in f[c.baseGlyph].contours for p in k if p.type), key=lambda p: p.y)
            x = top_pt.x + t[4]
            if _lowest_ink(f, base, x) is None:      # the top point sits beside the letter: move under its ink
                near = min((x + d for d in range(-120, 121, 4) if _lowest_ink(f, base, x + d) is not None),
                           key=lambda xx: abs(xx - x), default=x)
                c.transformation = t = (t[0], t[1], t[2], t[3], round(t[4] + near - x), t[5])
            dy = _seat_dy(f, base, c)
            c.transformation = t = (t[0], t[1], t[2], t[3], t[4], round(t[5] + dy))
            # verified, not assumed: the mark must overlap the letter, and merging them must give exactly the letter's
            # own contours: no loose part, and no pinhole (a cedilla's hook closing a speck of paper against the S)
            if not _seated(f, base, c):   # nearest clean seat in a small grid around the first one
                for ddx, ddy in sorted(((x, y) for x in range(-36, 37, 6) for y in range(-60, 61, 3)),
                                       key=lambda d: (d[0] / 2) ** 2 + d[1] ** 2):
                    c.transformation = (t[0], t[1], t[2], t[3], t[4] + ddx, t[5] + ddy)
                    if _seated(f, base, c):
                        break
                else:
                    c.transformation = t
                    UNSEATED.append((f.info.styleName, g.name))


UNSEATED = []            # (master, glyph) where no clean seat was found: the gate will then fail on that glyph
MIN_OVERLAP_AREA = 150  # units²: a mark below the letter must really overlap it, not touch it at a corner


def _seated(f, base, comp):
    from booleanOperations.booleanGlyph import BooleanGlyph
    from fontTools.pens.transformPen import TransformPointPen
    if _overlap_area(f, base, comp) < MIN_OVERLAP_AREA:
        return False
    alone, both = BooleanGlyph(), BooleanGlyph()
    f[base].drawPoints(alone.getPointPen())
    f[base].drawPoints(both.getPointPen())
    f[comp.baseGlyph].drawPoints(TransformPointPen(both.getPointPen(), comp.transformation))
    return len(both.removeOverlap().contours) == len(alone.removeOverlap().contours)


def _overlap_area(f, base, comp):
    """Area shared by the base glyph and a mark component, by boolean intersection."""
    from booleanOperations.booleanGlyph import BooleanGlyph
    from fontTools.pens.areaPen import AreaPen
    from fontTools.pens.transformPen import TransformPointPen
    a, b = BooleanGlyph(), BooleanGlyph()
    f[base].drawPoints(a.getPointPen())
    f[comp.baseGlyph].drawPoints(TransformPointPen(b.getPointPen(), comp.transformation))
    pen = AreaPen()
    (a & b).draw(pen)
    return abs(pen.value)


def _seat_dy(f, base, comp):
    """How far to move a mark that hangs below `base` so it is seated: the mark touches the letter at its highest
    point (an ogonek's top end, not its middle), so the letter's bottom is measured right above that point, and the
    mark goes half that bottom stroke into it, between 4 and BELOW_OVERLAP units (a vertical stem, as in I, would
    otherwise count as one 700-unit stroke). 0 for an accent above the letter."""
    t = comp.transformation
    mb = _ink(f, comp.baseGlyph)
    if mb is None or mb[3] + t[5] >= 60:
        return 0
    top_pt = max((p for c in f[comp.baseGlyph].contours for p in c if p.type), key=lambda p: p.y)
    x, top = top_pt.x + t[4], top_pt.y + t[5]
    bottom = _lowest_ink(f, base, x)
    if bottom is None:
        return 0
    overlap = min(BELOW_OVERLAP, max(4, 0.5 * _stroke_above(f, base, x, bottom)))
    return bottom + overlap - top


def _mark_dx_dy(f, comp, base, kind, shift):
    """Where a mark goes on the new capital. An accent above follows the letter's centre (a grave belongs over the
    A's apex). A mark below attaches somewhere particular (an ogonek at the right foot): in P it moves as the stretch
    moves the part of the letter above it; in Z it keeps its place across the letter's width and is seated on the
    letter's bottom (_seat_dy; re-seated per master after the carve by reseat_below_marks)."""
    t = comp.transformation
    mb = _ink(f, comp.baseGlyph)
    if mb is None:
        return 0, 0
    cx, top = (mb[0] + mb[2]) / 2 + t[4], mb[3] + t[5]
    old, new = _ink(f, base), _ink(f, f"{base}.ss01")
    if top >= 60:
        return ((new[0] + new[2]) - (old[0] + old[2])) / 2, 0
    if kind == "P":
        return shift(cx), 0
    frac = (cx - old[0]) / (old[2] - old[0])
    dx = new[0] + frac * (new[2] - new[0]) - cx
    moved = copy.deepcopy(comp)
    moved.transformation = (t[0], t[1], t[2], t[3], t[4] + dx, t[5])
    return dx, _seat_dy(f, f"{base}.ss01", moved)


@functools.lru_cache(maxsize=None)
def ratios():
    """Cinzel 400's ink width over cap height, against Sisifo Regular's, per capital (Q as O: its tail is Roman)."""
    t = _cinzel_static(400)
    gs, cm = t.getGlyphSet(), t.getBestCmap()
    cap_c = _ttink(gs, cm[ord("H")])[3]
    reg = ufoLib2.Font.open(ROOT / "sources" / "Sisifo-Regular.ufo")
    out = {}
    for ch in CAPS:
        bc, bl = _ttink(gs, cm[ord(ch)]), _ink(reg, ch)
        out[ch] = ((bc[2] - bc[0]) / cap_c) / ((bl[2] - bl[0]) / reg.info.capHeight)
    out["Q"] = out["O"]
    return out


def _ttink(gs, name):
    b = BoundsPen(gs)
    gs[name].draw(b)
    return b.bounds


RATIOS = None   # filled on first use (needs the Cinzel file): see ratios()


def add(fonts, kind, ref=None):
    """Add A.ss01 ... Z.ss01, the .ss01 accented capitals and the ss01 feature to every master in `fonts` (dict by
    style). Returns the new glyph names. ref (dict by style, plain masters): for P, where the bands are measured, so
    a carved master is stretched exactly as its plain one and the two stay compatible (P is built from GL's carved
    capitals: the same Angular cuts as the default capitals, re-proportioned)."""
    global RATIOS
    RATIOS = ratios()
    names = []
    shifts = {}
    for ch in CAPS:
        for s, f in fonts.items():
            shifts[(s, ch)] = lambda x: 0.0
            if kind == "P":
                g = copy.deepcopy(f[ch])
                if ch not in KEEP_WIDTH:
                    shifts[(s, ch)] = _stretch(g, (ref or fonts)[s], ch, RATIOS[ch])
            else:
                g = _cinzel_at_stem(ch, stem(f, "I"), f.info.capHeight)
            g.unicodes = []
            f.layers.defaultLayer.insertGlyph(g, f"{ch}.ss01", overwrite=True)
        names.append(f"{ch}.ss01")
    first = next(iter(fonts.values()))
    for g in list(first):
        if (g.name.endswith(".ss01") or g.contours or not g.components or g.components[0].baseGlyph not in CAPS
                or not g.unicodes):
            continue
        base = g.components[0].baseGlyph
        for s, f in fonts.items():
            n = copy.deepcopy(f[g.name])
            n.unicodes = []
            for i, c in enumerate(n.components):
                if i == 0:
                    c.baseGlyph = f"{base}.ss01"
                else:
                    dx, dy = _mark_dx_dy(f, c, base, kind, shifts[(s, base)])
                    t = c.transformation
                    c.transformation = (t[0], t[1], t[2], t[3], round(t[4] + dx), round(t[5] + dy))
            n.width = f[f"{base}.ss01"].width + (f[g.name].width - f[base].width)
            f.layers.defaultLayer.insertGlyph(n, f"{g.name}.ss01", overwrite=True)
        names.append(f"{g.name}.ss01")
    for f in fonts.values():
        order = [n for n in f.lib.get("public.glyphOrder", list(f.keys())) if not n.endswith(".ss01")]
        f.lib["public.glyphOrder"] = order + names
        sub = "\n".join(f"sub {n[:-5]} by {n};" for n in names)
        text = f.features.text.split("\nfeature ss01 {")[0].rstrip("\n")
        f.features.text = f"{text}\n\nfeature ss01 {{\n{sub}\n}} ss01;\n"
        if kind == "P":       # P keeps its letters' edges, so it joins their kerning groups
            for gname, members in f.groups.items():
                if gname.startswith("public.kern"):
                    members.extend(n for n in names if n[:-5] in members and n not in members)
        else:
            if CINZEL_COPYRIGHT not in (f.info.copyright or ""):
                f.info.copyright = f"{f.info.copyright.rstrip('. ')}. Inscriptional capitals (ss01) from Cinzel: {CINZEL_COPYRIGHT}"
            kern_z(f, names)
    return names
