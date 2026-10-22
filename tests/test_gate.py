import pytest

import gate


@pytest.mark.parametrize("w,style", [(300, "Light"), (400, "Regular"), (700, "Bold")])
def test_instances_match_original(w, style):
    r = gate.compare_outlines(w, style)
    assert r["compared"] == 394          # every glyph of the original but .notdef
    assert r["mismatches"] == [], r["mismatches"][:10]


def test_same_glyph_set_as_original():
    new, old = gate.instance(400), gate.original("Regular")
    tf = {d + ".tf" for d in ("zero", "one", "two", "three", "four", "five", "six", "seven", "eight", "nine")}
    assert set(new.getGlyphOrder()) == set(old.getGlyphOrder()) | tf   # helpers (zero.dnom...) stay unexported


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


def test_tabular_one_width_per_instance():
    widths = gate.tabular_widths((300, 400, 550, 700))
    assert all(len(s) == 1 for s in widths.values()), widths


def test_tnum_shaped_equal():
    assert gate.tnum_shaped_diff((300, 400, 550, 700)) <= 0.01


@pytest.fixture(params=["A", "E"])
def carved_font(request):
    import build
    p = build.ROOT / "build" / "variants" / request.param / "Sisifo[CARV,wght].ttf"
    if not p.exists():
        build.build_carved(request.param)
    return p


def test_carved_matches_original_at_carve0(carved_font):
    r = gate.compare_outlines(400, "Regular", vf=carved_font)
    assert r["compared"] == 394 and r["mismatches"] == [], r["mismatches"][:10]


def test_no_outline_errors_carved(carved_font):
    for w in (300, 550, 700):
        for c in (50, 100):
            assert gate.outline_errors(w, carve=c, vf=carved_font) == [], (w, c)


def test_no_direction_flips_carved(carved_font):
    assert gate.direction_flips((300, 550, 700), carves=(0, 50, 100), vf=carved_font) == []
