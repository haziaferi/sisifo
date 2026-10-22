import pytest
import ufoLib2
from fontTools.pens.areaPen import AreaPen
from fontTools.pens.boundsPen import BoundsPen

import carve
import compat
from conftest import SOURCES

STYLES = ("Light", "Regular", "Bold")
SHAPES = ["o", "O", "S", "a", "g", "e", "zero", "eight", "Q", "at"]


@pytest.fixture(scope="module")
def masters(tmp_path_factory):
    out = {}
    for v in ("A", "C", "E"):
        paths = carve.make_masters(v, tmp_path_factory.mktemp(v))
        out[v] = {k: ufoLib2.Font.open(p) for k, p in paths.items()}
    return out


def _area_bounds(font, name):
    a, b = AreaPen(font), BoundsPen(font)
    font[name].draw(a)
    font[name].draw(b)
    return a.value, b.bounds


def _curves(glyph):
    for c in glyph.contours:
        segs, _ = compat._segments(c)
        for i, (kind, ctl, p) in enumerate(segs):
            if kind == "curve":
                yield segs[i - 1][2], ctl, p


def _straight(p0, ctl, p3, tol=0.5):
    dx, dy = p3.x - p0.x, p3.y - p0.y
    n = (dx * dx + dy * dy) ** 0.5 or 1
    return all(abs((c.x - p0.x) * dy - (c.y - p0.y) * dx) / n <= tol for c in ctl)


@pytest.mark.parametrize("style", STYLES)
def test_carve0_preserves_shape(masters, style):
    src = ufoLib2.Font.open(SOURCES / f"Sisifo-{style}.ufo")
    for name in SHAPES:
        a0, b0 = _area_bounds(src, name)
        a1, b1 = _area_bounds(masters["C"][(style, 0)], name)
        assert abs(a1 - a0) <= 0.001 * abs(a0), name
        assert all(abs(x - y) <= 1 for x, y in zip(b0, b1)), name


@pytest.mark.parametrize("variant", ["A", "C", "E"])
def test_six_masters_compatible(masters, variant):
    fonts = list(masters[variant].values())
    assert len(fonts) == 6
    bad = [n for n in fonts[0].keys() if len({repr(compat.signature(f[n])) for f in fonts}) > 1]
    assert bad == []


@pytest.mark.parametrize("name", ["o", "S", "zero", "e"])
def test_facets_straight(masters, name):
    g = masters["A"][("Regular", 100)][name]
    assert all(_straight(p0, ctl, p3) for p0, ctl, p3 in _curves(g))


def test_flats_axis_aligned(masters):
    g = masters["A"][("Regular", 100)]["o"]
    outer = max(g.contours, key=lambda c: max(p.x for p in c) - min(p.x for p in c))
    on = [p for p in outer if p.type is not None]
    xs, ys = [p.x for p in on], [p.y for p in on]
    left = [p for p in on if p.x == min(xs)]
    right = [p for p in on if p.x == max(xs)]
    bottom = [p for p in on if p.y == min(ys)]
    top = [p for p in on if p.y == max(ys)]
    for side, coord in ((left, "y"), (right, "y"), (bottom, "x"), (top, "x")):
        span = max(getattr(p, coord) for p in side) - min(getattr(p, coord) for p in side)
        assert len(side) >= 2 and span > 50


@pytest.mark.parametrize("style", STYLES)
def test_flats_snap_to_metrics(masters, style):
    f = masters["A"][(style, 100)]
    ys = [p.y for c in f["o"].contours for p in c if p.type is not None]
    assert min(ys) == 0 and max(ys) == f.info.xHeight


def test_flats_only_keeps_curves(masters):
    g = masters["E"][("Regular", 100)]["o"]
    assert not all(_straight(p0, ctl, p3) for p0, ctl, p3 in _curves(g))


@pytest.mark.parametrize("style", STYLES)
def test_widths_and_components_unchanged(masters, style):
    src = ufoLib2.Font.open(SOURCES / f"Sisifo-{style}.ufo")
    for carved in (masters["A"][(style, 0)], masters["A"][(style, 100)]):
        for g in src:
            assert carved[g.name].width == g.width, g.name
            assert [(c.baseGlyph, tuple(c.transformation)) for c in carved[g.name].components] == \
                   [(c.baseGlyph, tuple(c.transformation)) for c in g.components], g.name


def _topology(font, name):
    from booleanOperations.booleanGlyph import BooleanGlyph
    bg = BooleanGlyph()
    font[name].drawPoints(bg.getPointPen())
    return len(bg.removeOverlap().contours)


@pytest.mark.parametrize("variant", ["A", "C"])
@pytest.mark.parametrize("style", STYLES)
def test_topology_unchanged(masters, variant, style):
    """A carve that lets a counter touch the outside (a stroke cut through) changes how many contours remain once
    overlaps merge."""
    c0, c100 = masters[variant][(style, 0)], masters[variant][(style, 100)]
    bad = [g.name for g in c0 if g.contours and _topology(c0, g.name) != _topology(c100, g.name)]
    assert bad == []


@pytest.mark.parametrize("style", STYLES)
def test_counters_not_snapped(masters, style):
    f = masters["A"][(style, 100)]
    inner = min(f["o"].contours, key=lambda c: max(p.x for p in c) - min(p.x for p in c))
    ys = [p.y for p in inner if p.type is not None]
    assert min(ys) > 0 and max(ys) < f.info.xHeight
