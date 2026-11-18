# Erebor art v4: right block relayout, gate runes, planted dwarves

Round 4 keeps everything in `STYLE-v2.md` and `STYLE-v3.md` except what this file changes. Read `README.md`, `STYLE-v2.md` and `STYLE-v3.md` first.

## What Jakub saw in the live app

- The top of the right block sits under the app's UI: the header row, its buttons and the dropdowns that open from them cover right-block-local y < 64 (S = 4, 1094 CSS px tall window). The R1 hall and its dwarf (slot s2) were invisible, and the king was too close to that UI.
- The dwarf's work cycle moves the whole body up and down, so the feet sink into the floor on some frames.
- New mapping of the usage limits: hourglass and Arkenstone both show the 5 h "Session" limit; the weekly limit lights the runes on the gate below the throne.

## Right block, new layout (`scene-right.png`, still 148×270, bottom-anchored, right edge on the panel's right edge)

Right-block-local coordinates. Top to bottom:

| Band | Local y | Content |
|---|---|---|
| unsafe | 0–63 | plain rock (transparent) or faint, unimportant decoration only; nothing that must be seen |
| R1 hall | 64–103 | the mine hall for slot s2, moved down from the top; floor's top surface at y 100; gold seam / work face at x ≈ 76–86 struck by the mirrored dwarf; stairs or ladder at its right end (x ≈ 133–147) where the dwarf enters |
| throne alcove | 104–155 | `throne.png` (100×48, unchanged art) placed at (48, 104), i.e. 48 px lower than v3; alcove backing, banners and ledge move with it |
| gate | 160–270 | the great gate, shortened to fit; its frame carries the rune row(s) that light up with the weekly limit; the lower part may be covered by the dragon and the hoard |

The throne sprites keep their alcove-local boxes from v3 (king x 34–65 y 10–41, Arkenstone x 42–57 y −1–14, hourglass x 80–91 y 26–45), so they move down by 48 with the alcove. The left block, the hoard and the dragon do not change.

## Gate runes (`gate-runes.png`)

- An overlay drawn over the gate's runes, transparent everywhere else, in a horizontal strip of 6 frames of identical size.
- Frame 0 = weekly limit 80–100 % left: all runes lit (pale gold-white core, gold glow 1 px around, same light language as the Arkenstone). Frames 1–4 = 60–79, 40–59, 20–39, 1–19 %: progressively fewer runes lit, the rest dim embers. Frame 5 = 0 % left: all runes dark or a faint dull red.
- The unlit rune carving itself is part of `scene-right.png`; the overlay only adds light.
- Keep the overlay box tight (the build places it with one background layer), and keep the runes clear of the dragon: the visible part of the gate on Jakub's screen is roughly local y 160–215 near the gate's left half.

## Dwarf work cycle (`dwarf.png`)

- Frames 0–7 (work) and 8–9 (rest): feet, boots and legs are pixel-identical across all ten frames and stand on the frame's bottom row exactly as the walk frames do. The torso may lean or dip by at most 1 px, never the feet. The motion lives in the arms, the pick, the beard and the head (a 1 px nod is fine).
- The walk frames 10–15 keep their timing; check that their feet touch the same bottom row.
- Sheet layout, colour rows and frame size do not change.

## Geometry file

The scene agent writes `src/_geom-right.json` with the final numbers the build reads:

```json
{"throne": [48, 104], "s2": {"x": 86, "y": 76, "start": 124},
 "runes": {"x": 0, "y": 0, "w": 0, "h": 0, "frames": 6}}
```

`s2.y` is the dwarf frame's top-left y (floor top − 24); `runes` is the overlay frame's top-left in right-block-local px and its size.

## File ownership in round 4

| Agent | Writes |
|---|---|
| scene | `src/scene.py`, `scene-right.png`, `scene-left.png` (only if needed), `rock-tile.png` (only if needed), `src/throne.py` and `throne.png` (only if needed), `gate-runes.png`, `src/_geom-right.json`, `check-scene.html`, `src/_scene_*` |
| dwarf | `src/dwarf.py`, `dwarf.png`, `check-dwarves.html`, `src/_dwarf*` |

Never edit `src/build_theme.py`, `preview*.html`, `README.md`, `STYLE-*.md` or another agent's files.
