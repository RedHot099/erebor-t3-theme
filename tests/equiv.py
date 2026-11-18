"""equiv.py VARIANT_DIR OUT.json [ART_DIR] — computed styles of the scene for many app states (animations finished/seeked)."""
import sys, asyncio, json, re, hashlib
from playwright.async_api import async_playwright
import os
P = sys.argv[3] if len(sys.argv) > 3 else os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
JS = r"""
async () => {
  const $ = id => document.getElementById(id);
  const area = document.querySelector('[data-workspace-area="conversation"]');
  const panel = $('dpanel'), root = document.documentElement;
  const h = s => s;   // strings are hashed in python
  const settle = (t) => { for (const a of document.getAnimations()) { if (!(a.timeline instanceof DocumentTimeline)) continue; try {
      if (a.constructor.name === 'CSSTransition') a.finish();
      else if (t === 'end') a.finish(); else { a.pause(); const d = a.effect.getComputedTiming().endTime; a.currentTime = d * t; }
    } catch (e) {} } };
  const snap = () => { const c = getComputedStyle(area), k = getComputedStyle(panel, '::after'), r = getComputedStyle(root);
    return [c.backgroundImage, c.backgroundPosition, c.backgroundSize, c.backgroundRepeat, c.backgroundColor, c.backgroundAttachment, c.imageRendering,
      c.animationDuration, c.animationTimingFunction, c.animationFillMode,
      k.content, k.backgroundImage, k.backgroundPosition, k.backgroundSize, k.backgroundRepeat, k.top, k.right, k.width, k.height, k.position,
      r.transitionDuration, r.transitionDelay, r.transitionTimingFunction, r.transitionBehavior, r.animationDuration,
      getComputedStyle(document.querySelector('section[aria-label="Usage limits"]')).display].join(' | '); };
  const out = {};
  const rec = (key, t = 'end') => { settle(t); out[key] = snap(); };
  const set = (id, v) => v === null ? $(id).removeAttribute('aria-label') : $(id).setAttribute('aria-label', v);
  // neutral start
  const extra = document.createElement('div'); $('sessrow').parentNode.appendChild(extra);
  const lone = document.createElement('div'); lone.setAttribute('data-v2-item-type', 'subagent'); document.querySelector('.lane').appendChild(lone);
  const appr = document.createElement('div'); document.querySelector('.lane').appendChild(appr);
  set('ctxrow', 'Context: 47% used'); set('sessrow', 'Session: 62% left'); set('weekrow', 'Weekly: 80% left');
  $('sg').hidden = true; $('sgb').removeAttribute('aria-description');
  rec('start');
  for (let v = 0; v <= 100; v++) { set('ctxrow', `Context: ${v}% used`); rec('ctx' + v); }
  for (const junk of ['Context: unknown', 'Context: 55% left', 'Context window', 'Context: 5.5% used', 'Context: 12.5% used']) { set('ctxrow', junk); rec('ctxjunk ' + junk); }
  set('ctxrow', 'Context: 47% used');
  for (const e of [null, 0, 1, 5, 9, 10, 15, 20, 35, 50, 65, 79, 80, 95, 100]) {
    e === null ? extra.removeAttribute('aria-label') : extra.setAttribute('aria-label', `Session · Fable: ${e}% left`);
    for (let v = 0; v <= 100; v++) { set('sessrow', `Session: ${v}% left`); rec(`ses${v}/${e}`); }
  }
  extra.removeAttribute('aria-label');
  for (const junk of ['Session: 5.5% left', 'Session: 100% used', 'Session', 'Session: 42.5% left', 'Sessions: 3% left']) { set('sessrow', junk); rec('sesjunk ' + junk); }
  set('sessrow', 'Session: 62% left');
  for (const f of [null, 0, 7, 10, 50, 84, 100]) {
    f === null ? $('fablerow').removeAttribute('aria-label') : $('fablerow').setAttribute('aria-label', `Weekly · Fable: ${f}% left`);
    for (let v = 0; v <= 100; v++) { set('weekrow', `Weekly: ${v}% left`); rec(`wk${v}/${f}`); }
  }
  for (const junk of ['Weekly: 5.5% left', 'Weekly: 100% used', 'Weekly', 'Weekly: 42.5% left', 'Weekly: 10.5% left']) { set('weekrow', junk); rec('wkjunk ' + junk); }
  set('weekrow', 'Weekly: 80% left');
  // dwarves
  $('sg').hidden = false;
  for (const d of ['1 done', '0 working', '1 working · 1 done', '2 working', '3 working · 2 done', '4 working', '5 working', '6 working', '7 working',
                   '8 working', '9 working', '10 working', '12 working · 1 done', '1 workings', '11 working', 'Running', '3 queued · 1 working']) {
    $('sgb').setAttribute('aria-description', d);
    for (const t of [0, 0.3, 0.9995, 'end']) rec(`dw ${d} @${t}`, t);
  }
  $('sgb').setAttribute('aria-description', '1 done');
  for (const d of ['Running', 'Queued', 'Waiting', 'Done', 'Failed']) { lone.setAttribute('aria-description', d); for (const t of [0, 0.5, 'end']) rec(`lone ${d} @${t}`, t); }
  lone.removeAttribute('aria-description');
  // king
  const kt = [0, 0.01, 0.02, 0.0333, 0.034, 0.5, 0.999, 'end'];
  for (const lab of [null, 'Working', 'Connecting', 'Waiting', 'Pending Approval', 'Awaiting Input', 'Guest Request', 'Plan Ready', 'Failed', 'Completed'])
    for (const cur of [true, false]) {
      $('row').setAttribute('aria-label', ['Erebor theme', lab, 'scratch'].filter(Boolean).join(', '));
      cur ? $('row').setAttribute('aria-current', 'page') : $('row').removeAttribute('aria-current');
      for (const t of kt) rec(`king row ${lab} cur=${cur} @${t}`, t);
    }
  $('row').setAttribute('aria-label', 'Erebor theme, scratch'); $('row').setAttribute('aria-current', 'page');
  for (const b of ['Stop generation', 'Stopping', 'Send']) { $('send').setAttribute('aria-label', b); for (const t of kt) rec(`king btn ${b} @${t}`, t); }
  $('send').setAttribute('aria-label', 'Send');
  for (const [nm, on, off] of [['pending', () => { $('pending').hidden = false; $('pending').setAttribute('data-pending-user-input-toggle', ''); }, () => { $('pending').hidden = true; $('pending').removeAttribute('data-pending-user-input-toggle'); }],
                                ['approval', () => appr.setAttribute('data-approval-detail', ''), () => appr.removeAttribute('data-approval-detail')]]) {
    on(); for (const t of kt) rec(`king ${nm} @${t}`, t); off(); for (const t of kt) rec(`king ${nm} off @${t}`, t);
  }
  // precedence: failed row + stop button + pending
  $('row').setAttribute('aria-label', 'Erebor theme, Failed, scratch'); $('send').setAttribute('aria-label', 'Stop generation'); rec('king failed+working');
  $('row').setAttribute('aria-label', 'Erebor theme, Awaiting Input, scratch'); rec('king waiting+working');
  $('row').setAttribute('aria-label', 'Erebor theme, scratch'); $('send').setAttribute('aria-label', 'Send');
  // details closed: values hold (transitions are NOT finished here)
  const raw = k => { out[k] = snap(); };
  set('ctxrow', 'Context: 83% used'); set('sessrow', 'Session: 0% left'); set('weekrow', 'Weekly: 30% left'); rec('before-close');
  await new Promise(r => setTimeout(r, 1500));
  for (const id of ['ctxrow', 'sessrow', 'weekrow']) set(id, null);
  panel.hidden = true; panel.removeAttribute('data-thread-details-panel');
  await new Promise(r => setTimeout(r, 300)); raw('closed-held');
  panel.hidden = false; panel.setAttribute('data-thread-details-panel', 'inline');
  set('ctxrow', 'Context: 12% used'); set('sessrow', 'Session: 55% left'); set('weekrow', 'Weekly: 100% left');
  await new Promise(r => setTimeout(r, 1700)); raw('reopened');
  return out;
}
"""
async def main():
    var, outp = sys.argv[1], sys.argv[2]
    html = open(P + '/preview.html').read().replace('href="dist/erebor.css"', f'href="file://{var}/dist/erebor.css"')
    open(f'{var}/mock.html', 'w').write(html)
    res = {}
    async with async_playwright() as p:
        b = await p.chromium.launch(executable_path='/usr/bin/chromium')
        for w, hgt in ((1920, 1080), (1300, 800)):
            pg = await b.new_page(viewport={'width': w, 'height': hgt})
            await pg.goto(f'file://{var}/mock.html?ui=0')
            await pg.wait_for_timeout(500)
            r = await pg.evaluate(JS)
            for k, v in r.items():
                res[f'{w}:{k}'] = v
            await pg.close()
        await b.close()
    json.dump(res, open(outp, 'w'))
    print(var.split('/')[-1], len(res), 'states', hashlib.sha1(json.dumps(res, sort_keys=True).encode()).hexdigest()[:12])
asyncio.run(main())
