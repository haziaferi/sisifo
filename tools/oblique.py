"""Scripted obliques (stage 5): slant a master's outlines, at build time, after the carve and ss01.

x' = x + y tan(theta) - tan(theta) * xHeight / 2: a shear about the baseline, re-centred about half the x-height so a
slanted letter sits over its upright advance; advances and kerning carry over unchanged. A component's offset gains
dy tan(theta): its base glyph is already slanted and re-centred, so it is not shifted twice (accents stay over their
letters). Italic angle -theta goes into the font info.
"""
import math


def shift(font, theta):
    t = math.tan(math.radians(theta))
    return t, t * font.info.xHeight / 2


def slant_font(font, theta):
    t, c = shift(font, theta)
    for g in font:
        for contour in g.contours:
            for p in contour:
                p.x = p.x + p.y * t - c
        for comp in g.components:
            # the component maps its base's points q to M q + o; the base is already slanted (q' = A q - c), so for
            # the whole to be slanted (A (M q + o) - c) the component becomes M' = A M A^-1, o' = M' c + A o - c.
            # For a plain component that is just o + (dy t, 0); a flipped one (caroncomb.case is a flipped
            # circumflex) needs the full form, or its accent lands ~100 units off.
            xx, xy, yx, yy, dx, dy = comp.transformation      # x' = xx x + yx y + dx, y' = xy x + yy y + dy
            nxx, nyx = xx + t * xy, yx + t * yy - t * (xx + t * xy)
            nxy, nyy = xy, yy - t * xy
            ox = nxx * c + dx + t * dy - c
            oy = nxy * c + dy
            comp.transformation = (nxx, nxy, nyx, nyy, ox, oy)
    font.info.italicAngle = -theta
    font.info.postscriptSlantAngle = -theta
    return font


def slant_point(x, y, theta, x_height):
    """The same transform for one point (the gate slants Ortica's originals with it)."""
    t = math.tan(math.radians(theta))
    return x + y * t - t * x_height / 2, y
