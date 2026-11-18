"""Hoard layers.

hoard-back.png  480x92  the main pile: peak (dragon plateau) on the right, a second heap on the left,
                        a shallower valley behind the chat column. Translated up as context fills.
hoard-front.png 480x44  a low full-width dune layer in front; gives the thin layer at 0% and the
                        front ridge later. Translated up less than the back pile.
Both are single images, pushed down from their 100% position by a per-bucket translateY
(OFF_BACK, OFF_FRONT below; src/build_theme.py uses the same table).

hoard-back-tile.png  64x92  seamless repeat-x extensions for panels wider than the 480 px layers. Same top
hoard-front-tile.png 64x44  and offsets as their layer; shown only OUTSIDE the layer's 480 px span (left and
                            right of it). A calm, nearly flat pile of loose coins at the level the layers'
                            outer EDGE columns blend into, so the hoard runs on to the panel edges.
The layers' outer EDGE columns (x 0-15 and 464-479) are regenerated with a surface that eases from the layer's
own contour into the tile level, and the same coin texture as the tile; x 16-463 stay pixel-identical.
The back tile stays at row <= 8 everywhere: dragon.png's gold bed is opaque down to hoard-back row 7 and its
frame reaches canvas x 483, so anything lower would open a gap under the bed at the layer's right edge.
"""
import json
import os

import numpy as np
from PIL import Image

from common import (
    ARK,
    ARK_D,
    BAYER4,
    EMBER,
    EMBER_D,
    GOLD,
    OUT,
    hexrgb,
    save_indexed,
    upscale,
)

W = 480
PAL = ["#000000", GOLD["g00"], GOLD["g0"], GOLD["g05"], GOLD["g1"], GOLD["g15"], GOLD["g2"], GOLD["g3"], GOLD["g4"],
       EMBER, EMBER_D, ARK, ARK_D, "#0b0c0f", "#5c6b80", "#2a0c08"]
# ramp indices into PAL
R = [1, 2, 3, 4, 5, 6, 7, 8]
I_EMB, I_EMBD, I_ARK, I_ARKD, I_OUT, I_STEEL, I_RED = 9, 10, 11, 12, 13, 14, 15

# Geometry in native canvas px (480x270). offsets are translateY added to the 100% position.
BACK_H, FRONT_H = 92, 44
BACK_TOP_100, FRONT_TOP_100 = 146, 226
OFF_BACK = [round(106 * (1 - k / 10)) for k in range(11)]
OFF_FRONT = [round(36 * (1 - k / 10)) for k in range(11)]

# Extension tiles (repeat-x outside the 480 px span) and the layer edge zones that blend into them.
TILE_W = 64          # 64 px period: 256 CSS px at 4x, so the coin field does not read as a short repeat
EDGE = 16            # x 0-15 and 464-479 of each layer ease into the tile
# Tile surfaces: a base row plus low mounds (centre x, half width, rows). Back: at the dragon plateau's height,
# never below row 8, because dragon.png's bed is opaque down to hoard-back row 7 for canvas x 324-483
# (4 px past the layer), so a lower tile would leave a gap under the bed.
BACK_TILE_BASE, BACK_TILE_MOUNDS = 7, [(6, 7, 1.6), (27, 10, 1.1), (50, 6, 2.2), (39, 4, -0.8)]
FRONT_TILE_BASE, FRONT_TILE_MOUNDS = 5, [(12, 8, 1.4), (35, 6, 1.9), (54, 9, 1.0)]
BACK_TILE_HI = 8     # lowest allowed back tile row (dragon bed support)


def smooth_curve(points, n, seed, amp):
    xs = np.array([p[0] for p in points], float)
    ys = np.array([p[1] for p in points], float)
    x = np.arange(n)
    # Catmull-Rom-ish via cumulative cosine interpolation
    out = np.zeros(n)
    for i in range(len(xs) - 1):
        m = (x >= xs[i]) & (x <= xs[i + 1])
        t = (x[m] - xs[i]) / (xs[i + 1] - xs[i])
        t = (1 - np.cos(t * np.pi)) / 2
        out[m] = ys[i] * (1 - t) + ys[i + 1] * t
    r = np.random.default_rng(seed)
    bumps = np.zeros(n)
    k = 0
    while k < n:
        L = int(r.integers(3, 9))
        bumps[k:k + L] = r.choice([-1, 0, 0, 1]) * (1 if amp else 0)
        k += L
    return np.round(out + bumps).astype(int)


CHAT_X0, CHAT_X1 = 136, 344   # chat column in native px; gold here is kept dark for text


def dim_profile(x):
    """0 in the gutters, 3 steps darker behind the chat column, 24px dithered ramps."""
    if CHAT_X0 <= x <= CHAT_X1:
        return 3.0
    if CHAT_X0 - 24 <= x < CHAT_X0:
        return 3.0 * (x - (CHAT_X0 - 24)) / 24
    if CHAT_X1 < x <= CHAT_X1 + 24:
        return 3.0 * ((CHAT_X1 + 24) - x) / 24
    return 0.0


def build(h, surf, seed, items, density=0.62, wrap=False, n_glints=60):
    """Paint a pile. surf: top row per column. wrap=True makes it seamless in x (tiles): coins and glints wrap
    around, no chat-column dimming. The non-wrap path draws exactly what v2 drew (same RNG sequence)."""
    rng = np.random.default_rng(seed)
    w = len(surf)
    img = np.zeros((h, w), np.uint8)
    # local surface (min over a window) for depth shading
    if wrap:
        ls = np.array([surf[np.arange(x - 4, x + 5) % w].min() for x in range(w)])
    else:
        ls = np.array([surf[max(0, x - 4):x + 5].min() for x in range(w)])
    depth = np.zeros((h, w))
    for x in range(w):
        depth[:, x] = np.arange(h) - ls[x]

    def dim(x):
        return 0.0 if wrap else dim_profile(x)

    def base_for(y, x):
        d = depth[y, x]
        # the visible face of a pile is lit from above: crest brightest, gentle fall-off
        if d < 2:
            b = 5
        elif d < 6:
            b = 4
        elif d < 20:
            b = 3
        elif d < 40:
            b = 2
        else:
            b = 1
        dm = dim(x)
        b -= int(dm) + (1 if (dm % 1) > BAYER4[y % 4, x % 4] else 0)
        return b

    # gaps between coins: two steps darker than the coins around them
    for x in range(w):
        for y in range(max(0, surf[x]), h):
            img[y, x] = R[max(0, min(7, base_for(y, x) - 3))]
    # coins: 4x3 round faces seen at an angle, staggered, drawn top to bottom
    #   . H H .
    #   M H M D
    #   . D D .
    coins = []
    for y in range(-2, h, 2):
        off = (y // 2) % 2 * 2
        for x in range((0 if wrap else -4) + off, w, 4):
            if rng.random() < density:
                coins.append((y + int(rng.integers(-1, 1)), x + int(rng.integers(-1, 2))))
    coins.sort()
    for (cy, cx) in coins:
        xc = (cx + 1) % w if wrap else min(max(cx + 1, 0), w - 1)
        if cy < surf[xc] - 2 or cy >= h:
            continue
        if cy < surf[xc] - 1 and rng.random() < 0.6:
            continue
        b = base_for(max(cy, 0), xc) - (1 if rng.random() < 0.25 else 0)
        shape = [[None, b + 1, b + 1, None],
                 [b, b + 1, b, b - 1],
                 [None, b - 1, b - 1, None]]
        if rng.random() < 0.12 and depth[max(cy, 0), xc] < 10:
            shape[0][1] = b + 2
        for j in range(3):
            for i in range(4):
                v = shape[j][i]
                yy_, xx_ = cy + j, cx + i
                if wrap:
                    xx_ %= w
                if v is None or not (0 <= yy_ < h and 0 <= xx_ < w):
                    continue
                if yy_ >= surf[xx_] - 2:
                    img[yy_, xx_] = R[max(0, min(7, v))]
    # glints (cross sparkles) near the surface, in the gutters only
    for _ in range(n_glints):
        x = int(rng.integers(0, w)) if wrap else int(rng.integers(2, w - 2))
        if dim(x) > 0.3:
            continue
        y = int(surf[x] + rng.integers(0, 9))
        if 1 <= y < h - 1 and img[y, x]:
            img[y, x] = R[7]
            if rng.random() < 0.4:
                for (dx, dy) in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                    if img[y + dy, (x + dx) % w]:
                        img[y + dy, (x + dx) % w] = R[6]
    for fn, *args in items:
        fn(img, surf, *args)
    if wrap:
        return img
    # hard cap behind the chat column: nothing brighter than g1 (#7a5418) under text; in practice
    # ~97% of the band is g00/g0 and g1 survives only on a few crest coins that keep the silhouette
    for x in range(CHAT_X0 - 4, CHAT_X1 + 5):
        col = img[:, x]
        col[(col > R[3]) & (col <= R[7])] = R[3]
    return img


def stamp(img, x0, y0, rows, key, surf=None):
    for j, row in enumerate(rows):
        for i, c in enumerate(row):
            if c == ".":
                continue
            y, x = y0 + j, x0 + i
            if 0 <= y < img.shape[0] and 0 <= x < img.shape[1]:
                img[y, x] = key[c]


KEY = {"o": R[0], "0": R[0], "1": R[1], "2": R[2], "3": R[3], "4": R[4], "5": R[5], "6": R[6], "7": R[7],
       "e": I_EMB, "d": I_EMBD, "a": I_ARK, "b": I_ARKD, "s": I_STEEL, "r": I_RED, "x": I_OUT}


def goblet(img, surf, x, sink=2):
    rows = [".ooooooo.",
            "o7766654o",
            "o5666543o",
            ".o55443o.",
            "..o544o..",
            "...o5o...",
            "...o4o...",
            "..o654o..",
            ".o66543o.",
            ".ooooooo."]
    stamp(img, x - 4, surf[x] - 10 + sink, rows, KEY)


def gem(img, surf, x, depth, kind="e"):
    rows = {"e": [".o.", "oeo", "e7d", "odo", ".o."], "a": [".o.", "obo", "a7b", "obo", ".o."]}[kind]
    stamp(img, x - 1, surf[x] + depth - 1, rows, KEY)


def crown(img, surf, x, sink=1):
    rows = [".7...7...7.",
            "o6o.o6o.o6o",
            "o65o656o56o",
            "o6e66a66e6o",
            "o555555544o",
            ".ooooooooo."]
    stamp(img, x - 5, surf[x] - 6 + sink, rows, KEY)


def sword(img, surf, x, sink=0):
    rows = ["..o7o..",
            "..o5o..",
            "..oro..",
            "..oro..",
            "oo676oo",
            "o65554o",
            "oo0s0oo",
            "..oso..",
            "..oso.."]
    stamp(img, x - 3, surf[x] - 8 + sink, rows, KEY)


def chest(img, surf, x, sink=3):
    rows = [".oooooooooooo.",
            "o333363333333o",
            "o366666666663o",
            "o222242222222o",
            "oooooo66oooooo",
            "o2222o77o2222o",
            "o2222o44o2222o",
            "o366666666663o",
            "o222242222222o",
            "oooooooooooooo"]
    stamp(img, x - 7, surf[x] - 10 + sink, rows, KEY)


def shield(img, surf, x):
    rows = [".xxxxxxx.",
            "x6rrrrr4x",
            "xr66e66rx",
            "xrr666rrx",
            ".xrr6rrx.",
            "..xr6rx..",
            "...xxx..."]
    stamp(img, x - 4, surf[x] - 4, rows, KEY)


def arkenstone(img, surf, x, depth):
    # soft pale glow (dithered) then the stone, half buried
    cy = surf[x] + depth
    for y in range(cy - 6, cy + 6):
        for xx in range(x - 8, x + 9):
            if 0 <= y < img.shape[0] and img[y, xx]:
                d = np.hypot(xx - x, (y - cy) * 1.3)
                if d < 7 and BAYER4[y % 4, xx % 4] < (1 - d / 7) * 0.8:
                    img[y, xx] = I_ARKD
    rows = ["..a..",
            ".aab.",
            "aa7ab",
            ".bab.",
            "..b.."]
    stamp(img, x - 2, cy - 2, rows, {"a": I_ARK, "b": I_ARKD, "7": R[7]})
    img[cy - 4, x] = R[7]
    img[cy - 3, x] = I_ARK


ITEM_HALF_W = {"goblet": 4, "gem": 1, "crown": 5, "sword": 3, "chest": 7, "shield": 4, "arkenstone": 8}


def run_bumps(n, seed, values=(-1, 0, 0, 1), lo=3, hi=9):
    """Runs of 3-8 px at -1/0/+1, the same small surface bumps smooth_curve() adds."""
    r = np.random.default_rng(seed)
    out = np.zeros(n)
    k = 0
    while k < n:
        L = int(r.integers(lo, hi))
        out[k:k + L] = r.choice(values)
        k += L
    return out


def tile_surface(base, mounds, w=TILE_W):
    """A calm, periodic pile top: flat at row `base` with a few low, rounded coin mounds
    (centre x, half width, height in rows; negative height = shallow dip) that wrap around the tile edges."""
    x = np.arange(w)
    s = np.full(w, float(base))
    for cx, half, hgt in mounds:
        d = (x - cx + w / 2) % w - w / 2
        s -= hgt * np.clip(1 - (d / half) ** 2, 0, 1)
    return np.round(s).astype(int)


def ease_edges(s, level, seed):
    """Layer surface with its outer EDGE columns eased into the tile: flat at the tile's mean level at the
    outer edge, meeting the layer's own contour and slope at the inner end (cubic Hermite), with tile-sized
    bumps that fade out inward. Columns EDGE..W-EDGE-1 are returned unchanged."""
    out = s.astype(float).copy()
    bumps = run_bumps(2 * EDGE, seed)
    for side in (0, 1):
        inner = EDGE if side == 0 else W - 1 - EDGE          # first unchanged column
        step = 1 if side == 0 else -1                        # direction from the edge inward
        m1 = (s[inner + 6 * step] - s[inner]) / 6.0          # inward slope of the layer's contour
        for d in range(EDGE):                                # d = distance from the outer edge
            x = d if side == 0 else W - 1 - d
            u = d / EDGE
            h00, h01, h11 = 2 * u ** 3 - 3 * u ** 2 + 1, -2 * u ** 3 + 3 * u ** 2, u ** 3 - u ** 2
            y = h00 * level + h01 * s[inner] + h11 * EDGE * m1
            out[x] = y + (1 - u) ** 2 * bumps[side * EDGE + d]
    return np.round(out).astype(int)


def with_edges(img, h, surf, s_edge, seed, items, density=0.62):
    """Replace the layer's EDGE columns by a pile painted on the eased surface, then stamp again any item
    that reaches into them (only if its anchor height did not change, so nothing is drawn twice)."""
    zone = build(h, s_edge, seed, [], density)
    out = img.copy()
    out[:, :EDGE] = zone[:, :EDGE]
    out[:, W - EDGE:] = zone[:, W - EDGE:]
    for fn, x, *args in items:
        hw = ITEM_HALF_W[fn.__name__]
        if x - hw < EDGE or x + hw >= W - EDGE:
            inside = x - hw >= EDGE and x + hw < W - EDGE
            crosses = (x - hw < EDGE <= x + hw) or (x - hw < W - EDGE <= x + hw)
            assert not crosses or s_edge[x] == surf[x], (fn.__name__, x, "anchor moved on a zone boundary")
            if not inside:
                fn(out, s_edge, x, *args)
    return out


def main():
    # back pile silhouette (row of the top surface per column)
    # At 100% (back top at y=146): left heap ~41% of canvas height, valley behind the chat ~33%,
    # dragon plateau 45%. The plateau starts at x~316 so the dragon (left 324) always lies on gold.
    back_pts = [(0, 26), (22, 18), (46, 13), (70, 11), (96, 15), (122, 24), (152, 32), (186, 36), (216, 33),
                (246, 26), (276, 17), (298, 10), (316, 5), (342, 3), (370, 2), (400, 4), (430, 3), (456, 5),
                (479, 8)]
    sb = smooth_curve(back_pts, W, 3, 1)
    front_pts = [(0, 5), (34, 2), (70, 6), (104, 3), (140, 6), (176, 4), (214, 6), (250, 3), (290, 6),
                 (330, 3), (370, 6), (408, 2), (444, 5), (479, 3)]
    sf = smooth_curve(front_pts, W, 4, 1)

    back_items = [
        (arkenstone, 74, 5),
        (goblet, 44), (goblet, 112),
        (crown, 26), (sword, 96),
        (gem, 58, 3, "e"), (gem, 86, 6, "e"), (gem, 130, 4, "a"),
        (goblet, 446), (gem, 470, 3, "e"),
    ]
    front_items = [
        (chest, 62), (goblet, 30), (gem, 52, 6, "e"), (sword, 96), (gem, 108, 3, "a"),
        (goblet, 384), (crown, 420), (gem, 400, 2, "e"), (gem, 452, 3, "a"), (shield, 466),
    ]
    back = build(BACK_H, sb, 11, back_items)
    front = build(FRONT_H, sf, 12, front_items)

    # extension tiles: loose coins and a few glints. No trinket: in a 64 px repeat it recurs every 256 CSS px
    # and reads as a pattern; the trinkets stay in the layers.
    tb = tile_surface(BACK_TILE_BASE, BACK_TILE_MOUNDS)
    tf = tile_surface(FRONT_TILE_BASE, FRONT_TILE_MOUNDS)
    assert tb.max() <= BACK_TILE_HI
    back_tile = build(BACK_H, tb, 31, [], wrap=True, n_glints=4)
    front_tile = build(FRONT_H, tf, 32, [], wrap=True, n_glints=3)

    # layer edges eased into the tiles (x 16-463 unchanged); the back's right edge stays <= row 8 (dragon bed)
    sb2 = ease_edges(sb, tb.mean(), 41)
    sb2[W - EDGE:] = np.minimum(sb2[W - EDGE:], BACK_TILE_HI)
    sf2 = ease_edges(sf, tf.mean(), 42)
    back = with_edges(back, BACK_H, sb, sb2, 51, back_items)
    front = with_edges(front, FRONT_H, sf, sf2, 52, front_items)

    files = [("hoard-back.png", back), ("hoard-front.png", front),
             ("hoard-back-tile.png", back_tile), ("hoard-front-tile.png", front_tile)]
    for name, arr in files:
        n = save_indexed(os.path.join(OUT, name), arr, PAL, 0)
        print(name, arr.shape[1], "x", arr.shape[0], n, "bytes")
    geom = {"back_top_100": BACK_TOP_100, "front_top_100": FRONT_TOP_100,
            "off_back": OFF_BACK, "off_front": OFF_FRONT,
            "back_surface": sb2.tolist(), "front_surface": sf2.tolist(),
            "tile_w": TILE_W, "edge": EDGE,
            "back_tile_surface": tb.tolist(), "front_tile_surface": tf.tolist(),
            "tile_note": "hoard-*-tile.png repeat-x outside the layer's 480 px span only, same top and offsets "
                         "as their layer; *_surface = top row per column"}
    with open(os.path.join(OUT, "src", "_geom.json"), "w") as f:
        json.dump(geom, f)
    upscale(os.path.join(OUT, "hoard-back.png"), os.path.join(OUT, "src", "_hoard_back_x4.png"), 4, "#101215")
    upscale(os.path.join(OUT, "hoard-front.png"), os.path.join(OUT, "src", "_hoard_front_x4.png"), 4, "#101215")
    review_sheet(back, front, back_tile, front_tile)


def review_sheet(back, front, back_tile, front_tile, phases=(0, 23, 47)):
    """src/_hoard_tiles_x4.png: each layer's left and right edge (48 px) with 80 px of tile beside it, at three
    tile phases, 4x on dark stone."""
    lut = np.array([hexrgb(c) for c in PAL], np.uint8)
    lut[0] = hexrgb("#101215")
    rows = []
    for layer, tile in ((back, back_tile), (front, front_tile)):
        for p in phases:
            ext = np.tile(tile, (1, 4))[:, p:p + 80]
            rows.append(np.hstack([ext, layer[:, :48], np.zeros((layer.shape[0], 8), np.uint8),
                                   layer[:, W - 48:], ext]))
            rows.append(np.zeros((4, rows[-1].shape[1]), np.uint8))
    sheet = lut[np.vstack(rows)]
    Image.fromarray(sheet).resize((sheet.shape[1] * 4, sheet.shape[0] * 4), Image.NEAREST).save(
        os.path.join(OUT, "src", "_hoard_tiles_x4.png"))


if __name__ == "__main__":
    main()
