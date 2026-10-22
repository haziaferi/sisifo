# Sisifo Stage 2: Figures Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Give Sisifo tabular lining figures (`zero.tf` … `nine.tf`) and a `tnum` feature, so a set weight such as 62.5 keeps its width while it changes; leave the default (proportional) digits exactly as Ortica draws them.

**Architecture:** Each `.tf` glyph is a single component of its base digit, shifted to sit in one common advance per master. Components keep the masters compatible and let the stage 3 carve reach the tabular digits without extra work. The `tnum` lookup goes in the Regular master's features, which the designspace copies.

**Tech Stack:** as stage 1 (fontmake 3.12.2, ufoLib2, fontTools, pytest, the kept-open headless browser).

**Spec:** `docs/design.md`, goal 4 and stage 2.

## Global Constraints

- Default digits, punctuation and spacing unchanged: the stage 1 gate (394 glyphs at 300/400/700) must still pass.
- Tabular advance per master: `W = max digit ink width + 2 × median over digits of min(left, right sidebearing)`, rounded to an integer. Light 611, Regular 626, Bold 656 by the measured sources.
- Each digit keeps its own left/right balance inside `W`: `new left = round((W − ink) × L / (L + R))`.
- Component offsets are integers (TrueType composites).
- `tnum` maps the ten lining digits only. Oldstyle (`.osf`) digits stay proportional: with `onum` and `tnum` both on, `onum` wins. This is noted in FONTLOG, not fixed.

## Review Focus

1. **Every instance, not only the masters**: a person setting weight 550 expects ten equal digits. Test `test_tabular_one_width_per_instance` (300, 400, 550, 700).
2. **The feature works through a real shaper**: equal advances in the file prove nothing if `tnum` doesn't fire. Test `test_tnum_shaped_equal` (HarfBuzz in the browser, `font-feature-settings: "tnum"`).
3. **No digit overhangs its cell**: the widest digit at each master must keep both sidebearings ≥ 0. Test `test_tf_ink_inside_advance`.
4. **Rerunning the tool**: running `figures.py` twice must not add a second set of glyphs or a second feature block. Test `test_apply_is_idempotent`.
5. **Glyph set**: the build exports Ortica's glyphs plus exactly the ten `.tf` glyphs. Test `test_same_glyph_set_as_original` (updated).

---

### Task 1: Tabular glyphs and the feature

**Files:** Create `tools/figures.py`, `tests/test_figures.py`; modify `sources/Sisifo-*.ufo`.

**Interfaces (produces):** `figures.DIGITS: list[str]`; `figures.tabular_width(font) -> int`; `figures.apply(ufo_path) -> int` (returns W).

- [ ] Write failing tests: `test_tabular_width_rule`, `test_tf_is_shifted_digit` (one component, base digit, offset by the rule), `test_tf_ink_inside_advance`, `test_tnum_feature_maps_all_ten`, `test_apply_is_idempotent`.
- [ ] Run `python -m pytest tests/test_figures.py -v`; expected FAIL (no module `figures`).
- [ ] Implement, run it on the three sources, add the `.tf` names to `public.glyphOrder`.
- [ ] Run the tests; expected PASS. Commit "Sisifo: tabular figures and tnum".

### Task 2: Gate, measure, specimen

**Files:** Modify `tools/gate.py`, `tests/test_gate.py`, `tools/specimen.py`, `FONTLOG.md`.

**Interfaces (produces):** `gate.tabular_widths(weights) -> dict[int, set]`; `gate.tnum_shaped_diff(weights) -> float` (largest width difference in px at 100 px between "0000" … "9999").

- [ ] Write failing tests `test_tabular_one_width_per_instance`, `test_tnum_shaped_equal` (≤ 0.01 px); update `test_same_glyph_set_as_original` to expect the ten `.tf` glyphs.
- [ ] Implement, add both to `run()` / `main()`; rebuild; run `python tools/gate.py` bare: expected `GATE PASS`.
- [ ] Re-measure the numbers axis with `tools/measure.py`'s `measure()` on the variable font; record before (Ortica 0.639) and after in FONTLOG.
- [ ] Specimen: add a right-aligned column of set weights, proportional against `tnum`; send to the owner. Commit "Sisifo: stage 2 gate, numbers, specimen".
