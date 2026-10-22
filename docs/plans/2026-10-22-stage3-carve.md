# Sisifo Stage 3: Carve Masters Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a `CARV` axis (0–100) to Sisifo. 0 is Ortica Linear unchanged; 100 is carved, with facets and flat-cut bowls. Build a handful of variants, score them on the owner's eight axes and put all of them in front of the owner on the phone.

**Architecture:** `tools/carve.py` turns the three clean sources into six generated masters (wght 300/400/700 × CARV 0/100) under `build/masters/<variant>/`. Every curve is split at the same places in all six. The CARV 0 masters keep the exact curve shape, because the split is de Casteljau. The CARV 100 masters straighten each piece, which gives the facets, and line up the pieces around each smooth extreme, which gives the flats. Variants differ only in their parameters. `sources/` stays as Ortica plus stages 1–2.

**Tech Stack:** as stages 1–2.

**Spec:** `docs/design.md`, goals 1–2, stage 3, "How quality is judged".

## Calibration (measured from Ortica Angular Bold, 2026-10-22)

Angular is fully polygonal: 295 contours, no curves. Its outer `o` is an octagon, with flats centred on the four extremes and one diagonal cut per quarter. The flats sit exactly on the baseline and x-height, where Linear overshoots by 11 units. The median turn at its cuts is 43° (quartiles 35° and 49°). Its counters are drawn differently (corners at extremes). Sisifo uses one rule for all contours, so the variants stay one design.

## Global Constraints

- **Parameters per variant:**
  - `phi`: the half-angle of a flat, in degrees of tangent turn from the extreme (0 means no flats).
  - `theta`: the turn per facet (`None` means the curve between flats stays curved).
- **Variants:**

  | id | `phi` | `theta` | look |
  |---|---|---|---|
  | A | 22.5 | 45 | Angular |
  | B | 12 | 45 | short flats |
  | C | 12 | 25 | fine facets |
  | D | 22.5 | 25 | long flats, fine facets |
  | E | 15 | None | flats only |

- **The structure is decided once, on Regular.**
  - It covers which points are flat extremes and how many pieces each segment gets.
  - Splits are stored as fractions of each segment's total turn, and every weight places them on its own curve.
- **What gets a flat.** An on-curve point gets a flat only when it is smooth, its tangent is within 2° of horizontal or vertical, and both neighbouring segments are curves.
- **Snapping.** Only an overshoot snaps onto a line, and only in the direction the ink runs:
  - a bottom extreme up to 20 units below the baseline or descender;
  - a top extreme up to 20 units above the x-height, cap height or ascender.
  - Two cases this rules out, both found in the build: counters, because Light's `o` stroke is about 28 units thick and its counter's bottom would land on the baseline; and serif undersides, because the `I`'s serif sits 14 units under the cap height.
- **Depth cap, added after the first build.** No facet chord, and no unsnapped flat, cuts deeper than half the master's thin stroke (the top of the `o`: Light 28, Regular 32, Bold 37 units). It is checked at every weight. Large bowls therefore get more facets than small ones. Without the cap, `OE`'s long diagonal cut through its thin top stroke.
- **Hidden pieces keep their curve.** A piece with ink on both sides (inside another contour of the glyph) isn't straightened. Ortica keeps overlapping contours, and straightening such a piece would pull it out of the shape it overlaps: `m`'s arch came loose from its stem this way.
- **Unchanged at CARV 100:** advance widths, kerning and components.
- **The file:**
  - `fonts/variable/Sisifo[CARV,wght].ttf`;
  - `CARV` runs 0 to 100, default 0;
  - the named instances are Light to Bold at CARV 0;
  - target ≤ 400 KB.
- **Every stage 1–2 gate still holds at CARV 0.**

## Review Focus

1. **Intermediate carve** (CARV 50 at 550): a person sliding the size mapping expects a clean half-carved outline. Test: `test_no_outline_errors_carved` covers CARV 50 and 100 at 300, 550 and 700.
2. **Counters and small curves** (the `e` eye, `a` bowl joins, the `g` ear, `@`): short curves must not collapse or turn inside out. Test: `test_no_direction_flips_carved` sweeps CARV 0, 50 and 100.
3. **Digits stay distinct** (anti-goal): faceted 1/7, 3/8, 0/O, 5/6. The `distinct` sub-score at CARV 100 must be at least 0.9. This is checked in the measure task.
4. **Overshoot snapping:** after snapping, the bottom flat of `o` sits on the baseline at every weight. Test: `test_flats_snap_to_metrics`.
5. **Flats-only variant (E):** the middle pieces keep their curvature, so E is not quietly faceted. Test: `test_flats_only_keeps_curves`.

---

### Task 1: The carve tool

**Files:** Create `tools/carve.py`, `tests/test_carve.py`.

**Interfaces (produces):**
- `carve.VARIANTS: dict[str, dict]`;
- `carve.make_masters(variant: str, out_dir: Path) -> dict[tuple[str, int], Path]`, keyed by (style, carve);
- `carve.plan_glyph(glyphs, caps, metrics, phi, theta) -> list[dict]`, one dict per contour with `flats`, `splits` (turn fractions) and `hidden`. `glyphs`, `caps` and `metrics` are dicts keyed by style.
- Test added during the build: `test_topology_unchanged` (merged contour count equal at CARV 0 and 100) and `test_counters_not_snapped`.

- [ ] Write failing tests:
  - `test_carve0_preserves_shape`: area within 0.1 %, bounds within 1 unit, over o O S a g e zero eight Q at;
  - `test_six_masters_compatible`;
  - `test_facets_straight`;
  - `test_flats_axis_aligned`;
  - `test_flats_snap_to_metrics`;
  - `test_flats_only_keeps_curves`;
  - `test_widths_and_components_unchanged`.
- [ ] Implement; run the tests; commit "Sisifo: carve tool (stage 3)".

### Task 2: Two-axis build and gate

**Files:** Modify `tools/build.py`, `tools/gate.py`, `tests/test_build.py`, `tests/test_gate.py`.

**Interfaces (produces):**
- `build.build(variant="A") -> Path`, with `build/variants/<id>/Sisifo[CARV,wght].ttf` for the others;
- `gate.instance(w, carve=0)`.

- [ ] Write failing tests:
  - `test_axes`: wght 300–700 and CARV 0–100, default 0;
  - `test_no_outline_errors_carved`;
  - `test_no_direction_flips_carved`.
  - Existing gate tests run at CARV 0.
- [ ] Implement; build all five variants; `python tools/gate.py` bare must print `GATE PASS` for each. Commit.

### Task 3: Scores and the owner's review

**Files:** Create `tools/score_carve.py`, `tools/carve_specimen.py`; output `build/carve/`.

- [ ] Specimens per variant at 6T density:
  - display at 22, 28, 34, 44 and 56 px at CARV 100, Regular and Bold;
  - set numbers with `tnum`;
  - 13 px text at CARV 0;
  - blind-coded copies for the judges.
- [ ] Measured axes, on a static instance at wght 400 and CARV 100:
  - harmony, numbers, technical and calm (measured), using `tools/measure.py`;
  - small text unharmed: 13 px at CARV 0 against Ortica;
  - faithful to Ortica, at half weight: glyph pixel IoU at 64 px, widths and kerning against the original.
- [ ] Panel: three blind judges score stone, carving at display size and calm (0–4, with a reason).
  - Axis scores are absolute 0–1, and the mean is over eight axes, with faithful at half weight.
  - A gap under 0.02 is a tie.
- [ ] Artifact page:
  - every variant's 1:1 PNGs (1080 px wide, shown at 384 css px) with its scores;
  - the owner reviews it on the 6T in Waterfox.
- [ ] Commit "Sisifo: stage 3 variants scored".

---

## Round 2 (owner, 2026-10-22): personality

Owner's review of round 1: "even in A, the most angular version, the font still lost personality". Compared with
both Linear and Angular: it lost Linear's curves without gaining Angular's character. Measured cause, on 23 round
glyphs: Angular Bold has 369 cuts at a median turn of 42°; round 1's A has about 500 cuts at 30°, and C about 700 at
23°. The depth cap forced shallow, even cuts. Angular also cuts the two sides of a stroke out of phase (outer `o`: flats at
the extremes; counter: corners there), so its strokes swell and thin; round 1 cuts both sides alike.

Owner's decisions: build both directions and score them together; add a blind "personality" axis; score both Light
treatments.

### Variants

| id | direction | Light |
|---|---|---|
| R | chiselled rules | same carve at every weight |
| RL | chiselled rules | gentler toward Light (Light 0.5, Regular 0.75, Bold 1 of the full carve) |
| G | Angular's own cuts | same |
| GL | Angular's own cuts | gentler toward Light |
| B | round 1's best, carried over as the baseline | same |

- **Chiselled rules** (`carve.py`, new parameters):
  - Cuts turn about 42°, which is Angular's median.
  - **Counters out of phase.** A contour wound against the glyph's main contour gets no flats, and its extremes become corners. On the `o`, the outer octagon has flats at the extremes and the counter octagon has corners there: Angular's arrangement.
  - **Local depth.** Each cut is capped at half the stroke it cuts into, measured at that spot (a ray cast from the cut to the far edge of the ink), not at half the thinnest stroke in the font.
- **Angular's own cuts** (`tools/angular_fit.py`):
  - **Matching.** For each glyph where Angular Bold has the same number of contours as Linear Bold, contours are matched by bounding box. Angular is shifted so its ink centre sits on Linear's, and Linear's advance widths are kept.
  - **Splitting.** Each Angular corner is projected onto the Linear contour, and Linear is split there, keeping their order around the contour.
  - **CARV 100 Bold.** Every point takes Angular's position: inserted points sit on Angular's corners, and Linear's own points land on the nearest Angular edge.
  - **Light and Regular.** They take the same displacement, from each point's CARV 0 position to its carved position.
  - **Fallback.** Glyphs that don't match (contour counts differ, the order breaks, or a stroke cuts through) keep the chiselled rules, and the result lists them.
- **Light strength** is applied per master as C0 + s × (carved − C0). The structure is the same, so this only blends existing outlines.
- **Personality axis**:
  - **Specimens.** The panel also gets Ortica Linear (plain Sisifo) and Ortica Angular Bold (its one weight, used for every line) as unnamed specimens.
  - **The question.** "How much distinct, deliberate character does it have?", scored 0–4.
  - **Weighting.** It counts fully, making nine axes. Faithful keeps half weight.
  - **The references.** They're scored as controls and aren't ranked.
- **Gate:** unchanged. A variant that fails it is reported, not scored.
