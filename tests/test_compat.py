import math
import shutil

import pytest
import ufoLib2
from fontTools.pens.areaPen import AreaPen
from fontTools.pens.boundsPen import BoundsPen

import compat
from conftest import ORIGINAL_UFO, SOURCES

FIXED_NAMES = ["A", "I", "M", "Q", "V", "W", "X", "Y", "ampersand", "b", "d", "h", "k", "l", "m", "n", "p", "r", "u",
               "v", "w", "x", "y"]


def bez(p0, p1, p2, p3, s):
    u = 1 - s
    return tuple(u ** 3 * a + 3 * u * u * s * b + 3 * u * s * s * c + s ** 3 * d for a, b, c, d in zip(p0, p1, p2, p3))


def test_split_preserves_shape():
    P = ((0, 0), (10, 40), (60, 40), (80, 0))
    a, b = compat.split_cubic(*P, 0.37)
    assert a[0] == P[0] and b[3] == P[3] and a[3] == b[0]
    for s in range(101):                       # exact: the original at s is the first half at s/t or the second at (s-t)/(1-t)
        s = s / 100
        q = bez(*a, s / 0.37) if s <= 0.37 else bez(*b, (s - 0.37) / 0.63)
        assert math.dist(q, bez(*P, s)) < 1e-9


@pytest.fixture(scope="module")
def fixed(tmp_path_factory):
    d = tmp_path_factory.mktemp("ufos")
    fonts = []
    for s in ("Light", "Regular", "Bold"):
        shutil.copytree(SOURCES / f"Sisifo-{s}.ufo", d / f"{s}.ufo")
        fonts.append(ufoLib2.Font.open(d / f"{s}.ufo"))
    report = compat.make_compatible(*fonts)
    return fonts, report


def test_all_glyphs_compatible(fixed):
    (L, R, B), _ = fixed
    bad = [n for n in B.keys() if not (compat.signature(L[n]) == compat.signature(R[n]) == compat.signature(B[n]))]
    assert bad == []


def test_report_names_the_25(fixed):
    _, report = fixed
    assert set(report) == set(FIXED_NAMES) | {"f_k", "zero.dnom"}


def _area_bounds(glyph, font):
    a, b = AreaPen(font), BoundsPen(font)
    glyph.draw(a)
    glyph.draw(b)
    return a.value, b.bounds


@pytest.mark.parametrize("name", FIXED_NAMES)
@pytest.mark.parametrize("style,index", [("Light", 0), ("Regular", 1)])
def test_shape_unchanged(fixed, name, style, index):
    fonts, _ = fixed
    orig = ufoLib2.Font.open(ORIGINAL_UFO[style])
    a0, b0 = _area_bounds(orig[name], orig)
    a1, b1 = _area_bounds(fonts[index][name], fonts[index])
    assert abs(a1 - a0) <= 0.001 * abs(a0)
    assert all(abs(x - y) <= 1 for x, y in zip(b0, b1))
    assert fonts[index][name].width == orig[name].width


def test_f_k_reordered(fixed):
    (L, R, B), _ = fixed
    assert [len(c) for c in R["f_k"].contours] == [len(c) for c in B["f_k"].contours]


def test_zero_dnom_drawn(fixed):
    (L, R, B), _ = fixed
    assert [len(c) for c in R["zero.dnom"].contours] == [12, 12]
    assert R["zero.dnom"].width == 391          # Light 363 + 0.25 x (474 - 363)


def test_composites_resolve_at_all_masters(fixed):
    fonts, _ = fixed
    for f in fonts:
        for n in ("Agrave", "Eacute", "Igrave", "Ograve", "Ugrave", "Q"):
            assert all(c.baseGlyph in f for c in f[n].components)
