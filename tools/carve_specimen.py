"""Stage 3 specimens: each carve variant at the OnePlus 6T's density (2.8125), 1080 px wide = 384 dp.

Usage:  python tools/carve_specimen.py [round]   -> build/carve[2]/named/<id>.png (owner), blind/<code>.png
                                                  (judges), blind_codes.json; round 1 by default

Display text (titles, set numbers) is carved (CARV 100); the 13 px paragraph is plain (CARV 0), as the app will set
them once carve is tied to size. "plain" is Sisifo at CARV 0 throughout: a hidden control for the judges.
"""
import json
import pathlib
import random
import shutil
import sys

sys.path.insert(0, str(pathlib.Path.home() / ".claude" / "tools"))
import headless_browser as hb  # noqa: E402

ROOT = pathlib.Path(__file__).resolve().parent.parent
ROUND = sys.argv[1] if len(sys.argv) > 1 else "1"
OUT = ROOT / "build" / ("carve" if ROUND == "1" else f"carve{ROUND}")
# round 2 (personality) adds Ortica Angular Bold as a second reference; it has one weight, used for every line
VARIANTS = {"1": ["A", "B", "C", "D", "E"], "2": ["B", "R", "RL", "G", "GL"], "3": ["GL"],
            "4": ["GLP", "GLZ", "GL"]}[ROUND]
# round 3 re-scores GL after the guided fits and the evened 3, 8, S, beside round 2's GL (its specimen image is kept;
# the font itself was rebuilt)
PRIOR = {"3": {"GL_r2": ROOT / "build" / "carve2" / "named" / "GL.png"}}.get(ROUND, {})
ANGULAR = ROOT.parent / "ortica-src" / "fonts" / "OrticaAngular-Bold.otf"
CINZEL = ROOT.parent / "fonts" / "cinzel" / "Cinzel-wght.ttf"
TEXT = ("Labels stay in the list for reuse. Mobilità ed equilibrio, perché è così: "
        "a short walk, then the next set.")


def CAPS_BLOCK(v, carve):
    """Round 4 (stage 4): titles in capitals with the inscriptional set on (a no-op for faces without ss01)."""
    if ROUND != "4":
        return ""
    ss = "font-feature-settings:'ss01' 1;"
    return (f'<div class="lab">titles in capitals (ss01)</div>'
            f'<div style="font-size:56px;line-height:62px;{ss}{v(600, carve)}">SISIFO</div>'
            f'<div style="font-size:40px;line-height:46px;{ss}{v(400, carve)}">BENCH PRESS</div>'
            f'<div style="font-size:28px;line-height:34px;{ss}{v(700, carve)}">MOBILITÀ · EQUILIBRIO</div>')


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
<div style="font-size:34px;line-height:40px;{v(600, carve)}">SISIFO · ROCK · 1/7 3/8 0/O</div>{CAPS_BLOCK(v, carve)}
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
    hb.screenshot(str(p), str(out), 1080, 2450 if ROUND != "4" else 2900)   # round 4 adds a block of capitals


def main():
    fonts = {v: ROOT / "build" / "variants" / v / "Sisifo[CARV,wght].ttf" for v in VARIANTS}
    entries = [(v, fonts[v], 100) for v in VARIANTS] + [("plain", fonts[VARIANTS[0]], 0)]
    if ROUND in ("2", "3"):
        entries.append(("angular", ANGULAR, 100))
    if ROUND == "4":   # the reference for the inscriptional axis
        entries.append(("cinzel", CINZEL, 100))
    rng = random.Random(20261022)
    codes = [f"K{i}" for i in range(1, len(entries) + len(PRIOR) + 1)]
    rng.shuffle(codes)
    blind = {}
    (OUT / "named").mkdir(parents=True, exist_ok=True)
    (OUT / "blind").mkdir(parents=True, exist_ok=True)
    try:
        for (name, font, carve), code in zip(entries, codes):
            render(page(font, carve, f"Sisifo {name}"), OUT / "named" / f"{name}.png")
            render(page(font, carve, ""), OUT / "blind" / f"{code}.png")
            blind[code] = name
        for (name, png), code in zip(PRIOR.items(), codes[len(entries):]):
            shutil.copy(png, OUT / "named" / f"{name}.png")
            # the judges get that round's unlabelled copy: the named image says "Sisifo GL" at the top
            prior_codes = json.loads((png.parent.parent / "blind_codes.json").read_text(encoding="utf-8"))
            prior_code = next(c for c, n in prior_codes.items() if n == png.stem)
            shutil.copy(png.parent.parent / "blind" / f"{prior_code}.png", OUT / "blind" / f"{code}.png")
            blind[code] = name
    finally:
        hb.close_all()
    (OUT / "blind_codes.json").write_text(json.dumps(dict(sorted(blind.items())), indent=1), encoding="utf-8")
    print(OUT)


if __name__ == "__main__":
    main()
