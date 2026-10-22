import pytest
from fontTools.ttLib import TTFont

import build
from conftest import ORIGINAL


@pytest.fixture(scope="module")
def font():
    p = build.build()
    return p, TTFont(p)


def test_axis_and_instances(font):
    _, t = font
    ax = {a.axisTag: (a.minValue, a.defaultValue, a.maxValue) for a in t["fvar"].axes}
    assert ax == {"wght": (300, 400, 700)}
    names = [t["name"].getDebugName(i.subfamilyNameID) for i in t["fvar"].instances]
    assert names == ["Light", "Regular", "Medium", "SemiBold", "Bold"]
    assert [i.coordinates["wght"] for i in t["fvar"].instances] == [300, 400, 500, 600, 700]


def test_names_and_licence(font):
    _, t = font
    assert t["name"].getDebugName(1) == "Sisifo"
    assert "Benedetta Bovani" in t["name"].getDebugName(0)
    assert "Open Font License" in t["name"].getDebugName(13)


def test_coverage_at_least_ortica(font):
    _, t = font
    orig = TTFont(ORIGINAL["Regular"])
    assert set(orig.getBestCmap()) <= set(t.getBestCmap())
    assert len(t.getGlyphOrder()) >= len(orig.getGlyphOrder())


def test_size(font):
    p, _ = font
    assert p.stat().st_size <= 400 * 1024


@pytest.fixture(scope="module", params=["A", "E"])
def carved(request):
    p = build.build_carved(request.param)
    return p, TTFont(p)


def test_carved_axes(carved):
    _, t = carved
    ax = {a.axisTag: (a.minValue, a.defaultValue, a.maxValue) for a in t["fvar"].axes}
    assert ax == {"wght": (300, 400, 700), "CARV": (0, 0, 100)}
    assert all(i.coordinates["CARV"] == 0 for i in t["fvar"].instances)


def test_carved_size_and_coverage(carved):
    p, t = carved
    assert p.stat().st_size <= 400 * 1024
    assert set(TTFont(ORIGINAL["Regular"]).getBestCmap()) <= set(t.getBestCmap())


def test_ss01_off_is_gl():
    """Owner, 2026-10-23: "Keep GL inside GLZ: document that ss01 off is GL, no separate file." Every glyph of the GL
    build has the same outline and advance in the release, at several weight and carve points."""
    from fontTools.pens.recordingPen import DecomposingRecordingPen
    from fontTools.varLib.instancer import instantiateVariableFont
    gl, rel = build.build_carved("GL"), build.release()
    names = TTFont(gl).getGlyphOrder()
    for w, c in ((300, 0), (400, 100), (550, 50), (700, 100)):
        a = instantiateVariableFont(TTFont(gl), {"wght": w, "CARV": c}, static=True)
        b = instantiateVariableFont(TTFont(rel), {"wght": w, "CARV": c}, static=True)
        ga, gb = a.getGlyphSet(), b.getGlyphSet()
        for n in names:
            pa, pb = DecomposingRecordingPen(ga), DecomposingRecordingPen(gb)
            ga[n].draw(pa)
            gb[n].draw(pb)
            assert pa.value == pb.value and a["hmtx"].metrics[n] == b["hmtx"].metrics[n], (n, w, c)
