# Erebor art v2: shared style and layout contract

Every art agent in round 2 follows this file. Read `README.md` first for the existing layers, offsets and animation conventions; nothing there changes unless this file says so.

## Style: "bold outline" pass for the whole cast

Inspired by the *style* of Enter the Gungeon's sprites (bold readable silhouettes, clean cel shading). Style only: do not reproduce any character, boss or item from that game, and no guns.

- 1 px outline around every character and prop silhouette. Use near-black `#07080a` on the outer edge; inner separations (arm over body, beard over chest) may use a darkened tone of the local material instead (selective outline).
- Cel shading with 3–4 flat tones per material. No noise, no dithering on characters (dithering stays allowed for smoke, glow and the scene).
- Key light from the upper left (hall lamps). Warm bounce light `#cf9f4a` / `#7a5418` on undersides that face the gold.
- Eyes and focal points are one tone brighter than anything around them so they read at 4×.
- Palette stays as in `README.md`/the existing PNGs: stone #0b0c0f #101215 #171a1f #262a31 #3b414b; gold #3a2a10 #7a5418 #cf9f4a #efc77a #fff3c4; ember #d9582b; dragon hide #2a0c08 #4a1714 #6b2a1e; eye amber #ffb347; Arkenstone #cfe6ff. Add in-between shades sparingly. Indexed PNG, few colors.

## Rules for all round-2 agents

- Write only the files your brief names. Never edit `preview.html`, `README.md`, or another agent's files; the parent session integrates.
- Generators go in `src/`, run with `uv run --with pillow --with numpy --with zopfli python3 src/<x>.py`.
- Make your own check page or contact sheet (`check-<yourname>.html` or `src/_<yourname>_x4.png`) and look at it at 4× before you finish.
- Report: first line your exact model ID; files written; frame sizes, frame counts and order; base64 size of each PNG (`base64 -w0 f | wc -c`); anything open.

## Throne group (new, right gutter)

The throne group is anchored to the right edge of the canvas, above the dragon, below hall R1. Native canvas coordinates (480×270):

| Sprite | File | Frame size | Placed at (left, top) | Owner |
|---|---|---|---|---|
| Throne alcove (static) | `throne.png` | 100×48, 1 frame | 380, 56 | king agent |
| King | `king.png` | 32×32 per frame | 414, 66 (seat must line up) | king agent |
| Hourglass (5h limit) | `hourglass.png` | 12×20 per frame | 388, 82 (on the alcove's left pedestal) | props agent |
| Arkenstone (weekly limit) | `arkenstone.png` | 16×16 per frame | 422, 55 (socket above the throne back) | props agent |

Alcove-local slots the king agent must leave free and the props agent must fit (alcove-local = canvas minus (380, 56)):

- Left pedestal: flat top surface at local y 46, x 6–22. The hourglass frame's bottom row stands on it (hourglass frame local box x 8–19, y 26–45).
- Arkenstone socket: an empty carved socket above the throne back, local box x 42–57, y −1–14 (the gem may overlap the alcove's top edge by 1 px).
- King seat: the king frame's local box is x 34–65, y 10–41; the seat surface and armrests must line up with a seated king in that box.

At context buckets 9–10 the dragon's wing rises to canvas y ≈ 84–95 and covers the bottom of the alcove; the dragon is drawn in front. That is intended.

## Dragon (unchanged geometry)

`dragon.png` stays 2560×70: 16 frames of 160×70, one row, states asleep 0–3, eye slit 4–7, awake 8–11, wrathful 12–15, placed at `left: 324`, `top: 84` at 100% fill, moved by `--off-back`. Frame rows 60–69 are the gold bed; behind-the-chat dimming rules in `README.md` still apply to any gold in frame x 0–42.

## Dwarves (unchanged geometry)

`dwarf.png` stays 240×96: 4 rows × 10 frames of 24×24, same frame order and rows; `lamp.png` cone apex at (0,3).
