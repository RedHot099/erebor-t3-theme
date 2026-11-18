"""Upgrade of the seated king, anchored at (34, 12) on chamber.png.

Frames 0–5 work, 6–9 wait, 10–13 toast (hold 13), 14–17 doze, 18–20 sigh.
"""

import os

import numpy as np

from PIL import Image, ImageDraw

from common import OUT, save_indexed

FW, FH = 32, 32

PAL = {
    ".": "#000000",
    "o": "#07080a",                                                   # outline
    "Y": "#fff3c4", "G": "#efc77a", "g": "#cf9f4a", "n": "#7a5418",   # gold
    "r": "#d9582b",                                                   # ember gem
    "S": "#e2a676", "s": "#a8643e", "x": "#6e3a22",                   # skin
    "W": "#eceef2", "B": "#b8bcc6", "b": "#7a7f8a", "q": "#4f5662",   # beard / hair
    "R": "#b8323e", "C": "#7e1f2b", "c": "#45121b",                   # cloak
    "T": "#4b5d78", "t": "#2f3b50",                                   # tunic
    "K": "#2a1c14", "P": "#4a3426", "p": "#2e2018",                   # belt, trousers, boots
    "L": "#ead8a8", "l": "#b89f6e", "m": "#7a6440",                   # parchment
    "Z": "#d8dce2", "z": "#9aa0aa",                                   # dream "z"
    "v": "#3b414b", "V": "#626a76", "a": "#8fb0d6",                   # gloom cloud, rain
    "A": "#cfe6ff", "D": "#7fa3c9",                                   # waiting rune (Arkenstone light)
}
# glow pixels and effects are not outlined and do not get an outline around them
NO_OUTLINE = set(".oZzvVa")

# ----------------------------------------------------------------------------- parts
# Squared crown plates, a low heavy brow, a broad nose and a split moustache.
# Parts share an 18 px canvas, centred at x 7 in the seated pose.
CROWN = [
    ".YY...YGGG...GG...",
    ".YGG.GYrrGG.GGG...",
    ".GYGGGGrrGGGGGg...",
    ".GgGngGGGGgnGgg...",
    "..ggggnnnnnggn....",
]
BROW = {
    "front":  ("..bSSWWssWWSSsb...", "..bSSoSSSSossb...."),
    "down":   ("..bssWWssWWsssb...", "..bSSoxSSxossb...."),
    "closed": ("..bSSWWssWWSSsb...", "..bSSxxSSxxssb...."),
    "call":   ("..bSSWWssWWSSsb...", "..bSSoASSAossb...."),
}
HEAD = {
    name: CROWN + ["..bSSSSSSSSsssb..."] + list(brow) + [
        "..bSSSSYSxSSssb...",
        ".bBWBSYYSxSBWWBb..",
        ".BWWWWsSsWWWWWBBb.",
        ".WWBBWBxxBWWBBWBb." if name == "call" else
        ".WWBBWBssBWWBBWBb.",
    ]
    for name, brow in BROW.items()
}
TILT_LEFT = (2,) * 5 + (1,) * 6 + (0,) * 7
SLEEP_TILT = (0,) * 7 + (1,) * 6 + (2,) * 5

# Both braids have alternating shaded links and thick, rectangular gold cuffs.
BEARD = [
    ".WWWWBBBWWWWWWBBb.",
    ".BWWBWWbbWWWBWBBb.",
    "..WWWWb..BWWWWBb..",
    "..BBWWb..BWBWWBb..",
    "...WWBb..bWWWBb...",
    "...BWWb..bBWWBb...",
    "...YGGn..Gggn.....",
    "...Gggn..Ggn......",
    "....WBb..WWb......",
    ".....b....b.......",
]

# Seated body (full frame): cloak, tunic, belt, lap, shins and boots. No arms, head or beard.
BODY_SIT = [
    "................................",  # 0
    "................................",  # 1
    "................................",  # 2
    "................................",  # 3
    "................................",  # 4
    "................................",  # 5
    "................................",  # 6
    "................................",  # 7
    "................................",  # 8
    "................................",  # 9
    "................................",  # 10
    "................................",  # 11
    "........cCRRRRRRRRRRCCcc........",  # 12
    "......cRRRRRRRRRRRRRRRCCCc......",  # 13
    ".....cRRRRGGRRRRRRRRGGCCCCc.....",  # 14
    ".....cRRRgggTTTTTTTTnggCCCc.....",  # 15
    "......cRRRRgTTTTTTTtnCCCCc......",  # 16
    "......cRRRRgTTTTTTTtnCCCCc......",  # 17
    "......cRRRRgTTTTTTTtnCCCCc......",  # 18
    "......cRRRRgKKKGGKKKnCCCCc......",  # 19
    "......cRRRRgTTTTTTTtnCCCCc......",  # 20
    "......cRRRgPPPPPPPPPPnCCCc......",  # 21
    "......cRRgPPPPPPPPPPPPnCCc......",  # 22
    "......cCRgPPPPpPPpPPPPnCcc......",  # 23
    "......cCCgPPPpp..ppPPPnccc......",  # 24
    ".......cCnPPPp....pPPPncc.......",  # 25
    ".......ccnPPPp....pPPPncc.......",  # 26
    "........cnPPPp....pPPPnc........",  # 27
    ".........KKKKK....KKKKK.........",  # 28
    "........KKKKKK....KKKKKK........",  # 29
    "........KKKKKK....KKKKKK........",  # 30
    "................................",  # 31
]

# Half-risen body (full frame) for "waiting": up off the seat and leaning toward the viewer's left
# (shoulders 2 px higher and 3 px left of the seated ones, head lowered into them), left foot
# stepped out, the cloak trailing back toward the seat. No arms, head or beard.
BODY_RISE = [
    "................................",  # 0
    "................................",  # 1
    "................................",  # 2
    "................................",  # 3
    "................................",  # 4
    "................................",  # 5
    "................................",  # 6
    "................................",  # 7
    "................................",  # 8
    "................................",  # 9
    "........cCCCCCCCCCCc............",  # 10
    "......cCRRRRRRRRRRRRCc..........",  # 11
    ".....cRRRRRRRRRRRRRRCCc.........",  # 12
    ".....cRRRgTTTTTTTTnCCCCc........",  # 13
    "....cRRRRgTTTTTTTtnCCCCc........",  # 14
    "....cRRRRgTTTTTTTtnCCCCCc.......",  # 15
    "....cRRRRgTTTTTTTtnCCCCCc.......",  # 16
    "....cRRRRgTTTTTTTtnCCCCCCc......",  # 17
    "....cRRRRgKKKGGKKKnCCCCCCc......",  # 18
    "....cRRRRgTTTTTTTtnCCCCCcc......",  # 19
    ".....cRRRgPPPPPPPPnCCCCcc.......",  # 20
    ".....cRRgPPPPPPPPPPnCCcc........",  # 21
    "......cRgPPPPpPPPPPPnccc........",  # 22
    "......cCnPPPp..pPPPPn...........",  # 23
    ".......cPPPp....pPPPn...........",  # 24
    ".......PPPp......PPPp...........",  # 25
    "......PPPp.......PPPp...........",  # 26
    "......PPPp.......PPPp...........",  # 27
    ".....KKKKK.......KKKKK..........",  # 28
    "....KKKKKK.......KKKKKK.........",  # 29
    "....KKKKKK.......KKKKKK.........",  # 30
    "................................",  # 31
]
RISE_HEAD = (3, 4)   # head origin in the waiting pose: 4 px left of the seated head, lowered into the shoulders

PAULDRON = [".GGGn", "GTTtn", "gTttn", ".nnn."]
SCROLL = [
    ".lLLLLLLLLLLm.",
    "lLYYYYYYYYYLLm",
    "lYLlllLLLmmLLm",
    "lLYYYLLlllYLLm",
    ".mmmmmmmmmmmm.",
]
GOBLET = [
    "YYYYYG",
    "GYrrgn",
    "GGrrgn",
    ".GGgn.",
    "..gn..",
    ".Gggn.",
]
HAMMER = ["GYYYYn", "GTTgtn", "GTTgtn", "ngggnn"]
# Head turned crosswise to the shaft on the dais.
FALLEN_HAMMER = [".Gn..", "GYtn.", "GTTgn", ".gTgn", "..nn."]

# Waiting rune: a straight-bar "!" 3 px wide, bar rows 0-6, gap rows 7-8, dot rows 9-10. The bar
# does not taper and nothing glows into the gap, so it cannot read as a goblet's bowl, stem and foot.
RUNE_ROWS = (0, 1, 2, 3, 4, 5, 6, 9, 10)
RUNE_TONES = {0: "DDq", 1: "AAD", 2: "WWA"}   # dim, lit, blazing; columns left to right (light from the left)
CLOUD = [".VVV..", "VVVVV.", "vVVVvv", ".vvvv."]
ZZ = {
    "small": ["zzzz", "..z.", ".z..", "zzzz"],
    "big": ["ZZZZZ", "...Z.", "..Z..", ".Z...", "ZZZZZ"],
}


def blank():
    return [["."] * FW for _ in range(FH)]


def put(g, x, y, c):
    if 0 <= x < FW and 0 <= y < FH and c != ".":
        g[y][x] = c


def paste(g, rows, x0, y0, mirror=False):
    for j, row in enumerate(rows):
        r = row[::-1] if mirror else row
        for i, c in enumerate(r):
            put(g, x0 + i, y0 + j, c)


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


def sleeve(g, pts, lit="R", shade="C"):
    """Cloak sleeve along a polyline (shoulder, elbow, wrist), 2px thick: lit side up/left."""
    for (x0, y0), (x1, y1) in zip(pts, pts[1:]):
        steep = abs(y1 - y0) > abs(x1 - x0)
        for (x, y) in line(x0, y0, x1, y1):
            put(g, x, y, lit)
            if steep:
                put(g, x + 1, y, shade)
            else:
                put(g, x, y + 1, shade)


def hand(g, x, y, fist=True):
    put(g, x, y, "S")
    put(g, x + 1, y, "S")
    put(g, x, y + 1, "s")
    put(g, x + 1, y + 1, "s" if fist else "S")


def sceptre(g, x0, y0, x1, y1, fallen=False):
    """Gold shaft with a squared, steel-faced hammer head."""
    for x, y in line(x0, y0, x1, y1):
        put(g, x, y, "g")
        put(g, x + 1, y, "n")
    if fallen:
        paste(g, FALLEN_HAMMER, x1 - 2, y1 - 2)
    else:
        paste(g, HAMMER, x1 - 2, y1 - 2)


def outline(g):
    src = [row[:] for row in g]
    for y in range(FH):
        for x in range(FW):
            if src[y][x] != ".":
                continue
            for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                xx, yy = x + dx, y + dy
                if 0 <= xx < FW and 0 <= yy < FH and src[yy][xx] not in NO_OUTLINE:
                    g[y][x] = "o"
                    break


def fx_rune(g, x0, y0, level):
    """Waiting rune after the outline pass, with its own 1 px outline (which also fills the 2-row gap,
    leaving a notch on each side between bar and dot). level 0 dim, 1 lit, 2 blazing: white core plus
    two sparkle points beside the bar."""
    cells = {(x0 + i, y0 + j) for j in RUNE_ROWS for i in range(3)}
    for (cx, cy) in cells:
        for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            x, y = cx + dx, cy + dy
            if 0 <= x < FW and 0 <= y < FH and (x, y) not in cells and g[y][x] == ".":
                g[y][x] = "o"
    for (x, y) in cells:
        if 0 <= x < FW and 0 <= y < FH:
            g[y][x] = RUNE_TONES[level][x - x0]
    if level == 2:
        for (x, y) in ((x0 - 2, y0 + 5), (x0 + 4, y0 + 1)):
            if 0 <= x < FW and 0 <= y < FH and g[y][x] == ".":
                g[y][x] = "A"


def fx_z(g, size, x0, y0):
    for j, row in enumerate(ZZ[size]):
        for i, c in enumerate(row):
            if c != "." and 0 <= y0 + j < FH and 0 <= x0 + i < FW:
                g[y0 + j][x0 + i] = c


# ----------------------------------------------------------------------------- poses
def tilt(rows, drops):
    """Shear a part: column c moves down by drops[c] (the part grows by max(drops) rows)."""
    out = [["."] * len(rows[0]) for _ in range(len(rows) + max(drops))]
    for r, row in enumerate(rows):
        for c, ch in enumerate(row):
            if ch != ".":
                out[r + drops[c]][c] = ch
    return ["".join(r) for r in out]


def failed(g, sub, fx):
    sit_base(g)
    sleeve(g, [(23, 14), (25, 17), (26, 19)], lit="C", shade="c")
    hand(g, 25, 19)
    sleeve(g, [(7, 15), (6, 19), (8, 22)])
    hand(g, 7, 22, fist=False)
    top = (4, 3, 5)[sub]
    head = HEAD["closed"]
    paste(g, tilt(BEARD, TILT_LEFT), 6, top + len(head) - 1)
    paste(g, tilt(head, TILT_LEFT), 6, top)
    sceptre(g, 5, 23, 23, 29, fallen=True)
    fx.append(("cloud", sub))


def sit_base(g):
    paste(g, BODY_SIT, 0, 0)
    paste(g, PAULDRON, 5, 13)
    paste(g, PAULDRON, 22, 13, mirror=True)


def frame(i):
    g = blank()
    fx = []   # effects drawn after the outline

    if i <= 5:
        # The left hand anchors the scroll. The right alternates between
        # writing strokes, flattening the curl and lifting the quill.
        sit_base(g)
        sceptre(g, 3, 29, 4, 10)
        sleeve(g, [(7, 16), (7, 20), (9, 23)])
        sleeve(g, [(24, 16), (24, 20), (21, 21)], lit="C", shade="c")
        head_y = (5, 6, 5, 5, 4, 5)[i]
        paste(g, BEARD, 7, head_y + 10)
        paste(g, HEAD["down" if i != 4 else "front"], 7, head_y - 1)
        paste(g, SCROLL, 9, 23)
        hand(g, 9, 23)
        qx, qy = [(19, 22), (17, 23), (21, 23), (18, 22), (21, 20), (20, 21)][i]
        for x, y in line(qx - 2, qy + 3, qx + 2, qy - 4):
            put(g, x, y, "m")
        paste(g, [".YY", "YWB", "LB."], qx + 1, qy - 5)
        hand(g, qx, qy)

    elif i <= 9:
        # ---------------- waiting: half-risen, leaning toward the chat, a "!" rune over his shoulder ----------------
        # No sceptre and no held object: the rune floats free, so nothing reads as a raised goblet.
        sub = i - 6
        paste(g, BODY_RISE, 0, 0)
        sleeve(g, [(20, 11), (23, 13), (25, 16)], lit="C", shade="c")   # right arm braced on the armrest
        hand(g, 25, 16)
        hx, hy = RISE_HEAD
        paste(g, BEARD, hx, hy + 10)
        paste(g, HEAD["call"], hx, hy - 1)
        lift = [0, 1, 2, 1][sub]                                         # open left hand held out to the chat
        sleeve(g, [(7, 12), (3, 13), (1, 12 - lift)])
        paste(g, [".S..", "SSS.", ".Sss"], 1, 10 - lift)
        fx.append(("rune", sub))

    elif i <= 13:
        # ---------------- done-toast: leans back, raises a goblet in his left hand ----------------
        sub = i - 10
        sit_base(g)
        sceptre(g, 3, 29, 4, 10)                       # sceptre leans on the left armrest
        sleeve(g, [(8, 14), (6, 17), (5, 18)])
        hand(g, 4, 17)
        hy = 4 if sub == 3 else 3
        head = ("front", "closed", "down", "closed")[sub]
        paste(g, BEARD, 7, hy + 10)
        paste(g, HEAD[head], 7, hy - 1)
        cup_y = (3, 1, 2, 1)[sub]
        wrist_y = cup_y + 5
        sleeve(g, [(23, 14), (26, 12), (28, wrist_y)], lit="C", shade="c")
        hand(g, 27, wrist_y)
        cup = tilt(GOBLET, (1, 1, 0, 0, 0, 0)) if sub == 2 else GOBLET
        paste(g, cup, 25, cup_y)
        if sub == 1:
            fx.append(("glint", 30, 0))

    elif i <= 17:
        # ---------------- done-doze: nodding off ----------------
        sub = i - 14
        sit_base(g)
        sceptre(g, 3, 29, 4, 10)
        nod = (0, 1, 2, 1)[sub]
        # The off-centre head sinks into one shoulder. The folded hands rise
        # one pixel on the inhale while the boots stay planted.
        paste(g, tilt(BEARD, SLEEP_TILT), 9, 15 + nod)
        paste(g, tilt(HEAD["closed"], SLEEP_TILT), 9, 4 + nod)
        breath = int(sub == 2)
        sleeve(g, [(7, 16), (9, 22), (14, 24 - breath)])
        sleeve(g, [(24, 16), (23, 22), (17, 24 - breath)], lit="C", shade="c")
        hand(g, 14, 23 - breath)
        hand(g, 16, 23 - breath)
        fx.append(("z", sub))

    else:
        failed(g, i - 18, fx)

    outline(g)
    for e in fx:
        if e[0] == "rune":
            sub = e[1]
            # x 24-28 with outline, y 0-12: right of the Arkenstone socket box (frame x 8-23, y <= 4)
            fx_rune(g, 25, [2, 1, 1, 2][sub], [1, 2, 1, 0][sub])
        elif e[0] == "glint":
            x, y = e[1], e[2]
            for (dx, dy, c) in ((0, 0, "Y"), (-1, 0, "G"), (1, 0, "G"), (0, -1, "G"), (0, 1, "G")):
                if 0 <= x + dx < FW and 0 <= y + dy < FH and g[y + dy][x + dx] in ".o":
                    g[y + dy][x + dx] = c
        elif e[0] == "cloud":
            sub = e[1]
            cx, cy = 25, 2 + (sub == 1)
            for j, row in enumerate(CLOUD):
                for k, c in enumerate(row):
                    if c != ".":
                        g[cy + j][cx + k] = c
            drops = [((26, 7), (29, 9)), ((27, 9), (28, 7)), ((26, 9), (29, 8))][sub]
            for (x, y) in drops:
                if g[y][x] in ".o":
                    g[y][x] = "a"
        elif e[0] == "z":
            sub = e[1]
            if sub == 0:
                fx_z(g, "small", 26, 9)
            elif sub == 1:
                fx_z(g, "small", 27, 5)
            elif sub == 2:
                fx_z(g, "big", 26, 0)
                fx_z(g, "small", 26, 10)
            else:
                fx_z(g, "big", 27, 0)
                fx_z(g, "small", 27, 6)
    return g


N_FRAMES = 21


STATES = [
    ("Working", range(0, 6)),
    ("Waiting", range(6, 10)),
    ("Toast", range(10, 14)),
    ("Dozing", range(14, 18)),
    ("Failed", range(18, 21)),
]


def comparison(path):
    chamber = Image.open(os.path.join(OUT, "chamber.png")).convert("RGBA")
    sheets = [
        Image.open(name).convert("RGBA")
        for name in (path,)
    ]
    # Composite at the actual chamber offset before cropping to the throne.
    crop = (27, 1, 73, 49)
    width, height = crop[2] - crop[0], crop[3] - crop[1]
    gap, label = 8, 18
    def row_height(scale):
        return height * scale + 2 * label + gap

    def pair_width(scale):
        return width * scale + 2 * gap

    board = Image.new(
        "RGB", (6 * pair_width(4) + gap, len(STATES) * (row_height(3) + row_height(4)) + gap),
        "#101215",
    )
    draw = ImageDraw.Draw(board)
    for section, scale in enumerate((3, 4)):
        for row, (state, indices) in enumerate(STATES):
            y = section * len(STATES) * row_height(3) + row * row_height(scale) + gap
            draw.text((gap, y), f"{state} / {scale}x", fill="#eceef2")
            for col, i in enumerate(indices):
                for side, sheet in enumerate(sheets):
                    x = gap + col * pair_width(scale) + side * (width * scale + gap)
                    panel = Image.new("RGBA", chamber.size, "#171a1f")
                    panel.alpha_composite(chamber)
                    panel.alpha_composite(sheet.crop((i * FW, 0, (i + 1) * FW, FH)), (34, 12))
                    panel = panel.crop(crop).resize((width * scale, height * scale), Image.Resampling.NEAREST)
                    board.paste(panel, (x, y + label))
                    draw.text((x, y + label + height * scale), f"{i:02d}", fill="#b8bcc6")
    board.save(os.path.join(OUT, "src", "_king_states.png"), optimize=True)


def main():
    keys = list(PAL.keys())
    cmap = {k: i for i, k in enumerate(keys)}
    sheet = np.zeros((FH, FW * N_FRAMES), np.uint8)
    for i in range(N_FRAMES):
        g = frame(i)
        for y in range(FH):
            for x in range(FW):
                sheet[y, i * FW + x] = cmap[g[y][x]]
    path = os.path.join(OUT, "king.png")
    n = save_indexed(path, sheet, [PAL[k] for k in keys], 0)
    print("king.png", n, "bytes", sheet.shape)
    comparison(path)


if __name__ == "__main__":
    main()
