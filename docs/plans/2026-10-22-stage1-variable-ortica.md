# Sisifo Stage 1: Variable Ortica Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build `Sisifo[wght].ttf`, a variable font (wght 300–700) made from Ortica Linear's Light, Regular and Bold sources, whose instances at 300/400/700 match the original Ortica Linear fonts.

**Architecture:** Copy the three Ortica Linear UFOs into a new local repository, make every glyph point-compatible by splitting cubic curves in Light/Regular where Bold has extra points (shape-preserving), rename to Sisifo, build with fontmake from a designspace, and gate the result against the original OTFs with outline and browser-shaping comparisons.

**Tech Stack:** Python 3, fontmake 3.12.2, ufoLib2, fontTools, pytest 9.1.1, the kept-open headless browser (`~/.claude/tools/headless_browser.py`) for shaping checks.

**Spec:** `docs/design.md` (copy of `research/type-2026-10-22/sisifo-design.md`, approved 2026-10-22); this plan covers its stage 1 only.

## Global Constraints

- Root: this repository (developed inside SisyphusFit's `research/type-2026-10-22/sisifo/`; local until the owner approves `github.com/haziaferi/sisifo` at the end of stage 1).
- Source: `research/type-2026-10-22/ortica-src` at commit `27bf44d`, UFOs `source/Ortica Linear-{Light,Regular,Bold}.ufo`; originals to gate against: `ortica-src/fonts/OrticaLinear-{Light,Regular,Bold}.otf`.
- Licence: SIL OFL 1.1; keep `© 2021, Benedetta Bovani & Colllettivo` and add `Sisifo modifications © 2026 haziaferi`; family name `Sisifo`, never `Ortica`.
- Axis: `wght` min 300, default 400, max 700; named instances Light 300, Regular 400, Medium 500, SemiBold 600, Bold 700.
- Output: `fonts/variable/Sisifo[wght].ttf`, target ≤ 400 KB.
- Coverage: at least Ortica Linear's 405 glyphs and every code point its cmap maps.
- Scripts run with `python -I` where they need no user site packages; fontmake/ufoLib2 live in the user site, so tools run with plain `python`.
- Gates run bare (never through a pipe) and exit non-zero on failure.

## Review Focus

1. **Intermediate weights** (350, 550, 650): a person setting weight 550 expects a clean outline between Regular and Bold, not a kink where a split point was placed badly. Test: `test_intermediate_instances_clean` in Task 4.
2. **Accented and composite glyphs** (`Agrave`, `Eacute`, `Q` with its `O` component): they follow their base glyphs, so a broken base breaks them silently. Test: `test_composites_resolve_at_all_masters` in Task 2.
3. **Kerning across weights**: Bold has 506 pairs, Regular 485, Light 478; a person expects "AV", "To", "Yo" to tighten at every weight as in Ortica. Test: `test_kerning_widths_match_original` in Task 4.
4. **Figures and punctuation used by the app** (`0–9 . , × · – ’ « »` and `àèéìòù`): must be present and unchanged. Test: `test_app_characters_match_original` in Task 4.
5. **The `zero.dnom` bug fix**: Regular is empty upstream; the fix must not be mistaken for a regression by the gate. Test: `test_zero_dnom_drawn` in Task 2, and the documented exemption in Task 4.

---

### Task 1: Repository, sources and naming

**Files:**
- Create: `sisifo/sources/Sisifo-{Light,Regular,Bold}.ufo` (copied from ortica-src), `sisifo/OFL.txt`, `sisifo/FONTLOG.md`, `sisifo/docs/design.md`, `sisifo/tools/rename.py`, `sisifo/tests/test_naming.py`, `sisifo/.gitignore`

**Interfaces:**
- Produces: `sources/Sisifo-Light.ufo`, `sources/Sisifo-Regular.ufo`, `sources/Sisifo-Bold.ufo` (UFO 3), used by every later task; `tools.rename.rename(ufo_path: Path, style: str) -> None`.

- [ ] **Step 1: `git init`, copy the three Linear UFOs and the design; write `.gitignore` (`fonts/`, `__pycache__/`, `build/`).**
- [ ] **Step 2: Write the failing test `tests/test_naming.py::test_family_and_copyright`**

```python
@pytest.mark.parametrize("style,weight", [("Light", 300), ("Regular", 400), ("Bold", 700)])
def test_family_and_copyright(style, weight):
    f = ufoLib2.Font.open(SOURCES / f"Sisifo-{style}.ufo")
    assert f.info.familyName == "Sisifo" and f.info.styleName == style
    assert f.info.openTypeOS2WeightClass == weight
    assert "Benedetta Bovani" in f.info.copyright and "Sisifo" in f.info.copyright
    assert "Ortica" not in (f.info.familyName + (f.info.openTypeNamePreferredFamilyName or ""))
    assert "SIL Open Font License" in f.info.openTypeNameLicense
```

- [ ] **Step 3: Run `python -m pytest tests/test_naming.py -v`; expected FAIL (familyName is "Ortica Linear").**
- [ ] **Step 4: Implement `rename(ufo_path, style)` in `tools/rename.py`**: set familyName, styleName, styleMapFamilyName, openTypeNamePreferredFamilyName/SubfamilyName, postscriptFontName `Sisifo-<style>`, copyright (both lines), version 0.1, vendor `NONE`; drop `openTypeNameUniqueID`. Run it on the three copies. Write `OFL.txt` (OFL 1.1 text with both copyright lines) and `FONTLOG.md` (base, commit 27bf44d, what changed).
- [ ] **Step 5: Run the test; expected PASS. Commit "Sisifo: Ortica Linear sources, renamed, OFL".**

### Task 2: Make the masters compatible

**Files:**
- Create: `sisifo/tools/compat.py`, `sisifo/tests/test_compat.py`

**Interfaces:**
- Consumes: the three UFOs from Task 1.
- Produces: `split_cubic(p0, p1, p2, p3, t: float) -> tuple[list[Pt], list[Pt]]`; `signature(glyph) -> tuple` (contour point counts and types, component base names); `make_compatible(light: Font, regular: Font, bold: Font) -> dict[str, str]` (glyph name → what was done) mutating Light and Regular in place; CLI `python tools/compat.py` saves the UFOs and prints the report.

- [ ] **Step 1: Write the failing tests in `tests/test_compat.py`**

```python
def test_split_preserves_shape():
    a, b = compat.split_cubic((0, 0), (10, 40), (60, 40), (80, 0), 0.37)
    for s in [i / 50 for i in range(51)]:   # every point of the original lies on one of the halves
        assert min(dist(bez((0, 0), (10, 40), (60, 40), (80, 0), s), on_halves(a, b)) ) < 0.01

def test_all_glyphs_compatible(fixed):            # fixed = make_compatible on fresh copies
    L, R, B = fixed
    assert [n for n in B.keys() if not (compat.signature(L[n]) == compat.signature(R[n]) == compat.signature(B[n]))] == []

@pytest.mark.parametrize("name", ["A","I","M","Q","V","W","X","Y","ampersand","b","d","h","k","l","m","n","p","r","u","v","w","x","y"])
def test_shape_unchanged(fixed, originals, name):  # Light and Regular: same area (±0.1 %) and bounds (±1 unit)
    ...

def test_f_k_reordered(fixed):
    assert [len(c) for c in fixed[1]["f_k"].contours] == [len(c) for c in fixed[2]["f_k"].contours]

def test_zero_dnom_drawn(fixed):
    r = fixed[1]["zero.dnom"]
    assert [len(c) for c in r.contours] == [12, 12] and r.width == 391   # Light 363 + 0.25 × (474 − 363)

def test_composites_resolve_at_all_masters(fixed):
    for f in fixed:
        for n in ("Agrave", "Eacute", "Igrave", "Ograve", "Ugrave", "Q"):
            assert all(c.baseGlyph in f for c in f[n].components)
```

- [ ] **Step 2: Run `python -m pytest tests/test_compat.py -v`; expected FAIL (module missing).**
- [ ] **Step 3: Implement `tools/compat.py`.** For each glyph whose signatures differ, per contour: turn Regular's and Bold's contours into segment lists (`line` / `curve`, with on-curve end points). Align with a small dynamic programme where one source curve may match a run of 1–3 consecutive Bold curves (Bold's extra points come from splitting one curve into two or three, as in `l`'s head serif). For each such run, split the Light and Regular curve at the parameters where Bold's inner on-curve points fall, measured by arc-length fraction along Bold's run, so the split mirrors Bold's structure; round the new points to integers. `f_k`: reorder Regular's contours to Bold's order by matching point counts. `zero.dnom` in Regular: interpolate Light and Bold contours and width at 0.25. Glyphs that still differ after this are reported by name and the CLI exits 1.
- [ ] **Step 4: Run the tests; expected PASS. Run `python tools/compat.py`; expected "25 fixed, 0 left".**
- [ ] **Step 5: Commit "Sisifo: compatible masters (25 glyphs)".**

### Task 3: Build the variable font

**Files:**
- Create: `sisifo/sources/Sisifo.designspace`, `sisifo/tools/build.py`, `sisifo/tests/test_build.py`

**Interfaces:**
- Consumes: compatible UFOs (Task 2).
- Produces: `fonts/variable/Sisifo[wght].ttf`; `build.build() -> Path`.

- [ ] **Step 1: Write the failing test `tests/test_build.py`**

```python
def test_variable_font():
    p = build.build(); t = TTFont(p)
    ax = {a.axisTag: (a.minValue, a.defaultValue, a.maxValue) for a in t["fvar"].axes}
    assert ax == {"wght": (300, 400, 700)}
    assert [t["name"].getDebugName(i.subfamilyNameID) for i in t["fvar"].instances] == ["Light", "Regular", "Medium", "SemiBold", "Bold"]
    assert t["name"].getDebugName(1) == "Sisifo"
    orig = TTFont(ORIGINAL["Regular"]).getBestCmap()
    assert set(orig) <= set(t.getBestCmap())
    assert p.stat().st_size <= 400 * 1024
```

- [ ] **Step 2: Run it; expected FAIL.**
- [ ] **Step 3: Write `Sisifo.designspace` (axis and instances as in Global Constraints; Regular is the default source and carries the features and kerning groups) and `build()`**: runs `fontmake -m sources/Sisifo.designspace -o variable --output-path fonts/variable/Sisifo[wght].ttf` through `subprocess` with an argv list; raises on a non-zero exit with fontmake's output.
- [ ] **Step 4: Run it; expected PASS. Commit "Sisifo: variable build, wght 300-700".**

### Task 4: Gate against Ortica Linear

**Files:**
- Create: `sisifo/tools/gate.py`, `sisifo/tests/test_gate.py`

**Interfaces:**
- Consumes: `fonts/variable/Sisifo[wght].ttf` (Task 3); originals `ortica-src/fonts/OrticaLinear-*.otf`.
- Produces: `gate.run() -> dict` (per check: pass/fail and details), CLI `python tools/gate.py` writes `build/gate.json`, prints a table, exits 1 on any failure.

- [ ] **Step 1: Write the failing tests in `tests/test_gate.py`**

```python
@pytest.mark.parametrize("w,style", [(300, "Light"), (400, "Regular"), (700, "Bold")])
def test_instances_match_original(w, style):
    r = gate.compare_outlines(w, style)          # per glyph: advance equal; area within 1 %; bounds within 3 units
    assert r["mismatches"] == [] , r["mismatches"][:10]   # zero.dnom@400 is excluded and listed in r["exempt"]

def test_no_outline_errors():
    assert gate.outline_errors() == []           # open contours, empty contours, contours with < 3 points, NaN

def test_intermediate_instances_clean():
    for w in (350, 550, 650):
        assert gate.outline_errors(w) == [] and gate.monotonic_bounds(w)   # each glyph's bounds lie between its neighbours'

def test_kerning_widths_match_original():
    assert gate.shaped_widths_diff(["AVATAR", "To Ty Yo", "Wave LT"], weights=(300, 400, 700)) <= 0.5   # px at 100 px, HarfBuzz via the browser

def test_app_characters_match_original():
    assert gate.compare_outlines(400, "Regular", chars="0123456789.,×·–’«»àèéìòùÀÈÉÌÒÙ")["mismatches"] == []
```

- [ ] **Step 2: Run; expected FAIL.**
- [ ] **Step 3: Implement `gate.py`**: instances with `fontTools.varLib.instancer.instantiateVariableFont`; areas with `AreaPen`, bounds with `BoundsPen` (the 1 % / 3-unit tolerance absorbs fontmake's cubic-to-quadratic conversion, about 1 unit); shaped widths with the kept-open headless browser: one page with both fonts as `@font-face`, `canvas.measureText` per string, weight set by `font-variation-settings`; exemption list `{("zero.dnom", 400): "empty upstream; drawn in Task 2"}`.
- [ ] **Step 4: Run `python -m pytest -v` (all tasks) and `python tools/gate.py` bare; expected all PASS and exit 0.**
- [ ] **Step 5: Commit "Sisifo: gate against Ortica Linear".**

### Task 5: Specimen and owner checkpoint

**Files:**
- Create: `sisifo/tools/specimen.py`, `sisifo/build/specimen.png`

- [ ] **Step 1: Render Sisifo at 300/400/500/600/700 and Ortica Linear 300/400/700 side by side (display line, the set number "62.5 kg × 5", a 13 px paragraph), at the 6T's density (2.8125).**
- [ ] **Step 2: Check by eye that 300/400/700 look identical to Ortica and that 500/600 sit between; record in `FONTLOG.md`.**
- [ ] **Step 3: Commit "Sisifo: stage 1 specimen". Report to the owner: gate table, specimen, and the question whether to create `github.com/haziaferi/sisifo` and push.**
