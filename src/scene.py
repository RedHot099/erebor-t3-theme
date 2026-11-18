"""Static background v5: anchored blocks over a seamless rock tile (STYLE-v3.md ... STYLE-v5.md).

  rock-tile.png            64x64    seamless dark cavern rock, repeated over the whole panel
  scene-left.png           148x270  halls L1-L3 (stairs at x 0-40) running to the column edge: mineral work
                                    face at x ~133-147, ore fragments spilling on the floor toward the column;
                                    right edge on the chat column's left edge
  scene-right-tunnels.png  148x270  halls R-top (floor top y 60) and R1 (floor top y 100), mirror of the left
                                    halls: work face at x ~0-15 on the column edge, entry stairs and door at
                                    x ~130-147; LEFT edge on the column's right edge
  scene-right.png          148x270  what lies below the chamber: decorative lair gate from y 164, pillar;
                                    right edge on the panel's right edge
  chamber.png              100x61   self-contained throne chamber: throne.png at (0, 2), ledge with the
                                    carved rune band at y 50-58, outline on every edge. Default position:
                                    right-block (48, 102); it also floats under the thread details card
  runes.png                11 frames light overlay for the ledge's five runes, chamber-local box; frame k
                                    = k half-steps lit (full / half / none per rune)

Blocks are bottom-anchored. Plain rock inside a block is transparent so the tile shows through;
structures end in a 1 px #07080a outline plus a dithered #0b0c0f rim. Run throne.py first.
(The v2 single 480x270 canvas was retired; its generator is gone.)
"""
import io
import json
import os

import numpy as np
from PIL import Image

from common import BAYER4, EMBER, EMBER_D, GOLD, OUT, STONE, WARM, hexrgb

BW, BH = 148, 270          # block size
TILE = 64

# Hall interiors in block-local px (x0, x1, y0, y1); y1 = floor row (top surface of the slab).
# Left halls: x1 = the work face; the floor runs on to the column edge (x 147).
HALLS_L = {"L1": (4, 135, 22, 52), "L2": (4, 134, 66, 96), "L3": (4, 133, 110, 140)}
# Right tunnels: x0 = the work face (column side), x1 = the end wall with the entry door.
HALLS_R = {"Rtop": (15, 146, 30, 60), "R1": (15, 146, 70, 100)}
STAIR_X = 131              # right tunnels: stairs from x 131 up to a door in the end wall
WALK_L, WALK_R = 44, 114   # walk-in start x (left: past the stairwell pillar; right: foot of the stairs)
# Pick tip meets the projecting facet at local x 23 (0 after mirroring).
SLOTS = (
    [{"block": "left", "x": v[1] - 25 + reach, "y": v[3] - 24, "start": WALK_L}
     for v, reach in zip(HALLS_L.values(), (2, 1, 3))]
    + [{"block": "right", "x": v[0] + 2 - reach, "y": v[3] - 24, "start": WALK_R}
       for v, reach in zip(HALLS_R.values(), (1, 2))]
)

# Sprite colour rows 0–3. Both gold stations share row 0.
ORE_TONES = ("g05", "g1", "g15", "g2", "g3")
ORES = (
    GOLD,
    dict(zip(ORE_TONES, ("#303e53", "#526985", "#86abc4", "#b6d4e6", "#e5f5ff"))),
    dict(zip(ORE_TONES, ("#351a2a", "#652b44", "#9d425d", "#d46d87", "#ffc5ca"))),
    dict(zip(ORE_TONES, ("#1d304d", "#304d79", "#4878ad", "#7eb3e3", "#cfe6ff"))),
)

CHAMBER_AT = (48, 102)     # chamber.png top-left in the right block (default position)
CH_W, CH_H = 100, 61       # throne.png at chamber (0, 2); ledge rows 50-58, outline row 59, rim row 60
THRONE_IN_CH = (0, 2)
GATE_CX = 98               # lair gate centre, symmetric about x 97.5 = the throne's centre line
GATE_TOP = 160             # gate() ytop; the gate's first row is ytop + 4 = 164

# Weekly runes: five original angular glyphs, 5x5, carved along the full width of the chamber's ledge.
RUNE_GLYPHS = [
    ["..#..", ".#.#.", "#.#.#", "..#..", "..#.."],
    ["#.#.#", ".###.", "..#..", "..#..", "..#.."],
    ["#....", "##...", "#.#..", "#..#.", "#...."],
    ["..#..", ".#.#.", "#...#", ".#.#.", "..#.."],
    ["#...#", ".#.#.", "..#..", "..#..", ".#.#."],
]
LEDGE_Y = CHAMBER_AT[1] + 50            # right-block rows 152-160 (top surface, carved band, underside)
RUNE_CX = [CHAMBER_AT[0] + c for c in (10, 30, 50, 70, 90)]   # glyph centre columns (right-block)
RUNE_Y = LEDGE_Y + 2                    # glyph rows 154-158, glow 153-159
RUNE_PANEL = (CHAMBER_AT[0] + 3, CHAMBER_AT[0] + 96, LEDGE_Y + 1, LEDGE_Y + 7)   # recess x0, x1, y0, y1


def value_noise(h, w, cy, cx, seed):
    r = np.random.default_rng(seed)
    g = r.random((h // cy + 3, w // cx + 3))
    ys = np.arange(h) / cy
    xs = np.arange(w) / cx
    y0 = ys.astype(int)
    x0 = xs.astype(int)
    fy = ys - y0
    fx = xs - x0
    fy = fy * fy * (3 - 2 * fy)
    fx = fx * fx * (3 - 2 * fx)
    a = g[y0][:, x0]
    b = g[y0][:, x0 + 1]
    c = g[y0 + 1][:, x0]
    d = g[y0 + 1][:, x0 + 1]
    top = a + (b - a) * fx[None, :]
    bot = c + (d - c) * fx[None, :]
    return top + (bot - top) * fy[:, None]


def noise1d(n, cell, seed, amp):
    return (value_noise(1, n, 1, cell, seed)[0] - 0.5) * 2 * amp


def voronoi(h, w, cell, seed, aspect=1.3):
    """(cell id, edge flag) for chunky raw rock (v2 drawing)."""
    r = np.random.default_rng(seed)
    gy, gx = h // cell + 2, int(w // (cell * aspect)) + 3
    pts = [((j + r.uniform(0.15, 0.85)) * cell - cell / 2, (i + r.uniform(0.15, 0.85)) * cell * aspect - cell / 2)
           for j in range(gy) for i in range(gx)]
    yy, xx = np.mgrid[0:h, 0:w]
    best = np.full((h, w), 1e9)
    second = np.full((h, w), 1e9)
    bid = np.zeros((h, w), int)
    for k, (py, px) in enumerate(pts):
        d = np.sqrt((yy - py) ** 2 * 1.4 * aspect + (xx - px) ** 2 / aspect)
        m = d < best
        second = np.where(m, best, np.minimum(second, d))
        bid = np.where(m, k, bid)
        best = np.where(m, d, best)
    edge = (second - best) < 1.15
    return bid, edge


def dilate4(m):
    out = m.copy()
    out[1:, :] |= m[:-1, :]
    out[:-1, :] |= m[1:, :]
    out[:, 1:] |= m[:, :-1]
    out[:, :-1] |= m[:, 1:]
    return out


def save_png(path, rgba):
    """Save an RGBA array as an indexed PNG (palette + tRNS). Index 0 = fully transparent."""
    h, w, _ = rgba.shape
    flat = rgba.reshape(-1, 4).copy()
    flat[flat[:, 3] == 0] = 0
    cols, inv = np.unique(flat, axis=0, return_inverse=True)
    order = np.argsort([0 if c[3] == 0 else (1 if c[3] < 255 else 2) for c in cols], kind="stable")
    cols = cols[order]
    remap = np.empty(len(order), int)
    remap[order] = np.arange(len(order))
    idx = remap[inv.reshape(-1)].reshape(h, w).astype(np.uint8)
    assert len(cols) <= 256, len(cols)
    img = Image.fromarray(idx, "P")
    pal = []
    for c in cols:
        pal += [int(c[0]), int(c[1]), int(c[2])]
    img.putpalette(pal)
    bits = 1
    while (1 << bits) < len(cols):
        bits *= 2
    kw = {"optimize": True, "bits": bits}
    alphas = [int(c[3]) for c in cols]
    if min(alphas) < 255:
        last = max(i for i, a in enumerate(alphas) if a < 255)
        kw["transparency"] = bytes(alphas[:last + 1])
    buf = io.BytesIO()
    img.save(buf, "PNG", **kw)
    data = buf.getvalue()
    try:
        import zopfli.png
        d2 = zopfli.png.optimize(data)
        if len(d2) < len(data) and Image.open(io.BytesIO(d2)).mode == "P":   # stay indexed
            data = d2
    except ImportError as e:  # zopfli is optional
        print("zopfli unavailable:", e)
    with open(path, "wb") as f:
        f.write(data)
    return len(data), len(cols)


# ---------------------------------------------------------------- tile

def rock_tile(npts=26, mind=11, aspect=1.8, seed=5):
    """Seamless 64x64 cavern rock: flat #101215 chunks from a periodic Voronoi with random seeds
    (no grid, so the repeat does not show), broken #0b0c0f cracks, some #171a1f top edges and
    four #262a31 glints. Calm enough to sit behind chat text."""
    n = TILE
    r = np.random.default_rng(seed)
    pts = []
    while len(pts) < npts:                      # dart throwing on the torus
        p = (r.uniform(0, n), r.uniform(0, n))
        if all(min(abs(p[0] - q[0]), n - abs(p[0] - q[0])) ** 2 * aspect ** 2
               + min(abs(p[1] - q[1]), n - abs(p[1] - q[1])) ** 2 >= mind ** 2 for q in pts):
            pts.append(p)
    yy, xx = np.mgrid[0:n, 0:n]
    best = np.full((n, n), 1e9)
    sec = best.copy()
    bid = np.zeros((n, n), int)
    for k, (py, px) in enumerate(pts):
        dy = np.abs(yy - py)
        dx = np.abs(xx - px)
        d = np.sqrt((np.minimum(dy, n - dy) * aspect) ** 2 + np.minimum(dx, n - dx) ** 2)
        m = d < best
        sec = np.where(m, best, np.minimum(sec, d))
        bid = np.where(m, k, bid)
        best = np.where(m, d, best)
    edge = (sec - best) < 1.1 * aspect ** 0.5
    rng = np.random.default_rng(seed + 1)
    lit = rng.random(len(pts)) < 0.4            # chunks whose top edge catches a little light
    lvl = np.full((n, n), 2, np.int16)
    top = (np.roll(bid, 1, 0) != bid) & ~edge
    lvl[top & lit[bid]] = 3
    lvl[edge & (rng.random((n, n)) < 0.75)] = 1
    sp = rng.random((n, n))
    lvl[(sp < 0.03) & (lvl == 2)] = 1
    lvl[(sp > 0.985) & (lvl == 2)] = 3
    glints = 0
    for c in rng.permutation(len(pts)):
        if glints >= 4 or not lit[c]:
            continue
        ys, xs = np.where((bid == c) & top)
        if len(ys):
            i = np.argmin(xs + ys * 0.5)
            lvl[ys[i], xs[i]] = 5
            glints += 1
    rgba = np.zeros((n, n, 4), np.uint8)
    for v, c in {1: "#0b0c0f", 2: "#101215", 3: "#171a1f", 5: "#262a31"}.items():
        rgba[lvl == v, :3] = hexrgb(c)
    rgba[..., 3] = 255
    return rgba


# ---------------------------------------------------------------- block canvas

class Block:
    def __init__(self, seed):
        self.lvl = np.full((BH, BW), -1, np.int16)   # stone level 0..8, -1 = plain rock (transparent)
        self.ov = np.full((BH, BW), "", object)      # colour overrides on structures
        self.deco = np.full((BH, BW), "", object)    # ore, sparks: drawn after the outline, no outline
        self.warm = np.zeros((BH, BW), np.float32)
        self.extra = np.zeros((BH, BW), bool)        # silhouettes of layers drawn on top (alcove)
        self.rawrock = np.zeros((BH, BW), bool)      # raw rock past a dig face: fades out, no outline
        self.rng = np.random.default_rng(seed)
        bid, edge = voronoi(BH, BW, 11, seed + 7)
        shade = np.random.default_rng(seed + 8).integers(-1, 2, bid.max() + 1)
        rk = 3 + shade[bid]
        rk[(np.roll(bid, 1, 0) != bid) | (np.roll(bid, 1, 1) != bid)] += 1
        rk[np.roll(bid, -1, 0) != bid] -= 1
        rk[edge] = 1
        self.rk = np.clip(rk, 1, 5)                  # raw-rock texture for rough wall zones

    def put(self, y, x, v):
        if 0 <= y < BH and 0 <= x < BW:
            self.lvl[y, x] = v
            self.ov[y, x] = ""

    # ---- halls (same drawing as v2) ----
    def hall(self, x0, x1, y0, y1, slab=(2, 2)):
        lvl = self.lvl
        x1c = min(x1, BW)
        for y in range(y0, y1):
            ry = (y - y0) // 5
            for x in range(x0, x1c):
                m = ((y - y0) % 5 == 4) or ((x + (ry % 2) * 5) % 10 == 9)
                rx = (x + (ry % 2) * 5) // 10
                face = 2 + (((rx * 5 + ry * 3) % 7) == 0) + (((rx * 3 + ry) % 4) != 0)
                v = 1 if m else face
                if (y - y0) % 5 == 0 and not m:
                    v += 1
                lvl[y, x] = v
        for x in range(x0, x1c):                     # carved lintel band
            lvl[y0, x], lvl[y0 + 1, x], lvl[y0 + 2, x], lvl[y0 + 3, x] = 6, 5, 5, 2
            t = (x - x0) % 8
            if t in (1, 7):
                lvl[y0 + 2, x] = 3
            if t in (2, 6):
                lvl[y0 + 1, x] = 3
            if t in (3, 5):
                lvl[y0 + 1, x] = 7
                lvl[y0 + 2, x] = 3
            if t == 4:
                lvl[y0 + 2, x] = 7
        for x in range(x0 - slab[0], min(x1 + slab[1], BW)):   # floor slab
            if 0 <= x:
                lvl[y1, x] = 7
                lvl[y1 + 1, x] = 5
                lvl[y1 + 2, x] = 5 if (x % 9) else 3
                lvl[y1 + 3, x] = 3

    def dig_face(self, x_face, y0, y1, direction, seed, ore):
        """Unfinished end of a hall. direction +1: face on the hall's right, -1: on its left.
        Beyond the face the raw rock (with the ore) dithers out into plain rock, so it meets the
        tile without a hard edge."""
        rr = np.random.default_rng(seed)
        prof = noise1d(y1 - y0, 4, seed, 2.5)
        depth = 9 + noise1d(y1 - y0 + 8, 5, seed + 1, 3.0)
        face_x = {}
        for i, y in enumerate(range(y0, y1)):
            fx = int(round(x_face + prof[i]))
            face_x[y] = fx
            for k in range(1, 16):
                x = fx + direction * k
                if not 0 <= x < BW:
                    continue
                # raw rock: solid for 3 px, then a Bayer fade over the next `depth` px
                t = (k - 4) / max(1.0, depth[i])
                if k <= 4 or BAYER4[y % 4, x % 4] > t:
                    if k <= 4:                       # freshly cut, catches the light
                        v = np.clip(self.rk[y, x] + (1 if k <= 2 else 0), 2, 5)
                    else:
                        v = np.clip(self.rk[y, x] - (1 if k > 7 else 0), 1, 4 if k <= 7 else 3)
                    self.lvl[y, x] = int(v)
                    self.rawrock[y, x] = True
                else:
                    self.lvl[y, x] = -1
                self.ov[y, x] = ""
            self.lvl[y, fx] = 2
            span = range(fx - 12, fx) if direction > 0 else range(fx + 1, fx + 13)
            for x in span:
                if rr.random() < 0.85 * (1 - abs(x - fx) / 13):
                    self.lvl[y, x] = max(1, self.rk[y, x] - 1)
        # the lintel's top row stops at the face as well; raw rock fades above it
        for y in (y0 - 1,):
            fx = face_x[y0]
            for k in range(1, 16):
                x = fx + direction * k
                if 0 <= x < BW:
                    t = (k - 1) / 8
                    if BAYER4[y % 4, x % 4] > t:
                        self.lvl[y, x] = int(np.clip(self.rk[y, x], 1, 3))
                        self.rawrock[y, x] = True
                    else:
                        self.lvl[y, x] = -1
        for x in range(BW):                    # raw rock fades upward over the lintel too
            for j, t in ((2, 0.3), (3, 0.65)):
                y = y0 - j
                if self.rawrock[y + 1, x] and BAYER4[y % 4, x % 4] > t + 0.1 * abs(x - face_x[y0]):
                    self.lvl[y, x] = int(np.clip(self.rk[y, x], 1, 3))
                    self.rawrock[y, x] = True
        # Broken branches run into the rock from the exposed facet at pick height.
        strike_y = y1 - 9
        for dy, offsets in ((-7, (5, 6)), (-6, (4, 5)), (-5, (3, 4)), (-4, (2, 3)),
                            (-3, (2,)), (1, (4,)), (2, (4, 5)), (3, (5, 6)),
                            (4, (6, 7)), (5, (8,))):
            y = strike_y + dy
            for i, k in enumerate(offsets):
                x = face_x[y] + direction * k
                if self.rawrock[y, x]:
                    self.deco[y, x] = ore["g15" if i == 0 else "g05"]

        # The central facet projects a pixel into the hall. Extend into the rock in
        # face-relative coordinates, keeping the brightest facet on the lit edge.
        nx = face_x[strike_y]
        facet = (".11..", "1321.", "22310", ".2100", "..00.")
        for dy, row in enumerate(facet, -2):
            for dx, tone in enumerate(row, -1):
                if tone != ".":
                    self.deco[strike_y + dy, nx + direction * dx] = ore[ORE_TONES[int(tone) + 1]]
        for dy, dx in ((-10, 8), (-8, 3), (-3, 7), (0, 7), (5, 3), (7, 9), (9, 2)):
            y = strike_y + dy
            if y < y1:
                x = face_x[y] + direction * dx
                if self.rawrock[y, x]:
                    self.deco[y, x] = ore["g1"]
        # rubble on the floor at the face
        for k in range(9):
            x = x_face - direction * (k + 1)
            hgt = max(0, 3 - k // 3 - (k % 2))
            for j in range(hgt):
                self.lvl[y1 - 1 - j, x] = 5 if j == hgt - 1 else 4
                if rr.random() < 0.2:
                    self.deco[y1 - 1 - j, x] = ore["g05"]
        return face_x

    def pillar(self, px, y0, y1, w=5):
        lvl = self.lvl
        for y in range(y0, y1):
            for k in range(w):
                lvl[y, px + k] = 6 if k == 0 else (3 if k == w - 1 else 5)
                self.ov[y, px + k] = ""
        for (yy0, n) in ((y0, 3), (y1 - 3, 3)):
            for j in range(n):
                for k in range(-2, w + 2):
                    v = 6 if j == 0 else (5 if j == 1 else 4)
                    if yy0 == y0:
                        v = 7 if j == n - 1 else 5
                    self.put(yy0 + j, px + k, v)
        for y in range(y0 + 3, y1 - 3):
            lvl[y, px - 1] = min(lvl[y, px - 1], 1)
            lvl[y, px + w] = min(lvl[y, px + w], 1)

    def flight(self, xa, ya, xb, yb, run=3):
        dx = 1 if xb > xa else -1
        n = max(1, abs(xb - xa) // run)
        drop = yb - ya
        for s in range(n):
            ytop = ya + round((s + 1) * drop / n)
            for r in range(run):
                x = xa + dx * (s * run + r)
                if not (0 <= x < BW):
                    continue
                first = r == 0
                for j in range(7):
                    if j == 0:
                        v = 7
                    elif j == 1:
                        v = 5 if first else 6
                    elif j < 4:
                        v = 4 if first else 5
                    elif j < 6:
                        v = 4
                    else:
                        v = 1
                    self.put(ytop + j, x, v)

    def hole(self, x0, x1, y0, y1):
        for y in range(y0, y1):
            for x in range(x0, x1):
                ry = (y - y0) // 5
                rx = (x + (ry % 2) * 5) // 10
                mort = ((y - y0) % 5 == 4) or ((x + (ry % 2) * 5) % 10 == 9)
                self.put(y, x, 1 if mort else (2 + ((rx + ry) % 5 == 0)))

    def landing(self, x0, x1, y):
        for x in range(x0, x1):
            for j, v in enumerate((7, 6, 4, 1)):
                self.put(y + j, x, v)

    def railing(self, x0, x1, y):
        for x in range(x0, x1):
            self.put(y - 5, x, 6)
        for x in range(x0, x1, 4):
            for j in range(1, 5):
                self.put(y - j, x, 5)
        self.put(y - 5, x0 - 1, 7)

    def big_pillar(self, px, y0, y1, w=9):
        for y in range(y0, y1):
            for k in range(w):
                v = 4
                if k <= 1:
                    v = 5
                elif k >= w - 2:
                    v = 2
                elif k == w // 2 and (y // 3) % 2 == 0:
                    v = 3
                self.put(y, px + k, v)
            self.put(y, px - 1, 1)
            self.put(y, px + w, 1)
        for j in range(4):                              # capital
            for k in range(-3 + (j // 2), w + 3 - (j // 2)):
                self.put(y0 + j, px + k, 6 if j == 0 else (5 if j < 3 else 3))
        for j in range(4):                              # base, its foot is the panel bottom / the gold
            for k in range(-3 + (j // 2), w + 3 - (j // 2)):
                self.put(y1 - 13 + j, px + k, 5 if j == 3 else 4 if j else 6)
        for y in range(y1 - 9, y1):                     # plinth down to the panel bottom
            for k in range(-3, w + 3):
                v = 3 if k in (-3, w + 2) else (4 if (y - y1) % 4 else 2)
                self.put(y, px + k, v)

    def lamp(self, lx, ly, r=20, bracket=True):
        if bracket:
            self.put(ly + 4, lx, 7)
            self.put(ly + 5, lx, 6)
            self.put(ly + 6, lx, 5)
            for d in (-1, 0, 1):
                self.put(ly + 3, lx + d, 6)
        for j, row in enumerate((".e.", "e3e", "343", ".3.")):
            for i, c in enumerate(row):
                if c != ".":
                    y, x = ly - 1 + j, lx - 1 + i
                    if self.lvl[y, x] < 0:
                        self.lvl[y, x] = 1
                    self.ov[y, x] = {"e": "ember", "3": "g3", "4": "g4"}[c]
        yy, xx = np.mgrid[0:BH, 0:BW]
        d = np.hypot(xx - lx, (yy - ly) * 1.15)
        self.warm = np.maximum(self.warm, np.clip(1 - d / r, 0, 1))

    def gate(self, gcx, ytop=108, ybot=BH, half=(9, 18, 28), door_half=16):
        """Sealed lair gate (v2 drawing, narrower)."""
        h1, h2, h3 = half

        def outer(x, y):
            d = abs(x + 0.5 - gcx)
            return (y >= ytop + 4 and d < h1) or (y >= ytop + 10 and d < h2) or (y >= ytop + 16 and d < h3)

        def is_open(x, y):
            d = abs(x + 0.5 - gcx)
            if y < ytop + 32 or d >= door_half:
                return False
            return y - (ytop + 32) >= max(0, d - (door_half - 6))

        for y in range(ytop, ybot):
            for x in range(gcx - h3 - 3, gcx + h3 + 3):
                if not outer(x, y):
                    continue
                dx_ = x - gcx
                if is_open(x, y):
                    v = 2
                    if dx_ in (-1, 0):
                        v = 0 if dx_ == 0 else 3
                    elif abs(dx_) in (door_half - 2, door_half - 1) or (y - (ytop + 38)) % 26 == 0:
                        v = 1
                    elif (abs(dx_) + y) % 8 == 0 and 4 < abs(dx_) < door_half - 4:
                        v = 3
                    if not is_open(x - 1, y):
                        v = 0
                    self.put(y, x, v)
                    continue
                v = 4
                if not outer(x - 1, y) or not outer(x, y - 1):
                    v = 6
                elif not outer(x + 1, y):
                    v = 2
                elif is_open(x + 1, y):
                    v = 1
                elif is_open(x - 1, y) or (is_open(x, y + 1) and not is_open(x, y)):
                    v = 5
                else:
                    if ytop + 18 <= y < ytop + 28:
                        r = y - (ytop + 18)
                        t = (x - gcx + 64) % 8
                        if t == r % 8 or t == (7 - r) % 8:
                            v = 3 if r < 5 else 5
                    elif y >= ytop + 28 and abs(dx_) > door_half + 2:
                        py = (y - (ytop + 28)) % 10
                        pxo = abs(abs(dx_) - (door_half + 6))
                        if pxo + abs(py - 5) == 3:
                            v = 3
                        elif pxo + abs(py - 5) == 2:
                            v = 5
                    elif y < ytop + 16 and (y - ytop - 4) % 6 == 3:
                        v = 3
                self.put(y, x, v)
        for (dx_, dy_) in [(0, 0), (-1, 1), (1, 1), (-2, 2), (2, 2), (-1, 3), (1, 3), (0, 4), (0, 2)]:
            self.put(ytop + 6 + dy_, gcx + dx_, 7)

    def rune_ledge(self, x0, x1):
        """Throne ledge x0..x1-1, rows LEDGE_Y..LEDGE_Y+8: lit top surface, a front face with a recessed
        band holding the five carved runes (unlit), dark underside. Light from the upper left: the
        recess's top and left walls are in shadow, its bottom and right lips lit; each groove is dark
        with a lit lower-right wall."""
        y = LEDGE_Y
        for x in range(x0, x1):
            col = [6, 5, 4, 4, 4, 4, 4, 5, 2]           # top, front face ..., lower lip, underside
            if (x - x0) % 12 == 6:                      # block joints on the face
                col[2:7] = [3, 3, 3, 3, 3]
            for j, v in enumerate(col):
                self.put(y + j, x, v)
        rx0, rx1, ry0, ry1 = RUNE_PANEL
        for yy in range(ry0, ry1 + 1):
            for x in range(rx0, rx1 + 1):
                v = 3
                if yy == ry0 or x == rx0:
                    v = 1
                elif yy == ry1:
                    v = 6
                elif x == rx1:
                    v = 5
                elif x == rx0 + 1:
                    v = 2
                self.put(yy, x, v)
        for k in range(len(RUNE_CX) - 1):               # carved diamond dividers between the runes
            cx = (RUNE_CX[k] + RUNE_CX[k + 1]) // 2
            for (dy, dx) in ((-1, 0), (0, -1), (0, 1), (1, 0)):
                self.put(ry0 + 3 + dy, cx + dx, 5 if dy < 0 or dx < 0 else 2)
            self.put(ry0 + 3, cx, 1)
        strokes = rune_strokes()
        h = len(RUNE_GLYPHS[0])
        for (yy, x) in strokes:
            self.put(yy, x, 0 if (yy - RUNE_Y) in (0, h - 1) else 1)
        for (yy, x) in strokes:
            for (dy, dx) in ((1, 0), (0, 1)):
                if (yy + dy, x + dx) not in strokes and rx0 < x + dx < rx1 and ry0 < yy + dy < ry1:
                    self.put(yy + dy, x + dx, 4)

    def spill(self, x_face, y1, direction, ore):
        """Angular chips gather at the face, with gaps between pieces on the floor."""
        for offset, rows in ((1, (".2.", "231", "110")),
                             (6, (".2", "10")),
                             (9, ("1", "20")),
                             (12, ("1",))):
            for j, row in enumerate(reversed(rows), 1):
                for i, tone in enumerate(row):
                    x = x_face + direction * (offset + i)
                    if 0 <= x < BW and tone != ".":
                        self.put(y1 - j, x, 4)
                        self.deco[y1 - j, x] = ore[ORE_TONES[int(tone)]]

    # ---- outline + compose ----
    def finish(self):
        struct = (self.lvl >= 0) & ~self.rawrock
        allm = (self.lvl >= 0) | self.extra
        ring1 = dilate4(struct | self.extra) & ~allm
        self.lvl[ring1] = 0
        allm |= ring1
        ring2 = dilate4(allm & ~self.rawrock) & ~allm
        yy, xx = np.mgrid[0:BH, 0:BW]
        ring2 &= ((xx + yy) % 2 == 0)
        self.lvl[ring2] = 1
        self.ring2 = ring2

    def render(self):
        named = dict(GOLD)
        named.update({"ember": EMBER, "ember_d": EMBER_D})
        S = [hexrgb(c) for c in STONE]
        Wm = [hexrgb(c) for c in WARM]
        glow_rgb = hexrgb(GOLD["g2"])
        out = np.zeros((BH, BW, 4), np.uint8)
        for y in range(BH):
            for x in range(BW):
                o = self.deco[y, x] or self.ov[y, x]
                if o:
                    out[y, x, :3] = hexrgb(named.get(o, o))
                    out[y, x, 3] = 255
                    continue
                b = BAYER4[y % 4, x % 4]
                g = self.warm[y, x]
                lv = int(self.lvl[y, x])
                if lv < 0 or self.ring2[y, x]:
                    # plain rock: translucent warm dither where a lamp reaches it
                    if g > 0.12 and b < (g - 0.12) * 1.6:
                        out[y, x, :3] = glow_rgb
                        out[y, x, 3] = 26 if g > 0.45 else 16
                    elif self.ring2[y, x]:
                        out[y, x, :3] = S[1]
                        out[y, x, 3] = 255
                    continue
                if g > 0.62 or (g > 0.5 and b < (g - 0.5) / 0.12):
                    lv += 2
                elif g > 0.32 or (g > 0.18 and b < (g - 0.18) / 0.14):
                    lv += 1
                lv = int(np.clip(lv, 0, 8))
                out[y, x, :3] = Wm[lv] if (g > 0.02 and b < min(1, g * 2.6)) else S[lv]
                out[y, x, 3] = 255
        return out


# ---------------------------------------------------------------- gate runes

def rune_strokes(which=None):
    """Set of (y, x) stroke pixels of the runes (all, or the indices in `which`)."""
    out = set()
    for i, (g, cx) in enumerate(zip(RUNE_GLYPHS, RUNE_CX)):
        if which is not None and i not in which:
            continue
        for j, row in enumerate(g):
            for k, c in enumerate(row):
                if c == "#":
                    out.add((RUNE_Y + j, cx - 2 + k))
    return out


def rune_frames():
    """11 overlay frames (RGBA, right-block full size) and their tight common box (x, y, w, h).
    Frame k = k half-steps: runes 0 .. k//2-1 full, rune k//2 half if k is odd, the rest none.
    full: #fff3c4 core with a 1 px #7a5418 glow; half: lower two rows full, middle row gold, top rows
    ember (reads as a rune half filled with light); none: dim ember; frame 0: all dull red."""
    n = len(RUNE_GLYPHS)
    core, halo, mid = hexrgb(GOLD["g4"]), hexrgb(GOLD["g1"]), hexrgb(GOLD["g2"])
    ember, dull = hexrgb(EMBER_D), hexrgb("#4a1714")
    frames = []
    for k in range(11):
        img = np.zeros((BH, BW, 4), np.uint8)

        def px(y, x, c):
            img[y, x, :3] = c
            img[y, x, 3] = 255

        for i in range(n):
            st = rune_strokes({i})
            state = "full" if i < k // 2 else ("half" if (i == k // 2 and k % 2) else "none")
            lit = st if state == "full" else {p for p in st if p[0] >= RUNE_Y + 3} if state == "half" else set()
            for (y, x) in lit:                          # glow on 4-neighbours, so the gaps stay dark
                for (dy, dx) in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                    q = (y + dy, x + dx)
                    if q not in st and (state == "full" or q[0] >= RUNE_Y + 3):
                        px(q[0], q[1], halo)
            for (y, x) in st:
                if (y, x) in lit:
                    px(y, x, core)
                elif state == "half" and y == RUNE_Y + 2:
                    px(y, x, mid)
                else:
                    px(y, x, dull if k == 0 else ember)
        frames.append(img)
    a = np.zeros((BH, BW), bool)
    for img in frames:
        a |= img[..., 3] > 0
    ys, xs = np.where(a)
    box = (int(xs.min()), int(ys.min()), int(xs.max() - xs.min() + 1), int(ys.max() - ys.min() + 1))
    return frames, box


# ---------------------------------------------------------------- blocks

def left_block():
    b = Block(5)
    for name, (x0, x1, y0, y1) in HALLS_L.items():
        b.hall(x0, x1, y0, y1, slab=(2, BW - x1))      # the floor runs on to the column edge
    faces = {}
    for (name, (_, x1, y0, y1)), seed, ore in zip(HALLS_L.items(), (114, 112, 110), ORES):
        faces[name] = b.dig_face(x1, y0 + 1, y1, +1, seed, ore)
        b.spill(x1 + 1, y1, +1, ore)
    for name, (x0, x1, y0, y1) in HALLS_L.items():
        b.pillar(30, y0 + 4, y1, 5)
        b.pillar(84, y0 + 4, y1, 5)
    # outer stairwell L1 -> L2 -> L3 at x 3..30
    for (yf, yn) in ((52, 96), (96, 140)):
        b.hole(4, 30, yf, yn - 26)
        mid = yf + 22
        b.flight(28, yf, 7, mid)
        b.landing(3, 9, mid)
        b.flight(7, mid, 28, yn)
        b.railing(9, 30, yf)
    # chamber pillar holding up L3's floor
    b.big_pillar(40, 144, BH, w=9)
    for (lx, ly) in ((62, 31), (60, 75), (58, 119)):
        b.lamp(lx, ly)
    b.lamp(40, 172)
    b.finish()
    return b, faces


def tunnels_block():
    """R-top and R1: open on the column side (work face at x ~0-15), end wall at x 146 with a door at
    the top of a short flight of stairs (the walk-in starts at the stairs' foot)."""
    b = Block(9)
    faces = {}
    for (name, (x0, x1, y0, y1)), seed, ore in zip(HALLS_R.items(), (362, 366), (ORES[3], ORES[0])):
        b.hall(x0, x1, y0, y1, slab=(x0, 1))            # floor runs on to the column edge (x 0)
        faces[name] = b.dig_face(x0 - 1, y0 + 1, y1, -1, seed, ore)
        b.spill(x0 - 2, y1, -1, ore)
        b.pillar(58, y0 + 4, y1, 5)
        b.pillar(104, y0 + 4, y1, 5)
        b.lamp(82, y0 + 9)
        # entrance: stairs up to a dark door in the end wall
        top = y1 - 13
        b.flight(STAIR_X, y1, x1, top)
        for x in range(STAIR_X, x1 + 1):                # the floor slab runs on under the first step
            for j, v in enumerate((7, 5, 5 if x % 9 else 3, 3)):
                b.put(y1 + j, x, v)
        for y in range(top - 11, top + 1):              # door: dark opening with a lit jamb and lintel
            for x in range(x1 - 6, x1):
                v = 0
                if y == top - 11 or x == x1 - 6:
                    v = 6
                elif y == top - 10:
                    v = 1
                b.put(y, x, v)
        b.put(top - 12, x1 - 4, 7)                      # keystone
    b.finish()
    return b, faces


def right_block():
    """Only what lies below the chamber: the decorative lair gate and the pillar on the right."""
    b = Block(9)
    b.gate(GATE_CX, ytop=GATE_TOP)
    b.big_pillar(137, LEDGE_Y + 11, BH, w=7)
    b.lamp(137, LEDGE_Y + 26)
    b.finish()
    return b


def chamber(throne):
    """chamber.png: throne.png + the ledge with the carved rune band, outlined on every edge.
    Drawn in right-block coordinates at the default position, then cropped."""
    b = Block(11)
    ax, ay = CHAMBER_AT
    tx, ty = ax + THRONE_IN_CH[0], ay + THRONE_IN_CH[1]
    b.extra[ty:ty + 48, tx:tx + 100] |= throne[..., 3] > 0
    b.rune_ledge(ax + 1, ax + CH_W - 1)                 # x 49..146; the outline takes x 48 and 147
    b.finish()
    rgba = b.render()[ay:ay + CH_H, ax:ax + CH_W].copy()
    m = throne[..., 3] > 0
    t = THRONE_IN_CH
    rgba[t[1]:t[1] + 48, t[0]:t[0] + 100][m] = throne[m]
    return rgba


def compose(tile, left, right, panel_w, col_w=184, extra=()):
    """Composite at native px for review: tile, left block on the column's left edge, right block on
    the right edge, then extra (rgba, x, y) layers."""
    H = BH
    canvas = np.zeros((H, panel_w, 3), np.float32)
    for y in range(H):
        for x in range(panel_w):
            canvas[y, x] = tile[y % TILE, x % TILE, :3]
    col_l = (panel_w - col_w) // 2

    def paste(img, px, py):
        h, w = img.shape[:2]
        for j in range(h):
            yy = py + j
            if not 0 <= yy < H:
                continue
            for i in range(w):
                xx = px + i
                if 0 <= xx < panel_w and img[j, i, 3]:
                    a = img[j, i, 3] / 255
                    canvas[yy, xx] = canvas[yy, xx] * (1 - a) + img[j, i, :3] * a

    paste(left, col_l - BW, 0)
    paste(right, panel_w - BW, 0)
    for (img, px, py) in extra:
        paste(img, px + panel_w - BW if px is not None else 0, py)
    return canvas.astype(np.uint8), col_l


def write_geom(rbox):
    """Merge the scene keys into src/_geom.json (hoard.py writes the pile keys of the same file)."""
    path = os.path.join(OUT, "src", "_geom.json")
    try:
        with open(path) as f:
            geom = json.load(f)
    except (OSError, ValueError):
        geom = {}
    rx, ry, rw, rh = rbox
    t = THRONE_IN_CH
    geom.update({
        "slots": SLOTS,
        "chamber": {"w": CH_W, "h": CH_H, "at": list(CHAMBER_AT),
                    "king": [t[0] + 34, t[1] + 10], "ark": [t[0] + 42, t[1] - 1],
                    "hourglass": [t[0] + 80, t[1] + 26],
                    "runes": {"x": rx - CHAMBER_AT[0], "y": ry - CHAMBER_AT[1], "w": rw, "h": rh, "frames": 11}},
        "ledge_y": CHAMBER_AT[1] + CH_H - 1,           # first row below the ledge outline (rim row only)
    })
    with open(path, "w") as f:
        json.dump(geom, f)
    return {k: geom[k] for k in ("slots", "chamber", "ledge_y")}


def main():
    """Writes scene-left.png, scene-right-tunnels.png, scene-right.png, chamber.png, runes.png, the scene
    keys of src/_geom.json and a review sheet. rock-tile.png is unchanged; --all rebuilds it too."""
    import sys
    src = os.path.join(OUT, "src")
    sizes = {}
    tile = rock_tile()
    if "--all" in sys.argv:
        sizes["rock-tile.png"] = save_png(os.path.join(OUT, "rock-tile.png"), tile)

    left, faces = left_block()
    sizes["scene-left.png"] = save_png(os.path.join(OUT, "scene-left.png"), left.render())
    tun, tfaces = tunnels_block()
    sizes["scene-right-tunnels.png"] = save_png(os.path.join(OUT, "scene-right-tunnels.png"), tun.render())
    sizes["scene-right.png"] = save_png(os.path.join(OUT, "scene-right.png"), right_block().render())

    throne = np.array(Image.open(os.path.join(OUT, "throne.png")).convert("RGBA"))
    ch = chamber(throne)
    sizes["chamber.png"] = save_png(os.path.join(OUT, "chamber.png"), ch)

    frames, (rx, ry, rw, rh) = rune_frames()
    strip = np.concatenate([fr[ry:ry + rh, rx:rx + rw] for fr in frames], axis=1)
    sizes["runes.png"] = save_png(os.path.join(OUT, "runes.png"), strip)
    for k, (n, c) in sizes.items():
        print(f"{k} {n} B, {c} colours")
    g = write_geom((rx, ry, rw, rh))
    print(json.dumps(g))

    # review sheet: the chamber over the tile with each rune frame, 3x
    cols = []
    for fr in frames:
        img = np.zeros((CH_H + 8, CH_W + 8, 3), np.float32)
        for y in range(img.shape[0]):
            for x in range(img.shape[1]):
                img[y, x] = tile[y % TILE, x % TILE, :3]
        ov = ch.astype(np.float32)
        a = ov[..., 3:4] / 255
        img[4:4 + CH_H, 4:4 + CH_W] = img[4:4 + CH_H, 4:4 + CH_W] * (1 - a) + ov[..., :3] * a
        r = fr[ry:ry + rh, rx:rx + rw].astype(np.float32)
        oy, ox = 4 + ry - CHAMBER_AT[1], 4 + rx - CHAMBER_AT[0]
        a = r[..., 3:4] / 255
        img[oy:oy + rh, ox:ox + rw] = img[oy:oy + rh, ox:ox + rw] * (1 - a) + r[..., :3] * a
        cols.append(img.astype(np.uint8))
    rows = [np.concatenate(cols[i:i + 4] + [np.zeros_like(cols[0])] * (4 - len(cols[i:i + 4])), axis=1)
            for i in range(0, 11, 4)]
    sheet = np.concatenate(rows, axis=0)
    Image.fromarray(sheet).resize((sheet.shape[1] * 3, sheet.shape[0] * 3), Image.NEAREST).save(
        os.path.join(src, "_scene_v5_chamber_runes_x3.png"))
    with open(os.path.join(src, "_scene_v5_geom.json"), "w") as f:
        json.dump({"left_halls": HALLS_L, "left_face_x_min_max":
                   {k: [min(v.values()), max(v.values())] for k, v in faces.items()},
                   "right_halls": HALLS_R, "right_face_x_min_max":
                   {k: [min(v.values()), max(v.values())] for k, v in tfaces.items()},
                   "stairs_x": STAIR_X, "chamber_at": CHAMBER_AT, "ledge_rows": [LEDGE_Y, LEDGE_Y + 8],
                   "rune_band": RUNE_PANEL, "rune_centres_x": RUNE_CX, "gate_first_row": GATE_TOP + 4}, f, indent=1)


if __name__ == "__main__":
    main()
