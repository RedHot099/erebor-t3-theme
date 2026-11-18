"""measure.py JSON_OUT label=query[|settle_ms|window_ms|js] ...   env: W,H, GPU=1, MOCK=path"""
import sys, os, asyncio, json, time, collections, subprocess
from playwright.async_api import async_playwright
HERE = os.path.dirname(os.path.abspath(__file__))
PAGE = 'file://' + os.environ.get('MOCK', HERE + '/mock.html')
W, H = int(os.environ.get('W', 1920)), int(os.environ.get('H', 1080))
NAMES = ['UpdateLayoutTree', 'Layout', 'PrePaint', 'Paint', 'Layerize', 'Commit', 'RasterTask', 'ImageDecodeTask',
         'GPUTask', 'RunTask', 'FireAnimationFrame', 'Animate', 'UpdateLayerTree', 'CompositeLayers', 'DrawFrame',
         'Decode Image', 'Draw LazyPixelRef', 'PaintImage', 'ParseHTML', 'RasterizerTaskImpl::RunOnWorkerThread',
         'LayerTreeHostImpl::PrepareToDraw', 'Graphics.Pipeline', 'BeginMainThreadFrame', 'BeginFrame', 'ActivateLayerTree',
         'SVGImage::ServiceAnimations', 'InvalidateLayout', 'ScheduleStyleRecalculation', 'TileManager::ScheduleTasks']
def cpu_by_type(root):
    out = collections.Counter()
    pids = subprocess.run(['pgrep', '-P', str(root)], capture_output=True, text=True).stdout.split()
    todo = [str(root)] + pids
    seen = set()
    while todo:
        p = todo.pop()
        if p in seen: continue
        seen.add(p)
        todo += subprocess.run(['pgrep', '-P', p], capture_output=True, text=True).stdout.split()
        try:
            cmd = open(f'/proc/{p}/cmdline').read().replace('\0', ' ')
            st = open(f'/proc/{p}/stat').read().rsplit(')', 1)[1].split()
            t = (int(st[11]) + int(st[12])) / os.sysconf('SC_CLK_TCK')
        except Exception: continue
        typ = 'browser'
        for part in cmd.split():
            if part.startswith('--type='): typ = part[7:]
            if part.startswith('--utility-sub-type='): typ = part.split('.')[-1]
        out[typ] += t
    return out
async def run(p, spec):
    label, rest = spec.split('=', 1)
    parts = rest.split('|')
    q = parts[0]; settle = int(parts[1]) if len(parts) > 1 and parts[1] else 8000
    win = int(parts[2]) if len(parts) > 2 and parts[2] else 8000
    js = parts[3] if len(parts) > 3 else ''
    args = ['--enable-gpu', '--ignore-gpu-blocklist', '--use-angle=default', '--enable-gpu-rasterization'] if os.environ.get('GPU') else []
    b = await p.chromium.launch(executable_path='/usr/bin/chromium', args=args)
    pg = await b.new_page(viewport={'width': W, 'height': H})
    await pg.goto(PAGE + '?ui=0&' + q)
    await pg.wait_for_timeout(settle)
    cdp = await pg.context.new_cdp_session(pg)
    await cdp.send('Performance.enable')
    bpid = None
    try:
        bc = await b.new_browser_cdp_session()
        info = await bc.send('SystemInfo.getProcessInfo')
        bpid = [x['id'] for x in info['processInfo'] if x['type'] == 'browser'][0]
    except Exception as e: print('pid err', e)
    events = []
    cdp.on('Tracing.dataCollected', lambda d: events.extend(d['value']))
    done = asyncio.Event(); cdp.on('Tracing.tracingComplete', lambda d: done.set())
    if not os.environ.get('NOTRACE'): await cdp.send('Tracing.start', {'transferMode': 'ReportEvents', 'traceConfig': {'includedCategories':
        ['devtools.timeline', 'disabled-by-default-devtools.timeline', 'cc', 'viz', 'gpu', 'blink', 'toplevel', 'benchmark', 'disabled-by-default-devtools.timeline.frame', 'disabled-by-default-devtools.timeline.invalidationTracking']}})
    m0 = {x['name']: x['value'] for x in (await cdp.send('Performance.getMetrics'))['metrics']}
    c0 = cpu_by_type(bpid) if bpid else {}
    nel = await pg.evaluate('document.querySelectorAll("*").length')
    if js: await pg.evaluate(js)
    await pg.evaluate('''() => { window.__f = []; let last = performance.now(); const t = n => { window.__f.push(n - last); last = n; requestAnimationFrame(t); }; requestAnimationFrame(t); }''')
    await pg.wait_for_timeout(win)
    fr = await pg.evaluate('window.__f')
    m1 = {x['name']: x['value'] for x in (await cdp.send('Performance.getMetrics'))['metrics']}
    c1 = cpu_by_type(bpid) if bpid else {}
    if not os.environ.get('NOTRACE'): await cdp.send('Tracing.end'); await done.wait()
    agg = collections.defaultdict(lambda: [0, 0.0]); thr = {}
    paint_clips = collections.Counter()
    for e in events:
        if e.get('ph') == 'M' and e.get('name') == 'thread_name': thr[(e['pid'], e['tid'])] = e['args']['name']
    bythread = collections.Counter(); elc = []
    for e in events:
        if e.get('ph') == 'X':
            n = e['name']
            if n in NAMES: agg[n][0] += 1; agg[n][1] += e.get('dur', 0) / 1000
            if n == 'RunTask' or n == 'ThreadControllerImpl::RunTask':
                bythread[thr.get((e['pid'], e['tid']), '?')] += e.get('dur', 0) / 1000
            if n == 'UpdateLayoutTree' and 'elementCount' in e.get('args', {}): elc.append(e['args']['elementCount'])
            if n == 'Paint':
                c = e.get('args', {}).get('data', {}).get('clip')
                if c: paint_clips[(round(c[2] - c[0]), round(c[5] - c[1]))] += 1
    fr = sorted(fr[2:]) or [0]
    res = {'label': label, 'q': q, 'elements': nel, 'window_s': win / 1000,
           'perf': {k: round(m1[k] - m0[k], 4) for k in ['RecalcStyleCount', 'RecalcStyleDuration', 'LayoutCount', 'LayoutDuration', 'ScriptDuration', 'TaskDuration']},
           'cpu_s': {k: round(c1[k] - c0.get(k, 0), 2) for k in c1},
           'raf': {'n': len(fr), 'p50': round(fr[len(fr) // 2], 1), 'p95': round(fr[int(len(fr) * .95)], 1), 'max': round(fr[-1], 1)},
           'trace_ms': {k: [v[0], round(v[1], 1)] for k, v in sorted(agg.items())},
           'thread_ms': {k: round(v) for k, v in bythread.most_common(8)},
           'paint_clips': paint_clips.most_common(5), 'elcount': [len([x for x in elc if x > 50]), sum(x for x in elc if x > 50)]}
    if os.environ.get('KEEP'): json.dump(events, open(f'{HERE}/trace-{label}.json', 'w'))
    await b.close()
    return res
async def main():
    out = sys.argv[1]; allr = []
    async with async_playwright() as p:
        for spec in sys.argv[2:]:
            r = await run(p, spec); allr.append(r); print(json.dumps(r)); sys.stdout.flush()
    json.dump(allr, open(out, 'w'), indent=1)
asyncio.run(main())
