"""Score the stage 3 carve variants on the owner's eight axes (design.md, "How quality is judged").

Usage:  python tools/score_carve.py measure [round]   -> build/carve[2]/measured.json
        python tools/score_carve.py combine [round]   -> build/carve[2]/scores.json + a table (needs judge_*.json)
Round 2 adds the blind "personality" axis (weight 1) and Ortica Angular Bold as a second unnamed reference.

Measured on a static instance at wght 400 and CARV 100 (titles and set numbers are where the carve shows), with the
font search's own measure() (tools/search_measure.py, copied from the search):
  harmony, numbers, calm (measured half)   as in the font search
  technical                                measured on the variable file itself (weights, size, accents, licence)
  small text unharmed                      13 px x 2.8125 at CARV 0 against Ortica Linear Regular: x-height ratio,
                                           line width ratio, pixel IoU of the line (1.0 = the same)
  faithful to Ortica (weight 0.5)          CARV 100 against Ortica Linear Regular: mean pixel IoU of a-z A-Z 0-9 at
                                           64 px; advances equal; kerning (shaped widths of AVATAR, To Ty Yo, Wave LT
                                           in the browser, CARV 100 against CARV 0)
Judged by the blind panel (0-4, /4): stone, carving at display size, and calm (judged half).
Total = weighted mean over the eight axes (faithful counts half). A gap under 0.02 is a tie.
"""
import json
import math
import pathlib
import statistics
import sys

from fontTools.ttLib import TTFont
from fontTools.varLib.instancer import instantiateVariableFont
from fontTools.pens.basePen import BasePen
from PIL import Image, ImageDraw

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools"))
sys.path.insert(0, str(pathlib.Path.home() / ".claude" / "tools"))
import search_measure as measure  # noqa: E402
MEASURE_INK = measure.ink
sys.path.insert(0, str(ROOT / "tools"))
import gate  # noqa: E402

ROUND = sys.argv[2] if len(sys.argv) > 2 else "1"
OUT = ROOT / "build" / ("carve" if ROUND == "1" else f"carve{ROUND}")
ORTICA = ROOT / "vendor" / "ortica" / "fonts" / "OrticaLinear-Regular.otf"
VARIANTS = {"1": ["A", "B", "C", "D", "E"], "2": ["B", "R", "RL", "G", "GL"], "3": ["GL"],
            "4": ["GLP", "GLZ", "GL"], "5": ["GLZ_I7", "GLZ_I9", "GLZ_I12"]}[ROUND]
# round 3: round 2's GL is judged again beside the new GL; its measured axes come from round 2
PRIOR = {"3": {"GL_r2": ("carve2", "GL")}}.get(ROUND, {})
# round 2 (owner): a blind "personality" axis, judged against two unnamed references, plain and Ortica Angular
JUDGED = ["stone", "carving", "calm"] + (["personality"] if ROUND != "1" else []) + (["inscription"] if ROUND == "4"
                                                                                     else [])
CONTROLS = ["plain"] + (["angular"] if ROUND in ("2", "3") else []) + (["cinzel"] if ROUND == "4" else [])
if ROUND == "5":     # stage 5: obliques; the control is the browser's faked oblique (a plain skew of the upright)
    JUDGED = ["stone", "carving", "calm", "personality", "oblique"]
    CONTROLS = ["faux"]
FITS = ["fit_emphasis", "fit_notes", "fit_display"] if ROUND == "5" else []   # where the obliques go; not in totals
SMALL = "Labels stay in the list for reuse. Mobilità ed equilibrio, perché è così."
CHARS = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789"
AXES = {"harmony": 1, "stone": 1, "numbers": 1, "calm": 1, "technical": 1, "carving": 1, "small": 1, "faithful": 0.5}
if ROUND != "1":
    AXES["personality"] = 1
if ROUND == "4":          # stage 4 (owner): a blind "inscriptional character" axis
    AXES["inscription"] = 1
if ROUND == "5":          # stage 5 (owner): a blind "oblique quality" axis
    AXES["oblique"] = 1


def vf(v):
    d = ROOT / "build" / "variants" / v
    return d / "Sisifo-Italic[CARV,wght].ttf" if (d / "Sisifo-Italic[CARV,wght].ttf").exists() else d / "Sisifo[CARV,wght].ttf"


def static(v, carve):
    p = OUT / "static" / f"Sisifo-{v}-C{carve}.ttf"
    if not p.exists():
        p.parent.mkdir(parents=True, exist_ok=True)
        instantiateVariableFont(TTFont(vf(v)), {"wght": 400, "CARV": carve}, static=True).save(p)
    return p


class _Flat(BasePen):
    """Polylines of a glyph's contours (curves flattened)."""
    def __init__(self):
        super().__init__(None)
        self.polys, self.cur = [], []

    def _moveTo(self, p):
        self.cur = [p]

    def _lineTo(self, p):
        self.cur.append(p)

    def _curveToOne(self, a, b, c):
        p0 = self.cur[-1]
        for i in range(1, 13):
            t, u = i / 12, 1 - i / 12
            self.cur.append(tuple(u ** 3 * p0[k] + 3 * u * u * t * a[k] + 3 * u * t * t * b[k] + t ** 3 * c[k]
                                  for k in (0, 1)))

    def _closePath(self):
        self.polys.append(self.cur)
        self.cur = []


def _slant_of(font):
    """(tan, centring) of an oblique's slant, from its italic angle; None for an upright."""
    f = TTFont(font)
    theta = -f["post"].italicAngle
    if not theta:
        return None
    tt = math.tan(math.radians(theta))
    return tt, tt * f["OS/2"].sxHeight / 2


def _mask(font, text, size, canvas=None, slant=None):
    """Text rasterised from the outlines themselves, the same way for every font (no hinting: PIL hints TrueType and
    CFF differently, which alone made Sisifo's line 2 % wider than Ortica's with identical advances). Overlaps are
    merged first, then outer contours fill and counters clear, at 4x and averaged down."""
    t = TTFont(font)
    cmap, upm, hmtx = t.getBestCmap(), t["head"].unitsPerEm, t["hmtx"].metrics
    s, k = size / upm, 4
    width = sum(hmtx[cmap[ord(c)]][0] for c in text) * s
    w, h = canvas or (int(width) + 40, size * 2)
    im = Image.new("L", (w * k, h * k), 0)
    dr = ImageDraw.Draw(im)
    x = 20.0
    for c in text:
        name = cmap[ord(c)]
        pen = _Flat()
        gate._merged(t, name, slant).draw(pen)
        polys = sorted(pen.polys, key=lambda p: -abs(_area(p)))
        for poly in polys:
            pts = [((x + px * s) * k, (size * 1.5 - py * s) * k) for px, py in poly]
            if len(pts) > 2:
                dr.polygon(pts, fill=255 if _area(poly) * _area(polys[0]) > 0 else 0)
        x += hmtx[name][0] * s
    return im.resize((w, h), Image.LANCZOS), width


def _area(poly):
    return sum(poly[i][0] * poly[i - 1][1] - poly[i - 1][0] * poly[i][1] for i in range(len(poly))) / 2


def _iou(a, b):
    pa, pb = a.load(), b.load()
    inter = union = 0
    for y in range(a.height):
        for x in range(a.width):
            u, v = pa[x, y] > 96, pb[x, y] > 96
            inter += u and v
            union += u or v
    return inter / union if union else 1.0


def small_text(v):
    size = round(13 * 2.8125)
    new, wn = _mask(static(v, 0), SMALL, size)
    # an oblique is compared with Ortica slanted the same way (stage 5), as the gate does
    old, wo = _mask(ORTICA, SMALL, size, new.size, _slant_of(static(v, 0)))
    xh = lambda f: measure.bbox_units(TTFont(f), "x")[3]
    xr, wr = xh(static(v, 0)) / xh(ORTICA), wn / wo
    parts = {"xheight_ratio": round(xr, 4), "width_ratio": round(wr, 4), "line_iou": round(_iou(new, old), 4)}
    parts["small"] = round(statistics.mean([measure.clamp(1 - abs(xr - 1) / 0.1), measure.clamp(1 - abs(wr - 1) / 0.05),
                                            parts["line_iou"]]), 3)
    return parts


def _shaped_widths(font_path):
    import headless_browser as hb
    texts = ["AVATAR", "To Ty Yo", "Wave LT"]
    spans = "".join(f'<span data-k="{c}|{t}" style="font-variation-settings:{chr(39)}CARV{chr(39)} {c}">{t}</span><br>'
                    for c in (0, 100) for t in texts)
    page = OUT / "html" / "kern.html"
    page.parent.mkdir(parents=True, exist_ok=True)
    page.write_text(f"<!doctype html><meta charset=utf-8><style>@font-face{{font-family:S;src:url('"
                    f"{font_path.as_uri()}')}} body{{font:100px S;white-space:nowrap}}</style>{spans}", encoding="utf-8")
    js = ("(async()=>{await document.fonts.ready;const r={};for(const f of document.fonts){r['face:'+f.family]=f.status};"
          "document.querySelectorAll('span').forEach(s=>r[s.dataset.k]=s.getBoundingClientRect().width);"
          "return JSON.stringify(r)})()")
    try:
        res = json.loads(hb.evaluate(str(page), js, 3000, 1200))
    finally:
        hb.close_all()
    if res.get("face:S") != "loaded":
        raise RuntimeError("font not loaded in the kerning page")
    return max(abs(res[f"0|{t}"] - res[f"100|{t}"]) for t in texts)


def faithful(v):
    carved, orig = static(v, 100), ORTICA
    sl = _slant_of(carved)          # an oblique is compared with Ortica slanted the same way
    ious = []
    for ch in CHARS:
        a, _ = _mask(carved, ch, 64, (140, 128))
        b, _ = _mask(orig, ch, 64, (140, 128), sl)
        ious.append(_iou(a, b))
    t, o = TTFont(carved), TTFont(orig)
    tc, oc = t.getBestCmap(), o.getBestCmap()
    adv = statistics.mean(t["hmtx"].metrics[tc[ord(c)]][0] == o["hmtx"].metrics[oc[ord(c)]][0] for c in CHARS)
    kern_px = _shaped_widths(vf(v))
    plain = statistics.mean(_iou(_mask(static(v, 0), ch, 64, (140, 128))[0], _mask(orig, ch, 64, (140, 128), sl)[0])
                            for ch in CHARS)
    parts = {"shape_iou": round(statistics.mean(ious), 4), "shape_iou_plain": round(plain, 4),
             "worst": sorted(zip(ious, CHARS))[:3],
             "advances_equal": adv, "kern_diff_px": round(kern_px, 3), "kerning": 1.0 if kern_px <= 0.5 else 0.0}
    parts["faithful"] = round(statistics.mean([parts["shape_iou"], adv, parts["kerning"]]), 3)
    return parts


def _deslanted_ink(tan):
    """The font search's ink() with the slant taken out of the raster, so its spacing measure (blank columns between
    letters, which assumes upright stems) sees an oblique's letters as it sees upright ones."""
    from PIL import Image as _Image
    orig = MEASURE_INK

    def ink(ft, text, pad=20):
        im = orig(ft, text, pad)
        w, h = im.size
        out = im.transform((w + int(tan * h) + 1, h), _Image.AFFINE, (1, -tan, tan * h, 0, 1, 0),
                           resample=_Image.BICUBIC, fill=0)
        box = out.getbbox()      # back to the ink plus the same padding: the contrast reading uses the centre column
        if not box:
            return out
        cropped = out.crop(box)
        framed = _Image.new("L", (cropped.width + 2 * pad, cropped.height + 2 * pad), 0)
        framed.paste(cropped, (pad, pad))
        return framed
    return ink


def measure_all():
    out = {}
    for v in VARIANTS:
        sl = _slant_of(static(v, 100))
        measure.ink = _deslanted_ink(sl[0]) if sl else MEASURE_INK
        m = measure.measure({"family": f"Sisifo {v}", "slug": f"sisifo-{v}", "files": [str(static(v, 100))],
                             "licence_dir": str(ROOT)})
        tech = measure.measure({"family": f"Sisifo {v}", "slug": f"sisifo-{v}", "files": [str(vf(v))],
                                "licence_dir": str(ROOT)})
        out[v] = {"harmony": m["harmony"], "numbers": m["numbers"], "calm_measured": m["calm_measured"],
                  "technical": tech["technical"], "size_kb": tech["size_kb"],
                  "numbers_parts": {k: m[k] for k in ("tabular", "lining", "distinct", "decimal")},
                  **small_text(v), **faithful(v)}
        print(v, {k: out[v][k] for k in ("harmony", "numbers", "calm_measured", "technical", "small", "faithful")})
    (OUT / "measured.json").write_text(json.dumps(out, indent=1, ensure_ascii=False), encoding="utf-8")


def combine():
    m = json.loads((OUT / "measured.json").read_text(encoding="utf-8"))
    codes = json.loads((OUT / "blind_codes.json").read_text(encoding="utf-8"))
    judges = [json.loads(p.read_text(encoding="utf-8")) for p in sorted(OUT.glob("judge_*.json"))]
    by_name = {name: code for code, name in codes.items()}
    for name, (folder, v) in PRIOR.items():
        m[name] = json.loads((ROOT / "build" / folder / "measured.json").read_text(encoding="utf-8"))[v]
    rows = []
    for v in VARIANTS + list(PRIOR):
        code, x = by_name[v], m[v]
        votes = {k: [j[code][k] for j in judges] for k in JUDGED}
        r = {"variant": v, "code": code, "harmony": x["harmony"], "numbers": x["numbers"],
             "technical": x["technical"], "small": x["small"], "faithful": x["faithful"],
             **{k: round(statistics.mean(votes[k]) / 4, 3) for k in JUDGED if k != "calm"},
             "calm": round((statistics.mean(votes["calm"]) / 4 + x["calm_measured"]) / 2, 3),
             "votes": votes, "disagreement": max(max(s) - min(s) for s in votes.values()),
             "why": [{k: j[code][k + "_why"] for k in JUDGED} for j in judges],
             "fits": {k: round(statistics.mean(j[code][k] for j in judges) / 4, 3) for k in FITS}}
        r["total"] = round(sum(r[a] * w for a, w in AXES.items()) / sum(AXES.values()), 4)
        rows.append(r)
    controls = {c: {k: [j[by_name[c]][k] for j in judges] for k in JUDGED} for c in CONTROLS}
    rows.sort(key=lambda r: -r["total"])
    for i, r in enumerate(rows):
        r["tie_with_next"] = i + 1 < len(rows) and r["total"] - rows[i + 1]["total"] < 0.02
    (OUT / "scores.json").write_text(json.dumps({"rows": rows, "control_votes": controls,
                                                 "plain_control_votes": controls.get("plain")}, indent=1,
                                                ensure_ascii=False), encoding="utf-8")
    print("var  total  " + "  ".join(f"{a[:5]:>5}" for a in AXES) + "  disagree")
    for r in rows:
        print(f"{r['variant']:4} {r['total']:.3f}  " + "  ".join(f"{r[a]:5.2f}" for a in AXES)
              + f"  {r['disagreement']}{'  (tie with next)' if r['tie_with_next'] else ''}")
    print("control votes:", controls)


if __name__ == "__main__":
    {"measure": measure_all, "combine": combine}[sys.argv[1]]()
