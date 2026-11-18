# Developing the Erebor theme

This page covers the build, the offline preview, the checks and the art generators. For the reasons behind the CSS, including the performance rules, read [How the Erebor theme works](how-it-works.md).

Run every command from the repository root.

## Build the theme

```sh
uv run --with pillow --with numpy --with zopfli python src/build_theme.py
```

The build writes `dist/erebor.css`, `dist/erebor.json` and `dist/erebor.png`, and prints the CSS size. T3 Code rejects theme CSS over 100,000 characters. The current build is 93,802.

Environment variables:

- `EREBOR_OUT=<dir>` writes the files to `<dir>` instead of `dist/`.
- `OPT=png,svg,lad,is,pos,nest` builds without the renaming minifier, so the CSS keeps readable `--erb-*` names. `OPT=` (empty) builds the plain version that the equivalence check uses as a reference. The default is all optimisations: `png,svg,lad,is,pos,nest,min`.

## Preview without the app

Open `preview.html` in Chromium. It is a mock of the T3 Code DOM with the parts the theme reads, and it loads `dist/erebor.css`. Query parameters set the state, for example `preview.html?ctx=90&dw=3&prov=claude,codex,other`:

| Parameter | Meaning |
|---|---|
| `ctx` | context used, 0–100 |
| `s`, `wk` | session and weekly limit left, 0–100 |
| `dw` | running subagents, 0–5 |
| `done` | finished subagents in the group |
| `prov` | providers of the group's avatars: `claude`, `codex`, `other` |
| `lin` | running agents in the details card's list, same names as `prov` |
| `lone=1` | show one subagent as a lone row instead of a group |
| `state` | king: `working`, `waiting`, `done`, `doze`, `failed` |
| `det=0`, `ch` | close the details card; card height in px |
| `sb=0`, `w` | close the sidebar; app width in px |
| `ui=0` | hide the control panel |

## Test

Run the state checks before you install a changed build:

```sh
uv run --with playwright --with pillow --with numpy --with zopfli python tests/check_states.py
```

It builds a readable copy into `tests/.out/` and checks runes, Arkenstone, king states, dwarf slots and provider marks in the mock. Three provider combinations are marked `known`: with mixed providers, the group header alone cannot always say which avatar belongs to which dwarf.

Other tools in `tests/`:

- `equiv.py` and `cmp.py` compare two builds. `equiv.py <dir> <out.json>` records the computed styles of the scene in 5,350 app states for the CSS in `<dir>/dist/erebor.css`. `cmp.py a.json b.json` lists the differences. Use it after a refactor that must not change the picture.
- `perf/measure.py` and `perf/tab.py` measure style recalculation, paint and CPU in a mock with a long fake chat (`perf/mock.html`, parameters `tl` for chat length and `churn` for simulated streaming). For example: `GPU=1 uv run --with playwright python tests/perf/measure.py out.json "steady=dw=5|8000|8000"`, then `python tests/perf/tab.py out.json`.

## Files

| Path | Contents |
|---|---|
| `src/build_theme.py` | Builds the theme: layers, state rules, animations, colours. |
| `src/cssmin.py`, `src/pngopt.py` | Minifier and PNG encoder used by the build. |
| `src/scene.py` | Scene blocks, tunnels with ore, throne chamber, runes; writes `src/_geom.json` (dwarf stations, chamber layout). |
| `src/hoard.py`, `src/dragon.py`, `src/dwarf.py`, `src/king.py`, `src/props.py`, `src/throne.py`, `src/provider_signs.py` | Generators for the other sprites. `props.py` draws the hourglass and the Arkenstone. |
| `src/common.py` | Palette and indexed-PNG helpers. |
| `*.png` in the root | Runtime art the build reads. |
| `dist/` | The built theme. |
| `install.sh` | Copies the built theme into T3 Code's theme folder. |
| `preview.html` | Offline mock of the app. |
| `tests/` | State checks, equivalence check, performance harness. |
| `docs/how-it-works.md` | Why the CSS is built the way it is, including the performance rules. |
| `docs/development.md` | This page. |
| `docs/images/` | Screenshots for the README, taken from `preview.html`. |
| `docs/STYLE-v2.md` … `STYLE-v5.md` | Art briefs from the design rounds: palette, outline style, frame layouts, geometry. |

Generators write the art into the repository root and their review images as `src/_*.png`, which git ignores. Run a generator with `uv run --with pillow --with numpy python src/<name>.py`, then rebuild. `src/hoard.py` rewrites `src/_geom.json` without the keys that `src/scene.py` adds, so run `scene.py` after `hoard.py`.
