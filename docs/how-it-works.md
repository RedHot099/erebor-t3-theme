# How the Erebor theme works

A T3 Code theme is one JSON file with colours and up to 100,000 characters of CSS, plus an optional background image. There is no JavaScript. The theme therefore has two jobs that CSS does not do easily: draw an animated scene, and find out what the app is doing. This page explains the choices behind `src/build_theme.py`.

## The scene is one stack of background layers

The scene is the background of `[data-workspace-area="conversation"]`, the chat area: about 40 layers in one `background-image` list. The tunnels, the throne block and the dwarf stations are anchored to the edges of the chat column (`--chat-content-max-width`) and to the edges of the chat area, so the scene follows the window width and the sidebar.

A background layer cannot crop a sprite sheet to one frame. Every animated sprite is therefore a small SVG data URI that wraps the PNG frames and animates them inside, on its own clock. Static art is a PNG data URI. The back hoard is the theme's background-image file (`dist/erebor.png`), which keeps about 10,000 characters out of the CSS.

The throne chamber has a second copy in `[data-thread-details-panel="inline"]::after`. It is positioned with CSS anchors (`anchor-name: --erb-a` on the chat area, `--erb-c` on the card) and shows only when a tall card reaches the chamber (`position-visibility: no-overflow`). It then covers the scene's copy with rock and draws the chamber right under the card.

## State comes from the app's labels

The theme reads state with `:has()` from labels the app renders anyway:

- `aria-label` of the details card rows: `Context: N% used`, `Session: N% left`, `Weekly: N% left`;
- `aria-description` of the subagent group header (`N working · M done`) and of a lone subagent row (`Running`, `Queued`, `Waiting`);
- the active sidebar row's `aria-label`, `title, status[, project]`;
- the provider icons in the subagent avatars (their `svg[viewBox]`).

Percentages map to steps with attribute prefixes. `[aria-label^="Weekly: 4"]` matches 4 % and 40–49 %, so a later rule with the exact single-digit values corrects the small numbers. Rule order then decides.

The context and limit rows disappear when the details card closes. Without a fix, the hoard and the runes would reset each time. The theme holds the last value instead: when a row is missing, the property gets a `transition` with a delay of 10⁸ seconds and `allow-discrete`, so it keeps its old value until the row returns.

The provider marks after a subagent finishes come from the details card's list of running agents. CSS cannot pass a value from the card up to the chat area without `:has()`. So each matching icon in that list declares a named view timeline (`view-timeline`), `[data-chat-column]` makes the names visible to the chat area (`timeline-scope`), and the chat area runs one animation per name whose keyframes set the mark. When the icon is absent, its timeline does not exist and the animation has no effect.

## Performance rules

A performance council measured the theme in a mock with a long chat (`tests/perf/`). These rules came out of it. Breaking one shows up as stutter while the agent streams text or when dwarves arrive.

**No `:not()`, `:nth-child()`, `:first-child` or other structural pseudo-classes inside a `:has()` argument.** With one of them present, Chromium re-matches every `:has()` rule of the theme on each element insertion: about 18 ms per streamed element in a 600-message chat. Sibling chains (`.size-6 + .size-6`) are cheap and replace `:nth-child()`. Rule order replaces `:not()`. `:not(:has(…))` outside the argument is fine.

**Keep the number of `:has()` arguments small.** Any change to an `aria-label` in the page re-matches all of them, at about 0.1 ms per argument in a 5,000-element chat. The hourglass and the Arkenstone share one ladder of rules, and the dwarves use one argument per subagent count.

**Keep frequently changing state off `:root`.** A change of a custom property on `:root` restyles the whole document. The dwarf slots therefore live on the chat area as registered, non-inherited properties (`@property … inherits: false`). The count rules on the chat area only switch a toggle per slot (`--erb-onN`, empty when on, undefined when off). Every slot value starts with `var(--erb-onN)`, so it is invalid, and its reader's fallback applies, while the toggle is off.

**Do not move every state rule onto the chat area.** The chat area restyles on every step of a dwarf's walk, and each restyle re-runs the `:has()` rules that target it. Only the dwarf and provider rules live there. Context, limits and the king stay on `:root`, which restyles only when they change.

**Unload sprites that are not on screen.** An SVG sprite keeps animating and repainting the whole chat background even when it is positioned off screen. The walk sprites come from the walk keyframes only, so they unload when the walk ends.

**The walk properties do not inherit.** `--erb-dxN`, `--erb-aN`, `--erb-oN` and the walk-out gate `--erb-gtN` are animated on the chat area and read only there. If they inherited, every step of a walk would restyle the message timeline below.

## Size

The build keeps the CSS under the limit with `src/cssmin.py` (short names for `--erb-*` properties and keyframes, nested `:root` rules, shorter numbers) and `src/pngopt.py` (palette PNGs at the smallest bit depth, compressed with zopfli). `tests/equiv.py` checked that both change nothing on screen.
