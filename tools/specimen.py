"""Stage 1 specimen: Sisifo at 300-700 beside Ortica Linear at 300/400/700, at the OnePlus 6T's density (2.8125).

Usage:  python tools/specimen.py      -> build/specimen.png (1080 px wide = 384 dp on the 6T)
"""
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path.home() / ".claude" / "tools"))
import headless_browser as hb  # noqa: E402

ROOT = pathlib.Path(__file__).resolve().parent.parent
VF = ROOT / "fonts" / "variable" / "Sisifo[wght].ttf"
ORT = ROOT / "vendor" / "ortica" / "fonts"
ORIG = {300: "Light", 400: "Regular", 700: "Bold"}
TEXT = "Labels stay in the list for reuse. Mobilità ed equilibrio, perché è così."


def row(fam, w, label):
    return (f'<div class="row"><div class="lab">{label}</div>'
            f'<div style="font-family:{fam};font-weight:{w}">'
            f'<div class="d">Bench press</div><div class="n">62.5 <span>kg</span> × 5</div>'
            f'<div class="p">{TEXT}</div></div></div>')


SETS = ["62.5", "67.5", "100.0", "11.25", "48.0"]


def figures_block():
    """Right-aligned set weights, proportional against tnum: tabular columns line up, proportional ones wander."""
    col = lambda w, tnum: (f'<div class="col" style="font-weight:{w};font-feature-settings:{chr(39)}tnum{chr(39)} {tnum}">'
                           f'<div class="lab">{w} {"tnum" if tnum else "default"}</div>'
                           + "".join(f"<div>{s}</div>" for s in SETS) + "</div>")
    return '<div class="row figs">' + "".join(col(w, t) for w in (400, 700) for t in (0, 1)) + "</div>"


def main():
    faces = f"@font-face{{font-family:S;src:url('{VF.as_uri()}');font-weight:300 700}}" + "".join(
        f"@font-face{{font-family:O{w};src:url('{(ORT / f'OrticaLinear-{s}.otf').as_uri()}')}}" for w, s in ORIG.items())
    rows = ""
    for w in (300, 400, 500, 600, 700):
        rows += row("S", w, f"Sisifo {w}")
        if w in ORIG:
            rows += row(f"O{w}", 400, f"Ortica Linear {ORIG[w]} (original)")
    html = f"""<!doctype html><meta charset="utf-8"><style>{faces}
html{{zoom:2.8125}} body{{margin:0;width:384px;background:#ebebeb;color:#1c1c1c;padding:12px 16px;box-sizing:border-box}}
.row{{padding:8px 0;border-bottom:1px solid rgba(0,0,0,.1)}} .lab{{font:500 9px monospace;color:#575757;margin-bottom:2px}}
.d{{font-size:28px;line-height:32px}} .n{{font-size:34px;line-height:40px;font-variant-numeric:lining-nums}}
.n span{{font-size:16px;color:#575757}} .p{{font-size:13px;line-height:20px}}
.figs{{display:flex;gap:10px;font-family:S;font-size:26px;line-height:32px}} .col{{flex:1;text-align:right}}
.col .lab{{text-align:right}}</style>{figures_block()}{rows}"""
    page = ROOT / "build" / "specimen.html"
    page.parent.mkdir(exist_ok=True)
    page.write_text(html, encoding="utf-8")
    try:
        hb.screenshot(str(page), str(ROOT / "build" / "specimen.png"), 1080, 3400)
    finally:
        hb.close_all()
    print(ROOT / "build" / "specimen.png")


if __name__ == "__main__":
    main()
