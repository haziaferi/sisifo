import pytest
import ufoLib2

from conftest import SOURCES


@pytest.mark.parametrize("style,weight", [("Light", 300), ("Regular", 400), ("Bold", 700)])
def test_family_and_copyright(style, weight):
    f = ufoLib2.Font.open(SOURCES / f"Sisifo-{style}.ufo")
    assert f.info.familyName == "Sisifo" and f.info.styleName == style
    assert f.info.openTypeOS2WeightClass == weight
    assert "Benedetta Bovani" in f.info.copyright and "Sisifo" in f.info.copyright
    assert "Ortica" not in (f.info.familyName + (f.info.openTypeNamePreferredFamilyName or ""))
    assert "SIL Open Font License" in f.info.openTypeNameLicense
    assert f.info.postscriptFontName == f"Sisifo-{style}"
