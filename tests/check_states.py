"""State checks for the theme's app-state selectors, run on a readable build in the mock.

Builds the theme without the renaming minifier into tests/.out/readable, opens preview.html on that CSS in
headless Chromium and checks:
- weekly runes and Arkenstone for every value 0..100 %, and the Arkenstone twinkle at 100 %;
- the king state for the app's real sidebar status labels;
- dwarf slots for 12 running subagents;
- provider marks from the subagent group's avatars (10 combinations; 3 are known approximations);
- provider marks from the details card's list of running agents, and the neutral reset.

Run: uv run --with playwright --with pillow --with numpy --with zopfli python tests/check_states.py
Exit code 1 when a check fails.
"""
import asyncio
import math
import os
import pathlib
import subprocess
import sys

from playwright.async_api import async_playwright

ART = pathlib.Path(__file__).resolve().parent.parent
OUT = ART / "tests" / ".out" / "readable"
CHROMIUM = os.environ.get("CHROMIUM", "/usr/bin/chromium")


def build_readable() -> pathlib.Path:
    env = dict(os.environ, OPT="png,svg,lad,is,pos,nest", EREBOR_OUT=str(OUT / "dist"))
    subprocess.run([sys.executable, str(ART / "src" / "build_theme.py")], env=env, check=True,
                   stdout=subprocess.DEVNULL)
    mock = (ART / "preview.html").read_text().replace(
        'href="dist/erebor.css"', f'href="{(OUT / "dist" / "erebor.css").as_uri()}"')
    # the background image resolves against the page: keep the page next to a dist/ copy of it
    page = OUT / "preview.html"
    page.write_text(mock)
    return page


# readers: values are compared with the theme's own image variables
JS_SLOT_MARKS = """() => {
  const root = getComputedStyle(document.documentElement);
  const signs = [0, 1, 2].map(i => root.getPropertyValue('--s' + i).trim());
  const area = getComputedStyle(document.querySelector('[data-workspace-area="conversation"]'));
  return [1, 2, 3].map(i => { const v = area.getPropertyValue('--t' + i).trim(); return v ? signs.indexOf(v) : -1; });
}"""
PROVIDERS = ["other", "claude", "codex"]


async def main() -> int:
    page_path = build_readable()
    failures = 0

    def report(name, got, expected, known=False):
        nonlocal failures
        ok = got == expected
        if not ok and not known:
            failures += 1
        tag = "ok" if ok else ("known" if known else "FAIL")
        print(f"  {tag:5s} {name}: {got}" + ("" if ok else f" (expected {expected})"))

    async with async_playwright() as p:
        browser = await p.chromium.launch(executable_path=CHROMIUM)

        async def open_page(query):
            page = await browser.new_page()
            await page.goto(page_path.as_uri() + "?ui=0&" + query)
            await page.wait_for_timeout(300)
            return page

        print("weekly runes and Arkenstone, 0..100 %")
        page = await open_page("dw=0")
        bad = []
        for v in range(101):
            r = await page.evaluate("""(v) => {
              const $ = id => document.getElementById(id);
              $('weekrow').setAttribute('aria-label', 'Weekly: ' + v + '% left');
              $('sessrow').setAttribute('aria-label', 'Session: ' + v + '% left');
              const cs = getComputedStyle(document.documentElement);
              const find = (cur, pre, n) => { for (let i = 0; i < n; i++) if (cs.getPropertyValue(pre + i).trim() === cur) return i; return -1; };
              return [find(cs.getPropertyValue('--erb-runes').trim(), '--erb-img-rune', 11),
                      find(cs.getPropertyValue('--erb-ark-base').trim(), '--erb-img-ark', 6)];
            }""", v)
            ark = 5 if v == 0 else 4 if v < 20 else 3 if v < 40 else 2 if v < 60 else 1 if v < 80 else 0
            if r != [math.ceil(v / 10), ark]:
                bad.append(v)
        report("mismatched values", bad, [])
        twinkle = await page.evaluate("""() => {
          document.getElementById('sessrow').setAttribute('aria-label', 'Session: 100% left');
          const cs = getComputedStyle(document.documentElement);
          return cs.getPropertyValue('--erb-ark-fx').trim() === cs.getPropertyValue('--erb-img-ark-twinkle').trim();
        }""")
        report("Arkenstone twinkles at 100 %", twinkle, True)

        print("king state from the active sidebar row (\"title, status[, project]\")")
        for label, expected in [
            ("Erebor theme, Working, scratch", "working"), ("Erebor theme, Connecting", "working"),
            ("Erebor theme, Waiting, scratch", "working"), ("Erebor theme, Pending Approval, scratch", "waiting"),
            ("Erebor theme, Awaiting Input", "waiting"), ("Erebor theme, Guest Request, scratch", "waiting"),
            ("Erebor theme, Plan Ready, scratch", "waiting"), ("Erebor theme, Failed, scratch", "failed"),
            ("Erebor theme, Completed, scratch", "done"), ("Tests, Failed checks, Completed, scratch", "done"),
        ]:
            got = await page.evaluate("""(label) => {
              const row = document.getElementById('row');
              row.setAttribute('aria-label', label); row.setAttribute('aria-current', 'page');
              document.getElementById('send').setAttribute('aria-label', 'Send');
              const cs = getComputedStyle(document.documentElement), k = cs.getPropertyValue('--erb-king-1').trim();
              for (const n of ['working', 'waiting', 'failed', 'toast']) if (cs.getPropertyValue('--erb-img-king-' + n).trim() === k) return n;
              return '?';
            }""", label)
            report(label, "done" if got == "toast" else got, expected)
        await page.close()

        print("dwarf slots")
        page = await open_page("dw=0")
        walks = await page.evaluate("""() => {
          document.getElementById('sg').hidden = false;
          document.getElementById('sgb').setAttribute('aria-description', '12 working · 1 done');
          return getComputedStyle(document.querySelector('[data-workspace-area="conversation"]'))
            .animationName.split(', ').filter(n => n.startsWith('erb-walk')).length;
        }""")
        report("12 working -> walking slots", walks, 5)
        await page.close()

        print("provider marks from the group header avatars (all agents working)")
        known = {"other,codex,claude", "other,claude,codex", "claude,other,codex"}
        for combo in ["claude,codex,other", "codex,claude,claude", "claude,claude,codex", "other,codex,claude",
                      "claude,claude,claude", "codex,codex", "claude,other", "other,claude,codex",
                      "claude,other,codex"]:
            page = await open_page(f"dw=3&prov={combo}")
            got = [PROVIDERS[i] if i >= 0 else "-" for i in await page.evaluate(JS_SLOT_MARKS)]
            report(combo, got, (combo.split(",") + ["-"] * 3)[:3], known=combo in known)
            await page.close()
        page = await open_page("dw=1&lone=1&prov=claude")
        report("lone claude row", [PROVIDERS[i] if i >= 0 else "-" for i in await page.evaluate(JS_SLOT_MARKS)],
               ["claude", "-", "-"])
        await page.close()

        print("provider marks after a subagent finished (details card list of running agents)")
        for query, expected in [
            ("dw=1&done=1&prov=claude,codex", ["-", "-", "-"]),
            ("dw=1&done=1&prov=claude,codex&lin=codex", ["codex", "-", "-"]),
            ("dw=1&done=1&prov=claude,codex&lin=claude", ["claude", "-", "-"]),
            ("dw=2&done=1&prov=claude,codex,claude&lin=codex,claude", ["codex", "claude", "-"]),
            ("dw=2&done=1&prov=other,claude,codex&lin=other,codex", ["other", "codex", "-"]),
            ("dw=3&prov=claude,claude,claude&lin=codex,other,claude", ["codex", "other", "claude"]),
        ]:
            page = await open_page(query)
            got = [PROVIDERS[i] if i >= 0 else "-" for i in await page.evaluate(JS_SLOT_MARKS)]
            report(query, got, expected)
            await page.close()
        await browser.close()

    print("all checks passed" if not failures else f"{failures} check(s) failed")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
