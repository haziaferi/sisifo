# Sisifo Stage 5: Obliques Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Obliques of the release (GLZ) at every weight and carve. Three slant angles are scored on the design axes; two ways of delivering them are scored on the packaging axes. The owner chooses on the phone.

**Architecture:** `tools/oblique.py` slants the six generated masters (wght × CARV) at build time, after the carve and `ss01`. Either it builds them as a second file, or it adds them as the far end of a `slnt` axis in the one file. The slant is a shear about the baseline, re-centred so each glyph keeps its place in its advance, so spacing and kerning carry over. Components move with their offset's height, so accents stay over their letters.

**Spec:** `docs/design.md` goal 3 (scripted obliques) and stage 5.

## Owner's decisions (2026-10-23)

- **Angles:** 7°, 9° and 12°, all scored.
- **Delivery, both scored:**
  - a second file, `Sisifo-Italic[CARV,wght].ttf`;
  - a `slnt` axis inside one file.
- **Shape axes:** the nine from the carve rounds, plus a blind "oblique quality" axis. The judges also rate each version's fit for three uses, emphasis inside 13 px text, whole lines of notes, and display accents, which settles where the obliques go.
- **Delivery axes:** the five from the GL packaging question: app customization, app weight, app simplicity, licence and credits, build and upkeep.
- **Defaults stated to the owner:** the obliques keep the carve axis, and the `ss01` capitals slant too.

## Global Constraints

- **Slant:** x' = x + y·tan θ − tan θ · xHeight/2. Every glyph is re-centred about half the x-height, so a slanted letter sits over its upright advance. Advances and kerning are unchanged.
- **Composites:** a component's offset gains dy·tan θ. Its base is already slanted and re-centred, so it isn't shifted twice.
- **Metadata:** italic angle −θ in the fonts (OS/2 and post); style names "Italic" for the second file.
- **Gate for obliques:**
  - **Outlines.** At CARV 0, each glyph equals Ortica's original slanted the same way: advance equal, area within 1 % (a shear keeps area), bounds within 3 units.
  - **Shared checks.** Every other gate check applies: outline errors, direction flips, topology and tabular widths.

## Review Focus

1. **Accents on slanted capitals:** À's grave must still sit over the slanted A. Test: `test_accents_follow_slant`.
2. **The slnt axis at full slant equals the second file,** glyph for glyph. Test: `test_slnt_end_is_the_italic`.
3. **Default text is unchanged:** the upright release is untouched, and `slnt` 0 is it.
4. **Tabular figures stay tabular in the oblique:** covered by the gate's tnum check.
5. **Light obliques at 13 px stay sharp:** the "notes" use is scored by the panel at that size.
