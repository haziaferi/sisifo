"""Make Sisifo's Light and Regular masters point-compatible with Bold, without changing their shapes.

Usage:  python tools/compat.py     (edits sources/Sisifo-{Light,Regular}.ufo in place; prints what it did; exit 1 if
                                    any glyph is still incompatible)

Where Ortica's Bold draws a stretch as 2-3 cubic curves and Light/Regular draw it as one (e.g. the flag of l's head
serif), the single curve is split at the same fractions of its arc length where Bold's inner on-curve points fall.
A split never changes a curve's shape; new points are rounded to whole units. Which curve matches which run of Bold
curves is decided per contour by a small dynamic programme that minimises the distance between matched on-curve
points (both normalised to the glyph's box), so similar-looking stretches are not confused.
Two special cases: f_k's contours are reordered to Bold's order, and zero.dnom (empty in Ortica's Regular, an
upstream bug) is drawn by interpolating Light and Bold at 0.25, Regular's place on the 300-700 axis.
"""
import math
import pathlib
import sys

import ufoLib2
from ufoLib2.objects import Contour, Point

ROOT = pathlib.Path(__file__).resolve().parent.parent
MAX_RUN = 3


def split_cubic(p0, p1, p2, p3, t):
    """de Casteljau split of a cubic at t: two cubics, each as four points."""
    lerp = lambda a, b: (a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t)
    a, b, c = lerp(p0, p1), lerp(p1, p2), lerp(p2, p3)
    d, e = lerp(a, b), lerp(b, c)
    f = lerp(d, e)
    return [p0, a, d, f], [f, e, c, p3]


def _bez(P, s):
    u = 1 - s
    return tuple(u ** 3 * a + 3 * u * u * s * b + 3 * u * s * s * c + s ** 3 * d for a, b, c, d in zip(*P))


def _length(P, n=200):
    pts = [_bez(P, i / n) for i in range(n + 1)]
    return sum(math.dist(pts[i], pts[i + 1]) for i in range(n))


def _t_at_fraction(P, frac, n=400):
    """Parameter t where the arc length from 0 reaches frac of the total."""
    pts = [_bez(P, i / n) for i in range(n + 1)]
    cum = [0.0]
    for i in range(n):
        cum.append(cum[-1] + math.dist(pts[i], pts[i + 1]))
    goal = frac * cum[-1]
    for i in range(n):
        if cum[i + 1] >= goal:
            span = cum[i + 1] - cum[i]
            return (i + ((goal - cum[i]) / span if span else 0)) / n
    return 1.0


def signature(glyph):
    """Structure that must match across masters: point types per contour, and component bases."""
    return (tuple(tuple(p.type or "off" for p in c.points) for c in glyph.contours),
            tuple(sorted(c.baseGlyph for c in glyph.components)))


def _segments(contour):
    """Closed contour -> list of (type, [controls], oncurve Point); controls are the off-curve points before it.
    Also returns how many off-curve points trail the list (they belong to the first segment)."""
    pts = list(contour.points)
    trailing = 0
    while trailing < len(pts) and pts[-1 - trailing].type is None:
        trailing += 1
    order = pts[-trailing:] + pts[:-trailing] if trailing else pts
    segs, ctl = [], []
    for p in order:
        if p.type is None:
            ctl.append(p)
        else:
            segs.append((p.type, ctl, p))
            ctl = []
    return segs, trailing


def _emit(segs, trailing):
    out = []
    for _, ctl, p in segs:
        out += ctl + [p]
    if trailing:
        k = len(segs[0][1])
        out = out[k:] + out[:k]
    return out


def _xy(p):
    return (p.x, p.y)


def _align(rs, bs, rbox, bbox):
    """Minimum-cost match of R segments to runs of B segments. Returns run lengths per R segment, or None."""
    n, m = len(rs), len(bs)
    norm = lambda p, box: ((p[0] - box[0]) / max(1, box[2] - box[0]), (p[1] - box[1]) / max(1, box[3] - box[1]))
    INF = float("inf")
    dp = [[INF] * (m + 1) for _ in range(n + 1)]
    back = [[None] * (m + 1) for _ in range(n + 1)]
    dp[0][0] = 0.0
    for i in range(n):
        for j in range(m):
            if dp[i][j] == INF:
                continue
            for k in range(1, MAX_RUN + 1):
                if j + k > m:
                    break
                run = bs[j:j + k]
                if k == 1 and run[0][0] != rs[i][0]:
                    continue
                if k > 1 and (rs[i][0] != "curve" or any(s[0] != "curve" for s in run)):
                    continue
                cost = math.dist(norm(_xy(rs[i][2]), rbox), norm(_xy(run[-1][2]), bbox)) + 0.05 * (k - 1)
                if dp[i][j] + cost < dp[i + 1][j + k]:
                    dp[i + 1][j + k] = dp[i][j] + cost
                    back[i + 1][j + k] = k
    if dp[n][m] == INF:
        return None
    runs, j = [], m
    for i in range(n, 0, -1):
        k = back[i][j]
        runs.append(k)
        j -= k
    return runs[::-1]


def _box(glyph):
    xs = [p.x for c in glyph.contours for p in c.points] or [0]
    ys = [p.y for c in glyph.contours for p in c.points] or [0]
    return (min(xs), min(ys), max(xs), max(ys))


def _split_to_match(contour, runs, bsegs, rot=0):
    """Rebuild one Light/Regular contour so each segment i becomes runs[i] segments, split like Bold's run.
    bsegs is Bold's segment list rotated right by rot (a split stretch can wrap past the end of the point list);
    the result is rotated back so its point order mirrors Bold's."""
    segs, trailing = _segments(contour)
    out, j = [], 0
    for i, (typ, ctl, p) in enumerate(segs):
        k = runs[i]
        if k == 1:
            out.append((typ, ctl, p))
        else:
            start = _xy(segs[i - 1][2])
            P = [start] + [_xy(c) for c in ctl] + [_xy(p)]
            run = bsegs[j:j + k]
            bprev = _xy(bsegs[j - 1][2])
            lens, prev = [], bprev
            for (_, bctl, bp) in run:
                lens.append(_length([prev] + [_xy(c) for c in bctl] + [_xy(bp)]))
                prev = _xy(bp)
            total, acc, rest = sum(lens), 0.0, P
            done = 0.0
            for L_ in lens[:-1]:
                acc += L_
                frac = (acc / total - done) / (1 - done)           # fraction of what is left of the curve
                a, rest = split_cubic(*rest, _t_at_fraction(rest, frac))
                done = acc / total
                r = lambda q: Point(round(q[0]), round(q[1]))
                on = r(a[3])
                on.type, on.smooth = "curve", True
                out.append(("curve", [r(a[1]), r(a[2])], on))
            out.append(("curve", [Point(round(rest[1][0]), round(rest[1][1])),
                                  Point(round(rest[2][0]), round(rest[2][1]))], p))
        j += k
    if rot:
        out = out[rot:] + out[:rot]
    contour.points[:] = _emit(out, trailing)


def _rotate_start(glyph, ref):
    """Where a contour has the same point types as ref's but starts elsewhere, rotate its point list (shape unchanged)
    to the start whose on-curve points lie closest to ref's, both normalised to their glyph boxes."""
    changed = False
    gbox, rbox = _box(glyph), _box(ref)
    norm = lambda p, b: ((p.x - b[0]) / max(1, b[2] - b[0]), (p.y - b[1]) / max(1, b[3] - b[1]))
    for c, rc in zip(glyph.contours, ref.contours):
        pts, want = list(c.points), [p.type for p in rc.points]
        if len(pts) != len(want) or [p.type for p in pts] == want:
            continue
        best = None
        for r in range(len(pts)):
            cand = pts[r:] + pts[:r]
            if [p.type for p in cand] != want:
                continue
            d = sum(math.dist(norm(a, gbox), norm(b, rbox)) for a, b in zip(cand, rc.points) if a.type)
            if best is None or d < best[0]:
                best = (d, cand)
        if best:
            c.points[:] = best[1]
            changed = True
    return changed


def _fix_glyph(name, L, R, B):
    gL, gR, gB = L[name], R[name], B[name]
    rotated = any([_rotate_start(gL, gB), _rotate_start(gR, gB)]) if gR.contours else _rotate_start(gL, gB)
    if signature(gL) == signature(gB) and (signature(gR) == signature(gB)):
        return "contour start rotated to Bold's"
    if name == "zero.dnom" and not gR.contours:
        gR.clearContours()
        for cl, cb in zip(gL.contours, gB.contours):
            pts = []
            for pl, pb in zip(cl.points, cb.points):
                pts.append(Point(round(pl.x + 0.25 * (pb.x - pl.x)), round(pl.y + 0.25 * (pb.y - pl.y)),
                                 type=pl.type, smooth=pl.smooth))
            gR.contours.append(Contour(points=pts))
        gR.width = round(gL.width + 0.25 * (gB.width - gL.width))
        return ("drawn by interpolating Light and Bold at 0.25 (empty upstream)"
                + ("; Light's start rotated to Bold's" if rotated else ""))
    if len(gR.contours) == len(gB.contours) and sorted(map(len, gR.contours)) == sorted(map(len, gB.contours)) \
            and [len(c) for c in gR.contours] != [len(c) for c in gB.contours]:
        for g in (gL, gR):
            want = [len(c) for c in gB.contours]
            pool = list(g.contours)
            g.contours[:] = [pool.pop(next(i for i, c in enumerate(pool) if len(c) == n)) for n in want]
        return "contours reordered to Bold's order"
    done = []
    rbox, bbox = _box(gR), _box(gB)
    for ci, (cR, cB) in enumerate(zip(gR.contours, gB.contours)):
        if len(cR) == len(cB):
            continue
        rs, _ = _segments(cR)
        bs, _ = _segments(cB)
        for rot in range(MAX_RUN):      # a split stretch may wrap past the end of Bold's point list
            brot = bs[-rot:] + bs[:-rot] if rot else bs
            runs = _align(rs, brot, rbox, bbox)
            if runs is not None:
                break
        if runs is None:
            return None
        for g in (gL, gR):
            _split_to_match(g.contours[ci], runs, brot, rot)
        done.append(f"contour {ci}: split {sum(k - 1 for k in runs)} curve(s)")
    return "; ".join(done)


def make_compatible(light, regular, bold):
    report = {}
    for name in bold.keys():
        if signature(light[name]) == signature(regular[name]) == signature(bold[name]):
            continue
        what = _fix_glyph(name, light, regular, bold)
        if what is not None:
            report[name] = what
    return report


def main():
    fonts = [ufoLib2.Font.open(ROOT / "sources" / f"Sisifo-{s}.ufo") for s in ("Light", "Regular", "Bold")]
    report = make_compatible(*fonts)
    for n, w in sorted(report.items()):
        print(f"{n:12s} {w}")
    left = [n for n in fonts[2].keys() if not (signature(fonts[0][n]) == signature(fonts[1][n]) == signature(fonts[2][n]))]
    for f in fonts[:2]:
        f.save(overwrite=True)
    print(f"{len(report)} fixed, {len(left)} left" + (f": {left}" if left else ""))
    return 1 if left else 0


if __name__ == "__main__":
    sys.exit(main())
