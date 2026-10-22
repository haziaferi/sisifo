"""Fit Ortica Angular Bold's own cuts onto Sisifo's (Ortica Linear) outlines: the "Angular's own cuts" carve.

Used by tools/carve.py for variants G and GL. For one glyph:
1. Angular Bold is shifted so its ink centre sits on Linear Bold's (Linear's advance widths are kept); contours are
   matched by bounding-box centre, and the glyph is fitted only when both have the same number of contours.
2. Each Angular corner is projected onto its Linear contour (nearest point). The corners must come out in the
   contour's own order (or exactly reversed); otherwise the shapes don't correspond and the glyph is not fitted.
   A corner within SNAP_ARC units (along the contour) of an existing Linear point uses that point; any other
   is a new split, at the same segment and parameter in every master, so the masters stay compatible.
3. CARV 100 Bold: the corner points take Angular's corner positions; every point between two corners lands on the
   edge joining them, in proportion to where it lay between them along Linear's contour. All segments become
   straight.
4. Light and Regular CARV 100: the same displacement per point as Bold (from its CARV 0 position), times the
   variant's strength for that weight.
Glyphs that cannot be fitted return None, and carve.py carves them with the chiselled rules instead.
"""
import math
import pathlib

import ufoLib2
from fontTools.pens.boundsPen import BoundsPen
from ufoLib2.objects import Contour, Point

from compat import _segments, split_cubic

ROOT = pathlib.Path(__file__).resolve().parent.parent
ANGULAR = ROOT.parent / "ortica-src" / "source" / "Ortica Angular.ufo"
SNAP_ARC = 8
SAMPLES = 48


def _xy(p):
    return (p.x, p.y)


def _seg_points(segs, i):
    return [_xy(segs[i - 1][2])] + [_xy(q) for q in segs[i][1]] + [_xy(segs[i][2])]


def _at(P, t):
    if len(P) == 2:
        return (P[0][0] + (P[1][0] - P[0][0]) * t, P[0][1] + (P[1][1] - P[0][1]) * t)
    u = 1 - t
    return tuple(u ** 3 * P[0][k] + 3 * u * u * t * P[1][k] + 3 * u * t * t * P[2][k] + t ** 3 * P[3][k] for k in (0, 1))


def _samples(segs):
    """(segment, t, point, arc position) along a closed contour, starting at the first segment's start."""
    out, s, prev = [], 0.0, None
    for i in range(len(segs)):
        P = _seg_points(segs, i)
        for k in range(SAMPLES):
            t = k / SAMPLES
            q = _at(P, t)
            if prev is not None:
                s += math.dist(prev, q)
            out.append((i, t, q, s))
            prev = q
    total = s + math.dist(prev, out[0][2])
    return out, total


def _centre(glyph, font):
    b = BoundsPen(font)
    glyph.draw(b)
    return ((b.bounds[0] + b.bounds[2]) / 2, (b.bounds[1] + b.bounds[3]) / 2) if b.bounds else None


def _merge(glyph):
    """The glyph's contours (Angular's are all straight) with overlaps merged, as point lists."""
    from booleanOperations.booleanGlyph import BooleanGlyph
    bg = BooleanGlyph()
    for c in glyph.contours:
        c.drawPoints(bg.getPointPen())
    out = []
    for c in bg.removeOverlap().contours:
        pts = []
        pen = _Collect(pts)
        c.drawPoints(pen)
        out.append(pts)
    return out


class _Collect:
    """A minimal point pen keeping on-curve points (Angular has no curves)."""
    def __init__(self, pts):
        self.pts = pts

    def beginPath(self, **kw):
        pass

    def endPath(self):
        pass

    def addPoint(self, pt, segmentType=None, *a, **kw):
        if segmentType is not None:
            self.pts.append(tuple(pt))

    def addComponent(self, *a, **kw):
        pass


def _signed(pts):
    return sum(pts[i - 1][0] * pts[i][1] - pts[i][0] * pts[i - 1][1] for i in range(len(pts))) / 2


def _in_order(proj):
    """The projected corners rotated to start at the lowest arc position, if they run forwards around the contour
    (or exactly backwards); else None."""
    arcs = [p[0] for p in proj]
    for seq in (proj, list(reversed(proj))):
        k0 = [p[0] for p in seq].index(min(arcs))
        rot = seq[k0:] + seq[:k0]
        if all(rot[m + 1][0] > rot[m][0] for m in range(len(rot) - 1)):
            return rot
    return None


def _by_length(poly, samples, total, reverse):
    """Corners placed on the Linear contour at the same share of the contour's length as on Angular's polygon,
    starting from the corner nearest Linear's start point: in order by construction."""
    seq = list(reversed(poly)) if reverse else list(poly)
    start = samples[0][2]
    k0 = min(range(len(seq)), key=lambda k: math.dist(seq[k], start))
    seq = seq[k0:] + seq[:k0]
    lens = [math.dist(seq[k], seq[(k + 1) % len(seq)]) for k in range(len(seq))]
    perim = sum(lens)
    out, acc = [], 0.0
    for k, v in enumerate(seq):
        goal = acc / perim * total
        smp = min(samples, key=lambda q: abs(q[3] - goal))
        out.append((smp[3], smp[0], smp[1], v))
        acc += lens[k]
    return out


def plan(lin_bold, lin_font, ang, ang_font):
    """Per Linear contour: {"splits": {segment: sorted t values}, "corners": [(segment, t or None for its end
    point, Angular corner xy)] in contour order}, or None with the reason why the glyph cannot be fitted."""
    if [c.baseGlyph for c in lin_bold.components] != [c.baseGlyph for c in ang.components]:
        return None, "components differ"
    # as drawn first (where both overlap alike, as in m); merged if that is what matches (Angular builds its H from
    # three overlapping rectangles, Linear's H is one outline)
    raw = [[(p.x, p.y) for p in c if p.type is not None] for c in ang.contours]
    shapes = next((s for s in (raw, _merge(ang)) if len(s) == len(lin_bold.contours)), None)
    if not lin_bold.contours or shapes is None:
        return None, "contour count differs"
    cl, ca = _centre(lin_bold, lin_font), _centre(ang, ang_font)
    dx = cl[0] - ca[0]
    angs = [[(x + dx, y) for x, y in c] for c in shapes]
    # match contours by their whole bounding box: an o's outside and its counter share a centre, and matching them
    # crosswise fills the same Bold shape while moving every point across the stroke
    box = lambda pts: (min(x for x, _ in pts), min(y for _, y in pts), max(x for x, _ in pts), max(y for _, y in pts))
    left = list(range(len(angs)))
    pairs = []
    for c in lin_bold.contours:
        bl = box([(p.x, p.y) for p in c])
        j = min(left, key=lambda j: sum(abs(a - b) for a, b in zip(bl, box(angs[j]))))
        left.remove(j)
        pairs.append(j)
    plans = []
    for c, j in zip(lin_bold.contours, pairs):
        segs, _ = _segments(c)
        samples, total = _samples(segs)
        poly = angs[j]
        proj = []
        for v in poly:
            best = min(samples, key=lambda smp: math.dist(smp[2], v))
            proj.append((best[3], best[0], best[1], v))
        rot = _in_order(proj)
        if rot is None:   # shapes differ too much for nearest points: place corners by their share of the length
            rot = _by_length(poly, samples, total, _signed(poly) * _signed([smp[2] for smp in samples]) < 0)
        # existing on-curve points (segment ends) and their arc positions
        ends = {}
        for i in range(len(segs)):
            nxt = (i + 1) % len(segs)
            ends[i] = next(smp[3] for smp in samples if smp[0] == nxt and smp[1] == 0) if nxt else total
        splits, corners = {}, {}
        for arc, seg, t, v in rot:
            near = min(ends, key=lambda i: min(abs(ends[i] - arc), total - abs(ends[i] - arc)))
            gap = min(abs(ends[near] - arc), total - abs(ends[near] - arc))
            key = (near, None) if gap <= SNAP_ARC or not 0.02 < t < 0.98 else (seg, t)
            # two corners on one point: the one nearer to it wins (Angular has one corner fewer there)
            if key in corners and corners[key][0] <= gap:
                continue
            corners[key] = (gap, v)
        for (seg, t) in corners:
            if t is not None:
                splits.setdefault(seg, []).append(t)
        if len(corners) < 3:
            return None, "fewer than three corners"
        plans.append({"splits": {s: sorted(ts) for s, ts in splits.items()},
                      "corners": [(s, t, v) for (s, t), (_, v) in corners.items()]})
    return plans, None


def _split(P, ts):
    """Split one segment (line or cubic) at the parameters ts of the original; list of pieces."""
    out, rest, done = [], P, 0.0
    for t in ts:
        local = (t - done) / (1 - done)
        if len(P) == 2:
            q = _at(rest, local)
            out.append([rest[0], q])
            rest = [q, rest[1]]
        else:
            a, rest = split_cubic(*rest, local)
            out.append(a)
        done = t
    out.append(rest)
    return out


def contours(glyph, plans, carved_bold=None):
    """CARV 0 outline of this master with the fit's splits: list of contours, each a list of pieces [p0, (c1, c2,) p3]
    keyed back to (segment, t-or-None) for the corner points. With carved_bold (the Bold CARV 0 pieces and the plan),
    nothing else is needed: carving is done by carve_bold() and displacement() below."""
    out = []
    for c, pl in zip(glyph.contours, plans):
        segs, trailing = _segments(c)
        pieces = []
        for i in range(len(segs)):
            P = _seg_points(segs, i)
            for m, pc in enumerate(_split(P, pl["splits"].get(i, []))):
                pieces.append({"pts": [list(q) for q in pc], "end": (i, pl["splits"][i][m] if m < len(
                    pl["splits"].get(i, [])) else None), "kind": segs[i][0]})
        out.append({"pieces": pieces, "trailing": trailing, "first_len": len(pl["splits"].get(0, [])) + 1})
    return out


def carve_bold(c0, plans):
    """Move Bold's CARV 0 pieces onto Angular's polygon: the corners onto Angular's corners, every point between
    two corners onto the edge between them in proportion to its arc position. Returns new pieces (all straight)."""
    out = []
    for cont, pl in zip(c0, plans):
        pcs = cont["pieces"]
        ends = [tuple(pc["pts"][-1]) for pc in pcs]
        arc = [0.0]
        for m in range(1, len(ends)):
            arc.append(arc[-1] + math.dist(ends[m - 1], ends[m]))
        total = arc[-1] + math.dist(ends[-1], ends[0])
        corner_at = {}
        for seg, t, v in pl["corners"]:
            idx = next(m for m, pc in enumerate(pcs) if pc["end"] == (seg, t))
            corner_at[idx] = v
        order = sorted(corner_at)
        new_end = []
        for m in range(len(pcs)):
            if m in corner_at:
                new_end.append(corner_at[m])
                continue
            k = max([o for o in order if o < m], default=order[-1])
            nxt = min([o for o in order if o > m], default=order[0])
            a0 = arc[k] if k < m else arc[k] - total
            a1 = arc[nxt] if nxt > m else arc[nxt] + total
            f = (arc[m] - a0) / (a1 - a0) if a1 != a0 else 0
            va, vb = corner_at[k], corner_at[nxt]
            new_end.append((va[0] + (vb[0] - va[0]) * f, va[1] + (vb[1] - va[1]) * f))
        pieces = []
        for m, pc in enumerate(pcs):
            p0, p3 = new_end[m - 1], new_end[m]
            if len(pc["pts"]) == 4:
                pts = [p0, (p0[0] + (p3[0] - p0[0]) / 3, p0[1] + (p3[1] - p0[1]) / 3),
                       (p0[0] + 2 * (p3[0] - p0[0]) / 3, p0[1] + 2 * (p3[1] - p0[1]) / 3), p3]
            else:
                pts = [p0, p3]
            pieces.append({**pc, "pts": [list(q) for q in pts]})
        out.append({**cont, "pieces": pieces})
    return out


def displaced(c0, c0_bold, c100_bold, strength, ratios=None):
    """This master's CARV 100. Each corner and edge point moves as it does in Bold, except that the part of the move
    across the outline (along its normal, cutting into or out of the stroke) is scaled by ratios: this master's stroke
    thickness at that point over Bold's, so a cut on Light's thinner stroke is proportionally shallower. The part
    along the outline is kept. Segments are made straight; strength < 1 stops part of the way from plain."""
    out = []
    for ci, (cont, b0, b1) in enumerate(zip(c0, c0_bold, c100_bold)):
        ends0 = [pc["pts"][-1] for pc in cont["pieces"]]
        bends0 = [pc["pts"][-1] for pc in b0["pieces"]]
        new_end = []
        for m, (p, r0) in enumerate(zip(ends0, bends0)):
            r1 = b1["pieces"][m]["pts"][-1]
            dx, dy = r1[0] - r0[0], r1[1] - r0[1]
            a, b = bends0[m - 1], bends0[(m + 1) % len(bends0)]
            tx, ty = b[0] - a[0], b[1] - a[1]
            tl = math.hypot(tx, ty) or 1
            tx, ty = tx / tl, ty / tl
            along, across = dx * tx + dy * ty, -dx * ty + dy * tx
            r = ratios[ci][m] if ratios else 1.0
            new_end.append((p[0] + along * tx - r * across * ty, p[1] + along * ty + r * across * tx))
        pieces = []
        for m, pc in enumerate(cont["pieces"]):
            p0, p3 = new_end[m - 1], new_end[m]
            if len(pc["pts"]) == 4:
                full = [p0, (p0[0] + (p3[0] - p0[0]) / 3, p0[1] + (p3[1] - p0[1]) / 3),
                        (p0[0] + 2 * (p3[0] - p0[0]) / 3, p0[1] + 2 * (p3[1] - p0[1]) / 3), p3]
            else:
                full = [p0, p3]
            pts = [[q[0] + strength * (f[0] - q[0]), q[1] + strength * (f[1] - q[1])] for q, f in zip(pc["pts"], full)]
            pieces.append({**pc, "pts": pts})
        out.append({**cont, "pieces": pieces})
    return out


def end_points_and_tangents(c0):
    """Per contour, per piece: its end point and the outline's direction there (from the neighbouring ends)."""
    res = []
    for cont in c0:
        ends = [pc["pts"][-1] for pc in cont["pieces"]]
        res.append([(ends[m], (ends[(m + 1) % len(ends)][0] - ends[m - 1][0], ends[(m + 1) % len(ends)][1]
                               - ends[m - 1][1])) for m in range(len(ends))])
    return res


def to_contours(conts):
    """Pieces back to ufoLib2 contours, starting where the source contour started."""
    res = []
    for cont in conts:
        out = []
        for pc in cont["pieces"]:
            p = pc["pts"]
            if len(p) == 4:
                out += [Point(*p[1]), Point(*p[2]), Point(*p[3], type="curve")]
            else:
                out.append(Point(*p[1], type="line"))
        if cont["trailing"]:
            k = cont["first_len"] * 3 - 1
            out = out[k:] + out[:k]
        res.append(Contour(points=out))
    return res


def angular_contours(lin_bold, lin_font, ang, ang_font):
    """Angular's glyph as contours, shifted onto Linear's ink centre as the fit places it."""
    cl, ca = _centre(lin_bold, lin_font), _centre(ang, ang_font)
    dx = cl[0] - ca[0]
    return [Contour(points=[Point(p.x + dx, p.y, type="line") for p in c if p.type is not None])
            for c in ang.contours]


def load_angular():
    return ufoLib2.Font.open(ANGULAR)
