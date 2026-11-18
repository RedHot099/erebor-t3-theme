import json, sys
for f in sys.argv[1:]:
    print(f"{'label':28s} {'el':>6s} {'rend':>5s} {'gpu':>5s} {'main':>6s} {'paints/s':>8s} {'Paint':>6s} {'style#/s':>8s} {'styleMs':>7s} {'docStyle':>8s} {'raster':>7s} {'rafp95':>6s} {'max':>6s}  clips")
    for r in json.load(open(f)):
        t = r['trace_ms']; g = lambda k: t.get(k, [0, 0]); w = r['window_s']
        print(f"{r['label']:28s} {r['elements']:6d} {r['cpu_s'].get('renderer',0):5.2f} {r['cpu_s'].get('gpu-process',0):5.2f} {r['thread_ms'].get('CrRendererMain',0):6d} {g('Paint')[0]/w:8.1f} {g('Paint')[1]:6.0f} {g('UpdateLayoutTree')[0]/w:8.0f} {g('UpdateLayoutTree')[1]:7.0f} {r['perf']['RecalcStyleDuration']*1000:8.0f} {g('RasterTask')[1]:7.0f} {r['raf']['p95']:6.1f} {r['raf']['max']:6.1f}  {r['paint_clips'][:3]}")
