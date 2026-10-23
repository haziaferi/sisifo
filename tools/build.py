"""Build Sisifo's variable fonts.

Usage:  python tools/build.py          -> sources/Sisifo.designspace, fonts/variable/Sisifo[wght].ttf
        python tools/build.py A [E ..] -> build/variants/<id>/Sisifo[CARV,wght].ttf, two axes, from tools/carve.py masters
        python tools/build.py release  -> fonts/variable/Sisifo[CARV,wght].ttf, the chosen carve (CHOSEN)
"""
import pathlib
import subprocess
import sys

import ufoLib2
from fontTools.designspaceLib import AxisDescriptor, DesignSpaceDocument, InstanceDescriptor, SourceDescriptor

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools"))
import carve  # noqa: E402

DS = ROOT / "sources" / "Sisifo.designspace"
OUT = ROOT / "fonts" / "variable" / "Sisifo[wght].ttf"
MASTERS = [("Light", 300), ("Regular", 400), ("Bold", 700)]
INSTANCES = [("Light", 300), ("Regular", 400), ("Medium", 500), ("SemiBold", 600), ("Bold", 700)]


def _axis(doc, tag, name, lo, default, hi):
    ax = AxisDescriptor()
    ax.tag, ax.name, ax.minimum, ax.default, ax.maximum = tag, name, lo, default, hi
    doc.addAxis(ax)


def _finish(doc, regular_path, carve_axis, italic=False):
    # helper glyphs Ortica does not export (zero.dnom among them); fontmake reads this list from the designspace lib
    regular = ufoLib2.Font.open(regular_path)
    doc.lib["public.skipExportGlyphs"] = list(regular.lib.get("public.skipExportGlyphs", []))
    for style, w in INSTANCES:
        i = InstanceDescriptor()
        name = (f"{style} Italic" if style != "Regular" else "Italic") if italic else style
        i.familyName, i.styleName = "Sisifo", name
        i.location = {"Weight": w, "Carve": 0} if carve_axis else {"Weight": w}   # named instances are plain text
        i.postScriptFontName = "Sisifo-" + name.replace(" ", "")
        doc.addInstance(i)


def designspace() -> pathlib.Path:
    doc = DesignSpaceDocument()
    _axis(doc, "wght", "Weight", 300, 400, 700)
    for style, w in MASTERS:
        s = SourceDescriptor()
        s.filename = f"Sisifo-{style}.ufo"
        s.familyName, s.styleName, s.location = "Sisifo", style, {"Weight": w}
        if style == "Regular":   # the default master carries the features, groups and info
            s.copyLib = s.copyInfo = s.copyGroups = s.copyFeatures = True
        doc.addSource(s)
    _finish(doc, ROOT / "sources" / "Sisifo-Regular.ufo", carve_axis=False)
    doc.write(DS)
    return DS


def carved_designspace(variant) -> pathlib.Path:
    """wght 300/400/700 x CARV 0/100 from the masters tools/carve.py generates for the variant."""
    d = ROOT / "build" / "masters" / variant
    carve.make_masters(variant, d)
    doc = DesignSpaceDocument()
    _axis(doc, "wght", "Weight", 300, 400, 700)
    _axis(doc, "CARV", "Carve", 0, 0, 100)
    for style, w in MASTERS:
        for c in (0, 100):
            s = SourceDescriptor()
            s.path = str(d / f"Sisifo-{style}-C{c}.ufo")
            s.familyName, s.styleName, s.location = "Sisifo", style, {"Weight": w, "Carve": c}
            if style == "Regular" and c == 0:
                s.copyLib = s.copyInfo = s.copyGroups = s.copyFeatures = True
            doc.addSource(s)
    _finish(doc, d / "Sisifo-Regular-C0.ufo", carve_axis=True, italic=bool(carve.VARIANTS[variant].get("slant")))
    path = d / "Sisifo-carved.designspace"
    doc.write(path)
    return path


def _fontmake(ds, out, conversion_error=None) -> pathlib.Path:
    out.parent.mkdir(parents=True, exist_ok=True)
    cmd = [sys.executable, "-m", "fontmake", "-m", str(ds), "-o", "variable", "--output-path", str(out)]
    if conversion_error:
        cmd += ["--conversion-error", str(conversion_error)]
    # reproducible: the font's build time is the last commit's, so one commit always gives byte-identical fonts
    import os
    env = dict(os.environ)
    stamp = subprocess.run(["git", "log", "-1", "--format=%ct"], capture_output=True, text=True, cwd=ROOT)
    if stamp.returncode == 0 and stamp.stdout.strip():
        env.setdefault("SOURCE_DATE_EPOCH", stamp.stdout.strip())
    r = subprocess.run(cmd, capture_output=True, text=True, cwd=ROOT, env=env)
    if r.returncode:
        raise RuntimeError(f"fontmake failed ({r.returncode}):\n{r.stdout[-3000:]}\n{r.stderr[-3000:]}")
    return out


def build() -> pathlib.Path:
    return _fontmake(designspace(), OUT)


CHOSEN = "GLZ"  # owner, 2026-10-23: "Release GLZ" (GL carve + Cinzel capitals as ss01); GL before that
RELEASE = ROOT / "fonts" / "variable" / "Sisifo[CARV,wght].ttf"


def release() -> pathlib.Path:
    """The chosen carve as the font the app takes: fonts/variable/Sisifo[CARV,wght].ttf."""
    import shutil
    RELEASE.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy(build_carved(CHOSEN), RELEASE)
    return RELEASE


def build_slnt(angle) -> pathlib.Path:
    """Stage 5, delivery B: one file with wght, CARV and slnt; slnt 0 is the release, -angle its oblique."""
    up, it = ROOT / "build" / "masters" / CHOSEN, ROOT / "build" / "masters" / f"{CHOSEN}_I{angle}"
    carve.make_masters(CHOSEN, up)
    carve.make_masters(f"{CHOSEN}_I{angle}", it)
    doc = DesignSpaceDocument()
    _axis(doc, "wght", "Weight", 300, 400, 700)
    _axis(doc, "CARV", "Carve", 0, 0, 100)
    _axis(doc, "slnt", "Slant", -angle, 0, 0)
    for d, sl in ((up, 0), (it, -angle)):
        for style, w in MASTERS:
            for c in (0, 100):
                s = SourceDescriptor()
                s.path = str(d / f"Sisifo-{style}-C{c}.ufo")
                s.familyName, s.styleName = "Sisifo", style
                s.location = {"Weight": w, "Carve": c, "Slant": sl}
                if style == "Regular" and c == 0 and sl == 0:
                    s.copyLib = s.copyInfo = s.copyGroups = s.copyFeatures = True
                doc.addSource(s)
    _finish(doc, up / "Sisifo-Regular-C0.ufo", carve_axis=True)
    for i in doc.instances:
        i.location["Slant"] = 0
    path = ROOT / "build" / "masters" / f"{CHOSEN}-slnt{angle}.designspace"
    doc.write(path)
    return _fontmake(path, ROOT / "build" / "variants" / f"{CHOSEN}_S{angle}" / "Sisifo[CARV,slnt,wght].ttf",
                     conversion_error=0.00025)


def build_carved(variant="A") -> pathlib.Path:
    # cubic-to-quadratic error 0.25 unit, not fontmake's 1: the quadratics fall consistently inside the curve, and on a
    # thin accent (breve.case, Light, variant E) that cost 1.06 % of its area at CARV 0 (0.5 unit: still 1.06 %;
    # 0.25: 0.74 %; 0.1: 0.07 % but 12 KB more), past the gate's 1 %
    name = "Sisifo-Italic[CARV,wght].ttf" if carve.VARIANTS[variant].get("slant") else "Sisifo[CARV,wght].ttf"
    return _fontmake(carved_designspace(variant), ROOT / "build" / "variants" / variant / name,
                     conversion_error=0.00025)


if __name__ == "__main__":
    args = sys.argv[1:]
    if args == ["release"]:
        args, done = [], [release()]
    else:
        done = []
    for p in done + [build_carved(v) for v in args] or [build()]:
        print(p, f"{p.stat().st_size // 1024} KB")
