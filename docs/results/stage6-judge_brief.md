You are one of three independent judges scoring typefaces for SisyphusFit, an offline Android workout tracker. Its
voice is calm and judgement-free ("one must imagine Sisyphus happy"): it relies on habit, never shows failure, and
should feel grounded, like stone, engraving, slight imperfection, but never aggressive.

Judge blind. Look ONLY at the PNG files in `build/signoff/blind/` (open each with the Read tool). Do not open any
other file in the repository (not `named/`, `html/`, `blind_codes.json`, scores, docs or tools): the scoring must not
know which face or treatment is which.

## K1 to K8: specimen pages, one typeface each
Every page sets the same text at a phone's real size: titles, bold titles, titles in capitals, set numbers, 13 px
text, italic emphasis and notes, italic display lines, an upright line for comparison. Score each page 0 to 4
(integers; 2 is acceptable, 4 excellent) on:
- `stone`: the face as a whole reads as cut or carved stone lettering: grounded, solid, lapidary.
- `carving`: at display sizes (titles, set numbers), the letterforms themselves show chiselled cuts: crisp facets and
  flat-cut curves rather than smooth ink. A smooth face scores low here however good it is otherwise.
- `calm`: grounded and quiet with presence; even rhythm; no aggression, no shouting, no nervous texture.
- `personality`: a distinct, memorable character that still suits the app; not generic.
- `inscription`: the titles in capitals read like Roman inscriptional capitals (proportions, stroke, dignity).
- `oblique`: the italic lines (emphasis, notes, display) make a good oblique: a consistent slant, even colour, clearly
  distinct from the upright, not a crude mechanical skew, readable as 13 px emphasis.
- `small`: the 13 px lines read easily and comfortably at phone size: sharp, open, even, nothing clotting.

## M1 to M10: phone screens (1080 x 2340), the same app screens in one typeface with different treatments
Score each screen 0 to 4 on:
- `stone`: the titles and the big numbers read as carved, cut in stone, at their display sizes.
- `hierarchy`: the text roles (screen title, headings, labels, body, set numbers) are distinct at a glance, and the
  screen stays calm and orderly rather than busy or shouting.

## Output
Write one JSON file, `build/signoff/judge_N.json` (N is given below), shaped exactly like:
{"K1": {"stone": 3, "stone_why": "one sentence", "carving": 2, "carving_why": "...", "calm": ..., "calm_why": ...,
        "personality": ..., "personality_why": ..., "inscription": ..., "inscription_why": ...,
        "oblique": ..., "oblique_why": ..., "small": ..., "small_why": ...},
 ...,
 "M1": {"stone": 3, "stone_why": "...", "hierarchy": 3, "hierarchy_why": "..."}, ...}
Every K page gets all seven axes, every M screen both. Reasons are one sentence, about what you see. Reply with a
two-line summary when the file is written.
