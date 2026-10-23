"""Stage 6: full scoring for the owner's sign-off, and the size->carve mapping.

Usage:  python tools/signoff.py specimens   -> build/signoff/{named,blind}/*.png + blind_codes.json
        python tools/signoff.py measure     -> build/signoff/measured.json
        python tools/signoff.py combine     -> build/signoff/scores.json + tables (needs judge_*.json)
        python tools/signoff.py page        -> build/carve/page/index.html, the owner's review page (same link)

Part A, the release against the font search's finalists (owner, 2026-10-23: "Font-search finalists"): the five faces
the owner looked at as small text (Grenze, Ortica Linear, Avara, Cinzel, Bagnard), IBM Plex Sans (SPEC 0.36, the face
Sisifo would replace, with IBM's own italic) and Libertinus Sans (second in the search). One page per face: titles,
capitals (ss01 where a face has it), set numbers, 13 px text, the obliques. Ten axes, equal weight ("Ten, adapted"):
harmony, numbers, technical (measured, the font search's own measure); calm (half judged, half measured); stone,
carving, personality, inscription, oblique, small text (judged). Faithful-to-Ortica is left out: it only measures
Sisifo against its base. Faces without an italic file get the browser's faked oblique, as the app would show them.

Part B, two size->carve mappings (owner: "Score both") in the stage 1a screens, set in the release:
  stepped  carve 0 up to 16 dp (labels, eyebrows, body), 100 above (titles, headings, set numbers)
  ramp     0 up to 15 dp, rising evenly to 100 at 28 dp
Axes (owner): numbers at arm's length (measured), stone at display (judged), small text unharmed (measured),
hierarchy and calm (half judged, half measured). Equal weight.

The scoring reads fonts and mockups outside this repository (the SisyphusFit research folder: the font search's
fonts and the stage 1a screens); the build does not need them.
"""
import json
import pathlib
import random
import re
import statistics
import sys

from fontTools.ttLib import TTFont
from fontTools.varLib.instancer import instantiateVariableFont
from PIL import Image, ImageFilter

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools"))
sys.path.insert(0, str(pathlib.Path.home() / ".claude" / "tools"))
import search_measure as measure  # noqa: E402
from score_carve import _mask, _iou  # noqa: E402

OUT = ROOT / "build" / "signoff"
RES = ROOT / "fonts" / "variable"
UPRIGHT, ITALIC = RES / "Sisifo[CARV,wght].ttf", RES / "Sisifo-Italic[CARV,wght].ttf"
SEARCH = ROOT.parent / "fonts"                      # the font search's downloads
RESEARCH = ROOT.parent.parent                         # SisyphusFit/research
PLEX = RESEARCH / "screens-2026-10-20" / "polish" / "fonts" / "IBMPlexSans[wdth,wght].ttf"
SCREENS = RESEARCH / "screens-2026-10-20" / "polish" / "final" / "out"

# face: (files as (path, weight range, style)), licence folder; Sisifo alone has the CARV axis
FACES = {
    "sisifo": ([(UPRIGHT, "300 700", "normal"), (ITALIC, "300 700", "italic")], ROOT),
    "grenze": ([(SEARCH / "grenze" / "Grenze-wght.ttf", "100 900", "normal")], None),
    "ortica": ([(SEARCH / "ortica" / f"OrticaLinear-{s}.otf", w, "normal")
                for s, w in (("Light", "300"), ("Regular", "400"), ("Bold", "700"))], None),
    "avara": ([(SEARCH / "avara" / "Avara-Bold.ttf", "700", "normal"), (SEARCH / "avara" / "Avara-Black.ttf", "900", "normal"),
               (SEARCH / "avara" / "Avara-BoldItalic.ttf", "700", "italic")], None),
    "cinzel": ([(SEARCH / "cinzel" / "Cinzel-wght.ttf", "400 900", "normal")], None),
    "bagnard": ([(SEARCH / "bagnard" / "Bagnard.otf", "400", "normal")], None),
    "ibm-plex-sans": ([(PLEX, "100 700", "normal"),
                       (SEARCH / "ibm-plex-sans-italic" / "IBMPlexSansVar-Italic.ttf", "100 700", "italic")], None),
    "libertinus-sans": ([(SEARCH / "libertinus-sans" / f"LibertinusSans-{s}.otf", w, "normal")
                         for s, w in (("Regular", "400"), ("Bold", "700"))], None),
}
TEXT = ("Labels stay in the list for reuse. Mobilità ed equilibrio, perché è così: "
        "a short walk, then the next set.")
JUDGED_A = ["stone", "carving", "calm", "personality", "inscription", "oblique", "small"]
AXES_A = ["harmony", "numbers", "technical", "calm", "stone", "carving", "personality", "inscription", "oblique", "small"]

# Part B. The mockups' type roles (polish round, pbuild.DENSITY): size in dp and weight (titles take --w-med, 500)
ROLES = {"bal": {"xs": 13, "eb": 13, "b": 16, "t": 19, "h": 23, "ex": 28, "num": 40, "pad": 48},
         "cmp": {"xs": 12, "eb": 12, "b": 14, "t": 17, "h": 20, "ex": 24, "num": 34, "pad": 40}}
WEIGHT = {"xs": 400, "eb": 400, "b": 400, "t": 500, "h": 500, "ex": 500, "num": 500, "pad": 500}
NUMBER_ROLES = ["t", "h", "num", "pad"]       # where set numbers, amounts and timers sit
MAPPINGS = {"stepped": lambda s: 0 if s <= 16 else 100,
            "ramp": lambda s: round(max(0, min(1, (s - 15) / (28 - 15))) * 100)}
JS_MAPPINGS = {"stepped": "s<=16?0:100", "ramp": "Math.round(Math.max(0,Math.min(1,(s-15)/13))*100)"}
SCREENS_B = [("bal", "exercise"), ("bal", "exercise_rest"), ("bal", "history"), ("bal", "this_week"),
             ("cmp", "exercise")]
JUDGED_B = ["stone", "hierarchy"]
AXES_B = ["numbers", "stone", "small", "hierarchy"]
DENSITY = 2.8125     # the OnePlus 6T: 1080 px over 384 dp


# ------------------------------------------------------------------ part A specimens
def faces_css(face, family="F"):
    files, _ = FACES[face]
    return "".join(f"@font-face{{font-family:{family};src:url('{p.as_uri()}');font-weight:{w};font-style:{st};"
                   f"font-display:block}}" for p, w, st in files)


def face_page(face, label):
    carved = face == "sisifo"
    c = lambda n: f"font-variation-settings:'CARV' {n};" if carved else ""
    t = lambda size, w, n=100, extra="": (f'style="font-size:{size}px;line-height:{round(size * 1.15)}px;'
                                          f'font-weight:{w};{c(n)}{extra}"')
    ss, tn, it = "font-feature-settings:'ss01' 1;", "font-feature-settings:'tnum' 1;", "font-style:italic;"
    pre = "".join(f"<link rel=preload as=font crossorigin href='{p.as_uri()}'>" for p, _, _ in FACES[face][0])
    disp = "".join(f"<div {t(s, 400)}>Bench press</div>" for s in (56, 44, 34, 28, 22))
    return f"""<!doctype html><meta charset="utf-8">{pre}<style>{faces_css(face)}
html{{zoom:{DENSITY}}} body{{margin:0;width:384px;box-sizing:border-box;padding:12px 16px;background:#ebebeb;
color:#1c1c1c;font-family:F}} .lab{{font:500 9px monospace;color:#575757;margin:12px 0 3px}} i{{font-style:italic}}
.s{{font-size:13px;line-height:20px;font-weight:400;{c(0)}}}</style>
{f'<div class="lab">{label}</div>' if label else ''}
<div class="lab">titles, regular</div>{disp}
<div class="lab">titles, bold</div>
<div {t(44, 700)}>Squat</div><div {t(28, 700)}>Mobilità · Equilibrio</div>
<div {t(34, 600)}>SISIFO · ROCK · 1/7 3/8 0/O</div>
<div class="lab">titles in capitals</div>
<div {t(56, 600, extra=ss)}>SISIFO</div><div {t(40, 400, extra=ss)}>BENCH PRESS</div>
<div {t(28, 700, extra=ss)}>MOBILITÀ · EQUILIBRIO</div>
<div class="lab">set numbers</div>
<div {t(56, 700, extra=tn + 'white-space:nowrap')}>62.5 <span style="font-size:16px">kg</span> × 5</div>
<div {t(56, 400, extra=tn + 'white-space:nowrap')}>147.5 <span style="font-size:16px">kg</span> × 12</div>
<div class="lab">13 px text</div>
<div class="s">{TEXT}</div><div class="s" style="font-weight:700">Today · 3 sets · 1:30 rest</div>
<div class="lab">emphasis inside 13 px text</div>
<div class="s">Rest <i>ninety seconds</i> between sets, then <i>breathe</i>. Labels stay in the list for
<i>reuse</i>. Mobilità ed <i>equilibrio</i>, perché è <i>così</i>.</div>
<div class="lab">notes and hints (whole lines)</div>
<div class="s" style="{it}">Tip: a short walk between sets keeps the legs loose.</div>
<div class="s" style="{it}">Habit, not motivation: the next set starts when you are ready.</div>
<div class="s" style="{it}font-weight:300">Light: two sets today · 1:30 rest · perché è così</div>
<div class="lab">display accents</div>
<div {t(44, 600, extra=it)}>Bench press</div><div {t(30, 400, extra=it)}>Mobilità · Equilibrio</div>
<div {t(52, 700, extra=it + tn + 'white-space:nowrap')}>62.5 <span style="font-size:18px">kg</span> × 5</div>
<div {t(30, 500, extra=it + ss)}>SISIFO · ROCK</div>
<div class="lab">upright, for comparison</div><div {t(30, 600)}>Bench press 62.5</div>"""


# ------------------------------------------------------------------ part B specimens
def screen_page(density, name, mapping):
    """A stage 1a screen (final polish round, round floating control) set in the release, carve by font size."""
    src = SCREENS / f"plex-r-{density}" / f"{name}.html"
    html = src.read_text(encoding="utf-8")
    html = re.sub(r"@font-face\{font-family:'SF Plex'[^}]*\}", "", html)
    html = re.sub(r"<link rel='preload'[^>]*>", "", html)
    html = html.replace("--font:'SF Plex'", "--font:'SF Sisifo'")
    face = (f"@font-face{{font-family:'SF Sisifo';src:url('{UPRIGHT.as_uri()}');font-weight:300 700;"
            f"font-style:normal;font-display:block}}")
    html = html.replace("<style>", f"<link rel=preload as=font crossorigin href='{UPRIGHT.as_uri()}'><style>{face}", 1)
    # every element with its own text takes the carve of its computed size (dp: the page is 360 dp wide), then the
    # page is zoomed to the 6T's 3x
    js = ("<script>(()=>{const m=s=>" + JS_MAPPINGS[mapping] + ";for(const e of document.querySelectorAll('body *')){"
          "if(![...e.childNodes].some(n=>n.nodeType===3&&n.textContent.trim()))continue;"
          "e.style.fontVariationSettings=`'CARV' ${m(parseFloat(getComputedStyle(e).fontSize))}`}"
          "document.documentElement.style.zoom=3})()</script>")
    return html.replace("</body>", js + "</body>")


def render(html, out, height):
    import headless_browser as hb
    p = OUT / "html" / (out.stem + ".html")
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(html, encoding="utf-8")
    hb.screenshot(str(p), str(out), 1080, height)


def specimens():
    import headless_browser as hb
    for d in ("named", "blind"):
        (OUT / d).mkdir(parents=True, exist_ok=True)
    codes = {}
    rng = random.Random(20261023 + 6)
    a = [f"K{i}" for i in range(1, len(FACES) + 1)]
    rng.shuffle(a)
    b = [f"M{i}" for i in range(1, 2 * len(SCREENS_B) + 1)]
    rng.shuffle(b)
    try:
        for face, code in zip(FACES, a):
            render(face_page(face, face), OUT / "named" / f"{face}.png", 3860)
            render(face_page(face, ""), OUT / "blind" / f"{code}.png", 3860)
            codes[code] = face
        pairs = [(d, n, m) for d, n in SCREENS_B for m in MAPPINGS]
        for (d, n, m), code in zip(pairs, b):
            render(screen_page(d, n, m), OUT / "named" / f"{m}-{d}-{n}.png", 2340)
            (OUT / "blind" / f"{code}.png").write_bytes((OUT / "named" / f"{m}-{d}-{n}.png").read_bytes())
            codes[code] = f"{m}|{d}|{n}"
    finally:
        hb.close_all()
    (OUT / "blind_codes.json").write_text(json.dumps(dict(sorted(codes.items())), indent=1), encoding="utf-8")
    print(OUT)


# ------------------------------------------------------------------ measures
def _static(weight, carve):
    p = OUT / "static" / f"Sisifo-w{weight}-C{carve}.ttf"
    if not p.exists():
        p.parent.mkdir(parents=True, exist_ok=True)
        instantiateVariableFont(TTFont(UPRIGHT), {"wght": weight, "CARV": carve}, static=True).save(p)
    return p


def measure_faces():
    """The font search's measure on every face; Sisifo at Regular, CARV 100 (as in stages 3-5), technical on both
    release files. The other faces must give the search's own numbers again (checked, printed)."""
    old = json.loads((ROOT.parent / "measured.json").read_text(encoding="utf-8")) \
        if (ROOT.parent / "measured.json").exists() else {}
    out = {}
    for face, (files, lic) in FACES.items():
        paths = [str(p) for p, _, _ in files]
        c = {"family": face, "slug": face, "files": paths, "licence_dir": str(lic or files[0][0].parent)}
        if face == "sisifo":
            m = measure.measure({**c, "files": [str(_static(400, 100))]})
            m.update({k: v for k, v in measure.measure(c).items()
                      if k in ("technical", "licence", "accents", "n_weights", "weights", "size_kb", "size")})
        else:
            m = measure.measure(c)
        m["file"] = pathlib.Path(m["file"]).name     # results are published: no local paths
        out[face] = m
        o = old.get(face)
        same = o and all(o.get(k) == m.get(k) for k in ("harmony", "numbers", "calm_measured"))
        print(f"{face:16} harmony {m['harmony']:.3f} numbers {m['numbers']:.3f} technical {m['technical']:.3f} "
              f"calm {m['calm_measured']:.3f} {m['size_kb']} KB"
              + ("" if o is None else "  (search: same)" if same else
                 f"  (search: {o.get('harmony')} {o.get('numbers')} {o.get('calm_measured')})"))
    return out


SMALL = "Labels stay in the list for reuse. Mobilità ed equilibrio, perché è così."
PAIRS = [("1", "7"), ("3", "8"), ("0", "O"), ("5", "6"), ("6", "8")]


def _far(im):
    """A glyph as seen at arm's length: about twice the reading distance, so half the size, slightly soft."""
    return im.resize((max(1, im.width // 2), max(1, im.height // 2)), Image.LANCZOS).filter(ImageFilter.GaussianBlur(0.6))


def _distinct(font, px):
    ds = []
    for a, b in PAIRS:
        ia, _ = _mask(font, a, px, (px * 2, px * 2))
        ib, _ = _mask(font, b, px, (px * 2, px * 2))
        ds.append(1 - _iou(_far(ia), _far(ib)))
    return measure.clamp(statistics.mean(ds) / 0.5)


def _ink(font, px):
    im, _ = _mask(font, "Bench press 62.5", px)
    return sum(1 for v in im.get_flattened_data() if v > 96)


def measure_mappings():
    out = {}
    for mname, m in MAPPINGS.items():
        r = {}
        for d, roles in ROLES.items():
            carve = {k: m(s) for k, s in roles.items()}
            small = [_iou(_mask(_static(WEIGHT[k], carve[k]), SMALL, round(s * 3))[0],
                          _mask(_static(WEIGHT[k], 0), SMALL, round(s * 3))[0]) for k, s in roles.items() if s <= 16]
            nums = [_distinct(_static(WEIGHT[k], carve[k]), round(roles[k] * 3)) for k in NUMBER_ROLES]
            # hierarchy, measured: each step up the role ladder (distinct sizes) is at least 15 % more ink
            ladder = sorted({s: k for k, s in roles.items()}.items())
            inks = [_ink(_static(WEIGHT[k], carve[k]), round(s * 3)) for s, k in ladder]
            steps = [b >= a * 1.15 for a, b in zip(inks, inks[1:])]
            r[d] = {"carve": carve, "small": round(statistics.mean(small), 4), "numbers": round(statistics.mean(nums), 4),
                    "numbers_by_role": dict(zip(NUMBER_ROLES, (round(x, 3) for x in nums))),
                    "hierarchy_measured": round(sum(steps) / len(steps), 3)}
        r["small"] = round(statistics.mean(r[d]["small"] for d in ROLES), 4)
        r["numbers"] = round(statistics.mean(r[d]["numbers"] for d in ROLES), 4)
        r["hierarchy_measured"] = round(statistics.mean(r[d]["hierarchy_measured"] for d in ROLES), 3)
        out[mname] = r
        print(mname, {k: r[k] for k in ("small", "numbers", "hierarchy_measured")},
              {d: r[d]["carve"] for d in ROLES})
    return out


def measure_all():
    OUT.mkdir(parents=True, exist_ok=True)
    data = {"faces": measure_faces(), "mappings": measure_mappings()}
    (OUT / "measured.json").write_text(json.dumps(data, indent=1, ensure_ascii=False), encoding="utf-8")


# ------------------------------------------------------------------ combine
def _ranked(rows, axes):
    for r in rows:
        r["total"] = round(statistics.mean(r[a] for a in axes), 4)
    rows.sort(key=lambda r: -r["total"])
    for i, r in enumerate(rows):
        r["tie_with_next"] = i + 1 < len(rows) and r["total"] - rows[i + 1]["total"] < 0.02
    return rows


def combine():
    m = json.loads((OUT / "measured.json").read_text(encoding="utf-8"))
    codes = json.loads((OUT / "blind_codes.json").read_text(encoding="utf-8"))
    judges = [json.loads(p.read_text(encoding="utf-8")) for p in sorted(OUT.glob("judge_*.json"))]
    by_name = {n: c for c, n in codes.items()}
    faces = []
    for face in FACES:
        code, x = by_name[face], m["faces"][face]
        votes = {k: [j[code][k] for j in judges] for k in JUDGED_A}
        r = {"face": face, "code": code, "harmony": x["harmony"], "numbers": x["numbers"], "technical": x["technical"],
             **{k: round(statistics.mean(votes[k]) / 4, 3) for k in JUDGED_A if k != "calm"},
             "calm": round((statistics.mean(votes["calm"]) / 4 + x["calm_measured"]) / 2, 3), "size_kb": x["size_kb"],
             "votes": votes, "disagreement": max(max(v) - min(v) for v in votes.values()),
             "why": [{k: j[code][k + "_why"] for k in JUDGED_A} for j in judges]}
        faces.append(r)
    maps = []
    for mname in MAPPINGS:
        x = m["mappings"][mname]
        screens = [c for c, n in codes.items() if n.startswith(mname + "|")]
        votes = {k: [j[c][k] for j in judges for c in screens] for k in JUDGED_B}
        r = {"mapping": mname, "numbers": x["numbers"], "small": x["small"],
             "stone": round(statistics.mean(votes["stone"]) / 4, 3),
             "hierarchy": round((statistics.mean(votes["hierarchy"]) / 4 + x["hierarchy_measured"]) / 2, 3),
             "carve": {d: x[d]["carve"] for d in ROLES}, "votes": votes,
             "why": {c: [{k: j[c][k + "_why"] for k in JUDGED_B} for j in judges] for c in screens}}
        maps.append(r)
    data = {"faces": _ranked(faces, AXES_A), "mappings": _ranked(maps, AXES_B)}
    (OUT / "scores.json").write_text(json.dumps(data, indent=1, ensure_ascii=False), encoding="utf-8")
    print("face             total  " + "  ".join(f"{a[:5]:>5}" for a in AXES_A))
    for r in data["faces"]:
        print(f"{r['face']:16} {r['total']:.3f}  " + "  ".join(f"{r[a]:5.2f}" for a in AXES_A)
              + ("  (tie with next)" if r["tie_with_next"] else ""))
    print("mapping   total  " + "  ".join(f"{a[:5]:>5}" for a in AXES_B))
    for r in data["mappings"]:
        print(f"{r['mapping']:9} {r['total']:.3f}  " + "  ".join(f"{r[a]:5.2f}" for a in AXES_B)
              + ("  (tie with next)" if r["tie_with_next"] else ""))


# ------------------------------------------------------------------ the owner's page
NAMES = {"sisifo": "Sisifo", "grenze": "Grenze", "ortica": "Ortica Linear", "avara": "Avara", "cinzel": "Cinzel",
         "bagnard": "Bagnard", "ibm-plex-sans": "IBM Plex Sans", "libertinus-sans": "Libertinus Sans"}
LOOK = {"sisifo": "the release: upright and 12° italic, carved titles", "grenze": "wedge-serif humanist",
        "ortica": "Sisifo's base, uncarved, no italic", "avara": "rough, hand-cut serif; one weight and its italic",
        "cinzel": "inscriptional capitals; small caps for lowercase", "bagnard": "angular old-style; one weight",
        "ibm-plex-sans": "SPEC 0.36's face today, with IBM's italic", "libertinus-sans": "flared glyphic sans"}
# the panel's reasons, condensed (scores.json has them in full)
NOTE = {
    "sisifo": "Unanimous on stone, carving and personality (4 from all three): “crisp polygonal facets and flat-cut "
              "curves” at display size, while the facets disappear at 13 px. Calm, small text and oblique 3 from all.",
    "libertinus-sans": "The calmest and the best small text, but its flare is smooth: no cut facets (carving 1 from all).",
    "avara": "As carved and distinctive as Sisifo, but nervous: rough edges, uneven 13 px colour and a busy, "
             "lumpy italic.",
    "ortica": "Quiet and refined, “editorial rather than carved”. Its oblique is the browser's skew, which the "
              "judges took for a true italic.",
    "grenze": "Warm and well-made, the best measured numbers, but it reads as a bookish slab, not stone.",
    "bagnard": "Grounded mass and some sheared terminals, but very dark throughout and only one weight.",
    "ibm-plex-sans": "The most comfortable small text, and nothing of stone: 0 on stone, carving and inscription.",
    "cinzel": "Clearly lapidary capitals, but no lowercase: the 13 px text sets in small caps (0 from all).",
}
AXES_LABELS = [("stone", "Stone"), ("carving", "Carving"), ("personality", "Personality"), ("inscription", "Inscription"),
               ("oblique", "Oblique"), ("calm", "Calm"), ("small", "Small text"), ("harmony", "Harmony"),
               ("numbers", "Numbers"), ("technical", "Technical")]
MAP_LABELS = [("stone", "Stone"), ("hierarchy", "Hierarchy"), ("numbers", "Numbers far"), ("small", "Small text")]
ROLE_NAMES = {"xs": "label", "eb": "eyebrow", "b": "body", "t": "row title", "h": "heading", "ex": "exercise",
              "num": "set number", "pad": "keypad"}
PAGE_CSS = """
h2.sm { font-size:20px; }
.part { margin:0; font-size:13px; letter-spacing:.06em; text-transform:uppercase; color:var(--mute); }
.roles { border-collapse:collapse; font-size:13px; width:100%; font-variant-numeric:tabular-nums; }
.roles th, .roles td { text-align:right; padding:3px 4px; border-bottom:1px solid var(--rule); }
.roles th:first-child, .roles td:first-child { text-align:left; }
.roles th { font-weight:500; color:var(--mute); }
.pair { gap:6px; }
"""


def _bars(r, labels):
    return "".join(f'<div class="ax"><span>{lab}</span><i style="--v:{r[k]:.3f}"></i><b>{r[k]:.2f}</b></div>'
                   for k, lab in labels)


def _tie(r):
    return '<span class="tie">tie with next</span>' if r["tie_with_next"] else ""


def _face_card(r):
    f = r["face"]
    return f"""<section id="{f}">
  <header><h2>{NAMES[f]}</h2><p class="look">{LOOK[f]}</p><p class="total">{r['total']:.3f}{_tie(r)}</p></header>
  <p class="note">{NOTE[f]}</p>
  <div class="axes">{_bars(r, AXES_LABELS)}</div>
  <img src="img/{f}.png" width="384" alt="{NAMES[f]}: titles, capitals, set numbers, 13 px text and italics at 6T size">
</section>"""


def page():
    import shutil
    from carve_page import STYLE, OUT as PAGE
    s = json.loads((OUT / "scores.json").read_text(encoding="utf-8"))
    if PAGE.exists():
        shutil.rmtree(PAGE)
    (PAGE / "img").mkdir(parents=True)
    for p in (OUT / "named").glob("*.png"):
        shutil.copy(p, PAGE / "img" / p.name)
    faces, maps = s["faces"], {r["mapping"]: r for r in s["mappings"]}
    by_face = {r["face"]: r for r in faces}
    rows = "".join(f"<tr><td>{ROLE_NAMES[k]}</td><td>{ROLES['bal'][k]}</td>"
                   f"<td>{maps['stepped']['carve']['bal'][k]}</td><td>{maps['ramp']['carve']['bal'][k]}</td>"
                   f"<td>{ROLES['cmp'][k]}</td><td>{maps['ramp']['carve']['cmp'][k]}</td></tr>" for k in ROLES["bal"])
    table = (f'<table class="roles"><thead><tr><th>role</th><th>dp</th><th>stepped</th><th>ramp</th>'
             f'<th>compact dp</th><th>ramp</th></tr></thead><tbody>{rows}</tbody></table>'
             f'<p class="look">Carve 0 to 100 for each text role. Stepped gives compact the same values as balanced.</p>')
    look = {"stepped": "carve 0 up to 16 dp, 100 above", "ramp": "carve rises from 15 dp to full at 28 dp"}
    mcards = "\n".join(f"""<section id="{r['mapping']}">
  <header><h2>{r['mapping'].capitalize()}</h2><p class="look">{look[r['mapping']]}</p><p class="total">{r['total']:.3f}{_tie(r)}</p></header>
  <div class="axes">{_bars(r, MAP_LABELS)}</div>
</section>""" for r in s["mappings"])
    shots = "\n".join(f"""<section class="pair" id="{d}-{n}">
  <header><h2 class="sm">{n.replace('_', ' ').capitalize()}{' · compact' if d == 'cmp' else ''}</h2><p class="look">stepped, then ramp</p><p class="total">&nbsp;</p></header>
  <img src="img/stepped-{d}-{n}.png" width="384" alt="{n} screen, stepped mapping, at 6T size">
  <img src="img/ramp-{d}-{n}.png" width="384" alt="{n} screen, ramp mapping, at 6T size">
</section>""" for d, n in SCREENS_B)
    f0, f1, o = faces[0], faces[1], by_face["ortica"]
    intro = f"""<p>Stage 6. The release (upright and 12° italic) against the font search's finalists, judged blind on
ten axes; then two ways to tie carve to text size, in the stage 1a screens.</p>
<p><b>{NAMES[f0['face']]} ranks first, {f0['total']:.3f}</b>, ahead of {NAMES[f1['face']]} at {f1['total']:.3f}. Its
lowest axes are harmony ({f0['harmony']:.2f}, measured at full carve), calm ({f0['calm']:.2f}), oblique and small text
({f0['small']:.2f}). Two of these are judging noise: at 13 px Sisifo is Ortica glyph for glyph, yet Ortica scored
{o['small']:.2f}; Ortica has no italic, and the browser's skew of it scored {o['oblique']:.2f}.</p>
<p><b>The two mappings tie</b> (stepped {maps['stepped']['total']:.3f}, ramp {maps['ramp']['total']:.3f}). Numbers at
arm's length, small text and the measured hierarchy come out equal; the judges saw stepped as slightly more carved
(stone {maps['stepped']['stone']:.2f} against {maps['ramp']['stone']:.2f}) and found the pairs hard to tell apart.</p>
<p>Do you sign off Sisifo, and which mapping goes into the type tokens?</p>"""
    doc = f"""<title>Sisifo Sign-off</title>
<meta name="claude:viewport-fit-sides" content="cover">
{STYLE.replace('</style>', PAGE_CSS + '</style>')}
<main>
  <div class="intro">
    <h1>Sisifo sign-off</h1>
    {intro}
  </div>
<p class="part">The faces</p>
{chr(10).join(_face_card(r) for r in faces)}
<p class="part">Carve by text size</p>
<section id="roles">{table}</section>
{mcards}
{shots}
</main>"""
    (PAGE / "index.html").write_text(doc, encoding="utf-8")
    print(PAGE / "index.html")


if __name__ == "__main__":
    {"specimens": specimens, "measure": measure_all, "combine": combine, "page": page}[sys.argv[1]]()
