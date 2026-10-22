"""Build Sisifo's variable font from its three masters.

Usage:  python tools/build.py      -> sources/Sisifo.designspace, fonts/variable/Sisifo[wght].ttf
"""
import pathlib
import subprocess
import sys

from fontTools.designspaceLib import AxisDescriptor, DesignSpaceDocument, InstanceDescriptor, SourceDescriptor

ROOT = pathlib.Path(__file__).resolve().parent.parent
DS = ROOT / "sources" / "Sisifo.designspace"
OUT = ROOT / "fonts" / "variable" / "Sisifo[wght].ttf"
MASTERS = [("Light", 300), ("Regular", 400), ("Bold", 700)]
INSTANCES = [("Light", 300), ("Regular", 400), ("Medium", 500), ("SemiBold", 600), ("Bold", 700)]


def designspace() -> pathlib.Path:
    doc = DesignSpaceDocument()
    ax = AxisDescriptor()
    ax.tag, ax.name, ax.minimum, ax.default, ax.maximum = "wght", "Weight", 300, 400, 700
    doc.addAxis(ax)
    for style, w in MASTERS:
        s = SourceDescriptor()
        s.filename = f"Sisifo-{style}.ufo"
        s.familyName, s.styleName, s.location = "Sisifo", style, {"Weight": w}
        if style == "Regular":   # the default master carries the features, groups and info
            s.copyLib = s.copyInfo = s.copyGroups = s.copyFeatures = True
        doc.addSource(s)
    for style, w in INSTANCES:
        i = InstanceDescriptor()
        i.familyName, i.styleName, i.location = "Sisifo", style, {"Weight": w}
        i.postScriptFontName = f"Sisifo-{style}"
        doc.addInstance(i)
    doc.write(DS)
    return DS


def build() -> pathlib.Path:
    designspace()
    OUT.parent.mkdir(parents=True, exist_ok=True)
    r = subprocess.run([sys.executable, "-m", "fontmake", "-m", str(DS), "-o", "variable", "--output-path", str(OUT)],
                       capture_output=True, text=True, cwd=ROOT)
    if r.returncode:
        raise RuntimeError(f"fontmake failed ({r.returncode}):\n{r.stdout[-3000:]}\n{r.stderr[-3000:]}")
    return OUT


if __name__ == "__main__":
    print(build(), f"{OUT.stat().st_size // 1024} KB")
