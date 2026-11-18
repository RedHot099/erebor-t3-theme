# Erebor art v3: responsive layout contract

Round 3 keeps the v2 style (`STYLE-v2.md`: bold 1 px outline `#07080a`, 3–4 flat tones per material, key light upper left, same palette, indexed PNG). Read `README.md` and `STYLE-v2.md` first. This file changes only what it says.

## Why v3

The scene was one 480×270 canvas, centred and cropped. In the app the conversation panel is narrower than 1920 px: Jakub's laptop is 1800 CSS px wide, the sidebar takes 256 px, and the thread details panel another 280 px. Cropping the centred canvas cut the king, the throne and half of the left halls. In v3 the scene is split into blocks with their own anchors:

- the mines on the left are shortened from the left as the panel narrows (cropped at the panel's left edge);
- the throne group, the king and the dragon's head stay visible;
- the dwarves stay visible, and when a subagent starts its dwarf first walks to its workstation.

## Reference frame

Native px, scale S = 4 (3 on narrow panels). Reference panel: 1920 CSS px wide, chat column 736 px (46rem) centred, so the column covers native x 148–332 of the old 480 canvas. "Column-left edge" and "column-right edge" mean those two lines; they move with the panel width, the chat width setting and S.

## Layers and anchors

All blocks are anchored to the panel's bottom edge (block bottom = panel bottom). Above and beside the blocks the panel shows `rock-tile.png` repeated, so the panel can be any width or height.

| Layer | File | Size | Horizontal anchor | Reference canvas x |
|---|---|---|---|---|
| base | `rock-tile.png` | 64×64, seamless in x and y | repeat, origin top-left of the panel | everywhere |
| left block | `scene-left.png` | 148×270 | right edge on the column-left edge | 0–148 |
| right block | `scene-right.png` | 148×270 | right edge on the panel's right edge | 332–480 |
| throne alcove | `throne.png` | 100×48 | inside the right block at block-local (48, 56) | 380 |
| hoard (back, front) | `hoard-back.png`, `hoard-front.png` | 480 wide | centred on the panel | 0–480 |
| hoard extension | `hoard-back-tile.png`, `hoard-front-tile.png` | 32 wide, same heights as the layers | repeat-x across the panel behind the hoard layers | outside 0–480 |
| dragon | `dragon.png` | 160×70 frames | left edge 8 native px left of the column-right edge | 324 (unchanged) |

Block rules:

- Plain rock inside a block is transparent, so the tile shows through and no seam appears when the blocks move against the tile. A block draws only its structures (halls, floors, stairs, pillars, gate, alcove backing, veins) and their dark interiors and shadows. Edges of structures that touch plain rock end in an outline or a 1–2 px dark rim, not a hard cut.
- The left block's left part (local x 0–40) holds the stairs between halls L1–L3. It is the part that disappears first when the panel narrows; nothing important lives there.
- The tile is dark, low-contrast cavern rock from the existing scene's palette (#0b0c0f #101215 #171a1f, sparse #262a31). It must read as calm background behind chat text.

## Throne alcove change

The hourglass moves from the left pedestal to a right pedestal, so every key throne element sits in the alcove's right 66 px (the narrowest right gutter on Jakub's laptop with both panels open is 66 native px).

Alcove-local coordinates (alcove = 100×48, placed at right-block-local (48, 56)):

| Sprite | Local box | Notes |
|---|---|---|
| King frame | x 34–65, y 10–41 | unchanged, seat must line up as before |
| Arkenstone socket | x 42–57, y −1–14 | unchanged |
| Hourglass frame | x 80–91, y 26–45 | new: stands on a right pedestal whose flat top is local y 46, x 77–94 |
| Left pedestal | x 6–22 | becomes decoration (brazier, banner, chest); may be hidden behind the chat column |

## Dwarf workstations and walk-in

Frame 24×24, coordinates are the frame's top-left in block-local px. Dwarves stand on the hall floors at the same heights as in v2.

| Slot | Block | Hall | Station | Faces | Walk-in start | Walk distance |
|---|---|---|---|---|---|---|
| s1 | left | L2 | (87, 73) | right | (40, 73) | 47 px right |
| s2 | right | R1 | (86, 29) | left (mirrored) | (124, 29) | 38 px left |
| s3 | left | L1 | (89, 29) | right | (44, 29) | 45 px right |
| s4 | left | L3 | (85, 117) | right | (38, 117) | 47 px right |

- The left halls' work faces (gold veins) stay at their inner end, local x ≈ 110–125, next to the column.
- R1 needs a new work face: a gold seam on R1's back wall or a rock outcrop at right-block-local x ≈ 76–86, which the mirrored dwarf at (86, 29) strikes. R1 is entered from its right end (stairs or a ladder near local x 130–146), so the walk-in starts there.
- Walking speed: 20 native px per second. The walk cycle in `dwarf.png` is 6 frames at 100 ms (frames 10–15), and the body moves 2 px per frame. The headlamp cone moves with the dwarf.
- When the walk ends, the dwarf switches to its v2 work/rest loop.

## Scale tiers

- S = 4 when the panel is at least 1240 CSS px wide, otherwise S = 3. Blocks stay bottom-anchored at both scales.
- At S = 4 and 1240 px the left block is cropped by 82 native px, so the left stations (x ≥ 85) stay visible.

## File ownership in round 3

| Agent | Writes |
|---|---|
| scene | `src/scene.py`, `scene-left.png`, `scene-right.png`, `rock-tile.png`, `src/throne.py`, `throne.png`, `check-scene.html`, `src/_scene_*` |
| dwarf | `src/dwarf.py`, `dwarf.png`, `lamp.png` (only if needed), `check-dwarves.html`, `src/_dwarf*` |
| king | `src/king.py`, `king.png`, `check-king.html`, `src/_king*` |
| hoard | `src/hoard.py`, `hoard-back.png`, `hoard-front.png`, `hoard-back-tile.png`, `hoard-front-tile.png`, `src/_geom.json`, then rerun `src/dragon.py` without editing it, `check-hoard.html`, `src/_hoard*` |

Never edit `preview.html`, `README.md`, `STYLE-*.md` or another agent's files; the parent session integrates. Leave `scene.png` in place (the old preview still uses it).
