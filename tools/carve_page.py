"""Owner review page for the stage 3 carve variants (all of them, owner's choice), from build/carve[N]/scores.json.

Usage:  python tools/carve_page.py [round]   -> build/carve/page/index.html + img/*.png (published as an artifact;
                                               one page and one link, each round replaces the last)

Images are the 1:1 specimens (1080 px wide), shown 384 css px wide: one image pixel per screen pixel on the 6T.
Page text uses the system font: the phone's browser blocks web fonts, and the type under review is in the images.
"""
import html
import json
import pathlib
import shutil
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
ROUND = sys.argv[1] if len(sys.argv) > 1 else "1"
CARVE = ROOT / "build" / ("carve" if ROUND == "1" else f"carve{ROUND}")
OUT = ROOT / "build" / "carve" / "page"
LOOK = {"A": "Angular: long flats, 45° facets", "B": "short flats, 45° facets", "C": "short flats, fine 25° facets",
        "D": "long flats, fine 25° facets", "E": "flats only, curves kept",
        "R": "chiselled rules: 42° cuts, counters out of phase", "RL": "chiselled rules, gentler at Light",
        "G": "Ortica Angular's own cuts on Linear's outlines", "GL": "Angular's own cuts, gentler at Light",
        "GL_r2": "round 2's GL, before the guided fits and evening",
        "GLP": "GL + proportioned capitals (ss01): Sisifo's own, carved, re-proportioned to Cinzel's widths",
        "GLZ": "GL + Cinzel's capitals (ss01), carved by the rules"}
# the panel's reasons, condensed (scores.json has them in full)
NOTE = {
    "1": {
        "B": "Read as the most convincingly hewn by two of three judges. The full stop becomes a diamond, and the "
             "largest bold rounds step slightly.",
        "C": "The calmest of the carved ones: crisp, even cuts on a still-classical serif. All three judges call the "
             "carving moderate rather than decisive.",
        "D": "Clear, even chiselling. One judge sees the bold O, 0, C and 6 turn slightly stepped.",
        "A": "Strongest flats; the facets start to look low-poly on e, s, 5 and 6 at the largest sizes.",
        "E": "Very calm, but the carving barely registers: it reads as a plain classical serif.",
    },
    "2": {
        "GL": "The strongest voice of the four: \"unmistakable\", a chiselled character on a classical skeleton. The "
              "cost: lopsided 3 and 8, a skewed S and uneven facets read to two judges as partly processed.",
        "G": "The same voice, a little rougher, since Light is carved as hard as Bold. Same notes on 3, 8, S and 6.",
        "RL": "Every glyph cut the same way, crisp and consistent, digits clear. Recognisable, but \"uniformly "
              "processed rather than hand-cut\".",
        "R": "Practically the same as RL to the judges: consistent and clean, slightly mechanical.",
        "B": "Round 1's best, as the baseline: now read as \"a small step away from a generic serif\".",
    },
    "3": {
        "GL": "After your notes. The 6 is now Angular's 6: its arm curls and hooks, and it mirrors the 9 again. The "
              "3, 8 and S have even facets (length spread 0.15 to 0.02, 0.39 to 0.08, 0.51 to 0.04). A, R, q, the "
              "f-ligatures, @ and ® now carry Angular's cuts too: 170 glyphs instead of 154.",
        "GL_r2": "Round 2's GL, judged again beside the new one. The panel scored the two the same on every axis.",
    },
    "4": {
        "GLZ": "\"The most convincing Roman inscriptional capitals of the set\": wide round O, C, D against narrow E, "
               "S, B, a classical Q tail, a dignified rhythm. It also lifts the carving score above GL's. The cut "
               "finish puts it above Cinzel itself on inscription (0.92 against 0.58). Known gap: no kerning yet for "
               "these capitals.",
        "GL": "Today's release, without ss01: the title lines in capitals use the default capitals. Read as sturdy "
              "and dignified, \"more poster than lapidary\".",
        "GLP": "Read as condensed by all three judges. Sisifo's O, C and D are already about as wide as Cinzel's "
               "(ratios 1.02 to 1.05), so the stretch mostly narrowed E, S and B and the set lost width contrast.",
    },
}
INTRO = {
    "1": ("Five ways to carve Ortica Linear, ranked by the eight axes. Titles and set numbers are carved (CARV 100). "
          "The 13 px text stays plain, as it will in the app.",
          "<b>B, C and D tie</b> (within 0.02 of each other); A and E trail.",
          "Which one should move on, or should two of them be blended (for example C's facets with B's flats)?"),
    "2": ("Round 2, after your note that even A lost personality. Two directions, each with Light carved the same as "
          "Bold or more gently: chiselled rules (R, RL) and Ortica Angular's own cuts fitted to Linear's outlines "
          "(G, GL). Round 1's B is the baseline. A ninth axis, personality, was judged blind beside Ortica Linear and "
          "Ortica Angular.",
          "<b>GL leads</b> (0.848), then G, which ties with RL and R; B trails. Angular's cuts bring the personality "
          "(GL 0.92, near Angular itself), while the rules bring cleaner, more even carving (0.75 against 0.58).",
          "Which should move on: GL as it is, GL with its lopsided digits and S evened out, or R?"),
    "3": ("Round 3: GL after the guided fits and the evened 3, 8 and S, beside round 2's GL, with the same two "
          "references.",
          "<b>The panel scores them the same</b> (0.828 each). The same round 2 image scored 0.848 last round, so "
          "differences under about 0.02 are beyond what three judges see on a whole page. The changes are measured "
          "under the new GL; look at the 6, 9, 3, 8 and S in the set numbers and titles.",
          "Does the new GL read better to you on the phone than round 2's?"),
    "4": ("Stage 4: inscriptional capitals (ss01), for titles set in capitals. Two sources, both carved: Sisifo's own "
          "capitals re-proportioned (GLP) and Cinzel's capitals (GLZ); today's release (GL) is the baseline. Ten "
          "axes, with a blind inscription axis; plain Sisifo and Cinzel are the references.",
          "<b>GLZ leads clearly</b> (0.868; GL 0.811, GLP 0.767), first on every judged axis. Look at the block "
          "\"titles in capitals (ss01)\" in each image.",
          "Should GLZ become the release, with Cinzel's capitals as ss01?"),
}
AXES = [("inscription", "Inscription"), ("personality", "Personality"), ("stone", "Stone"), ("carving", "Carving"), ("calm", "Calm"),
        ("harmony", "Harmony"), ("numbers", "Numbers"), ("technical", "Technical"), ("small", "Small text"),
        ("faithful", "Faithful (½)")]


def card(r):
    v = r["variant"]
    bars = "".join(f'<div class="ax"><span>{label}</span><i style="--v:{r[k]:.3f}"></i><b>{r[k]:.2f}</b></div>'
                   for k, label in AXES if k in r)
    tie = '<span class="tie">tie with next</span>' if r["tie_with_next"] else ""
    return f"""<section id="{v.lower()}">
  <header><h2>{v}</h2><p class="look">{LOOK[v]}</p><p class="total">{r['total']:.3f}{tie}</p></header>
  <p class="note">{html.escape(NOTE[ROUND][v])}</p>
  <div class="axes">{bars}</div>
  <img src="img/{v}.png" width="384" alt="Sisifo variant {v}: titles, set numbers and 13 px text at 6T size">
</section>"""


def reference(name, title, look, votes, keys):
    said = "; ".join(f"{k} {votes[k]}" for k in keys)
    return f"""  <section class="control" id="{name}">
    <header><h2>{title}</h2><p class="look">{look}</p><p class="total">&nbsp;</p></header>
    <p class="note">Panel votes for this reference, unnamed among the others: {said}.</p>
    <img src="img/{name}.png" width="384" alt="{html.escape(look)} at 6T size, for comparison">
  </section>"""


def main():
    s = json.loads((CARVE / "scores.json").read_text(encoding="utf-8"))
    if OUT.exists():
        shutil.rmtree(OUT)
    (OUT / "img").mkdir(parents=True)
    for p in (CARVE / "named").glob("*.png"):
        shutil.copy(p, OUT / "img" / p.name)
    controls = s.get("control_votes", {"plain": s["plain_control_votes"]})
    keys = list(controls["plain"])
    refs = reference("plain", "0", "plain Sisifo (Ortica Linear's outlines), no carve", controls["plain"], keys)
    if "angular" in controls:
        refs += "\n" + reference("angular", "Ang", "Ortica Angular Bold, its one weight on every line",
                                 controls["angular"], keys)
    if "cinzel" in controls:
        refs += "\n" + reference("cinzel", "Cin", "Cinzel, uncarved, the inscriptional reference",
                                 controls["cinzel"], keys)
    intro = "".join(f"<p>{p}</p>" for p in INTRO[ROUND])
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
</style>
<main>
  <div class="intro">
    <h1>Sisifo carve variants{'' if ROUND == '1' else ', round ' + ROUND}</h1>
    {intro}
  </div>
{cards}
{refs}
</main>"""
    (OUT / "index.html").write_text(page, encoding="utf-8")
    print(OUT / "index.html")


if __name__ == "__main__":
    main()
