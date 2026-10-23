import re

import pytest
import ufoLib2
from fontTools.pens.boundsPen import BoundsPen

import compat
import ss01
from conftest import SOURCES

STYLES = ("Light", "Regular", "Bold")


@pytest.fixture(scope="module", params=["P", "Z"])
def fonts(request):
    fs = {s: ufoLib2.Font.open(SOURCES / f"Sisifo-{s}.ufo") for s in STYLES}
    names = ss01.add(fs, request.param)
    return request.param, fs, names


def _ink(font, name):
    b = BoundsPen(font)
    font[name].draw(b)
    return b.bounds


def test_all_capitals_and_italian_accents(fonts):
    _, fs, names = fonts
    for ch in "ABCDEFGHIJKLMNOPQRSTUVWXYZ":
        assert f"{ch}.ss01" in names
    for n in ("Agrave", "Egrave", "Eacute", "Igrave", "Ograve", "Ugrave"):
        assert f"{n}.ss01" in names


def test_ss01_compatible(fonts):
    _, fs, names = fonts
    bad = [n for n in names if len({repr(compat.signature(fs[s][n])) for s in STYLES}) > 1]
    assert bad == []


def test_feature_maps_every_new_glyph(fonts):
    _, fs, names = fonts
    block = re.search(r"feature ss01 \{(.*?)\} ss01;", fs["Regular"].features.text, re.S)
    assert block
    for n in names:
        assert f"sub {n[:-5]} by {n};" in block.group(1)


def test_accented_capitals_follow(fonts):
    """Owner's titles ("MOBILITÀ"): À's base is A.ss01 and its grave sits over A.ss01's middle as it did over A's."""
    _, fs, _ = fonts
    f = fs["Regular"]
    comps = f["Agrave.ss01"].components
    assert comps[0].baseGlyph == "A.ss01"
    a0, a1 = _ink(f, "A"), _ink(f, "A.ss01")
    shift = ((a1[0] + a1[2]) - (a0[0] + a0[2])) / 2
    orig = f["Agrave"].components[1].transformation[4]
    assert abs(comps[1].transformation[4] - (orig + shift)) <= 1


@pytest.mark.parametrize("ch", ["E", "F", "L", "S", "O", "H"])
def test_p_widths_follow_cinzel(ch):
    fs = {s: ufoLib2.Font.open(SOURCES / f"Sisifo-{s}.ufo") for s in STYLES}
    ss01.add(fs, "P")
    f = fs["Regular"]
    b0, b1 = _ink(f, ch), _ink(f, f"{ch}.ss01")
    assert abs((b1[2] - b1[0]) / (b0[2] - b0[0]) - ss01.RATIOS[ch]) <= 0.02


def test_p_keeps_stems():
    """P stretches in a band between the stems: H's left stem is as thick as before, at every weight."""
    fs = {s: ufoLib2.Font.open(SOURCES / f"Sisifo-{s}.ufo") for s in STYLES}
    before = {s: ss01.stem(fs[s], "H") for s in STYLES}
    ss01.add(fs, "P")
    for s in STYLES:
        assert abs(ss01.stem(fs[s], "H.ss01") - before[s]) <= 2


def test_z_stems_match_sisifo():
    """Z: Cinzel's I is matched to Sisifo's I stem at each weight (Light extrapolated)."""
    fs = {s: ufoLib2.Font.open(SOURCES / f"Sisifo-{s}.ufo") for s in STYLES}
    target = {s: ss01.stem(fs[s], "I") for s in STYLES}
    ss01.add(fs, "Z")
    for s in STYLES:
        assert abs(ss01.stem(fs[s], "I.ss01") - target[s]) <= 0.05 * target[s]


def test_z_credits_cinzel():
    fs = {s: ufoLib2.Font.open(SOURCES / f"Sisifo-{s}.ufo") for s in STYLES}
    ss01.add(fs, "Z")
    assert all("Cinzel Project Authors" in fs[s].info.copyright for s in STYLES)


def test_z_kerned_from_cinzel():
    """Z's capitals take Cinzel's own kerning at each master's weight: classic pairs tighten, every ss01 capital and
    its accented forms are in one kerning group per side."""
    fs = {s: ufoLib2.Font.open(SOURCES / f"Sisifo-{s}.ufo") for s in STYLES}
    names = ss01.add(fs, "Z")
    for s, f in fs.items():
        k = f.kerning
        for a, b in (("A", "V"), ("T", "A"), ("L", "T"), ("A", "Y")):
            assert k[(f"public.kern1.ss01_{a}", f"public.kern2.ss01_{b}")] < -40, (s, a, b)
        assert k[("public.kern1.ss01_T", "period")] < -40
        for side in ("kern1", "kern2"):
            grouped = [n for g, m in f.groups.items() if g.startswith(f"public.{side}.ss01_") for n in m]
            assert sorted(grouped) == sorted(names), (s, side)
