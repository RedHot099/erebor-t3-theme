"""Throne alcove, 100x48, static. v3: placed at block-local (48, 56) in scene-right.png
(canvas (380, 56) on the 1920 px reference panel).

Self-contained: its own stepped lintel, pilasters and floor, so it reads wherever CSS anchors it.

Slots from STYLE-v3.md (alcove-local px), kept free for the props:
  hourglass pedestal  RIGHT pedestal, flat top surface at y 46, x 77-94 (hourglass box x 80-91, y 26-45)
  left side           decoration only (iron-bound chest under the left sconce); may sit behind the chat
  Arkenstone socket   empty carved socket, box x 42-57, y -1-14 (centre 49.5, 6.5)
  king seat           king frame box x 34-65, y 10-41; seat cushion top y 30, armrests y 28,
                      the king's feet stand on the dais top at y 42
"""
import os

import numpy as np

from common import OUT, STONE, WARM, GOLD, EMBER, hexrgb, BAYER4, save_indexed, upscale

W, H = 100, 48
OUTLINE = "#07080a"
# dark banner / cushion reds (the king's cloak uses the brighter end of the same family)
RED = {"r0": "#2a0a10", "r1": "#42121a", "r2": "#621a26", "r3": "#7a1e2a"}
WOOD = {"w0": "#1c1410", "w1": "#2a1c14", "w2": "#3d2c22"}
LAMPS = [(14, 17), (85, 17)]


def main():
    lvl = np.full((H, W), -1, np.int16)      # stone level 0..8, -1 = transparent
    ov = np.full((H, W), "", object)         # named colour overrides (gold, cloth, flames)
    lit = np.zeros((H, W), bool)             # overrides that take the warm glow (stone-like props)
    yy, xx = np.mgrid[0:H, 0:W]

    # ---------- silhouette: lintel top at y 4, stepped crest in the middle ----------
    top = np.full(W, 4)
    top[42:58] = 2
    top[44:56] = 0
    for x in range(W):
        lvl[top[x]:, x] = 2

    # ---------- niche back wall: dark dressed stone, 10x5 running bond ----------
    for y in range(9, H):
        for x in range(5, 95):
            ry = (y - 9) // 5
            m = ((y - 9) % 5 == 4) or ((x + (ry % 2) * 5) % 10 == 9)
            rx = (x + (ry % 2) * 5) // 10
            v = 0 if m else (1 + (((rx * 3 + ry) % 4) == 0))
            if (y - 9) % 5 == 0 and not m:
                v += 1
            lvl[y, x] = v
    # shadow under the lintel and beside the left pilaster
    lvl[9, 5:95] = 0
    lvl[10, 5:95] = np.minimum(lvl[10, 5:95], 1)
    lvl[9:H, 5] = 0
    lvl[9:H, 6] = np.minimum(lvl[9:H, 6], 1)

    # ---------- lintel band, carved zig-zag ----------
    for x in range(W):
        lvl[4, x] = 6
        lvl[5, x] = 5
        lvl[6, x] = 4
        lvl[7, x] = 4
        lvl[8, x] = 2
        t = x % 8
        if t in (0, 4):
            lvl[6, x] = 6 if t == 0 else 2
        if t in (1, 7):
            lvl[6, x] = 3
            lvl[5, x] = 6 if t == 1 else 5
        if t in (2, 6):
            lvl[7, x] = 6 if t == 2 else 2
        if t in (3, 5):
            lvl[7, x] = 3
    lvl[4, 0] = 7

    # ---------- pilasters with a diamond chain ----------
    def pilaster(x0):
        for y in range(9, H):
            for k in range(5):
                x = x0 + k
                v = [5, 4, 4, 3, 2][k]
                lvl[y, x] = v
            py = (y - 11) % 8
            if 11 <= y < 43:
                for k in range(1, 4):
                    d = abs(k - 2) + abs(py - 4)
                    if d == 2:
                        lvl[y, x0 + k] = 6 if (k < 2 or (k == 2 and py < 4)) else 2
                    elif d == 0:
                        lvl[y, x0 + k] = 5
        for k in range(-1, 6):
            x = x0 + k
            if 0 <= x < W:
                lvl[9, x] = 6
                lvl[10, x] = 4
                lvl[11, x] = 2 if k in (-1, 5) else lvl[11, x]
                lvl[43, x] = 6
                lvl[44, x] = 5
                lvl[45, x] = 4

    pilaster(0)
    pilaster(95)
    lvl[9:H, 94] = np.minimum(lvl[9:H, 94], 1)

    # dark outer rim on both sides, so the frame stays crisp wherever CSS anchors it
    lvl[4:H, 0] = 0
    lvl[4:H, W - 1] = 0
    lvl[9:43, 1] = np.maximum(lvl[9:43, 1], 5)

    # ---------- crest: a stepped mountain medallion that holds the (empty) Arkenstone socket ----------
    crest_rows = {0: (44, 55), 1: (44, 55), 2: (42, 57), 3: (42, 57), 4: (40, 59), 5: (40, 59),
                  6: (40, 59), 7: (40, 59), 8: (40, 59), 9: (42, 57), 10: (42, 57), 11: (44, 55), 12: (46, 53)}

    def in_crest(x, y):
        r = crest_rows.get(y)
        return r is not None and r[0] <= x <= r[1]

    for y, (a, b) in crest_rows.items():
        for x in range(a, b + 1):
            v = 4
            if not in_crest(x, y - 1) or not in_crest(x - 1, y):
                v = 6
            elif not in_crest(x, y + 1) or not in_crest(x + 1, y):
                v = 2
            elif not in_crest(x - 1, y - 1):
                v = 5
            lvl[y, x] = v
        # the crest's lower edge casts a 1px shadow on the back wall
    for x in range(42, 58):
        for y in range(9, 14):
            if not in_crest(x, y) and in_crest(x, y - 1):
                lvl[y, x] = 0
    # socket hollow: hexagon centred on (49.5, 6.5), gold rim, four prongs
    hollow = {2: (48, 51), 3: (47, 52), 4: (46, 53), 5: (46, 53), 6: (46, 53), 7: (46, 53),
              8: (46, 53), 9: (47, 52), 10: (48, 51)}

    def in_hollow(x, y):
        r = hollow.get(y)
        return r is not None and r[0] <= x <= r[1]

    for y in range(0, 13):
        for x in range(44, 56):
            if in_hollow(x, y):
                ov[y, x] = OUTLINE if (x + y) % 5 else STONE[1]
            elif any(in_hollow(x + dx, y + dy) for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1))):
                # rim: lit on the upper left, dark gold on the lower right
                ov[y, x] = GOLD["g1"] if (x < 50 and y < 7) else GOLD["g05"]
    for (x, y) in ((47, 2), (52, 2), (47, 10), (52, 10)):
        ov[y, x] = GOLD["g15"]
    ov[1, 49] = GOLD["g2"]
    ov[1, 50] = GOLD["g15"]

    # dark rim along the stepped top edge (one row above the silhouette, outside the crest)
    for x in range(W):
        y = top[x] - 1
        if y >= 0 and lvl[y, x] < 0:
            lvl[y, x] = 0

    # ---------- floor, pedestal (hourglass slot) and the dais ----------
    lvl[46, 5:95] = np.maximum(lvl[46, 5:95], 1)
    lvl[47, 5:95] = 3
    for x in range(77, 95):                   # right pedestal: flat top surface at y 46, x 77..94
        lvl[46, x] = 7 if x < 93 else 5
        lvl[47, x] = 4 if (x - 77) % 4 else 2
    lvl[46, 76] = 0
    lvl[46, 95] = 0
    lvl[47, 76] = 1
    steps = [(46, 25, 74), (44, 29, 70), (42, 33, 66)]
    for (yt, a, b) in steps:
        for x in range(a, b + 1):
            lvl[yt, x] = 6 if x < b else 4
            lvl[yt + 1, x] = 4 if x > a else 5
            if yt == 44 and (x - a) % 6 == 3:
                ov[yt + 1, x] = GOLD["g05"]
        lvl[yt - 1, a:b + 1] = np.minimum(lvl[yt - 1, a:b + 1], 0)  # dark seam above each step
        lvl[yt + 1, b] = 2

    # ---------- banners ----------
    def banner(x0):
        x1 = x0 + 7
        for x in range(x0 - 1, x1 + 2):            # rod
            ov[10, x] = GOLD["g05"] if x0 <= x <= x1 else GOLD["g1"]
        for y in range(11, 36):
            for x in range(x0, x1 + 1):
                k = x - x0
                notch = y - 31                       # swallowtail: V notch from y 32
                if notch > 0 and abs(k - 3.5) < notch:
                    continue
                if y > 33 and not (k in (0, 7) or abs(k - 3.5) >= notch):
                    continue
                c = "r1"
                if k == 0:
                    c = "r2"
                elif k == 7:
                    c = "r0"
                elif k in (3, 4) and y % 6 in (2, 3):
                    c = "r0"                         # soft fold
                ov[y, x] = RED[c]
            # gold border stripes near the edges
            if 11 <= y <= 31:
                ov[y, x0 + 1] = GOLD["g05"]
                ov[y, x1 - 1] = GOLD["g00"]
        # emblem: a stepped peak over a diamond, small and mostly dark gold
        emb = [(3, 15), (4, 15), (2, 16), (3, 16), (4, 16), (5, 16), (1, 17), (2, 17), (5, 17), (6, 17),
               (3, 19), (4, 19), (2, 20), (5, 20), (3, 21), (4, 21)]
        for (k, y) in emb:
            ov[y, x0 + k] = GOLD["g1"] if k <= 3 else GOLD["g05"]
        ov[15, x0 + 3] = GOLD["g2"]
        ov[16, x0 + 2] = GOLD["g15"]

    banner(25)
    banner(67)

    # ---------- throne ----------
    T = np.full((H, W), "", object)   # throne pixels as stone levels "s<n>" or colour names

    def tput(x, y, c):
        if 0 <= x < W and 0 <= y < H:
            T[y, x] = c

    # back posts with stepped gold caps (x 40-42 and 57-59), rising beside the king's head
    for (a, b) in ((40, 42), (57, 59)):
        for y in range(14, 29):
            for x in range(a, b + 1):
                tput(x, y, "s6" if x == a else ("s4" if x < b else "s3"))
        for x in range(a - 1, b + 2):              # stepped stone cap and a gold bead
            tput(x, 13, "s6" if x < b + 1 else "s3")
            tput(x, 14, "s3")
        for x in range(a, b + 1):
            tput(x, 12, "s5" if x < b else "s3")
        tput(a + 1, 11, "g2")
    # back panel x 43-56, top rail at y 16, gold inlay frame, carved diamond (mostly behind the king)
    for y in range(16, 30):
        for x in range(43, 57):
            v = "s3"
            if y == 16:
                v = "s5"
            elif y == 17:
                v = "s2"
            elif x in (44, 55) or y == 18:
                v = "g05"
            elif abs(x - 49.5) + abs(y - 23) < 3.2:
                v = "g1" if x < 50 else "g05"
            tput(x, y, v)
    for x in range(45, 55):                       # stepped crown of the back rail
        tput(x, 15, "s5" if x < 50 else "s4")
    for x in range(47, 53):
        tput(x, 14, "s6" if x < 50 else "s4")
    # seat cushion and the seat's front edge
    for y in range(30, 33):
        for x in range(42, 58):
            tput(x, y, "r3" if y == 30 else ("r2" if y == 31 else "r1"))
    for x in range(41, 59):
        tput(x, 33, "s6" if x < 58 else "s4")
    # base panel below the seat, x 41-58, y 34-41, carved diamond with a gold centre
    for y in range(34, 42):
        for x in range(41, 59):
            v = "s3"
            if x == 41:
                v = "s5"
            elif x == 58:
                v = "s2"
            d = abs(x - 49.5) + abs(y - 37.5)
            if 3.4 < d < 4.6:
                v = "s5" if (x < 50 and y < 38) else "s1"
            elif d < 1.6:
                v = "g1"
            tput(x, y, v)
    # armrests (x 37-41 and 58-62): top surface at y 28, front posts down to the dais
    for (a, b, knob) in ((37, 41, 37), (58, 62, 62)):
        for x in range(a, b + 1):
            tput(x, 28, "s7" if x < b else "s5")
            tput(x, 29, "s4")
        for y in range(30, 42):
            for x in (a, a + 1, a + 2) if a == 37 else (b - 2, b - 1, b):
                tput(x, y, "s5" if x == (a if a == 37 else b - 2) else ("s4" if x != b else "s2"))
        tput(knob, 27, "g2")
        tput(knob + (1 if a == 37 else -1), 27, "g1")
        tput(knob, 28, "g1")
        tput(knob, 34, "g05")
        tput(knob, 38, "g05")

    tmask = T != ""
    # 1px outline around the throne against the wall
    om = np.zeros_like(tmask)
    for dy, dx in ((1, 0), (-1, 0), (0, 1), (0, -1)):
        om |= np.roll(np.roll(tmask, dy, 0), dx, 1)
    om &= ~tmask
    om[42:, :] = False   # the dais carries it
    om[:, 0] = False
    for y in range(H):
        for x in range(W):
            c = T[y, x]
            if om[y, x]:
                ov[y, x] = OUTLINE
            if not c:
                continue
            if c[0] == "s":
                lvl[y, x] = int(c[1:])
                ov[y, x] = ""
                lit[y, x] = True
            elif c in RED:
                ov[y, x] = RED[c]
            else:
                ov[y, x] = GOLD[c]

    # outline the banners against the wall (not along their rod)
    bm = np.zeros((H, W), bool)
    for y in range(11, 36):
        for x in range(W):
            bm[y, x] = ov[y, x] in RED.values() or (ov[y, x] in (GOLD["g05"], GOLD["g00"], GOLD["g1"],
                                                                     GOLD["g15"], GOLD["g2"])
                                                     and (25 <= x <= 32 or 67 <= x <= 74))
    ob = np.zeros_like(bm)
    for dy, dx in ((1, 0), (-1, 0), (0, 1), (0, -1)):
        ob |= np.roll(np.roll(bm, dy, 0), dx, 1)
    ob &= ~bm
    ob[:11, :] = False
    for y, x in zip(*np.where(ob)):
        if ov[y, x] == "":
            ov[y, x] = OUTLINE

    # ---------- small iron-bound chest on the left, under the left sconce (one gold glint) ----------
    C0 = 9                                     # chest x 9..19, lid y 40, standing on the floor row 46
    for y in range(40, 47):
        for x in range(C0, C0 + 11):
            c = WOOD["w1"]
            if y == 40:
                c = WOOD["w2"]
            elif x in (C0, C0 + 10) or y == 46:
                c = WOOD["w0"]
            if x in (C0 + 3, C0 + 7) or y == 43:
                c = STONE[5] if y in (40, 43) else STONE[4]
            ov[y, x] = c
    ov[43, C0 + 5] = GOLD["g2"]
    ov[44, C0 + 5] = GOLD["g05"]
    for x in range(C0 - 1, C0 + 12):
        ov[39, x] = OUTLINE
    for y in range(39, 47):
        ov[y, C0 - 1] = OUTLINE
        ov[y, C0 + 11] = OUTLINE
    for (x, c) in ((C0 + 2, "g1"), (C0 + 3, "g15"), (C0 + 6, "g05")):   # coins spilling over the lid
        ov[39, x] = GOLD[c]
        ov[38, x] = OUTLINE
    for (x, c) in ((C0 + 12, "g1"), (C0 + 13, "g05")):                  # two coins on the floor beside it
        ov[46, x] = GOLD[c]
        ov[45, x] = OUTLINE

    # ---------- sconces and their faint warm glow ----------
    warm = np.zeros((H, W), np.float32)
    flame = [".e.", "e3e", "343", ".3."]
    for (lx, ly) in LAMPS:
        for j, row in enumerate(flame):
            for i, c in enumerate(row):
                if c != ".":
                    ov[ly - 2 + j, lx - 1 + i] = {"e": EMBER, "3": GOLD["g3"], "4": GOLD["g4"]}[c]
        lvl[ly + 2, lx - 1:lx + 2] = 6
        lvl[ly + 3, lx] = 6
        lvl[ly + 4, lx] = 5
        lvl[ly + 5, lx] = 4
        r = 17
        d = np.hypot(xx - lx, (yy - ly) * 1.15)
        warm = np.maximum(warm, np.clip(1 - d / r, 0, 1) * 0.85)
    # a faint warm wash on the throne and dais from both lamps
    d = np.hypot((xx - 49.5) / 1.6, (yy - 30))
    warm = np.maximum(warm, np.clip(1 - d / 22, 0, 1) * 0.4)

    # ---------- compose to RGB ----------
    out = np.zeros((H, W, 3), np.uint8)
    alpha = np.zeros((H, W), bool)
    S = [hexrgb(c) for c in STONE]
    Wm = [hexrgb(c) for c in WARM]
    for y in range(H):
        for x in range(W):
            if lvl[y, x] < 0 and not ov[y, x]:
                continue
            alpha[y, x] = True
            o = ov[y, x]
            if o:
                out[y, x] = hexrgb(o)
                continue
            b = BAYER4[y % 4, x % 4]
            l = int(lvl[y, x])
            g = warm[y, x]
            if g > 0.62 or (g > 0.5 and b < (g - 0.5) / 0.12):
                l += 2
            elif g > 0.3 or (g > 0.16 and b < (g - 0.16) / 0.14):
                l += 1
            l = int(np.clip(l, 0, 8))
            if g > 0.04 and b < min(1, g * 2.4):
                out[y, x] = Wm[l]
            else:
                out[y, x] = S[l]

    # index it: 0 = transparent
    cols = sorted({tuple(out[y, x]) for y in range(H) for x in range(W) if alpha[y, x]})
    pal = ["#000000"] + ["#%02x%02x%02x" % c for c in cols]
    lut = {c: i + 1 for i, c in enumerate(cols)}
    idx = np.zeros((H, W), np.uint8)
    for y in range(H):
        for x in range(W):
            if alpha[y, x]:
                idx[y, x] = lut[tuple(out[y, x])]
    path = os.path.join(OUT, "throne.png")
    n = save_indexed(path, idx, pal, 0)
    upscale(path, os.path.join(OUT, "src", "_scene_throne_x4.png"), 4, "#3b414b")
    print("throne.png", n, "bytes,", len(cols), "colours")


if __name__ == "__main__":
    main()
