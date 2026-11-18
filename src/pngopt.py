"""Smallest lossless PNG for a small pixel-art image: used-colours palette, minimal bit depth, zopfli."""
import io, struct, zlib, itertools
from PIL import Image
import zopfli.zlib as zz

def _chunk(t, d):
    return struct.pack(">I", len(d)) + t + d + struct.pack(">I", zlib.crc32(t + d) & 0xffffffff)

def best_png(img, iters=60):
    im = img.convert("RGBA")
    w, h = im.size
    px = list(im.get_flattened_data()) if hasattr(im, "get_flattened_data") else list(im.getdata())
    # normalise fully transparent pixels to one colour
    px = [(0, 0, 0, 0) if p[3] == 0 else p for p in px]
    cols = {}
    for p in px:
        cols[p] = cols.get(p, 0) + 1
    assert len(cols) <= 256
    # translucent/transparent first (short tRNS), then by frequency
    order = sorted(cols, key=lambda c: (c[3] == 255, -cols[c]))
    idx = {c: i for i, c in enumerate(order)}
    ntr = sum(1 for c in order if c[3] != 255)
    best = None
    depths = [d for d in (1, 2, 4, 8) if (1 << d) >= len(order)]
    for depth in depths[:2]:
        rows = []
        for y in range(h):
            r = [idx[p] for p in px[y * w:(y + 1) * w]]
            if depth == 8:
                rows.append(bytes(r))
            else:
                per = 8 // depth
                r += [0] * (-len(r) % per)
                b = bytearray()
                for i in range(0, len(r), per):
                    v = 0
                    for k in r[i:i + per]:
                        v = (v << depth) | k
                    b.append(v)
                rows.append(bytes(b))
        cands = [b"".join(b"\0" + r for r in rows)]
        # Up filter everywhere (helps repeated rows)
        up = bytearray(); prev = bytes(len(rows[0]))
        for r in rows:
            up.append(2); up += bytes((a - b) & 255 for a, b in zip(r, prev)); prev = r
        cands.append(bytes(up))
        for raw in cands:
            z = zz.compress(raw, numiterations=iters)
            data = (b"\x89PNG\r\n\x1a\n" + _chunk(b"IHDR", struct.pack(">IIBBBBB", w, h, depth, 3, 0, 0, 0))
                    + _chunk(b"PLTE", b"".join(bytes(c[:3]) for c in order))
                    + (_chunk(b"tRNS", bytes(c[3] for c in order[:ntr])) if ntr else b"")
                    + _chunk(b"IDAT", z) + _chunk(b"IEND", b""))
            if best is None or len(data) < len(best):
                best = data
    chk = Image.open(io.BytesIO(best)).convert("RGBA")
    a = list(chk.get_flattened_data()) if hasattr(chk, "get_flattened_data") else list(chk.getdata())
    assert [(0, 0, 0, 0) if p[3] == 0 else p for p in a] == px, "not lossless"
    return best
