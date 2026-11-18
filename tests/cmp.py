import json, sys, re, collections
a, b = json.load(open(sys.argv[1])), json.load(open(sys.argv[2]))
F = "bgImage bgPos bgSize bgRepeat bgColor bgAttach imgRender animDur animTF animFill k.content k.bgImage k.bgPos k.bgSize k.bgRepeat k.top k.right k.width k.height k.position r.trDur r.trDelay r.trTF r.trBeh r.animDur section".split()
bad = collections.Counter(); ex = {}
for k in a:
    fa, fb = a[k].split(' | '), b[k].split(' | ')
    assert len(fa) == len(F) == len(fb), (len(fa), len(F))
    for name, x, y in zip(F, fa, fb):
        if x != y:
            if name.endswith('bgSize'):
                xs, ys = x.split(', '), y.split(', ')
                if len(xs) == len(ys) and all(p == q or (q.endswith(' auto') and p.split()[0] == q.split()[0]) for p, q in zip(xs, ys)):
                    bad['(expected) ' + name + ' WxH -> W auto'] += 1; continue
            bad[name] += 1; ex.setdefault(name, (k, x[:300], y[:300]))
print(len(a), 'states;', dict(bad))
for n, e in ex.items(): print(n, *e, sep='\n   ')
