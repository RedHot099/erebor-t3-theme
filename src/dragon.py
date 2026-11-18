"""Dragon sprite strip: 16 frames of 160x70 in one row (2560x70).

Frames 0-3 asleep, 4-7 eye slit, 8-11 awake, 12-15 wrathful.
Side view, facing left, lying IN the hoard: belly, legs and tail sunk in coins, chin resting on a coin heap,
folded wing flat along the back. Bold-outline style (STYLE-v2.md): 1 px #07080a outline, flat cel tones,
scales only along the back, warm bounce light from the gold on the undersides.

The gold in the frame is one bed shared by all 16 frames. Where hoard-back.png lies behind the frame (same
--off-back offset, frame row fy = hoard row fy - 62), the bed copies its pixels, so the seam is invisible at
every bucket; above the hoard surface it adds a mound in the hoard's own coin style. Rebuild after hoard.py.
"""
import os

import numpy as np
from PIL import Image, ImageDraw

from common import OUT, GOLD, EMBER, EMBER_D, ARK, ARK_D, STONE, save_indexed, BAYER4, hexrgb
from hoard import dim_profile, CHAT_X0, CHAT_X1, BACK_TOP_100

# Left edge and top (at 100%) of the dragon on the 480x270 canvas (the v2 preview placed it at left 324px, top 84px).
DRAGON_X, DRAGON_TOP_100 = 324, 84
HOARD_DY = BACK_TOP_100 - DRAGON_TOP_100  # 62: hoard-back row = frame row - 62

FW, FH, NF = 160, 70, 4
STATES = ["asleep", "stirring", "awake", "wrathful"]

PAL = [
    "#000000",  # 0 transparent
    "#07080a",  # 1 outline
    "#1a0706",  # 2 inner line / deepest hide
    "#2a0c08",  # 3 hide shadow
    "#4a1714",  # 4 hide base
    "#6b2a1e",  # 5 hide light
    "#94432a",  # 6 hide highlight
    "#3d3022",  # 7 horn dark
    "#7d6a4e",  # 8 horn mid
    "#bfa983",  # 9 horn light, teeth, claws
    "#ffb347",  # 10 eye amber
    GOLD["g4"],  # 11 hot core / glint #fff3c4
    EMBER,  # 12 ember
    EMBER_D,  # 13 ember dark
    STONE[5],  # 14 smoke dark #262a31
    STONE[7],  # 15 smoke mid #3b414b
    STONE[8],  # 16 smoke light #4f5662
    GOLD["g00"],  # 17
    GOLD["g0"],  # 18
    GOLD["g05"],  # 19
    GOLD["g1"],  # 20
    GOLD["g15"],  # 21
    GOLD["g2"],  # 22
    GOLD["g3"],  # 23
    ARK_D,  # 24 (only if the copied hoard holds them)
    ARK,  # 25
    "#5c6b80",  # 26
]
OUTL, INL, SH, BA, LI, HI = 1, 2, 3, 4, 5, 6
HD, HM, HL = 7, 8, 9
AMB, HOT, EMB, EMBD = 10, 11, 12, 13
SM0, SM1, SM2 = 14, 15, 16
# gold ramp positions 0..7 (g00 g0 g05 g1 g15 g2 g3 g4), as in hoard.py
GR = [17, 18, 19, 20, 21, 22, 23, 11]
GPOS = {c: i for i, c in enumerate(GR)}
G1, G2 = GR[3], GR[5]

HIDE = (SH, BA, LI, HI)

YY, XX = np.mgrid[0:FH, 0:FW]


# ---------------------------------------------------------------- masks
def poly(points):
    im = Image.new("L", (FW, FH), 0)
    ImageDraw.Draw(im).polygon([(float(x), float(y)) for x, y in points], fill=1, outline=1)
    return np.array(im, bool)


def ellipse(cx, cy, rx, ry):
    im = Image.new("L", (FW, FH), 0)
    ImageDraw.Draw(im).ellipse([cx - rx, cy - ry, cx + rx, cy + ry], fill=1, outline=1)
    return np.array(im, bool)


def tube(pts, widths, steps=24):
    """Smooth tube through control points (Catmull-Rom), width interpolated."""
    im = Image.new("L", (FW, FH), 0)
    d = ImageDraw.Draw(im)
    P = np.array(pts, float)
    Wd = np.array(widths, float)
    P = np.vstack([P[0], P, P[-1]])
    for i in range(1, len(P) - 2):
        for t in np.linspace(0, 1, steps):
            t2, t3 = t * t, t * t * t
            c = 0.5 * ((2 * P[i]) + (-P[i - 1] + P[i + 1]) * t + (2 * P[i - 1] - 5 * P[i] + 4 * P[i + 1] - P[i + 2]) * t2
                       + (-P[i - 1] + 3 * P[i] - 3 * P[i + 1] + P[i + 2]) * t3)
            r = (Wd[i - 1] * (1 - t) + Wd[i] * t) / 2
            d.ellipse([c[0] - r, c[1] - r, c[0] + r, c[1] + r], fill=1)
    return np.array(im, bool)


def shift(m, dx, dy):
    """out[y + dy, x + dx] = m[y, x]"""
    out = np.zeros_like(m)
    h, w = m.shape
    ys = slice(max(0, dy), h + min(0, dy))
    yd = slice(max(0, -dy), h + min(0, -dy))
    xs = slice(max(0, dx), w + min(0, dx))
    xd = slice(max(0, -dx), w + min(0, -dx))
    out[ys, xs] = m[yd, xd]
    return out


def edge4(m):
    e = np.zeros_like(m)
    for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
        e |= m & ~shift(m, dx, dy)
    return e


def dome(m, R=8.0, light=(-0.55, -0.85, 0.75), cuts=(0.30, 0.62, 0.86), ramp=None, vgrad=0.0, vspan=None):
    """Round-form cel shading: a dome height from the distance to the edge, its normal lit from the upper
    left, quantised to flat tones (dark, base, light, highlight)."""
    dist = np.zeros(m.shape, float)
    cur = m.copy()
    k = 0
    while cur.any() and k < 40:
        k += 1
        dist[cur] += 1
        nb = cur & shift(cur, 1, 0) & shift(cur, -1, 0) & shift(cur, 0, 1) & shift(cur, 0, -1)
        if k % 2 == 0:
            nb &= shift(cur, 1, 1) & shift(cur, -1, -1) & shift(cur, 1, -1) & shift(cur, -1, 1)
        cur = nb
    u = np.clip(dist / R, 0, 1)
    h = R * np.sqrt(1 - (1 - u) ** 2)
    hp = np.pad(h, 1)
    gx = (hp[1:-1, 2:] - hp[1:-1, :-2]) / 2
    gy = (hp[2:, 1:-1] - hp[:-2, 1:-1]) / 2
    n = np.stack([-gx, -gy, np.ones_like(h)], -1)
    n /= np.linalg.norm(n, axis=-1, keepdims=True)
    lv = np.array(light, float)
    lv /= np.linalg.norm(lv)
    lam = n @ lv
    if vgrad:  # the lower body turns away from the lamps, into the gold's shadow
        ys = np.nonzero(m.any(1))[0]
        y0, y1 = vspan or (ys.min(), ys.max())
        lam = lam - vgrad * np.clip((YY - y0) / max(1, y1 - y0), 0, 1)
    dark, base, lit, hi = ramp or HIDE
    c = np.zeros(m.shape, np.uint8)
    c[m] = dark
    c[m & (lam > cuts[0])] = base
    c[m & (lam > cuts[1])] = lit
    c[m & (lam > cuts[2])] = hi
    return c


# ---------------------------------------------------------------- the gold bed
def load_hoard():
    """hoard-back.png cropped to the frame, as our palette indices (0 where the hoard is transparent)."""
    im = Image.open(os.path.join(OUT, "hoard-back.png")).convert("RGBA")
    a = np.array(im)
    lut = {hexrgb(c): i for i, c in enumerate(PAL) if i}
    out = np.zeros((FH, FW), np.uint8)
    for fy in range(FH):
        hy = fy - HOARD_DY
        if not (0 <= hy < a.shape[0]):
            continue
        for fx in range(FW):
            cx = DRAGON_X + fx
            if cx >= a.shape[1]:
                continue
            r, g, b, al = a[hy, cx]
            if al == 0:
                continue
            out[fy, fx] = lut[(int(r), int(g), int(b))]
    return out


def bed_surface(hoard_top):
    """Top row of the gold per frame column: a chin heap, the sunk neck and belly, rounded coin drifts that
    climb over the forepaw, up the flank and over the tail."""
    x = np.arange(FW, dtype=float)
    s = np.full(FW, 57.0) + 0.7 * np.sin(x / 3.3) + 0.5 * np.sin(x / 7.9 + 2)
    # chin heap: a round mound under the jaw, top row 53-54, a dip behind it, a slope down in front of the snout
    chin = 53.6 + 3.2 * ((x - 18) / 18) ** 2
    s = np.where(x < 37, chin, s)
    s = np.where((x >= 37) & (x < 55), 58.0, s)
    s = np.where(x < 3, 57.0 + (3 - x) * 1.6, s)
    s = np.where((x > 112) & (x < 150), s + 1.5, s)  # the tail arch lies on top here
    for (cx, w, h) in ((60, 4.0, 4.2), (104, 7.0, 7.5), (143, 4.5, 5.5)):
        s = s - h * np.clip(1 - ((x - cx) / w) ** 2, 0, 1) ** 0.6
    s = np.round(s).astype(int)
    return np.minimum(s, hoard_top)


def coin_rows(b):
    return [[None, b + 1, b + 1, None], [b, b + 1, b, b - 1], [None, b - 1, b - 1, None]]


def dimmed(pos, fx, fy):
    """Apply hoard.py's chat-column dimming to a gold ramp position at frame pixel (fx, fy)."""
    cx = DRAGON_X + fx
    dm = dim_profile(cx)
    pos = pos - int(dm) - (1 if (dm % 1) > BAYER4[fy % 4, cx % 4] else 0)
    if CHAT_X0 - 4 <= cx <= CHAT_X1 + 4:
        pos = min(pos, 3)
    return max(0, min(7, pos))


def build_bed(hoard):
    """Returns (bed colour array, bed mask). Same for every frame."""
    has = hoard > 0
    hoard_top = np.array([np.argmax(has[:, x]) if has[:, x].any() else FH for x in range(FW)])
    surf = bed_surface(hoard_top)
    ls = np.array([surf[max(0, x - 4):x + 5].min() for x in range(FW)])  # local surface, as hoard.py
    hls = np.array([hoard_top[max(0, x - 4):x + 5].min() for x in range(FW)])
    rng = np.random.default_rng(7)
    bed = np.zeros((FH, FW), np.uint8)
    mask = YY >= surf[None, :]

    def bright(y, x):
        return 5 if y - ls[x] < 2 else 4

    # mound gaps (two ramp steps under the coin tone, as in hoard.py)
    for x in range(FW):
        for y in range(surf[x], FH):
            if not has[y, x]:
                bed[y, x] = GR[dimmed(bright(y, x) - 3, x, y)]
    # mound coins, staggered, top to bottom
    coins = []
    for y in range(40, FH, 2):
        off = (y // 2) % 2 * 2
        for x in range(-4 + off, FW, 4):
            if rng.random() < 0.7:
                coins.append((y + int(rng.integers(-1, 1)), x + int(rng.integers(-1, 2))))
    coins.sort()
    for (cy, cx) in coins:
        xc = min(max(cx + 1, 0), FW - 1)
        if cy < surf[xc] - 1 or cy >= FH:
            continue
        if cy < surf[xc] and rng.random() < 0.5:
            continue
        b = bright(max(cy, 0), xc) - (1 if rng.random() < 0.25 else 0)
        rows = coin_rows(b)
        if rng.random() < 0.15 and cy - ls[xc] < 3:
            rows[0][1] = b + 2
        for j in range(3):
            for i in range(4):
                v = rows[j][i]
                y, x = cy + j, cx + i
                if v is None or not (0 <= y < FH and 0 <= x < FW):
                    continue
                if y < surf[x] - 1 or has[y, x]:
                    continue
                bed[y, x] = GR[dimmed(v, x, y)]
                mask[y, x] = True
    # below the hoard surface: the hoard's own pixels; its bright crest goes one step down where the mound
    # covers it, so no second crest line shows inside the mound
    for x in range(FW):
        for y in range(FH):
            if not has[y, x] or y < surf[x] - 1:
                continue
            c = hoard[y, x]
            if c in GPOS and y - hls[x] < 2 and y - ls[x] >= 2 and dim_profile(DRAGON_X + x) < 1:
                c = GR[max(0, GPOS[c] - 1)]
            bed[y, x] = c
            mask[y, x] = True
    return bed, mask, surf


# ---------------------------------------------------------------- drawing helpers
def put(img, x, y, c):
    if 0 <= y < FH and 0 <= x < FW:
        img[y, x] = c


def spike(x, y, h, lean=1):
    """Triangle mask: base centred at (x, y), tip h px up, leaning back (to +x)."""
    return poly([(x - h // 2 - 1, y + 1), (x + lean * h // 2 + 1, y - h), (x + h // 2 + 1, y + 1)])


class Layer:
    """Parts painted back to front: colour, part id, and an inner-line rule."""

    def __init__(self):
        self.col = np.zeros((FH, FW), np.uint8)
        self.pid = np.zeros((FH, FW), np.int16)
        self.n = 0
        self.lines = []  # (mask of part, line colour)

    def add(self, m, colours, line=INL):
        self.n += 1
        behind = (self.pid > 0) & ~m
        self.col[m] = colours[m]
        self.pid[m] = self.n
        if line:
            # front part's own boundary pixels where it overlaps an earlier part
            touch = np.zeros_like(m)
            for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                touch |= m & shift(behind, -dx, -dy)
            self.lines.append((touch, line, self.n))
        return self.n

    def apply_lines(self):
        for touch, line, n in self.lines:
            self.col[touch & (self.pid == n)] = line


# ---------------------------------------------------------------- the dragon
def ctrl(points, xs):
    px, py = zip(*points)
    return np.round(np.interp(xs, px, py)).astype(int)


# head profile in frame coords; the jaw rests on the chin heap (top row 54)
HEAD_X0, HEAD_X1, MOUTH_X1 = 1, 55, 36
HEAD_TOP = [(1, 45), (2, 43), (3, 42), (6, 42), (8, 43), (12, 44), (18, 44), (22, 43), (25, 41), (27, 38), (29, 36),
            (40, 36), (43, 37), (49, 39), (53, 42), (55, 46)]
HEAD_MOUTH = [(1, 50), (26, 50), (32, 49), (36, 48)]
HEAD_JAW = [(1, 51), (2, 53), (5, 54), (9, 55), (44, 55), (50, 56), (54, 54), (55, 51)]
EYE_X0, EYE_Y0 = 30, 41  # eye stamps: 9 wide, rows 41-46

EYE = {
    "asleep": ["",
               "..OOOOO..",
               ".OhhhhhO.",
               "OlllllllO",
               ".OOOOOOO.",
               "..lllll.."],
    "awake": ["",
              "..OOOOO..",
              ".OHAOAAO.",
              "OAAAOAAAO",
              ".OEEOEEO.",
              "..OOOOO.."],
    "wrathful": ["..OOOOOO.",
                 ".OAHOHAAO",
                 "OAHHOHHAO",
                 "OAAAOAAAO",
                 ".OEEOEEO.",
                 "..OOOOO.."],
}
EYE_KEY = {"O": OUTL, "A": AMB, "H": HOT, "E": EMB, "D": EMBD, "h": HI, "l": LI, "s": SH, "b": BA, "i": INL}
SLIT = [["D", "E", "E", "E", "E", "E", "D"], ["E", "A", "A", "A", "A", "A", "E"], ["A", "A", "H", "H", "H", "A", "A"],
        ["E", "A", "A", "A", "A", "E", "D"]]


def stamp(img, x0, y0, rows, key):
    for j, row in enumerate(rows):
        for i, ch in enumerate(row):
            if ch != ".":
                put(img, x0 + i, y0 + j, key[ch])


def snarl(x, lift):
    """How far the upper head rises at column x when the dragon bares its teeth (0 from the eye back)."""
    return int(round(lift * max(0.0, 1 - (x - 1) / 30)))


def head(lift):
    """Upper head and lower jaw masks and their colours, built column by column."""
    xs = np.arange(FW)
    top, mouth, jb = ctrl(HEAD_TOP, xs), ctrl(HEAD_MOUTH, xs), ctrl(HEAD_JAW, xs)
    up = np.zeros((FH, FW), bool)
    jaw = np.zeros((FH, FW), bool)
    col = np.zeros((FH, FW), np.uint8)
    for x in range(HEAD_X0, HEAD_X1 + 1):
        d = snarl(x, lift)
        t = top[x] - d
        if x <= MOUTH_X1:
            m = mouth[x] - d
            up[t:m + 1, x] = True
            jaw[mouth[x] + 1:jb[x] + 1, x] = True
            col[t:m + 1, x] = BA
            col[t + 1, x] = HI
            col[t + 2:t + 4, x] = LI
            col[m - 1, x] = SH
            col[m, x] = OUTL  # mouth line
            col[mouth[x] + 1, x] = SH  # under the lip
            col[mouth[x] + 2:jb[x] + 1, x] = BA
        else:
            up[t:jb[x] + 1, x] = True
            col[t:jb[x] + 1, x] = BA
            col[t + 1, x] = HI if x < 46 else LI
            col[t + 2:t + 4, x] = LI
    # brow: the overhang shades the eye
    for x in range(29, 42):
        col[41 - snarl(x, lift), x] = SH
    return up, jaw, col


def draw(state, f):
    angry = state == "wrathful"
    breath = ([0, 1, 0, 1] if angry else [0, 1, 1, 0])[f]
    lift = 3 if angry else 0
    L = Layer()

    def by(x, y):
        """breathing: the ribs rise, the neck in front of the shoulder stays put"""
        return y - (breath if x > 76 else 0)

    # far horn, behind the neck: only its tip clears the neck line
    far_horn = tube([(51, 42), (59, 38), (68, 33), (77, 30)], [5, 4, 3, 1])
    L.add(far_horn, dome(far_horn, R=2, ramp=(HD, HD, HM, HM)), line=OUTL)

    # dorsal spikes along the spine; the folded wing hides their bases
    spikes = np.zeros((FH, FW), bool)
    for (sx, sy, h) in ((108, 23, 5), (117, 23, 5), (126, 23, 5), (135, 24, 4), (143, 28, 4)):
        spikes |= spike(sx, by(sx, sy), h)
    L.add(spikes, dome(spikes, R=2, ramp=(HD, HM, HL, HL)), line=OUTL)

    # body: neck, shoulders, back, rump; the belly is in the gold
    top = [(50, 47), (52, 41), (56, 38), (62, 35), (70, 32), (78, 29), (86, 26), (94, 24), (104, 23), (116, 23),
           (126, 23), (134, 24), (141, 27), (146, 31), (150, 36), (153, 43), (154, 52), (154, 66), (48, 66)]
    body = poly([(x, by(x, y)) for x, y in top])
    n_body = L.add(body, dome(body, R=12, vgrad=0.5, vspan=(30, 56)))

    # haunch, under the wing's trailing edge
    haunch = ellipse(135, 47, 15, 12)
    L.add(haunch, dome(haunch, R=9, vgrad=0.2, vspan=(40, 58)), line=INL)

    # folded wing, flat along the back; the wrist is the high point
    wy = -breath
    wrist = (95, 19 + wy)
    tips = [(101, 43), (115, 43), (129, 41), (141, 38), (151, 34)]
    sags = [(93, 38), (108, 38), (122, 37), (135, 35), (146, 33)]
    wing_pts = [(84, 34), (89, 25), wrist, (110, 22 + wy), (126, 23 + wy), (141, 26 + wy), (152, 29 + wy),
                (154, 32 + wy), tips[4]]
    for t, s_ in zip(tips[::-1][1:], sags[::-1][:-1]):
        wing_pts += [s_, t]
    wing_pts += [sags[0]]
    wing = poly(wing_pts)
    wc = np.zeros((FH, FW), np.uint8)
    wc[wing] = SH
    ang = np.degrees(np.arctan2(YY - wrist[1], XX - wrist[0]))
    tip_ang = [np.degrees(np.arctan2(ty - wrist[1], tx - wrist[0])) for tx, ty in tips]
    for a_hi, a_lo in zip(tip_ang[:-1], tip_ang[1:]):
        span = a_hi - a_lo
        wc[wing & (ang < a_hi) & (ang > a_hi - span * 0.34)] = BA
        wc[wing & (ang > a_lo) & (ang < a_lo + span * 0.20)] = INL
    bones = Image.new("L", (FW, FH), 0)
    bd = ImageDraw.Draw(bones)
    for t in tips[:-1]:
        bd.line([wrist, t], fill=1, width=1)
    bones = np.array(bones, bool) & wing
    wc[bones] = LI
    arm = tube([(85, 34), (89, 26), (wrist[0], wrist[1] + 1), (110, 23 + wy), (126, 24 + wy), (141, 27 + wy),
                (152, 30 + wy)], [5, 5, 4, 3, 3, 2, 2])
    arm &= wing | shift(wing, 0, -1)
    ac = dome(arm, R=2)
    wc[arm] = ac[arm]
    L.add(wing | arm, wc, line=INL)

    # tail: from the rump, round the back of the haunch, forward along the coins to a spade by the forearm
    tail = tube([(147, 45), (151, 51), (149, 56), (143, 58), (137, 55), (130, 52), (122, 52), (115, 54), (107, 58)],
                [8, 8, 8, 8, 8, 7, 7, 6, 5])
    L.add(tail, dome(tail, R=3, vgrad=0.2, vspan=(48, 60)), line=OUTL)
    tsp = np.zeros((FH, FW), bool)
    for sx in (135, 127, 119):
        col = np.nonzero(tail[:, sx])[0]
        tsp |= spike(sx, col.min() + 1, 4) & ~tail
    L.add(tsp, dome(tsp, R=1, ramp=(HD, HM, HL, HL)), line=OUTL)

    # foreleg: upper arm against the chest, forearm lying forward on the coins, paw half buried
    upper = tube([(86, 35), (84, 44), (80, 51)], [13, 12, 10])
    L.add(upper, dome(upper, R=6, vgrad=0.25, vspan=(36, 56)), line=OUTL)
    fore = tube([(81, 51), (72, 52), (65, 52)], [9, 8, 7]) | ellipse(62, 52, 4, 4)
    L.add(fore, dome(fore, R=4), line=OUTL)

    # cheek frill behind the jaw hinge (bone), then the head over it
    frill = poly([(49, 43), (65, 39), (54, 47)]) | poly([(50, 49), (66, 51), (51, 54)])
    L.add(frill, dome(frill, R=2, ramp=(HD, HM, HL, HL)), line=OUTL)
    up, jaw, hc = head(lift)
    L.add(jaw, hc, line=INL)
    L.add(up, hc, line=INL)

    # near horn, from the back of the skull, sweeping back over the neck
    horn = tube([(46, 39), (55, 34), (66, 30), (77, 26), (87, 24)], [7, 6, 4, 2, 1])
    L.add(horn, dome(horn, R=3, ramp=(HD, HM, HL, HL), cuts=(0.2, 0.55, 0.9)), line=OUTL)
    he = edge4(horn)
    for (x0, y0) in ((53, 33), (60, 30), (67, 28)):  # growth rings
        for j in range(4):
            if horn[y0 + j, x0 + j // 2] and not he[y0 + j, x0 + j // 2]:
                L.col[y0 + j, x0 + j // 2] = HD

    # no lone pixels on the hide: a pixel whose four neighbours share one tone of the same part takes that tone
    c, pid = L.col, L.pid
    for _ in range(2):
        for y in range(1, FH - 1):
            for x in range(1, FW - 1):
                if c[y, x] not in (SH, BA, LI, HI):
                    continue
                nb = [(c[y + dy, x + dx], pid[y + dy, x + dx]) for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1))]
                if all(n == nb[0] for n in nb) and nb[0][1] == pid[y, x] and nb[0][0] != c[y, x]:
                    c[y, x] = nb[0][0]
    L.apply_lines()
    img = L.col
    dragon = L.pid > 0

    # scales, suggested along the back only: a neat row of small arcs under the neck crest
    darker = {HI: LI, LI: BA, BA: SH, SH: INL}
    for i, x in enumerate(range(58, 88, 4)):
        col = np.nonzero(horn[:, x])[0]
        yv = (col.max() if len(col) else np.nonzero(body[:, x])[0].min()) + 3 + (i % 2)
        pts = ((x - 1, yv), (x, yv + 1), (x + 1, yv))
        if all(L.pid[y, xx] == n_body and img[y, xx] in darker for xx, y in pts):
            for xx, y in pts:
                img[y, xx] = darker[img[y, xx]]

    # ---------------- head details
    xs = np.arange(FW)
    mouth = ctrl(HEAD_MOUTH, xs)
    if angry:
        # bared teeth between the raised lip and the jaw, glow in the throat
        for x in range(2, MOUTH_X1 + 1):
            ylip = mouth[x] - snarl(x, lift)
            gap = list(range(ylip + 1, mouth[x] + 1))
            for y in gap:
                img[y, x] = EMB if (x + f) % 4 else HOT
                dragon[y, x] = True
            if gap and x % 3 != 0:
                put(img, x, gap[0], HL)  # upper teeth
            if len(gap) > 2 and x % 3 == 1:
                put(img, x, gap[1], HL)  # long fangs at the front
            if len(gap) > 1 and x % 3 == 2:
                put(img, x, gap[-1], HL)  # lower teeth
            put(img, x, ylip, OUTL)
    else:
        for (x, y) in ((7, 51), (7, 52), (13, 51)):
            put(img, x, y, HL)  # fang tips over the lower lip
    # nostril
    for (x, y, c) in ((3, 44, OUTL), (4, 44, OUTL), (4, 45, SH)):
        put(img, x, y - snarl(x, lift), c)
    if angry:
        put(img, 3, 44 - snarl(3, lift), HOT if f % 2 == 0 else EMB)
        put(img, 4, 44 - snarl(4, lift), EMB)

    # jaw muscle: an inner-line arc from the mouth corner down to the hinge, lit above it
    for (x, y) in ((37, 49), (38, 50), (39, 51), (40, 51), (41, 52), (42, 52), (43, 53)):
        put(img, x, y, INL)
        if img[y - 1, x] in (BA, SH):
            put(img, x, y - 1, LI)
    if angry:  # the eye's glow on the underside of the brow
        for x in range(29, 42):
            if img[41 - snarl(x, lift), x] == SH:
                put(img, x, 41 - snarl(x, lift), EMBD)

    # ---------------- eye: big, one tone brighter than anything round it
    ey0 = EYE_Y0 - snarl(EYE_X0 + 4, lift)
    if state == "stirring":
        rows = ["",
                "..OOOOO..",
                ".OhhhhhO.",
                "OOOOOOOOO",
                "O" + "".join(SLIT[f]) + "O",
                ".OOOOOOO."]
        stamp(img, EYE_X0, ey0, rows, EYE_KEY)
        if f == 2:
            put(img, EYE_X0 - 1, ey0 + 4, EMB)
            put(img, EYE_X0 + 9, ey0 + 4, EMB)
    elif state == "awake":
        rows = list(EYE["awake"])
        if f in (2, 3):  # glance towards the chat
            rows[2], rows[3], rows[4] = ".OHOAAAO.", "OAAOAAAAO", ".OEOEEEO."
        stamp(img, EYE_X0, ey0, rows, EYE_KEY)
    elif state == "wrathful":
        stamp(img, EYE_X0, ey0, EYE["wrathful"], EYE_KEY)
        for (x, y) in ((28, 43), (29, 42), (30, 42), (31, 41)):  # brow pressed down at the front
            put(img, x, y + ey0 - EYE_Y0, OUTL)
    else:
        stamp(img, EYE_X0, ey0, EYE["asleep"], EYE_KEY)
    return img, dragon


def claws(out, bed_m, pts):
    """Ivory claws hooking forward and down into the coins; drawn after the outline pass, never over the gold."""
    shape = [(0, 0, OUTL), (1, 0, OUTL), (-1, 1, OUTL), (0, 1, HL), (1, 1, HM), (-1, 2, OUTL), (0, 2, HL), (1, 2, OUTL),
             (-1, 3, HL)]
    for (x, y) in pts:
        for (dx, dy, c) in shape:
            if 0 <= y + dy < FH and 0 <= x + dx < FW and not bed_m[y + dy, x + dx]:
                out[y + dy, x + dx] = c


def frame(state, f, bed, bed_m, surf):
    img, dragon = draw(state, f)

    # the gold bed is in front of everything
    vis = dragon & ~bed_m
    out = np.zeros((FH, FW), np.uint8)
    out[vis] = img[vis]
    empty = ~vis & ~bed_m
    near_empty = np.zeros_like(vis)
    for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
        near_empty |= vis & shift(empty, -dx, -dy)
    keep = np.isin(out, [AMB, HOT, EMB, EMBD])
    out[near_empty & ~keep] = OUTL
    # warm bounce from the gold: the hide row just above the coins, and a lit row above that
    hide = np.isin(out, [SH, BA, LI, HI, INL])
    above_gold = vis & shift(bed_m, 0, -1)
    out[above_gold & hide] = G1
    above2 = vis & shift(above_gold, 0, -1) & np.isin(out, [SH, BA, INL])
    out[above2] = LI
    for x in range(CHAT_X1 + 1 - DRAGON_X, 34):  # the jaw on its heap: brightest bounce, outside the chat band
        y = surf[x] - 1
        if 0 <= y < FH and out[y, x] == G1 and x % 4 != 1:
            out[y, x] = G2
    out[bed_m] = bed[bed_m]
    claws(out, bed_m, [(57, 49), (56, 52)])

    # loose coins resting on the forearm and the tail
    for (cx, cy) in ((72, 46), (141, 51)):
        for j, row in enumerate(coin_rows(5)):
            for i, v in enumerate(row):
                if v is not None:
                    put(out, cx + i, cy + j, GR[v])
        for i in (1, 2):
            if out[cy + 3, cx + i] in (SH, BA, LI, HI):
                put(out, cx + i, cy + 3, INL)

    # ---------------- smoke and embers
    if state == "wrathful":
        ph = f * np.pi / 2
        for k in range(24):
            yc = 41 - k * 1.7
            r = 1.4 + k * 0.22
            xc = 3 + k * 0.35 + 2.0 * np.sin(k * 0.35 - ph) * min(1, k / 5)
            for y in range(int(yc - r) - 1, int(yc + r) + 2):
                for x in range(int(xc - r) - 1, int(xc + r) + 2):
                    if not (0 <= y < FH and 0 <= x < FW) or out[y, x] not in (0, SM0, SM1, SM2):
                        continue
                    dd = ((x - xc) ** 2 + (y - yc) ** 2) / (r * r)
                    if dd > 1:
                        continue
                    bb = BAYER4[y % 4, x % 4]
                    if dd > 0.55 and bb > (1 - k / 28) * 0.9:
                        continue
                    if k > 16 and bb > (24 - k) / 8:
                        continue
                    c = SM0
                    if dd < 0.55:
                        c = SM1
                    if dd < 0.25 and y < yc:
                        c = SM2
                    if out[y, x] == 0 or c > out[y, x]:
                        out[y, x] = c
        embers = [[(3, 36), (9, 27), (2, 18), (11, 8)], [(4, 33), (10, 24), (4, 15), (13, 5)],
                  [(2, 35), (8, 28), (3, 20), (10, 10)], [(5, 31), (11, 22), (1, 13), (12, 6)]][f]
        for i, (x, y) in enumerate(embers):
            put(out, x, y, [HOT, AMB, EMB, EMB][i])
    else:
        wisp = {0: [], 1: [], 2: [(2, 41), (1, 40), (1, 39)], 3: [(1, 39), (0, 38), (1, 37), (0, 36)]}[f]
        for (x, y) in wisp:
            if out[y, x] == 0:
                out[y, x] = SM0 if state == "asleep" else SM1
    return out


def main():
    hoard = load_hoard()
    bed, bed_m, surf = build_bed(hoard)
    strip = np.zeros((FH, FW * NF * 4), np.uint8)
    for s, st in enumerate(STATES):
        for f in range(NF):
            strip[:, (s * NF + f) * FW:(s * NF + f + 1) * FW] = frame(st, f, bed, bed_m, surf)
    used = sorted(set(np.unique(strip).tolist()))
    n = save_indexed(os.path.join(OUT, "dragon.png"), strip, PAL, 0)
    print("dragon.png", n, "bytes", strip.shape, "colours used", len(used))
    # review sheet: frame 3 of every state (asleep, eye slit / awake, wrathful), 4x, on the scene's dark stone
    rgb = np.array([hexrgb(c) for c in PAL], np.uint8)
    rgb[0] = hexrgb("#101215")
    sheet = np.zeros((FH * 2, FW * 2), np.uint8)
    for s in range(4):
        sheet[(s // 2) * FH:(s // 2 + 1) * FH, (s % 2) * FW:(s % 2 + 1) * FW] = strip[:, (s * NF + 2) * FW:(s * NF + 3) * FW]
    Image.fromarray(rgb[sheet]).resize((FW * 8, FH * 8), Image.NEAREST).save(os.path.join(OUT, "src", "_dragon_x4.png"))


if __name__ == "__main__":
    main()
