import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools"))
SOURCES = ROOT / "sources"
ORTICA = ROOT / "vendor" / "ortica"
ORIGINAL = {s: ORTICA / "fonts" / f"OrticaLinear-{s}.otf" for s in ("Light", "Regular", "Bold")}
ORIGINAL_UFO = {s: ORTICA / "source" / f"Ortica Linear-{s}.ufo" for s in ("Light", "Regular", "Bold")}
