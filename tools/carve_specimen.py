"""Stage 3 specimens: each carve variant at the OnePlus 6T's density (2.8125), 1080 px wide = 384 dp.

Usage:  python tools/carve_specimen.py      -> build/carve/named/<id>.png (owner) and build/carve/blind/<code>.png
                                               (judges), build/carve/blind_codes.json

Display text (titles, set numbers) is carved (CARV 100); the 13 px paragraph is plain (CARV 0), as the app will set
them once carve is tied to size. "plain" is Sisifo at CARV 0 throughout: a hidden control for the judges.
"""
import json
import pathlib
import random
import sys

sys.path.insert(0, str(pathlib.Path.home() / ".claude" / "tools"))
import headless_browser as hb  # noqa: E402

ROOT = pathlib.Path(__file__).resolve().parent.parent
OUT = ROOT / "build" / "carve"
VARIANTS = ["A", "B", "C", "D", "E"]
TEXT = ("Labels stay in the list for reuse. Mobilità ed equilibrio, perché è così: "
        "a short walk, then the next set.")


def page(font_path, carve, label):
    v = lambda w, c: f"font-variation-settings:'wght' {w},'CARV' {c}"
    disp = "".join(f'<div style="font-size:{s}px;line-height:{round(s * 1.15)}px;{v(400, carve)}">Bench press</div>'
                   for s in (56, 44, 34, 28, 22))
    return f"""<!doctype html><meta charset="utf-8"><style>
@font-face{{font-family:S;src:url('{font_path.as_uri()}')}}
html{{zoom:2.8125}} body{{margin:0;width:384px;box-sizing:border-box;padding:12px 16px;background:#ebebeb;color:#1c1c1c;
font-family:S}} .lab{{font:500 9px monospace;color:#575757;margin:10px 0 2px}}
.n{{font-feature-settings:'tnum' 1;white-space:nowrap}} .n span{{font-size:16px;color:#575757}}</style>
{f'<div class="lab">{label}</div>' if label else ''}
<div class="lab">titles, regular</div>{disp}
<div class="lab">titles, bold</div>
<div style="font-size:44px;line-height:50px;{v(700, carve)}">Squat</div>
<div style="font-size:28px;line-height:34px;{v(700, carve)}">Mobilità · Equilibrio</div>
<div style="font-size:34px;line-height:40px;{v(600, carve)}">SISIFO · ROCK · 1/7 3/8 0/O</div>
<div class="lab">set numbers</div>
<div class="n" style="font-size:56px;line-height:62px;{v(700, carve)}">62.5 <span>kg</span> × 5</div>
<div class="n" style="font-size:56px;line-height:62px;{v(400, carve)}">147.5 <span>kg</span> × 12</div>
<div class="lab">13 px text (plain)</div>
<div style="font-size:13px;line-height:20px;{v(400, 0)}">{TEXT}</div>
<div style="font-size:13px;line-height:20px;{v(700, 0)}">Today · 3 sets · 1:30 rest</div>"""


def render(html, out):
    p = OUT / "html" / (out.stem + ".html")
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(html, encoding="utf-8")
    hb.screenshot(str(p), str(out), 1080, 2450)


def main():
    fonts = {v: ROOT / "build" / "variants" / v / "Sisifo[CARV,wght].ttf" for v in VARIANTS}
    entries = [(v, fonts[v], 100) for v in VARIANTS] + [("plain", fonts["A"], 0)]
    rng = random.Random(20261022)
    codes = [f"K{i}" for i in range(1, len(entries) + 1)]
    rng.shuffle(codes)
    blind = {}
    (OUT / "named").mkdir(parents=True, exist_ok=True)
    (OUT / "blind").mkdir(parents=True, exist_ok=True)
    try:
        for (name, font, carve), code in zip(entries, codes):
            render(page(font, carve, f"Sisifo {name}"), OUT / "named" / f"{name}.png")
            render(page(font, carve, ""), OUT / "blind" / f"{code}.png")
            blind[code] = name
    finally:
        hb.close_all()
    (OUT / "blind_codes.json").write_text(json.dumps(dict(sorted(blind.items())), indent=1), encoding="utf-8")
    print(OUT)


if __name__ == "__main__":
    main()
