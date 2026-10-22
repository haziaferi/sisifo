import pytest

import gate


@pytest.mark.parametrize("w,style", [(300, "Light"), (400, "Regular"), (700, "Bold")])
def test_instances_match_original(w, style):
    r = gate.compare_outlines(w, style)
    assert r["compared"] == 394          # every glyph of the original but .notdef
    assert r["mismatches"] == [], r["mismatches"][:10]


def test_same_glyph_set_as_original():
    new, old = gate.instance(400), gate.original("Regular")
    assert set(new.getGlyphOrder()) == set(old.getGlyphOrder())   # helper glyphs (zero.dnom...) stay unexported


@pytest.mark.parametrize("w", [300, 400, 700, 350, 550, 650])
def test_no_outline_errors(w):
    assert gate.outline_errors(w) == []


def test_intermediate_instances_clean():
    assert gate.direction_flips((300, 350, 400, 550, 650, 700)) == []


def test_kerning_widths_match_original():
    assert gate.shaped_widths_diff(["AVATAR", "To Ty Yo", "Wave LT", "Panca piana 62.5 kg"],
                                   weights=(300, 400, 700)) <= 0.5


def test_app_characters_match_original():
    r = gate.compare_outlines(400, "Regular", chars="0123456789.,×·–’«»àèéìòùÀÈÉÌÒÙ")
    assert r["compared"] == 30 and r["mismatches"] == []
