"""Throne-alcove indicator props: hourglass (5h limit) and Arkenstone (weekly limit).

hourglass.png   180x20: 15 frames of 12x20, one row.
    0-10   sand left in the top bulb: 100%, 90% ... 0% (frames 8-10 ember sand, <= 20% left)
    11-12  trickle overlay (transparent, falling grains at the neck), CSS adds it on frames 0-9
    13-14  "empty and smoking" loop for 0% (full frames: frame 10 plus smoke wisps)
arkenstone.png  128x16: 8 frames of 16x16, one row.
    0-5    gem brightness for 100, 80, 60, 40, 20, 0 % left (dithered halo shrinks, 0% is grey stone)
    6-7    twinkle overlay (transparent), CSS adds it on frames 0-2

Run:  uv run --with pillow --with numpy --with zopfli python3 src/props.py
Also writes src/_props_alcove.png (a stand-in alcove for review) and src/_props_sheet.png (contact sheet).
"""
import io
import os

import numpy as np
from PIL import Image, ImageDraw, ImageFont

from common import BAYER4, OUT, hexrgb

SRC = os.path.join(OUT, "src")

# ---------------------------------------------------------------- palette (STYLE-v2 plus a few in-betweens)
OL = "#07080a"                      # outer outline
ST_H, ST_M, ST_D, ST_X = "#4f5662", "#3b414b", "#262a31", "#171a1f"   # stone, light -> dark
GOLD_L, GOLD_M, GOLD_D, GOLD_X, GOLD_XX = "#efc77a", "#cf9f4a", "#a67a30", "#7a5418", "#5a3e15"
GOLD_HOT = "#fff3c4"
EMB_L, EMB_M, EMB_D = "#ffb347", "#d9582b", "#8a2f18"
SMOKE = "#aab3c0"
GLASS = ("#8fb0d6", 62)             # empty glass tint (translucent)
GLINT = ("#cfe6ff", 150)

# ---------------------------------------------------------------- tiny RGBA canvas helpers


class Canvas:
    def __init__(self, w, h):
        self.a = np.zeros((h, w, 4), np.uint8)
        self.w, self.h = w, h

    def put(self, x, y, col, alpha=255):
        if 0 <= x < self.w and 0 <= y < self.h:
            self.a[y, x] = hexrgb(col) + (alpha,)

    def get(self, x, y):
        return tuple(self.a[y, x])

    def opaque(self, x, y):
        return self.a[y, x, 3] > 0


def save_rgba_indexed(path, rgba):
    """Quantise an RGBA array with <= 256 exact colours to an optimised palette PNG (index 0 = transparent)."""
    h, w, _ = rgba.shape
    pal = [(0, 0, 0, 0)]
    idx = np.zeros((h, w), np.uint8)
    for y in range(h):
        for x in range(w):
            c = tuple(int(v) for v in rgba[y, x])
            if c[3] == 0:
                continue
            if c not in pal:
                pal.append(c)
            idx[y, x] = pal.index(c)
    img = Image.fromarray(idx, "P")
    flat = []
    for c in pal:
        flat += list(c[:3])
    img.putpalette(flat)
    trns = bytes(c[3] for c in pal)
    bits = 1
    while (1 << bits) < len(pal):
        bits *= 2
    buf = io.BytesIO()
    img.save(buf, "PNG", optimize=True, bits=min(bits, 8), transparency=trns)
    data = buf.getvalue()
    try:
        import zopfli.png
        d2 = zopfli.png.optimize(data)
        back = Image.open(io.BytesIO(d2)).convert("RGBA")
        if len(d2) < len(data) and np.array_equal(np.array(back), np.array(Image.open(io.BytesIO(data)).convert("RGBA"))):
            data = d2
    except Exception as e:
        print("zopfli unavailable:", e)
    with open(path, "wb") as f:
        f.write(data)
    return len(data), len(pal)


# ================================================================ HOURGLASS 12x20
HW, HH = 12, 20
# interior (sand) width per row, centred on x 5.5; rows 3..16 are the glass, mirror symmetric (y <-> 19-y)
WID = {3: 6, 4: 8, 5: 8, 6: 6, 7: 4, 8: 2, 9: 2, 10: 2, 11: 2, 12: 4, 13: 6, 14: 8, 15: 8, 16: 6}
TOP_Y = list(range(3, 9))      # upper bulb rows
BOT_Y = list(range(11, 17))    # lower bulb rows
NECK_Y = [9, 10]


def row_x(y):
    w = WID[y]
    return range(6 - w // 2, 6 + w // 2)


UPPER = [(x, y) for y in TOP_Y for x in row_x(y)]
LOWER = [(x, y) for y in BOT_Y for x in row_x(y)]
NECK = [(x, y) for y in NECK_Y for x in row_x(y)]
assert len(UPPER) == len(LOWER) == 34


def remaining(frac):
    return int(round(34 * frac))


def upper_sand(k):
    """Pixels of sand left in the top bulb at k tenths used: a crater (centre drains first)."""
    n = remaining(1 - k / 10)
    order = sorted(UPPER, key=lambda p: (p[1] + abs(p[0] - 5.5) * 0.45, p[0]))   # first = removed first
    return set(order[len(order) - n:]) if n else set()


def lower_sand(k):
    """Pixels of sand in the bottom bulb: a mound (centre fills first)."""
    n = remaining(k / 10)
    order = sorted(LOWER, key=lambda p: ((16 - p[1]) + abs(p[0] - 5.5) * 0.45, p[0]))
    return set(order[:n]) if n else set()


def sand_tones(k):
    if k >= 8:
        return EMB_L, EMB_M, EMB_D
    return GOLD_L, GOLD_M, GOLD_D


def draw_glass(c, k):
    sand_u, sand_l = upper_sand(k), lower_sand(k)
    sand = sand_u | sand_l
    neck_full = k <= 9
    if neck_full:
        sand |= set(NECK)
    light, mid, dark = sand_tones(k)
    # glass outline and empty tint
    for y, w in WID.items():
        c.put(5 - w // 2, y, OL)
        c.put(6 + w // 2, y, OL)
        for x in row_x(y):
            c.put(x, y, *GLASS)
    # ember sand throws a dithered glow into the empty glass around it
    if k >= 8:
        for y, w in WID.items():
            for x in row_x(y):
                if (x, y) in sand or y < 10:
                    continue
                d = min(np.hypot(x - sx, y - sy) for sx, sy in sand) if sand else 9
                if d < 2.6 and (1 - d / 2.6) > BAYER4[y % 4, x % 4]:
                    c.put(x, y, EMB_M, 105)
    # glint on the empty glass (upper left of each bulb)
    for (x, y) in ((2, 4), (2, 5), (3, 14), (2, 14)):
        if (x, y) not in sand:
            c.put(x, y, *GLINT)
    # sand: cel shaded, lit from the upper left
    for (x, y) in sorted(sand):
        up = (x, y - 1) in sand
        left = (x - 1, y) in sand
        right = (x + 1, y) in sand
        down = (x, y + 1) in sand
        col = mid
        if not up:                      # surface / top edge catches the lamp
            col = light
        elif not left and x <= 3:       # left glass wall
            col = light if y % 2 == 0 else mid
        if not right and x >= 8:        # right wall in shade
            col = dark
        if not down and y in (15, 16, 8) and (x, y) in sand_l | sand_u:
            col = dark if col == mid else col
        c.put(x, y, col)
    return sand


def draw_caps(c, k, sand):
    """Brass caps with a carved tooth row; lit from the upper left."""
    for x in range(1, 11):
        hi = GOLD_M if x <= 3 else (GOLD_D if x <= 9 else GOLD_X)
        tooth = GOLD_X if x % 2 else GOLD_XX
        # top cap: outline, lit face, carved teeth
        c.put(x, 0, OL)
        c.put(x, 1, hi)
        c.put(x, 2, tooth)
        # bottom cap: lit top face, carved teeth, outline on the pedestal
        c.put(x, 17, hi)
        c.put(x, 18, tooth)
        c.put(x, 19, OL)
    for y in (1, 2, 17, 18):
        c.put(0, y, OL)
        c.put(11, y, OL)
    c.put(5, 1, GOLD_X)
    c.put(6, 1, GOLD_X)
    c.put(5, 18, GOLD_XX)
    c.put(6, 18, GOLD_XX)
    # ember sand lights the faces that look at it
    if k >= 8:
        for x in range(4, 8):
            if (x, 16) in sand and x in row_x(16):
                c.put(x, 17, EMB_D)
        for x in range(3, 9):
            if (x, 3) in sand and x in row_x(3):
                c.put(x, 2, EMB_D)


def hourglass_frame(k):
    c = Canvas(HW, HH)
    sand = draw_glass(c, k)
    draw_caps(c, k, sand)
    return c


def smoke_frame(phase):
    """Frame 10 plus smoke puffs rising through the empty upper bulb, a drifting spark and a flickering ember."""
    c = hourglass_frame(10)
    puffs = {
        0: [(6, 10, 120), (5, 9, 190), (6, 8, 190), (5, 8, 120), (5, 7, 190), (6, 6, 190), (4, 6, 120), (5, 5, 190),
            (6, 5, 120), (7, 4, 190), (4, 4, 190), (5, 4, 120), (4, 3, 120), (6, 3, 190)],
        1: [(5, 10, 120), (6, 9, 190), (5, 8, 190), (6, 8, 120), (6, 7, 190), (5, 6, 190), (7, 6, 120), (6, 5, 190),
            (5, 5, 120), (4, 4, 190), (7, 4, 190), (6, 4, 120), (5, 3, 120), (7, 3, 190)],
    }[phase]
    for x, y, a in puffs:
        c.put(x, y, SMOKE, a)
    sx, sy = {0: (7, 7), 1: (4, 6)}[phase]
    c.put(sx, sy, EMB_L)
    fx, fy = {0: (3, 14), 1: (8, 14)}[phase]
    c.put(fx, fy, EMB_L)
    return c


def trickle_frame(phase):
    """Transparent overlay: falling grains through the neck and the lower bulb."""
    c = Canvas(HW, HH)
    if phase == 0:
        pts = [(5, 10, GOLD_HOT), (6, 12, GOLD_HOT), (5, 13, GOLD_L), (6, 14, GOLD_HOT), (5, 15, GOLD_L)]
    else:
        pts = [(6, 10, GOLD_HOT), (5, 12, GOLD_L), (6, 13, GOLD_HOT), (5, 14, GOLD_L), (6, 15, GOLD_HOT)]
    for x, y, col in pts:
        c.put(x, y, col)
    return c


def build_hourglass():
    frames = [hourglass_frame(k) for k in range(11)]
    frames += [trickle_frame(0), trickle_frame(1), smoke_frame(0), smoke_frame(1)]
    sheet = np.concatenate([f.a for f in frames], axis=1)
    return sheet, frames


# ================================================================ ARKENSTONE 16x16
AW = AH = 16
# 8x8 facet map inside the 10x10 silhouette (offset 3,3). W white glint, H body, S shade, D deep, '.' outside.
GEM = [
    "..WHHS..",
    ".WHSHHD.",
    "WHHSHSSD",
    "HSSHHSDD",
    "HHHSSHSD",
    "HSHSDSDD",
    ".SSHDDD.",
    "..SDDD..",
]
# silhouette outline: interior pixels listed above; the outline is every outside pixel 4-adjacent to the gem
# (diagonals are not outlined, so the corner stays a clean octagon)

# colour ramps (W, H, S, D) for 100, 80, 60, 40, 20, 0 % left
LEVELS = [
    ("#ffffff", "#cfe6ff", "#7fa3c9", "#4f6f96"),
    ("#e6f1ff", "#b9d6f2", "#7399c3", "#486891"),
    ("#cfe6ff", "#93b8dd", "#617fa6", "#3e5a7d"),
    ("#9dbddf", "#6f94bc", "#506d92", "#34495f"),
    ("#6d86a6", "#546c8c", "#3e5370", "#2a3a50"),
    ("#6a717d", "#4f5662", "#3b414b", "#262a31"),      # 0%: dull grey stone
]
# halo outer radius per level (None = no halo); gem silhouette is about r = 5
HALO_R = [8.2, 7.0, 6.35, 5.9, 5.65, None]
HALO_IN, HALO_OUT = ("#bcdcff", 135), ("#6f9fd6", 105)


def gem_pixels():
    inside = {}
    for j, row in enumerate(GEM):
        for i, ch in enumerate(row):
            if ch != ".":
                inside[(i + 4, j + 4)] = ch
    return inside


def arkenstone_frame(level):
    c = Canvas(AW, AH)
    inside = gem_pixels()
    R = HALO_R[level]
    if R:
        for y in range(AH):
            for x in range(AW):
                if (x, y) in inside:
                    continue
                r = np.hypot(x - 7.5, y - 7.5)
                inten = (R - r) / (R - 5.2)
                if inten <= 0:
                    continue
                inten = min(0.85, inten)
                if inten > BAYER4[y % 4, x % 4]:
                    c.put(x, y, *(HALO_IN if inten > 0.55 else HALO_OUT))
    ring = set()
    for (x, y) in inside:
        for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            if (x + dx, y + dy) not in inside:
                ring.add((x + dx, y + dy))
    for (x, y) in ring:
        c.put(x, y, OL)
    ramp = dict(zip("WHSD", LEVELS[level]))
    for (x, y), ch in inside.items():
        c.put(x, y, ramp[ch])
    return c


def twinkle_frame(phase):
    c = Canvas(AW, AH)
    if phase == 0:     # star on the upper left facet, a speck on the right
        for x, y in ((5, 4), (4, 5), (6, 5), (5, 6)):
            c.put(x, y, "#ffffff")
        c.put(5, 5, "#ffffff")
        c.put(5, 2, "#ffffff", 200)
        c.put(3, 5, "#ffffff", 200)
        c.put(11, 9, "#ffffff")
    else:              # smaller star lower right, a speck upper left
        for x, y in ((10, 9), (9, 10), (11, 10), (10, 11)):
            c.put(x, y, "#ffffff")
        c.put(10, 10, "#ffffff")
        c.put(10, 12, "#ffffff", 200)
        c.put(12, 10, "#ffffff", 200)
        c.put(6, 5, "#ffffff")
    return c


def build_arkenstone():
    frames = [arkenstone_frame(i) for i in range(6)] + [twinkle_frame(0), twinkle_frame(1)]
    sheet = np.concatenate([f.a for f in frames], axis=1)
    return sheet, frames


# ================================================================ stand-in alcove (100x49 at canvas 380,55)
def build_alcove():
    """Dark stone box standing in for throne.png: alcove at local (0,0)-(99,47); the image starts one row above (y -1)."""
    w, h = 100, 49
    c = Canvas(w, h)
    oy = 1  # local y -> image row
    for y in range(0, 48):
        for x in range(0, 100):
            edge = x in (0, 99) or y == 0
            c.put(x, y + oy, OL if edge else ("#262a31" if (x < 3 or x > 96 or y < 3) else "#101215"))
    # inner back wall with a faint lamp-lit wash
    for y in range(3, 46):
        for x in range(3, 97):
            if (x + y) % 2 == 0 and 8 < x < 92 and y < 40:
                c.put(x, y + oy, "#12151a")
    # left pedestal: top surface at local y 46, x 6-22
    for x in range(6, 23):
        c.put(x, 46 + oy, ST_H)
        c.put(x, 47 + oy, ST_M)
    # throne back and seat (stand-in for the king agent's art)
    for y in range(12, 46):
        for x in range(38, 62):
            c.put(x, y + oy, "#1e2127" if x > 40 else OL)
    for x in range(34, 66):
        for y in range(38, 46):
            c.put(x, y + oy, "#262a31")
    for x in range(34, 66):
        c.put(x, 38 + oy, "#30353d")
    # Arkenstone socket: ring in the throne back, local box x 42-57, y -1..14
    for y in range(-1, 15):
        for x in range(42, 58):
            d = np.hypot(x - 49.5, y - 6.5)
            if 4.4 <= d <= 7.9:
                c.put(x, y + oy, "#3b414b" if d < 6.4 else ST_D)
            elif d < 4.4:
                c.put(x, y + oy, "#0b0c0f")
    return c


# ================================================================ contact sheet
def font(size):
    try:
        return ImageFont.load_default(size=size)
    except TypeError:
        return ImageFont.load_default()


def over(bg, fg):
    base = Image.fromarray(bg.copy(), "RGBA")
    base.alpha_composite(Image.fromarray(fg, "RGBA"))
    return np.array(base)


def contact_sheet(hframes, aframes, alcove, path, k=6):
    bgh = hframes[0].a.copy()
    bgh[:] = hexrgb("#101215") + (255,)
    gap, lab = 10, 18
    f = font(13)
    cols_h = 11
    cw, ch = HW * k, HH * k
    W = max(cols_h * (cw + gap) + gap, 8 * (AW * k + gap) + gap)
    H = lab + ch + gap + lab + ch + gap + lab + AH * k + gap + lab + AH * k + gap + 8
    img = Image.new("RGBA", (W, H), hexrgb("#07080a") + (255,))
    d = ImageDraw.Draw(img)

    def tile(arr, x, y, bgcol="#101215"):
        a = np.zeros(arr.shape, np.uint8)
        a[:] = hexrgb(bgcol) + (255,)
        t = Image.fromarray(over(a, arr), "RGBA").resize((arr.shape[1] * k, arr.shape[0] * k), Image.NEAREST)
        img.alpha_composite(t, (x, y))

    y0 = 4
    d.text((gap, y0), "hourglass 0-10 (100% ... 0% left)", fill="#aab", font=f)
    y0 += lab
    for i in range(11):
        tile(hframes[i].a, gap + i * (cw + gap), y0)
        d.text((gap + i * (cw + gap) + 2, y0 + ch - 14), str(i), fill="#fff", font=f)
    y0 += ch + gap
    d.text((gap, y0), "11-12 trickle on frame 3 / 13-14 smoke / 11-12 on 9 (ember)", fill="#aab", font=f)
    y0 += lab
    for j, (fi, base) in enumerate(((11, 3), (12, 3), (13, None), (14, None), (11, 9), (12, 9))):
        arr = hframes[fi].a if base is None else over(hframes[base].a, hframes[fi].a)
        tile(arr, gap + j * (cw + gap), y0)
    y0 += ch + gap
    d.text((gap, y0), "arkenstone 0-5 (100, 80, 60, 40, 20, 0 % left)", fill="#aab", font=f)
    y0 += lab
    for i in range(6):
        tile(aframes[i].a, gap + i * (AW * k + gap), y0)
    y0 += AH * k + gap
    d.text((gap, y0), "6-7 twinkle over frames 0 and 1", fill="#aab", font=f)
    y0 += lab
    for j, (fi, base) in enumerate(((6, 0), (7, 0), (6, 1), (7, 1))):
        tile(over(aframes[base].a, aframes[fi].a), gap + j * (AW * k + gap), y0)
    img.convert("RGB").save(path)


def main():
    hsheet, hframes = build_hourglass()
    asheet, aframes = build_arkenstone()
    n1, c1 = save_rgba_indexed(os.path.join(OUT, "hourglass.png"), hsheet)
    n2, c2 = save_rgba_indexed(os.path.join(OUT, "arkenstone.png"), asheet)
    alc = build_alcove()
    Image.fromarray(alc.a, "RGBA").save(os.path.join(SRC, "_props_alcove.png"))
    contact_sheet(hframes, aframes, alc, os.path.join(SRC, "_props_sheet.png"))
    for name in ("hourglass.png", "arkenstone.png"):
        p = os.path.join(OUT, name)
        b64 = len(__import__("base64").b64encode(open(p, "rb").read()))
        print(name, os.path.getsize(p), "bytes,", b64, "base64")
    print("palette sizes:", c1, c2)


if __name__ == "__main__":
    main()
