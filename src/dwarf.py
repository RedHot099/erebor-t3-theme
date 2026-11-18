"""Dwarf miner sprite sheet + headlamp cone, bold-outline pass (STYLE-v2.md, walk-in from STYLE-v3.md).

dwarf.png  384x96: 4 rows (colour variants) x 16 frames of 24x24, facing right.
           frames 0-7 working loop (wind-up, swing, hit + spark, recover), frames 8-9 resting loop,
           frames 10-15 walk cycle (pick on the shoulder), 100 ms per frame while the slot moves 2 px per frame.
lamp.png   14x14: one translucent headlamp cone; its apex (pixel 0,3) sits on the headlamp.

Round 4 (STYLE-v4.md): in frames 0-9 the legs, boots and hem are pixel-identical and stand on the same rows as
the hall floors (mining soles on row 22, their outline on row 23). The swing lives in the arms, the pick, a 1 px chest
lean, a 1 px head nod and the beard tip; lamp.png is only rewritten with --lamp. The walk keeps the round-2
head and torso: on the contact frames
(10, 13) the lamp sits on the same pixels as in work frame 0, on the passing frames (11, 12, 14, 15) the body
bobs 1 px up, so the cone goes 1 px up with it (see WALK_BOB).

Style: every frame is drawn as flat-tone fills on a padded canvas, then a 1 px #07080a outline is dilated
around the whole silhouette (body, helmet, beard, pick). Overlaps where the body sits in front of the
pick get their own outline pixels, so a handle that passes behind the head stays readable. Key light is
the upper left: highlights on the upper-left edges, shade on the lower right, warm bounce on the soles.
"""
import os
import sys

import numpy as np

from common import OUT, save_indexed
from scene import ORES

FW, FH = 24, 24
BX, BY = 3, 4  # body template offset inside the frame
PAD = 6        # padded canvas margin: lets a frame be drawn past 24x24 so clipping can be detected

SHARED = {
    ".": "#000000", "o": "#07080a",
    # skin: highlight, base, shade
    "Q": "#e8ae80", "S": "#d89a6c", "s": "#9a5c3a",
    # tunic (cool slate): light, base, shade
    "u": "#667d9e", "T": "#4b5d78", "t": "#2f3b50",
    # belt and buckle
    "k": "#4a3424", "K": "#2a1c14", "G": "#efc77a",
    # trousers and boots: light, base, shade, warm bounce under the soles
    "p": "#5a4030", "P": "#3d2c22", "q": "#2a1c14", "Y": "#7a5418",
    # pick handle: base, butt
    "W": "#a06c38", "w": "#5a3a20", "z": "#5c3322",
    # pick steel: light, mid, dark
    "m": "#dde4ec", "M": "#8f9aa8", "n": "#4f5662",
    # lamp, spark core, spark glow, ember
    "L": "#fff3c4", "*": "#fff3c4", "+": "#efc77a", "x": "#d9582b",
}
# helmet: shade, base, light, rim | beard: deep, shade, base, light
VARIANTS = [
    (("#4a525e", "#7d8794", "#c4ccd6", "#e8eef4"), ("#8a3418", "#c95a26", "#f08c48", "#ffb77a")),   # iron, ginger
    (("#6a3e16", "#a8702c", "#e0b060", "#f6d896"), ("#4a2a18", "#7a4a2a", "#ad7642", "#c28a52")),   # bronze, brown
    (("#2e4260", "#4f6f96", "#8fb0d6", "#c4def5"), ("#7a7f8a", "#b8bcc6", "#eceef2", "#fbfcfd")),   # blue steel, white
    (("#6e2416", "#a8402a", "#de7448", "#f4a878"), ("#9a7430", "#d8ae52", "#f6dc98", "#fff0bf")),   # copper, blond
]
VAR_KEYS = ["h", "H", "I", "J", "b", "B", "C", "D"]

# Fill only (the outline is added around the silhouette). Cols 0-19, rows 0-19; drawn at (BX, BY).
# h H I J = helmet shade/base/light/rim, b B C D = beard deep/shade/base/light.
BODY = [
    "....................",  # 0
    "....................",  # 1
    "....................",  # 2
    "......IJIHH.........",  # 3
    ".....JIIHHHh........",  # 4
    ".....IHHHHHhLL......",  # 5
    "....Hhhhhhhhhhh.....",  # 6   brim
    ".....bBSSSoSS.......",  # 7   o = the eye
    ".....bBSSSSSSs......",  # 8
    "....ubCDDCCBB.......",  # 9
    "...uTbCDCCBBB.......",  # 10
    "...uTTbCCCBBB.......",  # 11
    "...tTTTbCBBB........",  # 12
    "...kKKKKGBb.........",  # 13
    "...TTTttbb..........",  # 14  (cols 3-10)
    "....pPq.pPq.........",  # 15
    "....pPq.pPq.........",  # 16
    "...pPY..pPY.........",  # 17
]
BODY_CHARS = "hHIJbBCDsSQuTtkKGWwmMn"
HAND_RING = True
# rows (template) that belong to the head group, and chars that stay with the shoulders
HEAD_ROWS = range(3, 13)
STAY = "uTt"


def line(x0, y0, x1, y1):
    pts = []
    dx, dy = abs(x1 - x0), -abs(y1 - y0)
    sx = 1 if x0 < x1 else -1
    sy = 1 if y0 < y1 else -1
    err = dx + dy
    while True:
        pts.append((x0, y0))
        if x0 == x1 and y0 == y1:
            break
        e2 = 2 * err
        if e2 >= dy:
            err += dy
            x0 += sx
        if e2 <= dx:
            err += dx
            y0 += sy
    return pts


class Canvas:
    """Padded canvas: coordinates are frame coordinates, (0,0) is the frame's top-left pixel."""

    def __init__(self):
        self.w, self.h = FW + 2 * PAD, FH + 2 * PAD
        self.g = [["."] * self.w for _ in range(self.h)]

    def put(self, x, y, c):
        xx, yy = x + PAD, y + PAD
        if 0 <= xx < self.w and 0 <= yy < self.h:
            self.g[yy][xx] = c

    def get(self, x, y):
        xx, yy = x + PAD, y + PAD
        if 0 <= xx < self.w and 0 <= yy < self.h:
            return self.g[yy][xx]
        return "."

    def mask(self):
        return {(x - PAD, y - PAD) for y in range(self.h) for x in range(self.w) if self.g[y][x] != "."}

    def outline(self, around=None, only_on=None, ch="o"):
        """Write 'o' on every cell 4-adjacent to the silhouette `around` (default: all fill).
        With only_on, only cells whose current value is in that set are overwritten (inner outlines)."""
        around = self.mask() if around is None else around
        add = []
        for (x, y) in around:
            for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                p = (x + dx, y + dy)
                if p in around:
                    continue
                cur = self.get(*p)
                if only_on is None:
                    if cur == ".":
                        add.append(p)
                elif cur in only_on:
                    add.append(p)
        for (x, y) in add:
            self.put(x, y, ch)

    def crop(self):
        out = [["."] * FW for _ in range(FH)]
        clipped = []
        for y in range(self.h):
            for x in range(self.w):
                c = self.g[y][x]
                fx, fy = x - PAD, y - PAD
                if c == ".":
                    continue
                if 0 <= fx < FW and 0 <= fy < FH:
                    out[fy][fx] = c
                else:
                    clipped.append((fx, fy, c))
        return out, clipped


def draw_pick(cv, hx, hy, ang_deg, back=2, length=9):
    """Handle from the hands (hx,hy) along ang (0 = right, -90 = up); head at the far end."""
    a = np.radians(ang_deg)
    ux, uy = np.cos(a), np.sin(a)
    x0, y0 = round(hx - ux * back), round(hy - uy * back)
    x1, y1 = round(hx + ux * length), round(hy + uy * length)
    pts = line(x0, y0, x1, y1)
    for (x, y) in pts:
        cv.put(x, y, "W")
    cv.put(x0, y0, "w")
    # head: perpendicular, curved; the long spike points along the swing direction
    px, py = -uy, ux
    for k in range(-3, 4):
        bend = abs(k) * 0.35
        x = round(x1 + px * k - ux * bend)
        y = round(y1 + py * k - uy * bend)
        cv.put(x, y, "m" if k in (-1, 0) else "M")
    cv.put(round(x1 + px * 4 - ux * 1.6), round(y1 + py * 4 - uy * 1.6), "M")
    # thickness: a dark steel row on the grip side of the three centre pixels
    for k in (-1, 1):
        x = round(x1 + px * k - ux * (abs(k) * 0.35 + 1))
        y = round(y1 + py * k - uy * (abs(k) * 0.35 + 1))
        if cv.get(x, y) == ".":
            cv.put(x, y, "n")


def draw_arm(cv, sx, sy, hx, hy):
    for (x, y) in line(sx, sy, hx, hy):
        cv.put(x, y, "T")
        cv.put(x, y + 1, "t")


def draw_hands(cv, hx, hy):
    cv.put(hx, hy, "Q")
    cv.put(hx + 1, hy, "S")
    cv.put(hx, hy + 1, "s")
    cv.put(hx + 1, hy + 1, "s")


# Body groups for the planted poses (round 4). The legs (template rows 15-17) and the hem (row 14) never move,
# so the boots stand on the same pixels in every work and rest frame, on the same row as the walk contact boots.
LEG_ROWS = range(14, 18)
TORSO_ROWS = range(9, 14)
HEAD_CHARS = "hHIJbBCDSQsoL"   # helmet, beard, face, eye, lamp: everything that nods with the head
BEARD_CHARS = "bBCD"
CHEST_COLS = range(3, 9)       # template columns where the tunic continues behind the beard


def draw_body(cv, lean=0, head=(0, 0), sway=0):
    """Planted dwarf. lean: x shift of the chest and belt (rows 9-13), at most 1 px.
    head: absolute (dx, dy) of the head group (helmet, face, beard). sway: extra x shift of the
    beard's lower rows (11-13), which lag behind the head. Legs and hem never move."""
    hdx, hdy = head
    # 1) legs and hem, fixed
    for y in LEG_ROWS:
        for x, c in enumerate(BODY[y]):
            if c != "." and not (c in BEARD_CHARS and y == 14):
                cv.put(x + BX, y + BY, c)
                if y == 17:
                    cv.put(x + BX, y + BY, BODY[16][x] if BODY[16][x] != "." else "q")
                    cv.put(x + BX, y + BY + 1, c)
    # 2) chest and belt, leaning; the tunic is continued behind the beard so a moving beard leaves no hole
    for y in TORSO_ROWS:
        row = BODY[y]
        for x, c in enumerate(row):
            if c == ".":
                continue
            if c in HEAD_CHARS:
                if x in CHEST_COLS:
                    c = "k" if y == 13 else ("t" if x == CHEST_COLS[-1] else "T")
                else:
                    continue
            cv.put(x + BX + lean, y + BY, c)
    # 3) head group: helmet and face rows 3-8, beard rows 7-13 (and the beard tip on the hem row)
    for y in range(3, 15):
        for x, c in enumerate(BODY[y]):
            if c == "." or c not in HEAD_CHARS:
                continue
            if y >= 9 and c not in BEARD_CHARS:
                continue
            ex = sway if (c in BEARD_CHARS and y >= 11) else 0
            if y + hdy > 14:
                continue  # never over the legs
            cv.put(x + BX + hdx + ex, y + BY + hdy, c)


# Chest lean, head offset, beard lag, grip, shaft angle, pick behind the body.
# Cock, lift, crest, descend, strike, follow through, rebound, lift again.
WORK = [
    (-1, (-1, 0), 0, (9, 11), -146, True),
    (-1, (-1, 0), 0, (9, 10), -121, True),
    (0, (0, -1), -1, (11, 10), -88, True),
    (0, (0, 0), -1, (14, 10), -35, False),
    (1, (1, 1), -1, (15, 13), 24, False),
    (1, (1, 1), 0, (14, 14), 39, False),
    (0, (0, 0), 1, (13, 12), -22, False),
    (-1, (0, 0), 0, (10, 10), -97, True),
]
WORK_MS = (150, 105, 65, 55, 80, 95, 105, 145)

# The strike emits one hot glint and two slower fragments toward the miner.
SPARK = {
    4: [(23, 14, "*"), (23, 13, "+"), (23, 15, "+"),
        (21, 12, "x"), (22, 16, "x")],
    5: [(20, 10, "+"), (21, 11, "x"), (21, 17, "+"), (22, 17, "x")],
    6: [(18, 10, "x"), (19, 11, "+"), (20, 20, "+"), (21, 20, "x")],
    7: [(17, 14, "x"), (19, 22, "x"), (20, 22, "+")],
}


def frame(kind, f, report):
    cv = Canvas()
    if kind == "work":
        lean, head, sway, (hx, hy), ang, behind = WORK[f]
    else:
        # resting on the pick; frame 9 breathes: the head and beard sink 1 px, the body stays
        lean, head, sway = 0, (0, f), 0
        hx, hy, ang, behind = 16, 13 + f, None, False
    sx, sy = 9 + lean, 14  # shoulder

    def pick():
        if ang is None:
            # leaning on the pick: handle on the ground, head on top, hands resting on the head
            for y in range(hy, 23):
                cv.put(17, y, "W")
            cv.put(17, 22, "w")
            for x, c in zip(range(14, 22), "MMmmmmMM"):
                cv.put(x, hy - 1 + (1 if x in (14, 21) else 0), c)
            for x in (18, 19):
                cv.put(x, hy, "n")
        else:
            draw_pick(cv, hx, hy, ang, back=2, length=8)

    if behind:
        pick()
    draw_arm(cv, sx, sy, hx, hy)
    body = Canvas()
    draw_body(body, lean, head, sway)
    body_mask = body.mask()
    if behind:
        # the body sits in front of the pick: give it its own outline over the pick pixels
        for (x, y) in body_mask:
            cv.put(x, y, body.get(x, y))
        cv.outline(around=body_mask, only_on=set("WwmMnTt"))
    else:
        for (x, y) in body_mask:
            cv.put(x, y, body.get(x, y))
        pick()
    if kind == "work" and not behind:
        elbow = (hx - 3, max(hy + 2, 15))
        draw_arm(cv, 11 + lean, 15, *elbow)
        draw_arm(cv, *elbow, hx, hy)
    draw_hands(cv, hx, hy)
    hand_cells = {(hx, hy), (hx + 1, hy), (hx, hy + 1), (hx + 1, hy + 1)}
    if HAND_RING:
        # selective outline: a dark skin tone separates the hands from the body or pick they overlap
        cv.outline(around=hand_cells, only_on=set(BODY_CHARS), ch="z")
    cv.outline()
    g, clipped = cv.crop()
    if clipped:
        report.append((kind, f, clipped))
    for (x, y, c) in SPARK.get(f, []) if kind == "work" else []:
        if g[y][x] == "." or (f == 4 and x == 23):
            g[y][x] = c
    return g


# ---------------------------------------------------------------------------------------------------------
# Walk cycle (frames 10-15). 6 frames of 100 ms; the slot moves +2 native px per frame (20 px/s), so a planted
# boot moves -2 px per frame inside the frame and stays put on the floor. Each foot is planted for 4 frames
# (contact, two passing frames, contact) and swings for 2, so the stride is 12 px per cycle.
# Per frame: body bob (dy), near-leg row centres, far-leg row centres. A leg's last entry is its boot row;
# legs start at the row under the hem (19 + dy), so a shorter list is a lifted foot.
WALK = [
    (0, [11, 12, 13], [9, 8, 7]),          # 10 contact: near foot ahead, far foot behind
    (-1, [10, 10, 11, 11], [9, 8, 7]),     # 11 passing: near planted, far toe-off (lifted 1 px)
    (-1, [10, 10, 9, 9], [11, 13]),        # 12 passing: near planted, far swings forward (lifted 2 px)
    (0, [9, 8, 7], [11, 12, 13]),          # 13 contact: far foot ahead, near foot behind
    (-1, [9, 8, 7], [10, 10, 11, 11]),     # 14 passing: far planted, near toe-off
    (-1, [11, 13], [10, 10, 9, 9]),        # 15 passing: far planted, near swings forward
]
WALK_BOB = [dy for dy, _, _ in WALK]  # lamp/cone offset per walk frame, native px
NEAR_LEG = ("p", "P", "q", "Y")   # light, base, shade, warm toe
FAR_LEG = ("P", "P", "q", "Y")    # the far leg is one tone darker
# pick on the shoulder: hand at the back edge of the beard, handle over the shoulder, head behind the back
CARRY = {"hx": 8, "hy": 13, "ang": -155, "length": 8, "back": 2}


def draw_leg(cv, top, xs, tones):
    """3 px wide leg from the hip row `top` down; the last row is a 4 px boot with the toe forward."""
    light, base, shade, toe = tones
    for i, cx in enumerate(xs):
        y = top + i
        if i == len(xs) - 1:
            for dx, c in zip((-1, 0, 1, 2), (light, base, base, toe)):
                cv.put(cx + dx, y, c)
        else:
            for dx, c in zip((-1, 0, 1), (light, base, shade)):
                cv.put(cx + dx, y, c)


def walk_frame(f, report):
    dy, near_xs, far_xs = WALK[f]
    cv = Canvas()
    top = 19 + dy
    far, near = Canvas(), Canvas()
    draw_leg(far, top, far_xs, FAR_LEG)
    draw_leg(near, top, near_xs, NEAR_LEG)
    far_m, near_m = far.mask(), near.mask()
    for (x, y) in far_m:
        cv.put(x, y, far.get(x, y))
    for (x, y) in near_m:
        cv.put(x, y, near.get(x, y))
    # the near leg passes in front of the far leg: separate them with outline pixels on the far leg
    for (x, y) in near_m:
        for ddx, ddy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            p = (x + ddx, y + ddy)
            if p in far_m and p not in near_m:
                cv.put(*p, "o")
    hx, hy = CARRY["hx"], CARRY["hy"] + dy
    pick = Canvas()
    draw_pick(pick, hx, hy, CARRY["ang"], back=CARRY["back"], length=CARRY["length"])
    pick_m = pick.mask()
    draw_arm(cv, 9, 14 + dy, hx, hy)
    # head and torso as in the work frames (template rows 0-14), without the template legs
    body = Canvas()
    for y, row in enumerate(BODY[:15]):
        for x, c in enumerate(row):
            if c != ".":
                body.put(x + BX, y + BY + dy, c)
    body_m = body.mask()
    for (x, y) in body_m:
        cv.put(x, y, body.get(x, y))
    # the handle rests on the shoulder: in front of the tunic, behind the beard and the head
    for (x, y) in pick_m:
        if body.get(x, y) in ".uTt":
            cv.put(x, y, pick.get(x, y))
    cv.outline(around=body_m, only_on=set("WwmMn"))
    cv.outline(around=pick_m, only_on=set("uTt"))
    draw_hands(cv, hx, hy)
    # half ring (shadow side only) of dark skin so the hand reads in front of the beard
    for p in ((hx + 2, hy), (hx + 2, hy + 1), (hx, hy + 2), (hx + 1, hy + 2)):
        if cv.get(*p) in BODY_CHARS:
            cv.put(*p, "z")
    cv.outline()
    g, clipped = cv.crop()
    if clipped:
        report.append(("walk", f, clipped))
    return g


def main():
    keys = list(SHARED.keys())
    pal_hex = [SHARED[k] for k in keys]
    base_len = len(pal_hex)
    for (hel, brd) in VARIANTS:
        pal_hex += list(hel) + list(brd)
    for v, ore in enumerate(ORES):
        pal_hex += [ore["g4" if v == 0 else "g3"], ore["g2"], ore["g15"]]
    sheet = np.zeros((FH * 4, FW * 16), np.uint8)
    report = []
    for v in range(4):
        cmap = {k: i for i, k in enumerate(keys)}
        for j, k in enumerate(VAR_KEYS):
            cmap[k] = base_len + v * 8 + j
        for j, k in enumerate("*+x"):
            cmap[k] = base_len + len(VARIANTS) * len(VAR_KEYS) + v * 3 + j
        rep = report if v == 0 else []
        frames = [frame("work", f, rep) for f in range(8)] + [frame("rest", f, rep) for f in range(2)] \
            + [walk_frame(f, rep) for f in range(6)]
        for i, g in enumerate(frames):
            for y in range(FH):
                for x in range(FW):
                    sheet[v * FH + y, i * FW + x] = cmap[g[y][x]]
    for kind, f, clipped in report:
        print("CLIPPED", kind, f, clipped)
    n = save_indexed(os.path.join(OUT, "dwarf.png"), sheet, pal_hex, 0)
    print("dwarf.png", n, "bytes", sheet.shape, len(pal_hex), "colours")

    if "--lamp" not in sys.argv:
        return
    # headlamp cone: a short warm fan from the lamp down towards the dig face.
    # 14x14, apex (lamp) at pixel (0, 3); place it at dwarf frame (16, 6) facing right.
    LW, LH = 14, 14
    lamp = np.zeros((LH, LW), np.uint8)
    ax, ay = 0, 3
    for y in range(LH):
        for x in range(LW):
            dx_, dy_ = x - ax + 0.5, y - ay + 0.5
            r = np.hypot(dx_, dy_)
            a = np.degrees(np.arctan2(dy_, dx_))
            if r < 1 or r > 13.5 or a < -14 or a > 52:
                continue
            centre = abs(a - 19) / 33
            level = 3 if (centre < 0.45 and r < 9) else (2 if centre < 0.8 and r < 12 else 1)
            lamp[y, x] = level
    pal = ["#000000", "#efc77a", "#f3d58f", "#fff3c4"]
    import io
    from PIL import Image
    img = Image.fromarray(lamp, "P")
    flat = []
    for c in pal:
        flat += [int(c[i:i + 2], 16) for i in (1, 3, 5)]
    img.putpalette(flat)
    buf = io.BytesIO()
    # per-index alpha: 0 transparent, then faint, medium, strongest
    img.save(buf, "PNG", optimize=True, transparency=bytes([0, 34, 52, 74]), bits=2)
    with open(os.path.join(OUT, "lamp.png"), "wb") as fh:
        fh.write(buf.getvalue())
    print("lamp.png", len(buf.getvalue()), "bytes")


if __name__ == "__main__":
    main()
