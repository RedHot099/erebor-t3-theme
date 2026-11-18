# Erebor art v5: tunnels at the chat column, movable throne chamber, half-lit runes

Round 5 keeps everything in `STYLE-v2.md` … `STYLE-v4.md` except what this file changes. Read `README.md` and all earlier STYLE files first.

## What Jakub asked for

1. The mine tunnels reach the chat column, so the dwarves look like they dig the gold that lies in the main thread.
2. Subagents fill the left tunnels first, top to bottom, then the right ones. Add a second tunnel at the top right.
3. The king's chamber always sits just below the thread details card (a floating card at the top right of the conversation, 280 CSS px wide, height varies with its rows). The right tunnels sit where the card covers them when it opens.
4. Each weekly rune has three states (full, half, none), so 5 runes show the weekly limit in 10 % steps.
5. The runes are spread along the full width of the chamber floor.

## Reference frame

Unchanged: native px, S = 4 (3 on narrow screens), canvas height 270, everything bottom-anchored unless stated. "Column-left/right edge" = the chat column edges (column 736 CSS px, centred). Visible part of a 1544 CSS px panel (Jakub's laptop with the sidebar open): 101 native px of gutter on each side of the column; on the narrowest panel (1264) 66.

## Layers and anchors (changed rows only)

| Layer | File | Size | Horizontal anchor | Notes |
|---|---|---|---|---|
| left block | `scene-left.png` | 148×270 | right edge on the column-left edge (unchanged) | halls L1–L3 now run all the way to local x 147: their open right end meets the column edge, and the work face (gold seam, nuggets spilling toward the column) is at x ≈ 132–147 |
| right tunnels | `scene-right-tunnels.png` (new) | 148×270 | **left** edge on the column-right edge; cropped by the panel's right edge | two halls: R-top (floor top at y 60) and R1 (floor top at y 100). Mirror image of the left halls: open left end at the column edge with the work face at x ≈ 0–15, entry stairs or ladder at the right end (x ≈ 120–147, cropped on narrow panels). Nothing important above y 20 (app header) |
| right block | `scene-right.png` | 148×270 | right edge on the panel's right edge (unchanged) | only what is below the chamber: the gate (decorative), pillars. The alcove, throne and ledge move into `chamber.png`. Transparent behind the chamber and above it |
| chamber | `chamber.png` (new) | about 100×62 | default: inside the right block at block-local (48, 102); when the details card is open: drawn as the card's `::after`, right-aligned with the panel, just below the card | self-contained: alcove backing and walls, banners, the throne (from `throne.png`), the right hourglass pedestal, the ledge with the carved rune band, and the Arkenstone socket above the throne. Outline/dark rim on every edge, transparent outside, so it reads correctly wherever it is placed against the rock tile |

The chamber moves at runtime, so it must not depend on anything drawn in `scene-right.png` or `scene-right-tunnels.png` to look complete.

## Runes (`gate-runes.png` → `runes.png`)

- Five runes spread evenly along the full width of the chamber's ledge band (e.g. centres at chamber-x ≈ 10, 30, 50, 70, 90).
- Three states per rune: full (bright core, gold glow, as now), half (clearly lit but dimmer: gold core, no glow, or the lower half lit; must read as "half" at S = 3), none (dull ember).
- `runes.png`: horizontal strip of 11 frames, frame k = k half-steps lit: runes 0 … ⌊k/2⌋−1 full, rune ⌊k/2⌋ half if k is odd, the rest none. Frame 10 = all full, frame 0 = all none (frame 0 may use the dull red of v4).

## Dwarf workstations (frame 24×24, top-left in block-local px; floors as given)

Fill order = slot number:

| Slot | Block | Hall | Faces |
|---|---|---|---|
| s1 | left | L1 (top) | right |
| s2 | left | L2 | right |
| s3 | left | L3 | right |
| s4 | right tunnels | R-top | left (mirrored) |
| s5 | right tunnels | R1 | left (mirrored) |

Stations stand next to the work face (left halls: frame x ≈ 108–116; right tunnels: frame x ≈ 16–24); walk-in starts at the hall's entry (left: x ≈ 40–60; right: x ≈ 110–124). Walking speed 20 px/s as before.

## Geometry file

The scene agent writes `src/_geom.json` (replaces `_geom-right.json`, delete that file):

```json
{"slots": [{"block": "left", "x": 0, "y": 0, "start": 0}, "... 5 entries, in slot order"],
 "chamber": {"w": 0, "h": 0, "at": [48, 102],
             "king": [0, 0], "ark": [0, 0], "hourglass": [0, 0],
             "runes": {"x": 0, "y": 0, "w": 0, "h": 0, "frames": 11}},
 "ledge_y": 0}
```

`block` is `left` or `right` (right = `scene-right-tunnels.png`, x measured from its left edge). Chamber sprite positions are chamber-local top-left (king 32×32, Arkenstone 16×16, hourglass 12×20). `ledge_y` is the right-block-local y of the bottom of the chamber's ledge in its default position (the dragon is capped below it).

## File ownership in round 5

| Agent | Writes |
|---|---|
| scene | `src/scene.py`, `scene-left.png`, `scene-right.png`, `scene-right-tunnels.png`, `chamber.png`, `runes.png`, `src/throne.py` and `throne.png` (only if needed), `src/_geom.json`, `check-scene.html`, `src/_scene_*`; delete `gate-runes.png` and `src/_geom-right.json` |

Never edit `src/build_theme.py`, `preview*.html`, `README.md`, `STYLE-*.md` or the dwarf, king, hoard or dragon files.
