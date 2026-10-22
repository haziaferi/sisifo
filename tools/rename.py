"""Rename a copied Ortica Linear UFO to Sisifo (OFL: a modified font takes its own name, credits stay).

Usage:  python tools/rename.py        (renames sources/Sisifo-{Light,Regular,Bold}.ufo in place)
"""
import pathlib

import ufoLib2

ROOT = pathlib.Path(__file__).resolve().parent.parent
WEIGHTS = {"Light": 300, "Regular": 400, "Bold": 700}
COPYRIGHT = ("Copyright 2021 Benedetta Bovani & Collletttivo (Ortica, https://github.com/collletttivo/ortica). "
             "Sisifo modifications copyright 2026 haziaferi.")
LICENSE = ("This Font Software is licensed under the SIL Open Font License, Version 1.1. "
           "This license is available with a FAQ at: https://openfontlicense.org")


def rename(ufo_path: pathlib.Path, style: str) -> None:
    f = ufoLib2.Font.open(ufo_path)
    i = f.info
    i.familyName = "Sisifo"
    i.styleName = style
    i.styleMapFamilyName = "Sisifo" if style in ("Regular", "Bold") else "Sisifo Light"
    i.styleMapStyleName = {"Regular": "regular", "Bold": "bold"}.get(style, "regular")
    i.openTypeNamePreferredFamilyName = "Sisifo"
    i.openTypeNamePreferredSubfamilyName = style
    i.postscriptFontName = f"Sisifo-{style}"
    i.postscriptFullName = f"Sisifo {style}"
    i.openTypeOS2WeightClass = WEIGHTS[style]
    i.copyright = COPYRIGHT
    i.openTypeNameLicense = LICENSE
    i.openTypeNameLicenseURL = "https://openfontlicense.org"
    i.openTypeNameDesigner = "Benedetta Bovani (Ortica); Sisifo derivation: haziaferi"
    i.versionMajor, i.versionMinor = 0, 1
    i.openTypeOS2VendorID = "NONE"
    i.openTypeNameUniqueID = None
    i.trademark = None
    f.save(ufo_path, overwrite=True)


if __name__ == "__main__":
    for style in WEIGHTS:
        rename(ROOT / "sources" / f"Sisifo-{style}.ufo", style)
        print("renamed", style)
