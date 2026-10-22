"""Generate Sisifo's six masters (wght 300/400/700 x CARV 0/100) for one carve variant.

Usage:  python tools/carve.py A [out_dir]     -> build/masters/A/Sisifo-{Light,Regular,Bold}-C{0,100}.ufo

Every curve is split at the same places in all six masters, so they interpolate:
- CARV 0 keeps each piece on the original curve (de Casteljau), so it is Ortica's outline, only with more points;
- CARV 100 straightens the pieces into facets, and around each smooth extreme lines up the two neighbouring pieces into
  one flat, axis-aligned cut ("trimmed flat where a chisel would stop"); a flat near a vertical metric (baseline,
  x-height, cap height, ascender, descender) snaps onto it, as Ortica Angular's flats sit on the lines.
Where the cuts fall is decided once, on Regular, as fractions of each segment's total tangent turn: `phi` degrees of
turn either side of an extreme make a flat, and the rest of the curve gets one facet per `theta` degrees (or stays
curved when theta is None). Widths, kerning and components are untouched.
"""
import math
import pathlib
import sys

import ufoLib2
from fontTools.pens.pointInsidePen import PointInsidePen
from ufoLib2.objects import Contour, Point

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from compat import _segments, split_cubic  # noqa: E402

ROOT = pathlib.Path(__file__).resolve().parent.parent
STYLES = ("Light", "Regular", "Bold")
VARIANTS = {
    "A": {"phi": 22.5, "theta": 45, "look": "Angular"},
    "B": {"phi": 12, "theta": 45, "look": "short flats"},
    "C": {"phi": 12, "theta": 25, "look": "fine facets"},
    "D": {"phi": 22.5, "theta": 25, "look": "long flats, fine facets"},
    "E": {"phi": 15, "theta": None, "look": "flats only"},
    # round 2 (personality): Angular's 42-degree cuts, counters out of phase, depth limited by the stroke cut into
    "R": {"phi": 22.5, "theta": 42, "phase": True, "local": True, "look": "chiselled rules"},
    "RL": {"phi": 22.5, "theta": 42, "phase": True, "local": True, "look": "chiselled rules, gentler at Light",
           "strength": {"Light": 0.5, "Regular": 0.75, "Bold": 1.0}},
    # Angular's own cuts (tools/angular_fit.py); glyphs that cannot be fitted take the chiselled rules above
    "G": {"phi": 22.5, "theta": 42, "phase": True, "local": True, "fit": "angular", "look": "Angular's own cuts"},
    "GL": {"phi": 22.5, "theta": 42, "phase": True, "local": True, "fit": "angular",
           "look": "Angular's own cuts, gentler at Light", "strength": {"Light": 0.5, "Regular": 0.75, "Bold": 1.0}},
}
# hand pins for the general Angular fit: glyph -> {Angular corner (merged order): (contour, segment[, t])}
ANCHORS = {
    # Angular's 6 curls its arm and hooks the terminal (corners 11-14); Linear's arm is thin and straight, so the
    # inner-arm corners 8-9 fell on Linear's outer curve and the hook was lost (owner: "closer to a straight line at
    # an angle"). Linear's 6, contour 0: segment 0 is the inner arm edge (junction to tip), 1 the terminal cut.
    "six": {8: (0, 0, 0.45), 9: (0, 0, 0.7), 10: (0, 0, 0.85), 11: (0, 0, 0.93), 12: (0, 0), 13: (0, 1, 0.5),
            14: (0, 1)},
}
# owner: "even out 3, 8, S": Angular's own facets there are uneven; angular_fit.even() re-spaces them along its edge
EVEN = {"three", "eight", "S", "three.osf", "eight.osf"}
LOCAL_CUT = 0.5             # round 2: no cut deeper than half the stroke it cuts into, measured where it cuts
AXIS_TOL = math.radians(2)   # a tangent within 2 degrees of horizontal/vertical counts as an extreme
SNAP = 20                    # a horizontal flat overshooting a vertical metric by up to 20 units lands on it
OVER = 2                     # ... or falling short of it by up to 2 (drawing noise)
CUT = 0.5                    # no cut goes deeper than half the master's thin stroke
SAMPLES = 240


def _bez(P, s):
    u = 1 - s
    return (u ** 3 * P[0][0] + 3 * u * u * s * P[1][0] + 3 * u * s * s * P[2][0] + s ** 3 * P[3][0],
            u ** 3 * P[0][1] + 3 * u * u * s * P[1][1] + 3 * u * s * s * P[2][1] + s ** 3 * P[3][1])


def _turns(P):
    """Cumulative absolute tangent turn (radians) at SAMPLES+1 even steps of t, from chord directions."""
    pts = [_bez(P, i / SAMPLES) for i in range(SAMPLES + 1)]
    dirs = [math.atan2(pts[i + 1][1] - pts[i][1], pts[i + 1][0] - pts[i][0]) for i in range(SAMPLES)]
    cum = [0.0, 0.0]
    for i in range(1, SAMPLES):
        d = (dirs[i] - dirs[i - 1] + math.pi) % (2 * math.pi) - math.pi
        cum.append(cum[-1] + abs(d))
    return cum


def _t_at_turn(cum, goal):
    for i in range(len(cum) - 1):
        if cum[i + 1] >= goal:
            span = cum[i + 1] - cum[i]
            return (i + ((goal - cum[i]) / span if span else 0)) / SAMPLES
    return 1.0


def _xy(p):
    return (p.x, p.y)


def _flat_axis(prev_ctl, p, next_ctl):
    """'v' (vertical flat, an x-extreme), 'h' (horizontal flat, a y-extreme) or None."""
    a, b = _xy(prev_ctl), _xy(next_ctl)
    if a == _xy(p) or b == _xy(p):
        return None
    d_in = math.atan2(p.y - a[1], p.x - a[0])
    d_out = math.atan2(b[1] - p.y, b[0] - p.x)
    if abs((d_out - d_in + math.pi) % (2 * math.pi) - math.pi) > AXIS_TOL:   # not smooth
        return None
    ang = d_out % math.pi
    if min(ang, math.pi - ang) <= AXIS_TOL:
        return "h"
    if abs(ang - math.pi / 2) <= AXIS_TOL:
        return "v"
    return None


def _hidden_test(glyph):
    """Test function for a piece of outline: is it hidden, i.e. ink on both sides of it? Ortica keeps overlapping
    contours (m's arches tuck into its stems, f ligatures cross), and a hidden piece must keep its curve: a chord would
    pull it out of the shape it overlaps and open a gap. A counter's edge has ink on one side only, so it is visible."""
    def ink(pt):
        pen = PointInsidePen(None, pt)   # nonzero winding over every contour, as the rasteriser fills
        for c in glyph.contours:
            c.draw(pen)
        return pen.getResult()

    def test(P):
        if len(glyph.contours) < 2:
            return False
        m, a, b = _bez(P, 0.5), _bez(P, 0.49), _bez(P, 0.51)
        dx, dy = b[0] - a[0], b[1] - a[1]
        n = math.hypot(dx, dy) or 1
        nx, ny = -dy / n * 2, dx / n * 2
        return ink((m[0] + nx, m[1] + ny)) and ink((m[0] - nx, m[1] - ny))
    return test


def _snap_target(y, bottom, metrics):
    """The metric an overshooting horizontal extreme lands on, or None. Only an overshoot snaps: a bottom extreme at or
    below a bottom line (baseline, descender), a top one at or above a top line (x-height, cap height, ascender).
    A counter just inside a thin stroke, or a serif's underside just under cap height, must never be pulled on."""
    near = [m for m in metrics["bottom" if bottom else "top"]
            if (-SNAP <= y - m <= OVER if bottom else -OVER <= y - m <= SNAP)]
    return min(near, key=lambda m: abs(y - m)) if near else None


def _sagitta(P):
    """How deep the chord of a cubic piece cuts: the largest distance of the curve from it."""
    (x0, y0), (x3, y3) = P[0], P[3]
    L = math.hypot(x3 - x0, y3 - y0) or 1
    return max(abs((x - x0) * (y3 - y0) - (y - y0) * (x3 - x0)) / L for x, y in (_bez(P, i / 16) for i in range(17)))


def _seg_P(segs, i):
    return [_xy(segs[i - 1][2])] + [_xy(q) for q in segs[i][1]] + [_xy(segs[i][2])]


def _polylines(glyph):
    """The glyph's contours flattened to closed polylines (for ray casts)."""
    out = []
    for c in glyph.contours:
        segs, _ = _segments(c)
        pts = []
        for i in range(len(segs)):
            if segs[i][0] == "curve":
                P = _seg_P(segs, i)
                pts += [_bez(P, k / 12) for k in range(1, 13)]
            else:
                pts.append(_xy(segs[i][2]))
        out.append(pts)
    return out


def _counter_edge(glyph, segs, i):
    """Phase (round 2): is the extreme at the end of segment i on a counter's edge, i.e. does the ink lie away from
    the curve's centre? A counter's extremes stay corners while the outside is flat there, so the stroke swells and
    thins around the letter, as in Angular's o. Decided locally, because Ortica draws some counters (e, 6) in the
    same contour as the outside."""
    n = len(segs)
    e = _xy(segs[i][2])
    a, b = _bez(_seg_P(segs, i), 0.5), _bez(_seg_P(segs, (i + 1) % n), 0.5)
    cx, cy = (a[0] + b[0]) / 2 - e[0], (a[1] + b[1]) / 2 - e[1]     # towards the centre of curvature
    d = math.hypot(cx, cy) or 1
    pen = PointInsidePen(None, (e[0] + 3 * cx / d, e[1] + 3 * cy / d))
    for c in glyph.contours:
        c.draw(pen)
    return not pen.getResult()


def _thickness(glyph, polys):
    """Function: the stroke thickness behind a point of the outline, along its inward normal (towards the ink): the
    distance to the nearest outline edge the ray meets. Overlapping contours can only shorten it (a cautious cap)."""
    def ink(pt):
        pen = PointInsidePen(None, pt)
        for c in glyph.contours:
            c.draw(pen)
        return pen.getResult()

    def measure(pt, tangent):
        tx, ty = tangent
        n = math.hypot(tx, ty) or 1
        nx, ny = -ty / n, tx / n
        if not ink((pt[0] + 2 * nx, pt[1] + 2 * ny)):
            nx, ny = -nx, -ny
        ox, oy = pt[0] + nx, pt[1] + ny      # start just inside, past the edge the point is on
        best = 1000.0
        for poly in polys:
            for i in range(len(poly)):
                (ax, ay), (bx, by) = poly[i - 1], poly[i]
                ex, ey = bx - ax, by - ay
                den = nx * ey - ny * ex
                if abs(den) < 1e-9:
                    continue
                s = ((ax - ox) * ey - (ay - oy) * ex) / den        # along the ray
                u = ((ax - ox) * ny - (ay - oy) * nx) / den        # along the edge
                if s > 0.5 and 0 <= u <= 1:
                    best = min(best, s + 1)
        return best
    return measure


def plan_glyph(glyphs, caps, metrics, phi, theta, phase=False, local=False):
    """How one glyph is carved, the same for every master. glyphs/caps/metrics are dicts by style; the structure (which
    extremes get flats, which pieces are hidden) is read on Regular, and every cut is checked on every weight: no facet
    and no unsnapped flat cuts deeper than that weight's cap (half its thin stroke), so a large bowl gets more facets
    than a small one, as a carver stops before cutting through.
    Per contour: {"flats": {segment index ending at a flat extreme: axis}, "splits": [turn fractions per segment],
    "hidden": [per segment, per piece: ink on both sides]}."""
    reg = glyphs["Regular"]
    hidden_at = _hidden_test(reg)
    thick = {s: _thickness(g, _polylines(g)) for s, g in glyphs.items()} if local else None
    plans = []
    for ci, c in enumerate(reg.contours):
        segs, _ = _segments(c)
        segs_w = {s: _segments(g.contours[ci])[0] for s, g in glyphs.items()}
        n = len(segs)
        flats = {}
        for i in range(n):
            nxt = segs[(i + 1) % n]
            if segs[i][0] == "curve" and nxt[0] == "curve" and segs[i][1] and nxt[1]:
                ax = _flat_axis(segs[i][1][-1], segs[i][2], nxt[1][0])
                if ax and not hidden_at([_xy(segs[i][1][-1]), _xy(segs[i][2]), _xy(segs[i][2]), _xy(nxt[1][0])]):
                    if phase and _counter_edge(reg, segs, i):
                        continue
                    flats[i] = ax
        splits, hidden = [], []
        for i, (kind, ctl, p) in enumerate(segs):
            if kind != "curve":
                splits.append([])
                hidden.append([False])
                continue
            Ps = {s: _seg_P(sg, i) for s, sg in segs_w.items()}
            cums = {s: _turns(P) for s, P in Ps.items()}
            T = cums["Regular"][-1]
            if T < 1e-6:
                splits.append([])
                hidden.append([hidden_at(Ps["Regular"])])
                continue
            at = lambda s, f: _bez(Ps[s], _t_at_turn(cums[s], f * cums[s][-1]))
            if local:   # half the stroke behind the middle of this segment, per weight
                seg_cap = {s: LOCAL_CUT * thick[s](_bez(P, 0.5), (_bez(P, 0.51)[0] - _bez(P, 0.49)[0],
                                                                  _bez(P, 0.51)[1] - _bez(P, 0.49)[1]))
                           for s, P in Ps.items()}
            else:
                seg_cap = caps

            def flat_cap(s, e, axis):
                return LOCAL_CUT * thick[s](e, (0, 1) if axis == "v" else (1, 0)) if local else caps[s]

            def flat_half(end):
                """Largest half-angle <= phi whose flat retreats no deeper than the cap at any weight."""
                j = i if end else (i - 1) % n
                if j not in flats:
                    return 0.0
                k = 0 if flats[j] == "v" else 1
                e = {s: (Ps[s][3] if end else Ps[s][0]) for s in Ps}
                fcap = {s: flat_cap(s, e[s], flats[j]) for s in Ps}
                f = min(math.radians(phi), 0.45 * T)
                while f > 1e-3:
                    ok = True
                    for s in Ps:
                        q = at(s, 1 - f / T if end else f / T)
                        snaps = k == 1 and _snap_target(e[s][1], q[1] > e[s][1], metrics[s]) is not None
                        if not snaps and abs(q[k] - e[s][k]) > fcap[s]:
                            ok = False
                    if ok:
                        return f
                    f *= 0.85
                return f

            ps, pe = flat_half(False), flat_half(True)
            cuts = ([ps] if ps else []) + ([T - pe] if pe else [])
            a, b = ps, T - pe
            if theta and b - a > 1e-6:
                k = max(1, round(math.degrees(b - a) / theta))
                while k < 24:
                    mids = [a + (b - a) * j / k for j in range(1, k)]
                    fr = sorted(x / T for x in [a, b] + mids if 1e-3 < x / T < 1 - 1e-3)
                    deep = any(_sagitta(pc) > seg_cap[s] for s in Ps for pc in _pieces(Ps[s], fr)[(1 if ps else 0):
                                                                                             (-1 if pe else None)])
                    if not deep:
                        break
                    k += 1
                cuts += [a + (b - a) * j / k for j in range(1, k)]
            splits.append(sorted(f for f in (x / T for x in cuts) if 1e-3 < f < 1 - 1e-3))
            hidden.append([hidden_at(pc) for pc in _pieces(Ps["Regular"], splits[-1])])
        plans.append({"flats": flats, "splits": splits, "hidden": hidden})
    return plans


def _pieces(P, fractions):
    """Split cubic P at the given turn fractions of its own total turn; list of 4-point pieces."""
    cum = _turns(P)
    ts = [_t_at_turn(cum, f * cum[-1]) for f in fractions]
    out, rest, done = [], P, 0.0
    for t in ts:
        local = (t - done) / (1 - done) if done < 1 else 0
        a, rest = split_cubic(*rest, min(max(local, 0.0), 1.0))
        out.append(a)
        done = t
    out.append(rest)
    return out


def _carve_contour(contour, plan, theta, carved, metrics):
    segs, trailing = _segments(contour)
    n = len(segs)
    # pieces per segment, each [p0, c1, c2, p3] as lists so the CARV 100 pass can move them
    built = []
    for i, (kind, ctl, p) in enumerate(segs):
        if kind == "curve":
            P = [_xy(segs[i - 1][2])] + [_xy(q) for q in ctl] + [_xy(p)]
            built.append([[list(q) for q in pc] for pc in _pieces(P, plan["splits"][i])])
        else:
            built.append([[list(_xy(segs[i - 1][2])), list(_xy(p))]])
    if carved:
        orig = [[[q[:] for q in pc] for pc in seg] for seg in built]
        for i, ax in plan["flats"].items():
            j = (i + 1) % n
            pa, e, pb = built[i][-1][0], built[i][-1][-1], built[j][0][-1]
            k = 0 if ax == "v" else 1
            v = (pa[k] + pb[k]) / 2
            if ax == "h":
                target = _snap_target(e[1], pa[1] > e[1], metrics)
                if target is not None:
                    v = target
            for q in (pa, e, pb, built[j][0][0]):
                q[k] = v
            if len(built[i]) > 1:
                built[i][-2][-1][k] = v      # the same point, as the end of the piece before
            if len(built[j]) > 1:
                built[j][1][0][k] = v
        for i, seg in enumerate(built):
            for m, pc in enumerate(seg):
                if len(pc) != 4:
                    continue
                flat = (m == 0 and (i - 1) % n in plan["flats"]) or (m == len(seg) - 1 and i in plan["flats"])
                if (theta or flat) and not plan["hidden"][i][m]:
                    p0, p3 = pc[0], pc[3]
                    pc[1] = [p0[0] + (p3[0] - p0[0]) / 3, p0[1] + (p3[1] - p0[1]) / 3]
                    pc[2] = [p0[0] + 2 * (p3[0] - p0[0]) / 3, p0[1] + 2 * (p3[1] - p0[1]) / 3]
                else:   # a curve piece keeps its shape; its handles follow their moved end points
                    o = orig[i][m]
                    pc[1] = [o[1][0] + pc[0][0] - o[0][0], o[1][1] + pc[0][1] - o[0][1]]
                    pc[2] = [o[2][0] + pc[3][0] - o[3][0], o[2][1] + pc[3][1] - o[3][1]]
        # keep shared points identical: a piece starts where the previous one ends
        for i in range(n):
            for m, pc in enumerate(built[i]):
                prev = built[i][m - 1] if m else built[i - 1][-1]
                pc[0] = prev[-1]
    out = []
    for i, (kind, ctl, p) in enumerate(segs):
        for pc in built[i]:
            if len(pc) == 4:
                out += [Point(*pc[1]), Point(*pc[2]), Point(*pc[3], type="curve", smooth=not carved)]
            else:
                out.append(Point(*pc[1], type=kind, smooth=p.smooth))
    if trailing:
        k = len(built[0]) * 3 - 1   # start, as the source does, at the first segment's on-curve end point
        out = out[k:] + out[:k]
    return Contour(points=out)


def _metrics(font):
    i = font.info
    return {"bottom": [0, i.descender], "top": [i.xHeight, i.capHeight, i.ascender]}


def cut_cap(font):
    """The deepest cut allowed in this master: CUT x its thin stroke, read as the top of the o (outer top minus
    counter top; Light 28, Regular 32, Bold 37 units)."""
    tops = sorted(max(p.y for p in c) for c in font["o"].contours)
    return CUT * (tops[-1] - tops[0])


def _merged_count(contours):
    from booleanOperations.booleanGlyph import BooleanGlyph
    g = ufoLib2.objects.Glyph()
    g.contours.extend(contours)
    bg = BooleanGlyph()
    g.drawPoints(bg.getPointPen())
    return len(bg.removeOverlap().contours)


def _bool(contours):
    from booleanOperations.booleanGlyph import BooleanGlyph
    g = ufoLib2.objects.Glyph()
    g.contours.extend(contours)
    bg = BooleanGlyph()
    g.drawPoints(bg.getPointPen())
    return bg


def _area_of(bg):
    from fontTools.pens.areaPen import AreaPen
    a = AreaPen()
    bg.draw(a)
    return abs(a.value)


def _iou(a, b):
    """Intersection over union of two outlines (overlaps merged), exactly, by boolean operations."""
    ga, gb = _bool(a), _bool(b)
    inter = _area_of(ga & gb)
    union = _area_of(_bool(a).removeOverlap()) + _area_of(_bool(b).removeOverlap()) - inter  # `|` returns empty here
    return inter / union if union else 1.0


def _angular_fits(src, v):
    """Glyph name -> {(style, carve): contours} for every glyph Ortica Angular's own cuts fit onto; the rest are
    logged (build/fit-<look>.json) and carved by the rules. A fit is kept only if no weight changes topology when
    carved (a stroke cut through or a part come loose)."""
    import json
    import angular_fit as af
    ang = af.load_angular()
    out, log, how = {}, {}, {}

    def attempt(name, plans, carver):
        """The six outlines for one fit, or the reason it is refused."""
        c0 = {s: af.contours(src[s][name], plans) for s in STYLES}
        c100_bold = carver(c0["Bold"], plans)
        th = {s: _thickness(src[s][name], _polylines(src[s][name])) for s in STYLES}
        tb = [[th["Bold"](p, t) for p, t in cont] for cont in af.end_points_and_tangents(c0["Bold"])]
        res = {}
        for s in STYLES:
            k = v.get("strength", {}).get(s, 1.0)
            ratios = [[min(1.0, th[s](p, t) / max(b, 1)) for (p, t), b in zip(cont, bc)]
                      for cont, bc in zip(af.end_points_and_tangents(c0[s]), tb)]
            res[(s, 0)] = af.to_contours(c0[s])
            res[(s, 100)] = af.to_contours(af.displaced(c0[s], c0["Bold"], c100_bold, k, ratios))
        if any(_merged_count(res[(s, 0)]) != _merged_count(res[(s, 100)]) for s in STYLES):
            return None, "topology changes when carved"
        # a scrambled correspondence can keep its topology: the carved Bold must be Angular's shape, and no lighter
        # weight may move much further from its plain outline than Bold does (Angular is a different drawing, so
        # Bold itself moves: its o overlaps Linear's by 0.74, and that difference is the personality being carried)
        target = af.angular_contours(src["Bold"][name], src["Bold"], ang[name], ang, name in EVEN)
        fit_iou = _iou(res[("Bold", 100)], target)
        drift = {s: _iou(res[(s, 0)], res[(s, 100)]) for s in STYLES}
        if fit_iou < 0.9 or min(drift.values()) < drift["Bold"] - 0.15:
            return None, (f"shape check: overlap with Angular {fit_iou:.2f}; with plain "
                          + ", ".join(f"{s} {d:.2f}" for s, d in drift.items()))
        return res, None

    for name in src["Bold"].keys():
        if not src["Bold"][name].contours:
            continue
        if name not in ang or not ang[name].contours:
            log[name] = "no Angular outline (absent, or components only)"
            continue
        res, why = None, None
        plans, why = af.plan(src["Bold"][name], src["Bold"], ang[name], ang, name in EVEN)
        if plans is not None:
            res, why = attempt(name, plans, af.carve_bold)
        if res is None:   # the general fit: overlapping pieces, or corners out of order (round 2, after the 6)
            gplans, gwhy = af.plan_general(src["Bold"][name], src["Bold"], ang[name], ang, ANCHORS.get(name),
                                           name in EVEN)
            if gplans is not None:
                res, gwhy = attempt(name, gplans, af.carve_bold_general)
            if res is None:
                log[name] = f"{why}; general fit: {gwhy}"
                continue
            how[name] = "general" + (" with anchors" if name in ANCHORS else "")
        out[name] = res
    log_path = ROOT / "build" / f"fit-{v['look'].replace(' ', '_').replace(',', '').replace(chr(39), '')}.json"
    log_path.parent.mkdir(exist_ok=True)
    log_path.write_text(json.dumps({"fitted": sorted(out), "general": how, "not_fitted": log}, indent=1),
                        encoding="utf-8")
    return out


def make_masters(variant, out_dir):
    v = VARIANTS[variant]
    out_dir = pathlib.Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    src = {s: ufoLib2.Font.open(ROOT / "sources" / f"Sisifo-{s}.ufo") for s in STYLES}
    caps = {s: cut_cap(f) for s, f in src.items()}
    metrics = {s: _metrics(f) for s, f in src.items()}
    plans = {name: plan_glyph({s: src[s][name] for s in STYLES}, caps, metrics, v["phi"], v["theta"],
                              v.get("phase", False), v.get("local", False))
             for name in src["Regular"].keys()}
    fitted = _angular_fits(src, v) if v.get("fit") == "angular" else {}
    paths = {}
    for s in STYLES:
        strength = v.get("strength", {}).get(s, 1.0)
        for carve_value in (0, 100):
            f = ufoLib2.Font.open(ROOT / "sources" / f"Sisifo-{s}.ufo")
            for g in f:
                if g.name in fitted:
                    g.clearContours()
                    g.contours.extend(fitted[g.name][(s, carve_value)])
                elif g.contours:
                    new = []
                    for c, p in zip(src[s][g.name].contours, plans[g.name]):
                        out = _carve_contour(c, p, v["theta"], carve_value == 100, _metrics(f))
                        if carve_value and strength < 1:   # a gentler carve: part of the way from plain to carved
                            plain = _carve_contour(c, p, v["theta"], False, _metrics(f))
                            for q, q0 in zip(out, plain):
                                q.x, q.y = q0.x + strength * (q.x - q0.x), q0.y + strength * (q.y - q0.y)
                        new.append(out)
                    g.clearContours()
                    g.contours.extend(new)
            if carve_value:
                f.info.styleName = f"{s} Carved"
            p = out_dir / f"Sisifo-{s}-C{carve_value}.ufo"
            f.save(p, overwrite=True)
            paths[(s, carve_value)] = p
    return paths


if __name__ == "__main__":
    var = sys.argv[1] if len(sys.argv) > 1 else "A"
    for k, p in make_masters(var, sys.argv[2] if len(sys.argv) > 2 else ROOT / "build" / "masters" / var).items():
        print(k, p)
