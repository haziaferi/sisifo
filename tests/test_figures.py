import re
import shutil
import statistics

import pytest
import ufoLib2
from fontTools.pens.boundsPen import BoundsPen

import figures
from conftest import SOURCES

STYLES = ("Light", "Regular", "Bold")


def _ink(font, name):
    b = BoundsPen(font)
    font[name].draw(b)
    return b.bounds


@pytest.fixture(scope="module", params=STYLES)
def font(request):
    return ufoLib2.Font.open(SOURCES / f"Sisifo-{request.param}.ufo")


def test_tabular_width_rule(font):
    inks, sides = [], []
    for d in figures.DIGITS:
        x0, _, x1, _ = _ink(font, d)
        inks.append(x1 - x0)
        sides.append(min(x0, font[d].width - x1))
    W = round(max(inks) + 2 * statistics.median(sides))
    assert figures.tabular_width(font) == W
    assert {font[d + ".tf"].width for d in figures.DIGITS} == {W}


def test_tf_is_shifted_digit(font):
    W = figures.tabular_width(font)
    for d in figures.DIGITS:
        g = font[d + ".tf"]
        assert not g.contours and len(g.components) == 1 and g.components[0].baseGlyph == d
        x0, _, x1, _ = _ink(font, d)
        L, R = x0, font[d].width - x1
        assert g.components[0].transformation[4] == round((W - (x1 - x0)) * L / (L + R)) - round(L)
        assert g.components[0].transformation[5] == 0


def test_tf_ink_inside_advance(font):
    for d in figures.DIGITS:
        x0, _, x1, _ = _ink(font, d + ".tf")
        assert x0 >= 0 and x1 <= font[d + ".tf"].width, d


def test_tnum_feature_maps_all_ten(font):
    block = re.search(r"feature tnum \{(.*?)\} tnum;", font.features.text, re.S)
    assert block
    for d in figures.DIGITS:
        assert f"sub {d} by {d}.tf;" in block.group(1)


def test_apply_is_idempotent(tmp_path):
    shutil.copytree(SOURCES / "Sisifo-Regular.ufo", tmp_path / "R.ufo")
    figures.apply(tmp_path / "R.ufo")
    figures.apply(tmp_path / "R.ufo")
    f = ufoLib2.Font.open(tmp_path / "R.ufo")
    assert f.features.text.count("feature tnum {") == 1
    assert sum(n.endswith(".tf") for n in f.keys()) == 10
    assert sum(n.endswith(".tf") for n in f.lib["public.glyphOrder"]) == 10
