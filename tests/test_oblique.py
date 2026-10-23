import copy
import math
import random

import pytest
import ufoLib2
from fontTools.pens.recordingPen import DecomposingRecordingPen

import oblique
from conftest import SOURCES


@pytest.mark.parametrize("matrix", [(1, 0, 0, 1, 186, 211), (1, 0, 0, -1, 40, 900), (0.8, 0.1, -0.2, 1.1, 5, -30)])
def test_component_slant_is_exact(matrix):
    """A component (plain, flipped like caroncomb.case, or any matrix) slanted with its base gives exactly the slanted
    composite."""
    t = math.tan(math.radians(9))
    c = t * 502 / 2
    slant = lambda p: (p[0] + t * p[1] - c, p[1])
    f = ufoLib2.Font()
    f.info.xHeight = 502
    f.newGlyph("base")
    g = f.newGlyph("comp")
    g.components.append(ufoLib2.objects.Component("base", matrix))
    oblique.slant_font(f, 9)
    xx, xy, yx, yy, dx, dy = matrix
    n = g.components[0].transformation
    rng = random.Random(9)
    for _ in range(20):
        q = (rng.uniform(-500, 500), rng.uniform(-500, 900))
        want = slant((xx * q[0] + yx * q[1] + dx, xy * q[0] + yy * q[1] + dy))
        qs = slant(q)
        got = (n[0] * qs[0] + n[2] * qs[1] + n[4], n[1] * qs[0] + n[3] * qs[1] + n[5])
        assert math.dist(want, got) < 1e-9


@pytest.mark.parametrize("name", ["Agrave", "Ccaron", "eacute", "iacute", "Uogonek"])
def test_accents_follow_slant(name):
    """Every point of an accented letter, drawn through its components, is the upright point slanted."""
    src = ufoLib2.Font.open(SOURCES / "Sisifo-Regular.ufo")
    sl = oblique.slant_font(copy.deepcopy(src), 9)
    a, b = DecomposingRecordingPen(src), DecomposingRecordingPen(sl)
    src[name].draw(a)
    sl[name].draw(b)
    pts = lambda rec: [p for _, args in rec.value for p in args]
    for p, q in zip(pts(a), pts(b)):
        want = oblique.slant_point(p[0], p[1], 9, src.info.xHeight)
        assert math.dist(want, q) < 1e-6, name


def test_slant_keeps_advances_and_kerning():
    src = ufoLib2.Font.open(SOURCES / "Sisifo-Regular.ufo")
    sl = oblique.slant_font(copy.deepcopy(src), 12)
    assert all(sl[g.name].width == g.width for g in src)
    assert dict(sl.kerning) == dict(src.kerning)
    assert sl.info.italicAngle == -12
