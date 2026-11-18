"""Shared palette and helpers for the Erebor pixel-art generators.

Run any generator with:  uv run --with pillow --with numpy --with zopfli python3 <script>.py
"""
import io
import os

import numpy as np
from PIL import Image

OUT = os.path.normpath(os.path.join(os.path.dirname(__file__), ".."))


def hexrgb(h):
    h = h.lstrip("#")
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))


# Stone ramp, dark to light (brief: #0b0c0f #101215 #171a1f #262a31 #3b414b plus in-betweens)
STONE = ["#07080a", "#0b0c0f", "#101215", "#171a1f", "#1e2127", "#262a31", "#30353d", "#3b414b", "#4f5662"]
# The same ramp lit by warm lamp/gold light
WARM = ["#0d0b09", "#12100d", "#191510", "#211b14", "#2b2318", "#362b1d", "#463724", "#5a472d", "#715a37"]
GOLD = {"g00": "#241a0c", "g0": "#3a2a10", "g05": "#5a3e15", "g1": "#7a5418", "g15": "#a67a30",
        "g2": "#cf9f4a", "g3": "#efc77a", "g4": "#fff3c4"}
EMBER = "#d9582b"
EMBER_D = "#8a2f18"
ARK = "#cfe6ff"
ARK_D = "#7fa3c9"

BAYER4 = np.array([[0, 8, 2, 10], [12, 4, 14, 6], [3, 11, 1, 9], [15, 7, 13, 5]]) / 16.0


def bayer(x, y):
    return BAYER4[y % 4, x % 4]


def save_indexed(path, idx, palette, transparent=0):
    """Save a 2D index array as an optimised palette PNG. palette: list of hex (index 0 = transparent)."""
    h, w = idx.shape
    img = Image.fromarray(idx.astype(np.uint8), "P")
    flat = []
    for c in palette:
        flat += list(hexrgb(c))
    img.putpalette(flat)
    bits = 1
    while (1 << bits) < len(palette):
        bits *= 2
    buf = io.BytesIO()
    kw = {"optimize": True, "bits": bits}
    if transparent is not None:
        kw["transparency"] = transparent
    img.save(buf, "PNG", **kw)
    data = buf.getvalue()
    try:
        import zopfli.png
        data2 = zopfli.png.optimize(data)
        if len(data2) < len(data):
            data = data2
    except Exception as e:  # zopfli is optional
        print("zopfli unavailable:", e)
    with open(path, "wb") as f:
        f.write(data)
    return len(data)


def save_rgb(path, rgb):
    img = Image.fromarray(rgb.astype(np.uint8), "RGB")
    img = img.quantize(colors=256, method=Image.Quantize.FASTOCTREE, dither=Image.Dither.NONE) \
        if len(np.unique(rgb.reshape(-1, 3), axis=0)) <= 256 else img
    buf = io.BytesIO()
    img.save(buf, "PNG", optimize=True)
    data = buf.getvalue()
    with open(path, "wb") as f:
        f.write(data)
    return len(data)


def upscale(path_in, path_out, k=4, bg=None):
    im = Image.open(path_in).convert("RGBA")
    if bg:
        base = Image.new("RGBA", im.size, hexrgb(bg) + (255,))
        base.alpha_composite(im)
        im = base
    im.resize((im.width * k, im.height * k), Image.NEAREST).save(path_out)
