"""Measure the type candidates on the owner's measured axes (2026-10-22). Standard library + fontTools + Pillow.

Usage:  python tools/measure.py            -> measured.json + a table   (run from research/type-2026-10-22)

Inputs: candidates_A.json, candidates_B.json (searchers), plus IBM Plex Sans as the reference (../screens-2026-10-20/
polish/fonts). Fonts are read as data only (fontTools parses, Pillow rasterises); nothing from the downloads runs.

Each font is measured on its Regular (wght 400, or the static file nearest 400). Sub-scores are 0..1, higher is better.

Harmony (owner: even, proportional space between letters; consistent x-height; ascender = descender)
  spacing_even   1 - CV of the ink gaps between neighbouring letters in lowercase words at 64 px (sidebearings +
                 kerning as rendered); CV 0 -> 1, CV >= 0.6 -> 0
  xheight_even   1 - CV of the flat tops of x, v, w, z, u, n, m, r (yMax in font units) / 0.05
  asc_desc       1 - |ascender extent - descender extent| / the larger, from b d h k l (yMax - xHeight) and p q g y (-yMin)
  Caps-only faces (no lowercase) are measured on capitals for spacing, and get x-height and asc/desc as None (the axis
  mean uses what exists, and the report says so).
Numbers at arm's length
  tabular        1 if every digit has the same advance by default or GSUB has tnum, else 0
  lining         1 - spread of digit heights (yMax of 0-9) relative to cap height (oldstyle figures score low)
  distinct       mean pixel distance (1 - IoU) of the confusable pairs 1/7, 3/8, 0/O, 5/6, 6/8 at 48 px, scaled /0.5
  decimal        the period's ink area relative to the stroke area of "1" at 48 px, capped at 1 (a dot you can see)
Technical fit
  licence        1 if a licence file is present and names OFL / Apache / MIT / CC / ITF free licence, else 0
  accents        share of à è é ì ò ù À È É Ì Ò Ù ’ « » – present in the cmap
  weights        number of weights (static files or the wght range in steps of 100), /4 capped at 1
  size           1 if the files total <= 400 KB, falling to 0 at 2 MB (APK weight)
Calm (measured part; the judged part comes from the blind panel)
  contrast       stroke contrast of "o" at 96 px: thin/thick; 1 = monoline, low = high contrast (sharper, louder)
  weight         ink density of "Hamburgefonstiv 0123456789" at 64 px; 1 at 0.12-0.22 (regular colour), lower if
                 much darker (shouting) or much lighter (faint at arm's length)
"""
import json
import pathlib
import re
import statistics

from fontTools.ttLib import TTFont
from PIL import Image, ImageDraw, ImageFont

HERE = pathlib.Path(__file__).resolve().parent.parent
PLEX = HERE.parent / "screens-2026-10-20" / "polish" / "fonts"
LICENCE_RE = re.compile(r"SIL Open Font|OFL|Apache License|MIT License|Creative Commons|CC0|CC BY|CC-BY|"
                        r"ITF Free Font|free for commercial", re.I)
ACCENTS = "àèéìòùÀÈÉÌÒÙ’«»–"


def candidates():
    out = []
    for f, half in (("candidates_A.json", "A"), ("candidates_B.json", "B")):
        p = HERE / f
        if p.exists():
            for c in json.loads(p.read_text(encoding="utf-8")):
                c["half"] = half
                out.append(c)
    out.append({"family": "IBM Plex Sans", "slug": "ibm-plex-sans", "half": "ref",
                "files": [str(PLEX / "IBMPlexSans[wdth,wght].ttf")], "licence": "SIL OFL 1.1",
                "licence_dir": str(PLEX)})
    return out


def font_files(c):
    d = HERE / "fonts" / c["slug"]
    files = [pathlib.Path(f) for f in c.get("files", []) if str(f).lower().endswith((".ttf", ".otf"))]
    files = [f if f.is_absolute() else HERE / f for f in files]
    if not files and d.exists():
        files = sorted(p for p in d.rglob("*") if p.suffix.lower() in (".ttf", ".otf"))
    files = [f for f in files if f.exists()]
    if "mono" not in c["family"].lower():   # a bundled Mono sibling (Overpass Mono) is not the candidate itself
        files = [f for f in files if "mono" not in f.name.lower()] or files
    return files


def weight_of(f):
    t = TTFont(str(f), lazy=True)
    w = t["OS/2"].usWeightClass if "OS/2" in t else 400
    italic = bool(t["OS/2"].fsSelection & 1) if "OS/2" in t else False
    name = t["name"].getDebugName(2) or ""
    return w, italic or "italic" in name.lower() or "oblique" in name.lower(), t


def pick_regular(files):
    best = None
    for f in files:
        try:
            w, it, t = weight_of(f)
        except Exception:
            continue
        if "fvar" in t:
            return f, t, True
        if it:
            continue
        if best is None or abs(w - 400) < abs(best[1] - 400):
            best = (f, w, t)
    return (best[0], best[2], False) if best else (None, None, False)


def weights(files):
    ws = set()
    for f in files:
        try:
            w, it, t = weight_of(f)
        except Exception:
            continue
        if "fvar" in t:
            for ax in t["fvar"].axes:
                if ax.axisTag == "wght":
                    return len(range(int(ax.minValue // 100) * 100, int(ax.maxValue) + 1, 100))
        if not it:
            ws.add(w)
    return len(ws)


def pil_font(f, size, variable):
    ft = ImageFont.truetype(str(f), size)
    if variable:
        try:
            axes = ft.get_variation_axes()
            ft.set_variation_by_axes([400 if a.get("name", b"") in (b"Weight", "Weight") else a["default"] for a in axes])
        except Exception:
            pass
    return ft


def ink(ft, text, pad=20):
    l, t, r, b = ft.getbbox(text)
    im = Image.new("L", (r - l + 2 * pad, b - t + 2 * pad), 0)
    ImageDraw.Draw(im).text((pad - l, pad - t), text, font=ft, fill=255)
    return im


def gaps(ft, word):
    im = ink(ft, word)
    w, h = im.size
    px = im.load()
    cols = [any(px[x, y] > 96 for y in range(h)) for x in range(w)]
    runs, cur = [], None
    for x, c in enumerate(cols):
        if c and cur is None:
            cur = x
        if not c and cur is not None:
            runs.append((cur, x))
            cur = None
    return [runs[i + 1][0] - runs[i][1] for i in range(len(runs) - 1)]


def iou_dist(ft, a, b):
    ia, ib = ink(ft, a, 4), ink(ft, b, 4)
    W, H = max(ia.width, ib.width), max(ia.height, ib.height)
    A, B = Image.new("L", (W, H)), Image.new("L", (W, H))
    A.paste(ia, ((W - ia.width) // 2, (H - ia.height) // 2))
    B.paste(ib, ((W - ib.width) // 2, (H - ib.height) // 2))
    pa, pb = A.load(), B.load()
    inter = union = 0
    for y in range(H):
        for x in range(W):
            u, v = pa[x, y] > 96, pb[x, y] > 96
            inter += u and v
            union += u or v
    return 1 - inter / union if union else 0


def area(ft, ch):
    return sum(1 for v in ink(ft, ch, 2).get_flattened_data() if v > 96)


def bbox_units(t, ch):
    cmap = t.getBestCmap()
    g = cmap.get(ord(ch))
    if g is None:
        return None
    gs = t.getGlyphSet()
    from fontTools.pens.boundsPen import BoundsPen
    pen = BoundsPen(gs)
    gs[g].draw(pen)
    return pen.bounds


def cv(xs):
    xs = [x for x in xs if x is not None]
    if len(xs) < 2:
        return None
    m = statistics.mean(xs)
    return statistics.pstdev(xs) / m if m else None


def clamp(x):
    return max(0.0, min(1.0, x))


def measure(c):
    files = font_files(c)
    f, t, variable = pick_regular(files)
    if f is None:
        return {"error": "no readable font file"}
    cmap = t.getBestCmap()
    has = lambda s: all(ord(ch) in cmap for ch in s)
    lower = has("abcdefghijklmnopqrstuvwxyz")
    r = {"file": str(f.relative_to(HERE.parent) if HERE.parent in f.parents else f), "variable": variable,
         "lowercase": lower}
    ft64, ft48, ft96 = pil_font(f, 64, variable), pil_font(f, 48, variable), pil_font(f, 96, variable)

    # harmony
    words = ["minimum", "hamburgefonstiv", "stone", "boulder", "mountain"] if lower else ["MINIMUM", "HAMBURG", "STONE", "BOULDER"]
    g = [x for w in words for x in gaps(ft64, w)]
    cg = cv(g)
    r["spacing_even"] = round(clamp(1 - (cg or 0) / 0.6), 3)
    if lower:
        tops = [bbox_units(t, ch) for ch in "xvwzunmr"]
        r["xheight_even"] = round(clamp(1 - (cv([b[3] for b in tops if b]) or 0) / 0.05), 3)
        xh = statistics.median([b[3] for b in tops if b])
        asc = statistics.mean([bbox_units(t, ch)[3] - xh for ch in "bdhkl" if bbox_units(t, ch)])
        des = statistics.mean([-bbox_units(t, ch)[1] for ch in "pqgy" if bbox_units(t, ch)])
        r["asc_desc"] = round(clamp(1 - abs(asc - des) / max(asc, des)), 3)
    else:
        r["xheight_even"] = r["asc_desc"] = None

    # numbers
    digits = "0123456789"
    if has(digits):
        hmtx = t["hmtx"].metrics
        adv = {hmtx[cmap[ord(d)]][0] for d in digits}
        fl = t["GSUB"].table.FeatureList if "GSUB" in t else None
        tnum = bool(fl) and any(fr.FeatureTag == "tnum" for fr in fl.FeatureRecord)
        r["tnum_feature"] = bool(tnum)
        r["tabular"] = 1.0 if (len(adv) == 1 or tnum) else 0.0
        hs = [bbox_units(t, d)[3] for d in digits]
        cap = (bbox_units(t, "H") or (0, 0, 0, max(hs)))[3]
        lnum = bool(fl) and any(fr.FeatureTag == "lnum" for fr in fl.FeatureRecord)
        r["lnum_feature"] = lnum   # the app switches lining figures on, so a font that has them is not penalised
        r["lining"] = 1.0 if lnum else round(clamp(1 - (max(hs) - min(hs)) / cap / 0.3), 3)
        pairs = [("1", "7"), ("3", "8"), ("0", "O"), ("5", "6"), ("6", "8")]
        r["distinct"] = round(clamp(statistics.mean(iou_dist(ft48, a, b) for a, b in pairs) / 0.5), 3)
        r["decimal"] = round(clamp(area(ft48, ".") / (0.25 * area(ft48, "1"))), 3)
    else:
        r.update(tnum_feature=False, tabular=0.0, lining=0.0, distinct=0.0, decimal=0.0)

    # technical
    licdir = pathlib.Path(c.get("licence_dir") or (HERE / "fonts" / c["slug"]))
    lic_text = " ".join(p.read_text(encoding="utf-8", errors="ignore")[:20000] for p in licdir.rglob("*")
                        if p.is_file() and re.search(r"licen|ofl|copying|readme", p.name, re.I))
    if c["slug"] == "ibm-plex-sans":
        lic_text = "SIL Open Font License"
    r["licence"] = 1.0 if LICENCE_RE.search(lic_text) else 0.0
    if re.search(r"ITF Free Font", lic_text, re.I) and not re.search(r"SIL Open Font", lic_text, re.I):
        r["licence"], r["licence_note"] = 0.5, "ITF FFL: no subsetting, no public-repo redistribution"
    r["accents"] = round(sum(ord(ch) in cmap for ch in ACCENTS) / len(ACCENTS), 3)
    r["n_weights"] = weights(files)
    r["weights"] = round(clamp(r["n_weights"] / 4), 3)
    kb = sum(p.stat().st_size for p in files) / 1024
    r["size_kb"] = round(kb)
    r["size"] = round(clamp(1 - (kb - 400) / 1600), 3)

    # calm, measured part
    o = ink(ft96, "o", 0)
    px, w, h = o.load(), o.width, o.height
    row = [px[x, h // 2] > 96 for x in range(w)]
    col = [px[w // 2, y] > 96 for y in range(h)]
    thick = next((len(m) for m in re.findall(r"1+", "".join("1" if v else "0" for v in row))), 1)
    thin = next((len(m) for m in re.findall(r"1+", "".join("1" if v else "0" for v in col))), 1)
    r["contrast"] = round(clamp(min(thick, thin) / max(thick, thin)), 3)
    sample = ink(ft64, "Hamburgefonstiv 0123456789" if lower else "HAMBURGEFONSTIV 0123456789", 0)
    dens = sum(1 for v in sample.get_flattened_data() if v > 96) / (sample.width * sample.height)
    r["ink_density"] = round(dens, 3)
    r["weight_colour"] = round(1.0 if 0.12 <= dens <= 0.22 else clamp(1 - (dens - 0.22) / 0.2) if dens > 0.22
                               else clamp(1 - (0.12 - dens) / 0.08), 3)

    mean = lambda ks: round(statistics.mean([r[k] for k in ks if r.get(k) is not None]), 3)
    r["harmony"] = mean(["spacing_even", "xheight_even", "asc_desc"])
    r["numbers"] = mean(["tabular", "lining", "distinct", "decimal"])
    r["technical"] = mean(["licence", "accents", "weights", "size"])
    r["calm_measured"] = mean(["contrast", "weight_colour"])
    return r


def main():
    out = {}
    for c in candidates():
        try:
            m = measure(c)
        except Exception as e:   # a broken file is a finding, not a crash
            m = {"error": f"{type(e).__name__}: {e}"}
        out[c["slug"]] = {"family": c["family"], "half": c["half"], **m}
        x = out[c["slug"]]
        print(f"{c['half']:3s} {c['family'][:28]:28s} " + (x.get("error") or
              f"harm {x['harmony']:.2f} num {x['numbers']:.2f} tech {x['technical']:.2f} calm~ {x['calm_measured']:.2f}"
              f"  tnum {x['tnum_feature']} lower {x['lowercase']} w{x['n_weights']} {x['size_kb']}KB"))
    (HERE / "measured.json").write_text(json.dumps(out, indent=1, ensure_ascii=False), encoding="utf-8")


if __name__ == "__main__":
    main()
