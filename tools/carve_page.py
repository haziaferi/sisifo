"""Owner review page for the stage 3 carve variants (all of them, owner's choice), from build/carve/scores.json.

Usage:  python tools/carve_page.py     -> build/carve/page/index.html + img/*.png (published as an artifact)

Images are the 1:1 specimens (1080 px wide), shown 384 css px wide: one image pixel per screen pixel on the 6T.
Page text uses the system font: the phone's browser blocks web fonts, and the type under review is in the images.
"""
import html
import json
import pathlib
import shutil

ROOT = pathlib.Path(__file__).resolve().parent.parent
CARVE = ROOT / "build" / "carve"
OUT = CARVE / "page"
LOOK = {"A": "Angular: long flats, 45° facets", "B": "short flats, 45° facets", "C": "short flats, fine 25° facets",
        "D": "long flats, fine 25° facets", "E": "flats only, curves kept"}
NOTE = {  # the panel's reasons, condensed (build/carve/scores.json has them in full)
    "B": "Read as the most convincingly hewn by two of three judges. The full stop becomes a diamond, and the largest "
         "bold rounds step slightly.",
    "C": "The calmest of the carved ones: crisp, even cuts on a still-classical serif. All three judges call the "
         "carving moderate rather than decisive.",
    "D": "Clear, even chiselling. One judge sees the bold O, 0, C and 6 turn slightly stepped.",
    "A": "Strongest flats; the facets start to look low-poly on e, s, 5 and 6 at the largest sizes.",
    "E": "Very calm, but the carving barely registers: it reads as a plain classical serif.",
}
AXES = [("stone", "Stone"), ("carving", "Carving"), ("calm", "Calm"), ("harmony", "Harmony"), ("numbers", "Numbers"),
        ("technical", "Technical"), ("small", "Small text"), ("faithful", "Faithful (½)")]


def card(r):
    v = r["variant"]
    bars = "".join(f'<div class="ax"><span>{label}</span><i style="--v:{r[k]:.3f}"></i><b>{r[k]:.2f}</b></div>'
                   for k, label in AXES)
    tie = '<span class="tie">tie with next</span>' if r["tie_with_next"] else ""
    return f"""<section id="{v.lower()}">
  <header><h2>{v}</h2><p class="look">{LOOK[v]}</p><p class="total">{r['total']:.3f}{tie}</p></header>
  <p class="note">{html.escape(NOTE[v])}</p>
  <div class="axes">{bars}</div>
  <img src="img/{v}.png" width="384" alt="Sisifo variant {v}: titles, set numbers and 13 px text at 6T size">
</section>"""


def main():
    s = json.loads((CARVE / "scores.json").read_text(encoding="utf-8"))
    (OUT / "img").mkdir(parents=True, exist_ok=True)
    for p in (CARVE / "named").glob("*.png"):
        shutil.copy(p, OUT / "img" / p.name)
    ctl = s["plain_control_votes"]
    cards = "\n".join(card(r) for r in s["rows"])
    page = f"""<title>Sisifo Carve Variants</title>
<meta name="claude:viewport-fit-sides" content="cover">
<style>
/* Layout: one 384 px column, the phone's own width, so each specimen shows 1:1 on the 6T */
:root {{ --bg:#ebebeb; --fg:#1c1c1c; --mute:#5c5c5c; --rule:#d2d2d2; --bar:#1c1c1c; --track:#d9d9d9;
  --ui: system-ui, -apple-system, "Segoe UI", Roboto, sans-serif; --mono: ui-monospace, "Cascadia Mono", monospace; }}
@media (prefers-color-scheme: dark) {{ :root:not([data-theme="light"]) {{ --bg:#161616; --fg:#e8e8e8; --mute:#a0a0a0;
  --rule:#333; --bar:#e8e8e8; --track:#333; color-scheme:dark }} }}
:root[data-theme="dark"] {{ --bg:#161616; --fg:#e8e8e8; --mute:#a0a0a0; --rule:#333; --bar:#e8e8e8; --track:#333;
  color-scheme:dark }}
body {{ background:var(--bg); color:var(--fg); font:15px/1.45 var(--ui);
  padding-left:max(16px, env(safe-area-inset-left, 0px)); padding-right:max(16px, env(safe-area-inset-right, 0px)); }}
main {{ max-width:384px; margin:0 auto; padding-block:20px 48px; display:grid; gap:36px; }}
h1 {{ font-size:22px; margin:0 0 6px; text-wrap:balance; }}
.intro p {{ margin:0 0 8px; color:var(--mute); }}
.intro b {{ color:var(--fg); }}
section {{ display:grid; gap:10px; border-top:1px solid var(--rule); padding-top:16px; }}
section header {{ display:grid; grid-template-columns:auto 1fr auto; align-items:baseline; gap:10px; }}
h2 {{ margin:0; font-size:28px; }}
.look {{ margin:0; color:var(--mute); font-size:13px; }}
.total {{ margin:0; font:600 17px var(--mono); font-variant-numeric:tabular-nums; text-align:right; }}
.tie {{ display:block; font:400 11px var(--ui); color:var(--mute); letter-spacing:.02em; }}
.note {{ margin:0; }}
.axes {{ display:grid; gap:3px; font-size:12px; }}
.ax {{ display:grid; grid-template-columns:84px 1fr 34px; align-items:center; gap:8px; }}
.ax span {{ color:var(--mute); }}
.ax i {{ height:6px; background:linear-gradient(90deg, var(--bar) calc(var(--v)*100%), var(--track) 0); }}
.ax b {{ font:500 12px var(--mono); font-variant-numeric:tabular-nums; text-align:right; }}
img {{ display:block; width:100%; max-width:384px; height:auto; }}
.control img {{ opacity:.95; }}
</style>
<main>
  <div class="intro">
    <h1>Sisifo carve variants</h1>
    <p>Five ways to carve Ortica Linear, ranked by the eight axes. Titles and set numbers are carved (CARV 100). The 13 px text stays plain, as it will in the app.</p>
    <p><b>B, C and D tie</b> (within 0.02 of each other); A and E trail. On this phone each image shows at its real size: hold it at arm's length for the set numbers.</p>
    <p>Which one should move on, or should two of them be blended (for example C's facets with B's flats)?</p>
  </div>
{cards}
  <section class="control" id="plain">
    <header><h2>0</h2><p class="look">plain Sisifo, no carve: the judges' hidden control</p><p class="total">&nbsp;</p></header>
    <p class="note">Panel votes for the control: stone {ctl['stone']}, carving {ctl['carving']}, calm {ctl['calm']}. The judges told carved from plain every time.</p>
    <img src="img/plain.png" width="384" alt="Sisifo uncarved at 6T size, for comparison">
  </section>
</main>"""
    (OUT / "index.html").write_text(page, encoding="utf-8")
    print(OUT / "index.html")


if __name__ == "__main__":
    main()
