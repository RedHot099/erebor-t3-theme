"""Post-pass on the generated CSS. Data URIs are cut out first and put back untouched."""
import re
from collections import Counter

def minify(css, OPT):
    uris = []
    def stash(m):
        uris.append(m.group(0)); return f"\x00{len(uris) - 1}\x00"
    css = re.sub(r'url\("data:[^"]*"\)', stash, css)
    if "pos" in OPT:
        W = "var(--chat-content-max-width, 46rem)"
        css = css.replace(f"{W} / 2", "var(--erb-h)")
        # into the chat area's own rule (a line of its own), not a state rule ending in the same selector
        css = re.sub(r'(^|\n)\[data-workspace-area="conversation"\]\{',
                     lambda m: m.group(1) + '[data-workspace-area="conversation"]{--erb-h:calc(' + W.replace(", ", ",") + '/2);',
                     css, count=1)
        css = css.replace(W, W.replace(", ", ","))
        css = re.sub(r" \+ 0 \* var\(--erb-u\)| - 0 \* var\(--erb-u\)", "", css)
        css = css.replace("calc(0 * var(--erb-u))", "0")
        css = re.sub(r"\+ -(\d)", r"- \1", css)
        css = re.sub(r"calc\((\d+%)\)", r"\1", css)
        css = re.sub(r"calc\(1 \* var\(--erb-u\)\)", "var(--erb-u)", css)
        css = css.replace(" * ", "*").replace(" / ", "/").replace("steps(1, end)", "steps(1)").replace(",end)", ")")
        css = css.replace("99999999s", "1e8s")
    if "nest" in OPT:
        lines = css.split("\n")
        out, run = [], []
        for l in lines:
            if l.startswith(":root:where(:has("):
                run.append("&" + l[5:])
            else:
                if run:
                    out.append(":root{" + "".join(run) + "}"); run = []
                out.append(l)
        if run:
            out.append(":root{" + "".join(run) + "}")
        css = "\n".join(out)
    if "min" in OPT:
        # image vars that are referenced once: inline the URL where it is used
        for m in re.finditer(r"(--erb-img-[\w-]+):(\x00\d+\x00);?", css):
            name, val = m.group(1), m.group(2)
            if len(re.findall(re.escape(f"var({name})") , css)) == 1:
                css = css.replace(m.group(0), "", 1).replace(f"var({name})", val)
        keep = {"--erb-anim-king", "erb-king-done"}   # preview.html drives the doze state with these
        names = Counter(n for n in re.findall(r"--erb-[\w-]+", css) if n not in keep)
        alpha = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789"
        short = [f"--E{c}" for c in alpha] + [f"--E{a}{b}" for a in alpha for b in alpha]
        table = {nm: short[i] for i, (nm, _) in enumerate(names.most_common())}
        css = re.sub(r"--erb-[\w-]+", lambda m: table.get(m.group(0), m.group(0)), css)
        kn = Counter(n for n in re.findall(r"(?<!-)erb-[\w-]+", css) if n not in keep)
        for i, (nm, _) in enumerate(sorted(kn.items(), key=lambda kv: -len(kv[0]))):
            css = css.replace(nm, f"E{alpha[i]}")
        css = css.replace(";}", "}").replace("}\n", "}")
    return re.sub(r"\x00(\d+)\x00", lambda m: uris[int(m.group(1))], css)
