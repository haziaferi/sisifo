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
