"""Build the Erebor T3 Code theme from the art in this folder.

Writes dist/erebor.css (the theme CSS, every image inlined) and dist/erebor.json (theme file).

The whole scene is a stack of background layers on [data-workspace-area="conversation"] (the chat
area), plus a copy of the throne chamber in the inline details card's ::after. A background layer
cannot clip a sprite sheet to one frame, so every animated sprite is a small SVG that wraps the PNG
frames and animates them inside (SVG-as-image animations run on their own clock). Dwarf walks are
animations on the chat area; the king's toast -> doze timer is an animation on :root.

State comes from the app's English aria-labels (other UI languages leave the scene at its defaults)
and assumes the default or "wide" chat width (with "full" width the column has no fixed length and the
scene's anchors drift).

Run: uv run --with pillow --with numpy --with zopfli python src/build_theme.py
"""
from __future__ import annotations

import base64
import io
import json
import os
import sys
from pathlib import Path

from PIL import Image

ART = Path(__file__).resolve().parent.parent
DIST = Path(os.environ.get("EREBOR_OUT", ART / "dist"))
# Size optimisations, all on by default (the CSS is capped at 100,000 characters). OPT= (empty) builds
# the plain version, which the equivalence checks compare against.
OPT = set(filter(None, os.environ.get("OPT", "png,svg,lad,is,pos,nest,min").split(",")))
sys.path.insert(0, str(Path(__file__).resolve().parent))

# ---------------------------------------------------------------- helpers

def png_bytes(img: Image.Image) -> bytes:
    if "png" in OPT:   # used-colour palette, minimal bit depth, zopfli; asserted lossless
        from pngopt import best_png
        return best_png(img)
    buf = io.BytesIO()
    img.save(buf, format="PNG", optimize=True)
    return buf.getvalue()


def crop(img: Image.Image, x: int, y: int, w: int, h: int) -> Image.Image:
    return img.crop((x, y, x + w, y + h))


def png_uri(img: Image.Image) -> str:
    return "data:image/png;base64," + base64.b64encode(png_bytes(img)).decode()


def load(name: str) -> Image.Image:
    return Image.open(ART / name)


HOARD_EXT = 256            # native px of tile added on each side of the 480 px hoard layers


def hoard_extended(main: str, tile: str, raw: bool = False):
    """The hoard layer with its seamless tile pasted on both sides, as one image.

    One wide image instead of a repeat-x tile layer: a repeating tile would also show through
    the hoard's own span (above the dimmed valley behind the chat)."""
    m, t = load(main).convert("RGBA"), load(tile).convert("RGBA")
    out = Image.new("RGBA", (m.width + 2 * HOARD_EXT, m.height))
    for x in range(0, out.width, t.width):
        out.paste(t, (x, 0))
    out.paste(Image.new("RGBA", m.size), (HOARD_EXT, 0))
    out.alpha_composite(m, (HOARD_EXT, 0))
    q = out.quantize(colors=64, method=Image.Quantize.FASTOCTREE, dither=Image.Dither.NONE)
    assert q.convert("RGBA").tobytes() == out.tobytes(), "palette lost colours"
    data = png_bytes(q)
    if "png" in OPT:
        return data if raw else "data:image/png;base64," + base64.b64encode(data).decode()
    try:
        import zopfli.png
        data = zopfli.png.optimize(data)
    except ImportError:
        pass
    return data if raw else "data:image/png;base64," + base64.b64encode(data).decode()


def file_uri(name: str) -> str:
    return "data:image/png;base64," + base64.b64encode((ART / name).read_bytes()).decode()


def svg_uri(svg: str) -> str:
    # only what a data URL inside url("...") needs: % and # (fragment); everything else stays readable
    return "data:image/svg+xml," + svg.replace("%", "%25").replace("#", "%23")


def url(uri: str) -> str:
    return f'url("{uri}")' if uri.startswith("data:") else uri


def sprite_svg(sheet: Image.Image, fw: int, fh: int, anim_css: str, *, mirror: bool = False,
               box_w: int | None = None, dx: int = 0, extra: str = "") -> str:
    """SVG of one fw x fh window onto `sheet` (frames in one row); `anim_css` animates `.s`.

    box_w widens the SVG (for the headlamp cone); dx places the frame inside it.
    `extra` is more SVG drawn on top (in the same mirrored group)."""
    bw = box_w or fw
    href = png_uri(sheet)
    if "svg" in OPT:
        anim = anim_css.replace(",end)", ")")
        if bw == fw and not mirror and not extra:   # the root viewBox already clips to one frame
            anim = anim.replace(".s{", "image{image-rendering:pixelated;", 1)
            return (f"<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 {bw} {fh}'><style>{anim}</style>"
                    f"<image width='{sheet.width}' height='{sheet.height}' href='{href}'/></svg>")
        xa = f" x='{dx}'" if dx else ""
        body = (f"<svg{xa} width='{fw}' height='{fh}'>"
                f"<image class='s' width='{sheet.width}' height='{sheet.height}' href='{href}'/></svg>{extra}")
        if mirror:
            body = f"<g transform='translate({bw}) scale(-1 1)'>{body}</g>"
        return (f"<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 {bw} {fh}'>"
                f"<style>image{{image-rendering:pixelated}}{anim}</style>{body}</svg>")
    body = (f"<svg x='{dx}' y='0' width='{fw}' height='{fh}' overflow='hidden'>"
            f"<image class='s' width='{sheet.width}' height='{sheet.height}' href='{href}'/></svg>{extra}")
    if mirror:
        body = f"<g transform='translate({bw} 0) scale(-1 1)'>{body}</g>"
    return (f"<svg xmlns='http://www.w3.org/2000/svg' width='{bw}' height='{fh}' viewBox='0 0 {bw} {fh}'>"
            f"<style>image{{image-rendering:pixelated}}{anim_css}</style>{body}</svg>")


def strip_anim(n: int, fw: int, dur: str, timing: str = "") -> str:
    """Loop through n frames of width fw, left to right."""
    return (f".s{{animation:a {dur} steps({n},end) infinite}}"
            f"@keyframes a{{to{{transform:translateX(-{n * fw}px)}}}}")


def table_anim(seq: list[tuple[float, int]], fw: int, dur: float, name: str = "a", cls: str = ".s",
               delay: float = 0.0) -> str:
    """Keyframes at percentages -> frame index (hold until the next keyframe)."""
    kf = "".join(f"{p:.3f}%{{transform:translateX(-{f * fw}px)}}" for p, f in seq)
    if "svg" in OPT:
        by = {}
        for p, f in seq:
            by.setdefault(f, []).append(f"{p:g}%")
        kf = "".join(f"{','.join(ps)}{{transform:translateX({-f * fw}px)}}" for f, ps in by.items())
    d = f" {delay}s" if delay else ""
    return (f"{cls}{{animation:{name} {dur}s steps(1,end) infinite{d}}}"
            f"@keyframes {name}{{{kf}}}")


# ---------------------------------------------------------------- geometry (native px)

S_DEFAULT, S_NARROW = 4, 3
NARROW_MAX = 1399          # viewport width (CSS px) at or below which the scene uses 3x
BLOCK_W = 148              # scene-left.png / scene-right.png width
CANVAS_H = 270

OFF_BACK = [106, 95, 85, 74, 64, 53, 42, 32, 21, 11, 0]
OFF_FRONT = [36, 32, 29, 25, 22, 18, 14, 11, 7, 4, 0]

GEOM = json.loads((ART / "src/_geom.json").read_text())   # written by src/scene.py (STYLE-v5)

# dwarf slots in fill order: block ("left" = scene-left.png, "right" = scene-right-tunnels.png), station
# (x, y), walk-in start x, colour row, work-loop stagger. Three dwarf looks: 1-2-3 on the left, 3-1 on the
# right, so the walk-in and walk-out sprites (both facings of rows 0-2) are shared between slots.
ROWS, DELAYS = [0, 1, 2, 2, 0], [0.0, -1.9, -3.7, -0.9, -2.8]
SLOTS = [dict(n=i + 1, block=g["block"], x=g["x"], y=g["y"], start=g["start"], mirror=g["block"] == "right",
              row=ROWS[i], d=DELAYS[i]) for i, g in enumerate(GEOM["slots"])]
NSLOTS = len(SLOTS)
WALK_SPEED = 20            # native px per second
LAMP_AT = (17, 6)          # cone offset inside a right-facing 24x24 dwarf frame
DWARF_BOX = 32             # SVG width: 24 px dwarf + room for the cone

# throne chamber: chamber-local sprite boxes, default place in the right block, ledge for the dragon cap
CH = GEOM["chamber"]
CH_AT = tuple(CH["at"])
RUNES = CH["runes"]
LEDGE_Y = GEOM["ledge_y"]
HOLD = "99999999s"   # transition delay that keeps the last value while the details card is closed
GOLD = "#dcab4f"   # UI accent: bright gold, never used as a tinted surface
WINE = "#3c1822"   # selected / highlighted surfaces

U = "var(--erb-u)"
AREA = '[data-workspace-area="conversation"]'   # the chat area: the scene is its background
C = "var(--chat-content-max-width, 46rem)"


def n(v: float) -> str:
    return f"{v:g}"


def x_center(xc: float, w: float) -> str:
    return f"calc(50% + {n(xc + w / 2 - 240)} * {U})"


def x_left_block(lx: float, w: float, extra: str = "") -> str:
    return f"calc(50% - {C} / 2 + {n(lx - BLOCK_W + w / 2)} * {U}{extra})"


def x_right_block(rx: float, w: float, extra: str = "") -> str:
    return f"calc(100% + {n(rx + w - BLOCK_W)} * {U}{extra})"


def x_right_tunnels(lx: float, w: float, extra: str = "") -> str:
    """scene-right-tunnels.png: its left edge on the column-right edge."""
    return f"calc(50% + {C} / 2 + {n(lx + w / 2)} * {U}{extra})"


def y_bottom(yc: float, h: float, extra: str = "") -> str:
    """Image of height h whose top is canvas y yc, canvas bottom = panel bottom."""
    return f"calc(100% - {n(CANVAS_H - yc - h)} * {U}{extra})"


def size(w: float, h: float) -> str:
    if "pos" in OPT:
        return f"calc({n(w)} * {U})"
    return f"calc({n(w)} * {U}) calc({n(h)} * {U})"


# ---------------------------------------------------------------- build

def build() -> tuple[str, dict]:
    css_vars: dict[str, str] = {}      # :root defaults
    area_vars: dict[str, str] = {}     # chat-area-only values, registered as non-inherited (see @property)
    rules: list[str] = []
    layers: list[dict] = []            # top to bottom

    def layer(name, image, x, y, w, h, repeat="no-repeat", sz=None):
        if image.startswith("var("):   # already a variable: use it as is
            layers.append(dict(img=image, pos=f"{x} {y}", size=sz or size(w, h), rep=repeat))
            return
        var = f"--erb-i-{name}"
        css_vars[var] = url(image)
        layers.append(dict(img=f"var({var})", pos=f"{x} {y}", size=sz or size(w, h), rep=repeat))

    def img(name, uri):
        """Define an image once on :root; rules refer to it by var()."""
        css_vars[f"--erb-img-{name}"] = url(uri)
        return f"var(--erb-img-{name})"

    # ---- sprites
    dragon = load("dragon.png")
    dragon_states = {}
    for i, (st, dur) in enumerate([("asleep", "4.8s"), ("stirring", "2.4s"), ("awake", "2s"), ("wrathful", ".72s")]):
        sheet = crop(dragon, i * 640, 0, 640, 70)
        dragon_states[st] = img(f"dragon-{st}", svg_uri(sprite_svg(sheet, 160, 70, strip_anim(4, 160, dur))))

    king = load("king.png")
    def king_frames(a, b):
        return crop(king, a * 32, 0, (b - a + 1) * 32, 32)
    work_seq = [(0, 0), (10, 1), (18, 0), (30, 1), (38, 2), (44, 0), (56, 1), (64, 0), (70, 3), (74, 4),
                (84, 5), (90, 4), (94, 3), (100, 0)]
    king_img = {k: img(f"king-{k}", v) for k, v in {
        "working": svg_uri(sprite_svg(king_frames(0, 5), 32, 32, table_anim(work_seq, 32, 16))),
        "waiting": svg_uri(sprite_svg(king_frames(6, 9), 32, 32, strip_anim(4, 32, "1.2s"))),
        "toast": svg_uri(sprite_svg(king_frames(10, 13), 32, 32,
                                    table_anim([(0, 0), (25, 1), (50, 2), (75, 3), (100, 3)], 32, 2))),
        "hold": png_uri(king_frames(13, 13)),
        "doze": svg_uri(sprite_svg(king_frames(14, 17), 32, 32, strip_anim(4, 32, "4s"))),
        "failed": svg_uri(sprite_svg(king_frames(18, 20), 32, 32,
                                     table_anim([(0, 0), (35, 1), (60, 0), (80, 2), (100, 0)], 32, 4.8))),
    }.items()}

    hg = load("hourglass.png")
    hg_base = [img(f"hg{i}", png_uri(crop(hg, i * 12, 0, 12, 20))) for i in range(11)]
    hg_trickle = img("hg-trickle", svg_uri(sprite_svg(crop(hg, 132, 0, 24, 20), 12, 20, strip_anim(2, 12, ".5s"))))
    hg_smoke = img("hg-smoke", svg_uri(sprite_svg(crop(hg, 156, 0, 24, 20), 12, 20, strip_anim(2, 12, "1.1s"))))

    ark = load("arkenstone.png")
    ark_base = [img(f"ark{i}", png_uri(crop(ark, i * 16, 0, 16, 16))) for i in range(6)]
    twinkle_css = (".s{animation:a 4.2s steps(2,end) infinite,o 4.2s steps(1,end) infinite}"
                   "@keyframes a{to{transform:translateX(-32px)}}"
                   "@keyframes o{0%,100%{opacity:0}8%{opacity:1}20%{opacity:0}58%{opacity:1}70%{opacity:0}}")
    ark_twinkle = img("ark-twinkle", svg_uri(sprite_svg(crop(ark, 96, 0, 32, 16), 16, 16, twinkle_css)))

    rs = load("runes.png")
    runes = [img(f"rune{i}", png_uri(crop(rs, i * RUNES["w"], 0, RUNES["w"], RUNES["h"])))
             for i in range(RUNES["frames"])]

    dwarf = load("dwarf.png")
    lamp = load("lamp.png")
    lamp_href = png_uri(lamp)

    from dwarf import WORK_MS

    work_duration = sum(WORK_MS)
    work_seconds = f"{work_duration / 1000:g}".lstrip("0")
    work_keyframes, elapsed = [], 0
    for f, duration in enumerate(WORK_MS):
        work_keyframes.append(f"{100 * elapsed / work_duration:g}%{{translate:{-24 * f}px}}")
        elapsed += duration
    work_keyframes.append(f"100%{{translate:{-24 * (len(WORK_MS) - 1)}px}}")

    def dwarf_work_svg(row, delay, mirror):
        """Work strip (frames 0-7) and rest strip (8-9) share one embedded image through <use>."""
        sheet = crop(dwarf, 0, row * 24, 240, 24)
        d = f" {delay}s" if delay else ""
        # The swing cycle is phased so the 3.2 s work window (4 swings) starts at frame 6 (lifting the pick
        # from low) and ends after frame 5 (pick low after the strike): it meets the rest pose (pick on the
        # ground) at both ends instead of jumping from or to the pick held overhead.
        dw = f" {delay - sum(WORK_MS[:6]) / 1000:g}s"
        css = (f".w{{animation:w {work_seconds}s step-end infinite{dw},v 5.6s steps(1,end) infinite{d}}}"
               f".r{{animation:r 1.2s steps(2,end) infinite{d},q 5.6s steps(1,end) infinite{d}}}"
               f"@keyframes w{{{''.join(work_keyframes)}}}"
               f"@keyframes r{{from{{translate:-192px}}to{{translate:-240px}}}}"
               f"@keyframes v{{0%{{opacity:1}}57.143%,100%{{opacity:0}}}}"
               f"@keyframes q{{0%{{opacity:0}}57.143%,100%{{opacity:1}}}}")
        body = (f"<defs><image id='i' width='240' height='24' href='{png_uri(sheet)}'/></defs>"
                f"<svg width='24' height='24' overflow='hidden'><use class='w' href='#i'/><use class='r' href='#i'/></svg>"
                f"<image x='{LAMP_AT[0]}' y='{LAMP_AT[1]}' width='{lamp.width}' height='{lamp.height}' href='{lamp_href}'/>")
        if "svg" in OPT:
            css = css.replace(",end)", ")").replace("from{translate:-192px}to", "0%{translate:-192px}to")
            body = body.replace(" overflow='hidden'", "")
            if mirror:
                body = f"<g transform='translate({DWARF_BOX}) scale(-1 1)'>{body}</g>"
            return svg_uri(f"<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 {DWARF_BOX} 24'>"
                           f"<style>image,use{{image-rendering:pixelated}}{css}</style>{body}</svg>")
        if mirror:
            body = f"<g transform='translate({DWARF_BOX} 0) scale(-1 1)'>{body}</g>"
        return svg_uri(f"<svg xmlns='http://www.w3.org/2000/svg' width='{DWARF_BOX}' height='24' "
                       f"viewBox='0 0 {DWARF_BOX} 24'><style>image,use{{image-rendering:pixelated}}{css}</style>"
                       f"{body}</svg>")

    def dwarf_svg(row, frames, anim_css, mirror):
        sheet = crop(dwarf, frames[0] * 24, row * 24, len(frames) * 24, 24)
        cone = (f"<image class='c' x='{LAMP_AT[0]}' y='{LAMP_AT[1]}' width='{lamp.width}' height='{lamp.height}' "
                f"href='{lamp_href}'/>")
        return svg_uri(sprite_svg(sheet, 24, 24, anim_css, mirror=mirror, box_w=DWARF_BOX, extra=cone))

    # ---- scene blocks
    # the tile grid starts at the bottom-right corner, so the chamber's card copy can line up with it
    layer("tile", file_uri("rock-tile.png"), "100%", "100%", 64, 64, repeat="repeat")
    # (listed bottom-up here, reversed at the end)
    layer("left", file_uri("scene-left.png"), x_left_block(0, BLOCK_W), y_bottom(0, CANVAS_H), BLOCK_W, CANVAS_H)
    layer("right", file_uri("scene-right.png"), x_right_block(0, BLOCK_W), y_bottom(0, CANVAS_H), BLOCK_W, CANVAS_H)
    layer("rtun", file_uri("scene-right-tunnels.png"), x_right_tunnels(0, BLOCK_W), y_bottom(0, CANVAS_H),
          BLOCK_W, CANVAS_H)
    hide = "* 100000px"

    # The throne chamber: one set of layers, always in the right block, and a second copy in the inline
    # details panel's ::after that appears right below the card only when a tall card reaches the chamber.
    css_vars["--erb-i-chamber"] = url(file_uri("chamber.png"))
    def chamber_layers(place):
        out = []   # bottom-up
        def add(image, x, y, w, h, extra=""):
            out.append(dict(img=image, pos=place(x, y, w, h, extra), size=size(w, h), rep="no-repeat"))
        add("var(--erb-i-chamber)", 0, 0, CH["w"], CH["h"])
        add("var(--erb-hg-base)", *CH["hourglass"], 12, 20)
        add("var(--erb-hg-fx)", *CH["hourglass"], 12, 20)
        add("var(--erb-ark-base)", *CH["ark"], 16, 16)
        add("var(--erb-ark-fx)", *CH["ark"], 16, 16)
        for k in ("k1", "k2", "k3"):
            add(f"var(--erb-king-{k[1]})", *CH["king"], 32, 32, f" - var(--erb-{k}h) {hide}")
        return out
    def in_block(x, y, w, h, extra):
        return (f"{x_right_block(CH_AT[0] + x, w, extra)} "
                f"{y_bottom(CH_AT[1] + y, h)}")
    def in_card(x, y, w, h, extra):   # the card copy's box can be taller than the chamber: bottom-anchored
        return f"calc({n(x)} * {U}{extra}) calc(100% - {n(CH['h'] - y - h)} * {U})"
    layers.extend(chamber_layers(in_block))
    card_layers = chamber_layers(in_card)
    card_layers.insert(1, dict(img="var(--erb-runes)", pos=in_card(RUNES["x"], RUNES["y"], RUNES["w"], RUNES["h"], ""),
                               size=size(RUNES["w"], RUNES["h"]), rep="no-repeat"))
    # rock behind it, on the background's tile grid, covers the background copy above the moved chamber
    card_layers.insert(0, dict(img="var(--erb-i-tile)", pos=f"100% calc({n((CANVAS_H - CH_AT[1]) % 64)} * {U})",
                               size=size(64, 64), rep="repeat"))

    # Dwarves. Provider light follows the walk offset. The shield stays on the station wall.
    providers = {
        "other": (".isolate", "#58d39ead"),
        "claude": ('svg[viewBox="0 0 256 257"]', "#d97757b8"),
        "codex": ('svg[viewBox="100 100 411 411"]', "#e5eeff9c"),
    }
    for index, provider in enumerate(providers):
        css_vars[f"--s{index}"] = url(png_uri(load(f"sign-{provider}.png")))

    css_vars["--gs"] = f"calc(19 * {U}) calc(15 * {U})"
    slot_rules = []
    LINEAGE = [(k, p) for k in range(1, 4) for p in range(len(providers))]   # slot k, provider index p
    walk_out = {s["n"]: f"erb-out-{s['n']} {abs(s['x'] - s['start']) / WALK_SPEED:.2f}s "
                        f"steps({abs(s['x'] - s['start'])},end) both" for s in SLOTS}
    walk_imgs = {}
    def walk_img(row, mirror):
        """Walk cycle of one dwarf look facing one way; shared by every slot that needs it."""
        if (row, mirror) not in walk_imgs:
            # the headlamp is 1 px higher on walk frames 11, 12, 14 and 15; same SVG clock as the frames
            lamp_bob = (".c{animation:b .6s step-end infinite}"
                        "@keyframes b{0%{transform:none}16.667%{transform:translateY(-1px)}"
                        "50%{transform:none}66.667%{transform:translateY(-1px)}}")
            svg = dwarf_svg(row, list(range(10, 16)), strip_anim(6, 24, ".6s") + lamp_bob, mirror)
            walk_imgs[(row, mirror)] = img(f"walk{row}{'m' if mirror else ''}", svg)
        return walk_imgs[(row, mirror)]
    for s in SLOTS:
        i = s["n"]
        xfun = x_left_block if s["block"] == "left" else x_right_tunnels
        sx = s["x"] - (DWARF_BOX - 24 if s["mirror"] else 0)       # SVG box origin
        if i <= 3:
            layers.append(dict(img=f"var(--m{i},none)", pos=f"{xfun(s['x'] - 13, 11)} {y_bottom(s['y'] + 3, 11)}",
                               size=size(11, 11), rep="no-repeat"))
            glow_x = xfun(s["x"] + 13, 19, f" + var(--erb-dx{i}) * {U}")
            layers.append(dict(img=f"radial-gradient(closest-side,var(--g{i},#0000),#0000)",
                               pos=f"{glow_x} {y_bottom(s['y'] + 4, 15)}",
                               size="var(--gs)", rep="no-repeat"))
        work = img(f"dw{i}-work", dwarf_work_svg(s["row"], s["d"], s["mirror"]))   # own stagger per slot
        walk, back = walk_img(s["row"], s["mirror"]), walk_img(s["row"], not s["mirror"])
        area_vars.update({f"--erb-wv{i}": "none", f"--erb-ov{i}": "none", f"--erb-gt{i}": f"var(--erb-gs{i})"})
        slot_rules.append((i, work, walk, back))
        # walk layer: at station + dx while walking in, hidden after arrival; work layer the other way round;
        # out layer: the opposite facing, shown while walking back out (--erb-o) after the subagent finished
        sxo = s["x"] - (DWARF_BOX - 24 if not s["mirror"] else 0)
        layers.append(dict(img=f"var(--erb-dw{i}-work,none)",
                           pos=f"{xfun(sx, DWARF_BOX, f' - (1 - var(--erb-a{i})) {hide}')} {y_bottom(s['y'], 24)}",
                           size=size(DWARF_BOX, 24), rep="no-repeat"))
        layers.append(dict(img=f"var(--erb-wv{i})",
                           pos=f"{xfun(sx, DWARF_BOX, f' + var(--erb-dx{i}) * {U} - var(--erb-a{i}) {hide}')} "
                               f"{y_bottom(s['y'] + 1, 24)}",
                           size=size(DWARF_BOX, 24), rep="no-repeat"))
        layers.append(dict(img=f"var(--erb-ov{i})",
                           pos=f"{xfun(sxo, DWARF_BOX, f' + var(--erb-dx{i}) * {U} - (2 - var(--erb-o{i}) - var(--erb-gt{i})) {hide}')} "
                               f"{y_bottom(s['y'] + 1, 24)}",
                           size=size(DWARF_BOX, 24), rep="no-repeat"))

    # hoard + dragon
    ob, of = "var(--erb-ob)", "var(--erb-of)"
    hw = 480 + 2 * HOARD_EXT
    # the back hoard is the theme's background-image file (dist/erebor.png), which keeps ~9.5k out of the CSS
    layer("hb", "var(--theme-background-image, none)", x_center(-HOARD_EXT, hw),
          y_bottom(146, 92, f" + {ob} * {U}"), hw, 92)
    # weekly runes on the chamber ledge, above the hoard that piles against it
    layer("runes", "var(--erb-runes)",
          x_right_block(CH_AT[0] + RUNES["x"], RUNES["w"]),
          y_bottom(CH_AT[1] + RUNES["y"], RUNES["h"]), RUNES["w"], RUNES["h"])
    # the dragon rises with the hoard but stops under the chamber's ledge, so it never covers the king
    dragon_lift = f"max({ob}, {n(LEDGE_Y - 84)})"
    layer("dragon", "var(--erb-dragon)", f"calc(50% + {C} / 2 + 72 * {U})", y_bottom(84, 70, f" + {dragon_lift} * {U}"),
          160, 70)
    layer("hf", hoard_extended("hoard-front.png", "hoard-front-tile.png"), x_center(-HOARD_EXT, hw),
          y_bottom(226, 44, f" + {of} * {U}"), hw, 44)
    # calm band behind the chat column
    css_vars["--erb-i-dim"] = ("linear-gradient(90deg, transparent, rgba(7,8,10,.42) 16px, "
                               "rgba(7,8,10,.42) calc(100% - 16px), transparent)")
    layers.append(dict(img="var(--erb-i-dim)", pos="50% 0", size=f"calc({C} + 32px) 100%", rep="no-repeat"))

    layers.reverse()   # CSS lists the top layer first

    # ---- defaults
    css_vars.update({
        "--erb-S": str(S_DEFAULT),
        "--erb-u": "calc(var(--erb-S) * 1px)",
        "--erb-ob": str(OFF_BACK[0]), "--erb-of": str(OFF_FRONT[0]),
        "--erb-dragon": dragon_states["asleep"],
        "--erb-hg-base": hg_base[0], "--erb-hg-fx": hg_trickle,
        "--erb-ark-base": ark_base[0], "--erb-ark-fx": ark_twinkle,
        "--erb-tr-ctx": "--erb-ob 1.2s steps(6,end),--erb-of 1.2s steps(6,end)",
        "--erb-tr-lim": "--erb-hg-base 0s", "--erb-tr-wk": "--erb-runes 0s",
        "--erb-runes": runes[-1],
        "--erb-king-1": king_img["toast"], "--erb-king-2": king_img["hold"], "--erb-king-3": king_img["doze"],
        "--erb-anim-king": "erb-king-done 120s steps(1, end) both",
    })
    for i in range(1, NSLOTS + 1):
        area_vars[f"--erb-on{i}"] = "var(--erb-many)"   # slot toggle: off unless 10+ (count rules switch it on)

    props = [("--erb-ob", "<number>", OFF_BACK[0]), ("--erb-of", "<number>", OFF_FRONT[0])]
    for i in range(1, NSLOTS + 1):
        props += [(f"--erb-dx{i}", "<number>", 0), (f"--erb-a{i}", "<number>", 1), (f"--erb-o{i}", "<number>", 0),
                  (f"--erb-gs{i}", "<number>", 0), (f"--erb-gt{i}", "<number>", 0)]
    props += [("--erb-k1h", "<number>", 0), ("--erb-k2h", "<number>", 0), ("--erb-k3h", "<number>", 0)]
    # The walk properties are animated and read on the conversation element only: not inheriting them keeps
    # every walk step from restyling the whole message timeline below it.
    walk_props = {f"--erb-{k}{i}" for i in range(1, NSLOTS + 1) for k in ("dx", "a", "o", "gt", "gs")}
    for name, syn, init in props:
        inh = "false" if name in walk_props else "true"
        rules.append(f"@property {name}{{syntax:'{syn}';inherits:{inh};initial-value:{init}}}")
    for name in area_vars:   # the walk sprites: set on the chat area only, changing them restyles only it
        if name not in walk_props:
            rules.append(f"@property {name}{{syntax:'*';inherits:false}}")

    rules.append(":root{" + ";".join(f"{k}:{v}" for k, v in css_vars.items()) + "}")
    # The context and usage rows live only in the thread details card. When it closes, every value
    # keeps its last state: a transition whose delay never ends holds the start value.
    rules.append(":root{transition:var(--erb-tr-ctx),var(--erb-tr-lim),var(--erb-tr-wk)!important}")
    # A finished subagent's dwarf walks back out. Its gate --erb-gsN drops to 0 at once; --erb-gtN, a copy
    # with a delayed transition, keeps 1 for the length of the walk. Both live on the chat area only.
    gates = ",".join(f"--erb-gt{s['n']} 0s {abs(s['x'] - s['start']) / WALK_SPEED:.2f}s" for s in SLOTS)
    hold = lambda *vs: ",".join(f"{v} 0s {HOLD} allow-discrete" for v in vs)
    rules.append(f':root:not(:has([aria-label^="Context: "][aria-label$="% used"]))'
                 f'{{--erb-tr-ctx:{hold("--erb-ob", "--erb-of", "--erb-dragon")}}}')
    rules.append(f':root:not(:has([aria-label^="Session: "][aria-label$="% left"]))'
                 f'{{--erb-tr-lim:{hold("--erb-hg-base", "--erb-hg-fx", "--erb-ark-base", "--erb-ark-fx")}}}')
    rules.append(f':root:not(:has([aria-label^="Weekly: "][aria-label$="% left"]))'
                 f'{{--erb-tr-wk:{hold("--erb-runes")}}}')
    rules.append(f"@media (max-width:{NARROW_MAX}px){{:root{{--erb-S:{S_NARROW}}}}}")

    # ---- the conversation element
    rules.append(
        f"{AREA}{{" + "".join(f"{k}:{v};" for k, v in area_vars.items()) + f"transition:{gates};"
        f"background-color:#0b0c0f!important;"
        f"background-image:{','.join(l['img'] for l in layers)}!important;"
        f"background-position:{','.join(l['pos'] for l in layers)}!important;"
        f"background-size:{','.join(l['size'] for l in layers)}!important;"
        f"background-repeat:{','.join(l['rep'] for l in layers)}!important;"
        f"background-attachment:scroll!important;"
        f"image-rendering:pixelated;anchor-name:--erb-a;"
        f"animation:{','.join(f'var(--erb-anim-{i},{walk_out[i]})' for i in range(1, NSLOTS + 1))}"
        + "".join(f",erb-lk{k}{p} 1s both" for k, p in LINEAGE) + ";"
        f"animation-timeline:{','.join(['auto'] * NSLOTS + [f'--erb-lt{k}{p}' for k, p in LINEAGE])}}}"
        f"{AREA}>*{{image-rendering:auto}}"
    )
    rules.append(":root{animation:var(--erb-anim-king)}")
    # the timeline's empty stand-in (new thread, thread loading) is an opaque bg-background box over the scene
    rules.append("[data-timeline-loading]{background:none!important}")
    # The scene shows context and limits, so their sections in the details card are hidden. They stay in
    # the DOM (display:none still matches :has()), which is all the theme needs.
    rules.append('[data-thread-details-card] section:is([aria-label="Usage limits"],[aria-label="Context window"])'
                 '{display:none!important}')
    # the throne chamber under the inline details card
    card = '[data-thread-details-panel="inline"]'
    rules.append("[data-thread-details-card]{anchor-name:--erb-c}")
    cl = list(reversed(card_layers))
    rules.append(
        # Shown only once the card reaches the chamber's place in the scene (position-visibility hides it while
        # its box, from that place down to just below the card, is shorter than the chamber). It then covers the
        # background copy with rock and draws the chamber right below the card, under the card itself (z -1).
        # Anchors line it up with the conversation area exactly like the background copy.
        f"{card}::after{{content:'';position:fixed;z-index:-1;pointer-events:none;position-visibility:no-overflow;"
        f"right:anchor(--erb-a right);width:calc({CH['w']} * {U});min-height:calc({CH['h']} * {U});"
        f"top:calc(anchor(--erb-a bottom) - {n(CANVAS_H - CH_AT[1])} * {U});"
        f"bottom:calc(anchor(--erb-c bottom) - {CH['h']} * {U});"
        f"background-image:{','.join(l['img'] for l in cl)};"
        f"background-position:{','.join(l['pos'] for l in cl)};"
        f"background-size:{','.join(l['size'] for l in cl)};"
        f"background-repeat:{','.join(l['rep'] for l in cl)};image-rendering:pixelated}}")
    rules.append("@keyframes erb-none{to{--erb-k1h:0}}")

    # ---- context buckets: "Context: N% used" in the thread details card
    def has_any(labels):
        return ",".join(f'[aria-label="{l}"]' for l in labels)

    def ctx_rule(sel, b):
        st = ("asleep" if b <= 5 else "stirring" if b <= 7 else "awake" if b == 8 else "wrathful")
        dr = "" if ("lad" in OPT and st == "asleep" and b) else f";--erb-dragon:{dragon_states[st]}"
        rules.append(f":root:where(:has({sel})){{--erb-ob:{OFF_BACK[b]};--erb-of:{OFF_FRONT[b]}{dr}}}")

    # tens digit first ("Context: 4" = 4% and 40-49%), then exact values that the prefix gets wrong
    for b in range(1, 10):
        ctx_rule(f'[aria-label^="Context: {b}"][aria-label$="% used"]', b)
    ctx_rule('[aria-label="Context: 100% used"]', 10)
    ctx_rule(has_any(f"Context: {v}% used" for v in range(10)), 0)

    # ---- 5 h "Session" row: hourglass frame (100% -> 0, 90-99 -> 1, ..., 10-19 and 1-9 -> 9, 0 -> 10, empty
    # and smoking) and Arkenstone frame (80-100 -> 0, 60-79 -> 1, 40-59 -> 2, 20-39 -> 3, 1-19 -> 4, 0 -> 5) from
    # one ladder of rules, so both cost one set of :has() arguments. Tens digit by prefix, then exact values.
    tens = {9: 0, 8: 0, 7: 1, 6: 1, 5: 2, 4: 2, 3: 3, 2: 3, 1: 4}
    def ses_rule(sel, f, a, extra=""):
        hg = f"--erb-hg-base:{hg_smoke if f == 10 else hg_base[f]}" + (";--erb-hg-fx:none" if f == 10 else "")
        ark = f"--erb-ark-base:{ark_base[a]}" + ("" if a <= 2 else ";--erb-ark-fx:none")
        rules.append(f":root:where(:has({sel})){{{hg};{ark}{extra}}}")
    for t in range(9, 1, -1):
        ses_rule(f'[aria-label^="Session: {t}"][aria-label$="% left"]', 10 - t, tens[t])
    ses_rule('[aria-label^="Session: 1"][aria-label$="% left"],' + has_any(f"Session: {v}% left" for v in range(2, 10)), 9, 4)
    ses_rule('[aria-label="Session: 100% left"]', 0, 0, f";--erb-ark-fx:{ark_twinkle}")   # undo the "1" rule
    ses_rule('[aria-label="Session: 0% left"]', 10, 5)

    # weekly runes: frame = half-steps lit = ceil(left / 10); prefix by tens digit, then exact values
    def rune_rule(sel, f):
        rules.append(f":root:where(:has({sel})){{--erb-runes:{runes[f]}}}")
    # only the account-wide "Weekly" row, never a per-model one such as "Weekly · Fable"
    wk = '[aria-label^="Weekly: "][aria-label$="% left"]'
    if "lad" in OPT:
        # 91-100 % is the :root default. Frame f: the tens digit f-1 by prefix, or exactly f0 %.
        pre = lambda t: f'[aria-label^="Weekly: {t}"][aria-label$="% left"]'
        for f in range(9, 2, -1):
            rune_rule(f'{pre(f - 1)},[aria-label="Weekly: {f}0% left"]', f)
        rune_rule(f'{pre(1)},[aria-label="Weekly: 20% left"]', 2)
        rune_rule('[aria-label="Weekly: 100% left"]', 10)   # the "1" prefix above also took 100 %
        rune_rule(has_any(["Weekly: 10% left"] + [f"Weekly: {v}% left" for v in range(1, 10)]), 1)
        rune_rule('[aria-label="Weekly: 0% left"]', 0)
    else:
        rune_rule(f'{wk}[aria-label*=": 100%"]', 10)
        for t in range(9, 0, -1):    # t0-t9 % -> t+1 half-steps, exactly t0 % -> t
            rune_rule(f'{wk}[aria-label*=": {t}"]:not([aria-label*=": 100%"])', t + 1)
            rune_rule(f'{wk}[aria-label*=": {t}0%"]', t)
        rune_rule(",".join(f'{wk}[aria-label*=": {v}%"]' for v in range(1, 10)), 1)
        rune_rule(f'{wk}[aria-label*=": 0%"]', 0)

    # ---- dwarves: running subagents, from the timeline's subagent group header ("N working · ...").
    # One :has() argument per count (fewer arguments = cheaper re-matching on every DOM change): each count
    # rule only switches slot toggles --erb-onN on (an empty value). Every slot value below is a static
    # declaration on the chat area that starts with var(--erb-onN), so it is invalid, and its reader's
    # fallback applies, while the toggle is off (undefined --erb-many).
    lone = '[data-v2-item-type="subagent"]:is([aria-description=Running],[aria-description=Queued],[aria-description=Waiting])'
    grp = lambda ks: "[data-subagent-group] " + (f'[aria-description^="{ks[0]} working"]' if len(ks) == 1 else
                     ":is(" + ",".join(f'[aria-description^="{k} working"]' for k in ks) + ")")
    on = lambda n: "".join(f"--erb-on{j}: ;" for j in range(1, n + 1))
    for k in range(1, NSLOTS):
        rules.append(f"{AREA}:where(:has({grp([k])})){{{on(k)}}}")
    rules.append(f"{AREA}:where(:has({grp(list(range(NSLOTS, 10)))})){{{on(NSLOTS)}}}")
    # 10-19 working: a :root rule (matched only when :root restyles, not on every walk step like the
    # chat-area rules above) sets --erb-many, which the slot toggles take as their default
    rules.append(f":root:where(:has({grp(list(range(10, 20)))})){{--erb-many: }}")
    rules.append(f"{AREA}:where(:has({lone})){{{on(1)}}}")
    slot_vars = {}
    for i, work, walk, back in slot_rules:
        marks = i <= 3   # provider marks for the first three slots
        if i <= 3:
            # No :nth-child()/:first-child here: a structural pseudo-class inside :has() makes Chromium re-match
            # every :has() rule of the theme on each element insertion (about 18 ms per streamed element in a
            # long chat). Sibling chains are cheap: avatar k..3 = the k-th avatar or a later one, so slot 3 is
            # exact, slot 2 is exact except when avatar 3 is codex and avatar 2 another non-Claude provider,
            # and slot 1 is exact when its provider does not repeat on avatars 2-3 (else it copies slot 2).
            av = lambda k: '[data-subagent-group]>button[aria-description*=" working"] .size-6' + "+.size-6" * (k - 1)
            mark = lambda cond, index, color: rules.append(
                f"{AREA}:where({cond}){{--t{i}:var(--s{index});--p{i}:{color}}}")
            plist = list(providers.values())
            if i == 1:   # a lone subagent row; first, because an expanded group's rows look the same
                for index, (icon, color) in enumerate(plist):
                    mark(f":has({lone} .size-6 {icon})", index, color)
            for index, (icon, color) in enumerate(plist):
                mark(f":has({av(i)} {icon})", index, color)
            claude, codex = plist[1], plist[2]
            if i == 2:   # avatar 2 is Claude when Claude matches from avatar 2 on and avatar 3 is codex
                mark(f":has({av(2)} {claude[0]}):has({av(3)} {codex[0]})", 1, claude[1])
            if i == 1:
                # ambiguous: guess the same provider as avatar 2 (several subagents of one provider are common)
                for index, (icon, color) in enumerate(plist):
                    mark(f":has({av(2)} {icon})", index, color)
                mark(f":has({av(2)} {claude[0]}):has({av(3)} {codex[0]})", 1, claude[1])
                # exact: a branded provider seen on avatar 1..3 but not on 2..3 is avatar 1's
                for index in (1, 2):
                    icon, color = plist[index]
                    mark(f":has({av(1)} {icon}):not(:has({av(2)} {icon}))", index, color)
        s = SLOTS[i - 1]
        dist = abs(s["x"] - s["start"])
        dur = dist / WALK_SPEED
        sign = -1 if s["start"] < s["x"] else 1
        # the walk sprites are supplied by the walk keyframes only, so they are unloaded once the walk ends
        wv, ov = f"--erb-wv{i}:{walk}", f"--erb-ov{i}:{back}"
        rules.append(f"@keyframes erb-walk-{i}{{0%{{--erb-dx{i}:{sign * dist};--erb-a{i}:0;{wv}}}"
                     f"99.9%{{--erb-a{i}:0;{wv}}}100%{{--erb-dx{i}:0;--erb-a{i}:1;--erb-wv{i}:none}}}}")
        rules.append(f"@keyframes erb-out-{i}{{0%{{--erb-dx{i}:0;--erb-a{i}:0;--erb-o{i}:1;{ov}}}99.9%{{--erb-o{i}:1;{ov}}}"
                     f"100%{{--erb-dx{i}:{sign * dist};--erb-a{i}:0;--erb-o{i}:0;--erb-ov{i}:none}}}}")
        t = f"var(--erb-on{i}) "
        slot_vars.update({f"--erb-dw{i}-work": t + url(work), f"--erb-gs{i}": t + "1",
                          f"--erb-anim-{i}": t + f"erb-walk-{i} {dur:.2f}s steps({dist},end) both"})
        if marks:
            slot_vars.update({f"--m{i}": t + f"var(--t{i},none)", f"--g{i}": t + f"var(--p{i},#0000)"})

    # the slot values and toggles live on the chat area only and do not inherit: a dwarf arriving or leaving
    # restyles that element instead of the whole document
    rules.append(f"{AREA}{{" + ";".join(f"{k}:{v}" for k, v in slot_vars.items()) + "}")

    # Once an agent of the group has finished, the header's first-three avatars no longer say which
    # providers are still running: the marks go neutral rather than wrong...
    rules.append(f'{AREA}:where(:has([data-subagent-group]>button[aria-description*=" working · "]))'
                 "{" + ";".join(f"--t{j}:initial;--p{j}:initial" for j in range(1, 4)) + "}")
    # ...unless the details card lists the running agents (Lineage section; its "active" group has no
    # heading, so its list is the group's first child, unlike "Previous agents"). That list is exact. CSS
    # cannot carry state up without :has(), so each matching row icon exposes a named view timeline,
    # [data-chat-column] hoists the names, and the chat area runs one animation per name whose keyframes
    # set the mark (animations beat the rules above); an absent source leaves its animation inactive.
    # These are plain selectors, so :nth-child() costs nothing here.
    plist = list(providers.values())
    for k, p in LINEAGE:   # within a slot: other, claude, codex; the later animation wins
        icon, color = plist[p]
        rules.append(f"[data-thread-relationships-panel] div>ul:first-child>li:nth-child({k}) {icon}"
                     f"{{view-timeline:--erb-lt{k}{p}}}")
        rules.append(f"@keyframes erb-lk{k}{p}{{0%,to{{--t{k}:var(--s{p});--p{k}:{color}}}}}")
    rules.append("[data-chat-column]{timeline-scope:" + ",".join(f"--erb-lt{k}{p}" for k, p in LINEAGE) + "}")
    for k in [k for k in slot_vars if not k.startswith("--erb-gs")] + [f"--erb-on{j}" for j in range(1, NSLOTS + 1)] \
            + [f"--{c}{j}" for j in range(1, 4) for c in "tp"]:
        rules.append(f"@property {k}{{syntax:'*';inherits:false}}")

    # ---- king: done (default) < working < waiting < failed, later rule wins
    rules.append("@keyframes erb-king-done{0%{--erb-k1h:0;--erb-k2h:1;--erb-k3h:1}"
                 "3.333%{--erb-k1h:1;--erb-k2h:0;--erb-k3h:1}100%{--erb-k1h:1;--erb-k2h:1;--erb-k3h:0}}")
    row = '[data-sidebar-row][aria-current="page"]'
    working = (f'[data-slot="composer-host"] [aria-label="Stop generation"],'
               f'[data-slot="composer-host"] [aria-label="Stopping"],'
               f'{row}[aria-label*=", Working"],{row}[aria-label*=", Goal"],{row}[aria-label*=", Setting up"],'
               f'{row}[aria-label*=", Waiting"]')
    waiting = (f'[data-pending-user-input-toggle],[data-approval-detail],'
               f'{row}[aria-label*=", Approval"],{row}[aria-label*=", Input"],{row}[aria-label*=", Request"]')
    failed = f'{row}[aria-label*=", Failed"],{row}[aria-label*=", Limited"]'
    if "is" in OPT:
        # status words from Sidebar.logic.ts; the row label is "title, status[, project]", so the status is
        # matched as a whole list item, not anywhere (a title such as "Tests, Failed checks" stays harmless)
        lab = lambda *ws: row + ":is(" + ",".join(f'[aria-label*=", {w}, "],[aria-label$=", {w}"]' for w in ws) + ")"
        working = ('[data-slot="composer-host"] :is([aria-label="Stop generation"],[aria-label="Stopping"]),'
                   + lab("Working", "Connecting", "Waiting"))
        waiting = ('[data-pending-user-input-toggle],[data-approval-detail],'
                   + lab("Pending Approval", "Awaiting Input", "Guest Request", "Plan Ready"))
        failed = lab("Failed")
    for sel, img in ((working, "working"), (waiting, "waiting"), (failed, "failed")):
        rules.append(f":root:where(:has({sel})){{--erb-king-1:{king_img[img]};--erb-king-2:none;--erb-king-3:none;"
                     f"--erb-anim-king:erb-none 1s;--erb-k1h:0}}")

    rules.append('@media (prefers-reduced-motion:reduce){:root{--erb-tr-ctx:--erb-ob 0s,--erb-of 0s}}')

    css = "\n".join(rules)
    if OPT & {"pos", "min", "nest"}:
        from cssmin import minify
        css = minify(css, OPT)
    theme = {
        "version": 1, "name": "Erebor", "appearance": "dark",
        "canvas": "#101215", "accent": GOLD,
        # Every key the app accepts is set: keys left out are derived from the accent's hue, which turns
        # gold into brown surfaces. Neutrals stay cool slate, gold is for marks and text, and selected or
        # highlighted surfaces are burgundy.
        "colors": {
            "canvas": "#101215", "chrome": "#0b0c0f",
            "toolbar": "#0b0c0f", "toolbarForeground": "#c9ced6", "toolbarBorder": "#262a31",
            "toolbarControl": "#16191e", "toolbarControlForeground": "#c9ced6", "toolbarControlHover": "#22252c",
            "surface": "#101215", "surfaceRaised": "#16191e", "surfaceOverlay": "#16191e",
            "text": "#d8dce2", "textMuted": "#8a929e", "border": "#262a31", "input": "#2e323a",
            "focus": GOLD, "accent": GOLD, "accentForeground": "#1a1206",
            "secondary": "#1f2229", "secondaryForeground": "#d8dce2",
            "muted": "#181b20", "mutedForeground": "#8a929e",
            "placeholder": "#6b7380", "secondaryLabel": "#8a929e", "iconMuted": "#6b7380",
            "error": "#e0485a", "errorForeground": "#f07a88", "errorSurface": "#3a141c",
            "warning": "#efc77a", "warningForeground": "#f3d08a", "warningSurface": "#2e2414",
            "update": GOLD, "updateForeground": "#f3d08a", "updateSurface": WINE,
            "accentSurface": WINE, "accentSurfaceForeground": "#f3d08a",
            "messageSurface": "#1a1e24", "messageForeground": "#d8dce2",
            "messageAction": GOLD, "messageActionForeground": "#1a1206", "messageActionHover": "#e9bd63",
            "codeBackground": "#0b0c0f", "codeForeground": "#c7ccd4",
            "searchMatchBackground": "#5c1f2c", "searchMatchForeground": "#f3e3c0",
            "searchMatchActiveBackground": GOLD, "searchMatchActiveForeground": "#1a1206",
            "sidebar": "#0b0c0f", "sidebarForeground": "#c9ced6", "sidebarMutedForeground": "#858d99",
            "sidebarControlSurface": "#16191e", "sidebarBorder": "#1c1f25",
            "sidebarRowHover": "#171a1f", "sidebarRowActive": "#22252b", "sidebarRowSelected": WINE,
            "terminalBackground": "#0b0c0f", "terminalForeground": "#c9ced6", "terminalCursor": GOLD,
            "terminalSelection": "#4a1c27", "terminalScrollbar": "#262a31", "terminalScrollbarHover": "#3b414b",
        },
        "css": css,
    }
    return css, theme


def main() -> None:
    css, theme = build()
    DIST.mkdir(parents=True, exist_ok=True)
    (DIST / "erebor.css").write_text(css)
    (DIST / "erebor.json").write_text(json.dumps(theme, indent=2))
    # the back hoard ships as the theme's background-image file, installed beside erebor.json
    (DIST / "erebor.png").write_bytes(hoard_extended("hoard-back.png", "hoard-back-tile.png", raw=True))
    print(f"css: {len(css):,} chars (limit 100,000)")


if __name__ == "__main__":
    main()
