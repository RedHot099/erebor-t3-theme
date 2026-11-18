# Erebor

A dark T3 Code theme that draws a pixel-art cross-section of a dwarven mountain behind the chat. The scene reads the app's state: a dragon's hoard rises with the context window, dwarves mine while subagents run, and the King under the Mountain on his throne shows what the main thread is doing.

Personal theme. It needs no app changes and no JavaScript: everything is one theme file with CSS and a background image.

## What the scene shows

| Element | Reads | Behaviour |
|---|---|---|
| Hoard and dragon | `Context: N% used` | The hoard rises in 11 steps of 10 %. The dragon sleeps below 60 %, stirs at 60–79 %, wakes at 80–89 % and rages at 90–100 %. Its rise stops under the throne chamber. |
| Hourglass and Arkenstone | `Session: N% left` (5-hour limit) | The sand and the gem's light drain as the limit runs out. |
| Five runes on the chamber floor | `Weekly: N% left` | Each rune is full, half or dark: 10 % steps. Per-model rows such as `Weekly · Fable` are ignored. |
| King | the active sidebar row's status, the stop button, approval and input prompts | Working, waiting for you, toast when done (dozes after 2 minutes), failed. |
| Dwarves | the subagent group header (`N working · M done`) or a lone subagent row | One dwarf per running subagent, up to 5 (10–19 also show 5). A dwarf walks in from its tunnel's stairs and mines; when its subagent finishes, it walks back out. |
| Provider marks | subagent avatars; the details card's list of running agents | The first three dwarves get a lamp colour and a rune shield: Claude terracotta, Codex silver-white, other providers green. |
| Throne chamber | the thread details card | The chamber stays in the scene. If a tall card reaches it, a copy appears right under the card. |

The theme hides the **Usage limits** and **Context window** sections of the details card. Their rows stay in the page, so the scene can still read them.

The usage and context rows exist only while the thread details card is open. When you close the card, the scene keeps the last values.

## Install the theme on a computer

The built theme is committed in `dist/`, so installing needs only T3 Code and this repository. You do not need Python or a build.

1. Get the repository on the computer:

   ```sh
   git clone https://github.com/RedHot099/erebor-t3-theme.git
   cd erebor-t3-theme
   ```

2. Copy the two theme files into T3 Code's theme folder.
   - On Linux or macOS, run the install script from the repository folder:

     ```sh
     ./install.sh
     ```

   - On Windows, run in PowerShell from the repository folder:

     ```powershell
     $themes = if ($env:T3CODE_HOME) { "$env:T3CODE_HOME\userdata\themes" } else { "$HOME\.t3\userdata\themes" }
     New-Item -ItemType Directory -Force $themes | Out-Null
     Copy-Item dist\erebor.json, dist\erebor.png $themes
     ```

   T3 Code reads themes from `<T3 home>/userdata/themes`. The T3 home is `~/.t3`, or the folder in the `T3CODE_HOME` environment variable if you set one.
3. In T3 Code, open **Settings** and select **Erebor** under **Theme**. If Erebor is not in the list, restart T3 Code.

To update the theme later, pull the repository (`git pull`) and repeat step 2.

The theme works best with these app settings:

- the interface language is English, because the scene reads the app's English labels;
- the chat width is the default or **wide**, not **full**;
- the thread details card stays open, because the context and limit rows exist only there.

`erebor.png` is the back layer of the hoard. T3 Code serves it to the theme as `var(--theme-background-image)`. Keep it next to `erebor.json`.

## Build

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
| `docs/STYLE-v2.md` … `STYLE-v5.md` | Art briefs from the design rounds: palette, outline style, frame layouts, geometry. |

Generators write the art into the repository root and their review images as `src/_*.png`, which git ignores. Run a generator with `uv run --with pillow --with numpy python src/<name>.py`, then rebuild. `src/hoard.py` rewrites `src/_geom.json` without the keys that `src/scene.py` adds, so run `scene.py` after `hoard.py`.

## Known limits

- The theme reads the app's English labels. In another UI language the scene stays at its defaults.
- The **full** chat width setting is not supported: the column then has no fixed width and the scene's anchors drift. The default and **wide** widths work.
- Provider marks cover the first three dwarves. Without the details card's list of running agents, a finished subagent in a mixed-provider group turns the lamps neutral.
- The CSS is close to the 100,000-character limit.
