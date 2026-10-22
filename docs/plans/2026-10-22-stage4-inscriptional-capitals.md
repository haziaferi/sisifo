# Sisifo Stage 4: Inscriptional Capitals (ss01) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** An `ss01` stylistic set of capitals with Roman-inscription proportions, used for titles only. Build it two ways, carve both with the release carve (GL), and score them. The owner chooses on the phone.

**Architecture:** `tools/ss01.py` adds `A.ss01` … `Z.ss01` to the three masters in memory at build time, never in `sources/`, the same way the carve works. It also adds `.ss01` copies of every accented capital (the same components, with the base swapped) and an `ss01` feature. `carve.make_masters` applies it for variants that name an `ss01` source, and the carve then cuts the new capitals with the chiselled rules, because Angular has no inscriptional capitals.

**Spec:** `docs/design.md`, goal 2 (inscriptional capitals) and stage 4.

## Owner's decisions (2026-10-22)

- Both sources, scored:
  - **P, proportions only.** Sisifo's own capitals, re-proportioned to Cinzel's measured widths.
  - **Z, Cinzel's capitals fitted.** Cinzel's outlines, matched to Sisifo's stems, cap height and weights.
- Both carved. The carve is the release carve, GL, with rules for these glyphs.
- Axes: the nine from stage 3's round 2, plus a blind "inscriptional character" axis (does it read as Roman lettering cut in stone?).
- Default (stated to the owner): all of A–Z, with the accented capitals following automatically.

## Measured (Cinzel 400 against Sisifo Regular, ink width over cap height)

- **Narrower in Cinzel:** E 0.76, F 0.69, I 0.72, J 0.76, L 0.77, S 0.73, B 0.81, P 0.83, K 0.84, X 0.85, A 0.89, H 0.88, T 0.88.
- **Wider in Cinzel:** C 1.04, D 1.04, G 1.05, M 1.02, O 1.02. Q measures 1.76, almost all of it the long Roman tail.

## Global Constraints

- **P:**
  - **The stretch.** Each capital changes its ink width to Sisifo's width times the measured ratio. The change happens in a band across the letter, and points outside the band keep their place, so stems stay as thick as they were. The band is set per letter: between the stems for H, N and U; across the arms for E, F and L; the middle for round letters.
  - **Exceptions.** I and J keep their width: their difference is serif length, and a stretch would squeeze the stem. Q stretches its bowl as O does; its tail is unchanged.
  - **Guards.** No point may cross another (the band's compression factor stays above 0.4). Left sidebearings are kept, and the advance follows the new ink.
- **Z:**
  - **Weights.** Cinzel's instances are matched by stem: Sisifo's `I` stem per master sets the Cinzel weight, and Light is extrapolated linearly from Cinzel 400 and 900.
  - **Outline.** Quadratics are made cubic exactly, and the outline is scaled to Sisifo's cap height. Cinzel's sidebearings are kept.
  - **Licence.** `Copyright 2020 The Cinzel Project Authors (https://github.com/NDISCOVER/Cinzel)` is added to `OFL.txt` and to the font's copyright. Cinzel declares no Reserved Font Name.
- **Kerning:** P's capitals join their base letter's kerning groups. Z gets no kerning; that's noted as a known gap.
- **Unchanged:** default glyphs, so the gate at CARV 0 still matches Ortica's 394 glyphs.
- **The release** (`fonts/variable/Sisifo[CARV,wght].ttf`) changes only when the owner picks one.

## Review Focus

1. **Accented capitals in titles** ("MOBILITÀ", "PERCHÉ"): with ss01 on, À and É must change with A and E. Test: `test_accented_capitals_follow`.
2. **The masters stay compatible** for every new glyph across all six masters, including Z's extrapolated Light. Test: `test_ss01_compatible`.
3. **Stems keep their thickness under P's stretch:** H's left stem is equally thick before and after. Test: `test_p_keeps_stems`.
4. **Carving the new capitals keeps their topology:** this is covered by the gate's topology check on every glyph.
5. **Default text is untouched:** `ss01` is opt-in, and the CARV 0 gate still holds.

### Task 1: `tools/ss01.py` and tests

**Interfaces:**
- `ss01.RATIOS: dict[str, float]` (measured);
- `ss01.add(fonts: dict[str, Font], kind: str) -> list[str]`, which returns the new glyph names;
- `ss01.feature(fonts, names)`.

### Task 2: Build, gate, specimens, panel, page

- Variants:
  - `GLP` and `GLZ`: GL plus `ss01` source P or Z.
  - Specimens set titles with `font-feature-settings: 'ss01'`.
- Panel: the four stage 3 judged axes plus inscription. The references are plain and Cinzel (named only in the owner's page).
