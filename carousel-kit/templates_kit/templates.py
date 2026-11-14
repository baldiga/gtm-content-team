"""One renderer per library template. Each render(spec, fmt) returns a list of
pages [{"html": str, "duration": float?}]. fmt in feed | story | x.
Text fields accept *accent* and [[keep together]] markers and \\n line breaks."""
from __future__ import annotations

from tk import mk, page, progress, BRAND

NOT_BUILT = {
    6: "red-pen teardown: not built yet",
    11: "whiteboard: needs the owner's real photo; not built",
    13: "simple chart: not built yet",
    14: "exact prompt card: needs the owner's real prompt; not built",
}


def _s(x):
    return x if isinstance(x, dict) else {"t": x}


def header(spec, title_key="title", sub=True, cls="hd"):
    h = f'<h1 class="t">{mk(spec[title_key])}</h1>' if spec.get(title_key) else ""
    if sub and spec.get("subtitle"):
        h += f'<div class="sub">{mk(spec["subtitle"])}</div>'
    return f'<div class="{cls}">{h}</div>' if h else ""


def need(spec, *keys):
    miss = [k for k in keys if not spec.get(k)]
    if miss:
        raise SystemExit(f"template {spec.get('template')}: spec is missing {miss}")


# ======================================================== 1. animated stack map
CSS1 = """
.hdbox{position:absolute;top:0;right:0;left:0}
.cv{position:absolute;right:0;left:0}
.cv svg{position:absolute;inset:0;z-index:0}
.cv line{stroke:var(--rule);stroke-width:5;stroke-dasharray:10 10}
.cv line.on{stroke:var(--accent)}
.hub{position:absolute;z-index:1;border-radius:28px;background:var(--ink);color:var(--paper);display:flex;flex-direction:column;align-items:center;justify-content:center;text-align:center;padding:0 24px}
.hub .a{font-size:40px;font-weight:700;line-height:1.2}.hub .b{font-size:28px;color:var(--dsoft);margin-top:8px}
.node{position:absolute;z-index:1;border-radius:22px;background:#fff;border:3px solid var(--rule);display:flex;flex-direction:column;align-items:center;justify-content:center;text-align:center;font-size:36px;font-weight:600;line-height:1.15;padding:0 14px}
.node small{font-size:22px;font-weight:400;color:var(--soft);margin-top:6px}
.node.on{border-color:var(--accent);box-shadow:0 8px 0 #B4451A22}
.node.off{background:#EFEAE1;border-color:#E4DDD1;color:#CFC7BA;box-shadow:none}
.node.off small{color:#D6CFC3}
.node.fin.on{background:var(--accent);border-color:var(--accent);color:#fff}.node.fin.on small{color:var(--paper)}
.close{position:absolute;right:0;left:0;text-align:center;font-size:32px;color:var(--soft);line-height:1.3}
.close[data-hidden]{opacity:0}
.f-x .hub .a{font-size:36px}.f-x .node{font-size:32px}
"""
GEO1 = {
    "feed": dict(W=910, hd=270, top=300, h=700, close=1040, nw=300, nh=118, hw=420, hh=200),
    "story": dict(W=910, hd=260, top=300, h=760, close=1110, nw=300, nh=124, hw=420, hh=210),
    "x": dict(W=1440, hd=150, top=172, h=470, close=672, nw=330, nh=104, hw=470, hh=150),
}


def _stack_geo(n, g):
    W, H, nw, nh = g["W"], g["h"], g["nw"], g["nh"]
    bottom = n % 2 == 1
    pairs = n // 2
    side_h = H - (nh + 40 if bottom else 0)
    rows = [0] if pairs == 1 else [round(i * (side_h - nh) / (pairs - 1)) for i in range(pairs)]
    rects = []
    for r in rows:
        rects.append((W - nw, r)); rects.append((0, r))        # right first (RTL reading order)
    if bottom:
        rects.append(((W - nw) // 2, H - nh))
    hub = ((W - g["hw"]) // 2, (side_h - g["hh"]) // 2)
    return rects, hub


def r1(spec, fmt):
    need(spec, "title", "hub", "nodes")
    nodes = [_s(x) for x in spec["nodes"]]
    if not 3 <= len(nodes) <= 7:
        raise SystemExit("template 1: 3 to 7 nodes")
    g = GEO1[fmt]
    rects, (hx, hy) = _stack_geo(len(nodes), g)
    hub = _s(spec["hub"])
    hcx, hcy = hx + g["hw"] / 2, hy + g["hh"] / 2
    pages = []
    n = len(nodes)
    for k in range(n + 2):
        body = (f'<div class="hdbox fit" data-id="title" style="height:{g["hd"]}px;justify-content:flex-start">'
                f'<div class="in">{header(spec)}</div></div>')
        body += f'<div class="cv" style="top:{g["top"]}px;height:{g["h"]}px"><svg width="{g["W"]}" height="{g["h"]}">'
        for i, (x, y) in enumerate(rects):
            body += (f'<line x1="{x + g["nw"] / 2}" y1="{y + g["nh"] / 2}" x2="{hcx}" y2="{hcy}" '
                     f'class="{"on" if i < k else ""}"/>')
        body += "</svg>"
        body += (f'<div class="hub" style="left:{hx}px;top:{hy}px;width:{g["hw"]}px;height:{g["hh"]}px">'
                 f'<div class="a">{mk(hub["t"])}</div>' + (f'<div class="b">{mk(hub["s"])}</div>' if hub.get("s") else "") + "</div>")
        for i, ((x, y), nd) in enumerate(zip(rects, nodes)):
            cls = ("on" if i < k else "off") + (" fin" if (n % 2 == 1 and i == n - 1) else "")
            body += (f'<div class="node {cls}" style="left:{x}px;top:{y}px;width:{g["nw"]}px;height:{g["nh"]}px">'
                     f'{mk(nd["t"])}' + (f"<small>{mk(nd['s'])}</small>" if nd.get("s") else "") + "</div>")
        body += "</div>"
        if spec.get("closing"):
            hid = "" if k > n else " data-hidden"
            body += f'<div class="close"{hid} style="top:{g["close"]}px">{mk(spec["closing"])}</div>'
        dur = 1.0 if k == 0 else (3.0 if k == n + 1 else 0.9)
        pages.append({"html": page(fmt, body, CSS1), "duration": dur})
    if not spec.get("closing"):
        pages = pages[:-1]; pages[-1]["duration"] = 3.0
    return _open_full(spec, pages)


def _open_full(spec, pages):
    """open_full: GIF and MP4 open on the complete final frame (thumbnail), then replay the reveal."""
    if spec.get("open_full"):
        first = dict(pages[-1]); first["duration"] = float(spec.get("open_hold", 1.5))
        pages = [first] + pages[1:]
    return pages


# ======================================================== 2. dense cheat sheet
CSS2 = """
.grid{display:grid;grid-template-columns:repeat(var(--cols),1fr);gap:22px}
.blk{background:#FBF9F5;border:2px solid var(--rule);border-radius:22px;padding:28px 28px 30px;display:flex;gap:20px;align-items:flex-start}
.badge{flex:0 0 auto;width:58px;height:58px;border-radius:50%;background:var(--accent);color:#fff;font-weight:700;font-size:30px;display:flex;align-items:center;justify-content:center;direction:ltr}
.bh{font-size:36px;font-weight:700;line-height:1.2}
.bt{font-size:30px;line-height:1.4;color:var(--soft);margin-top:8px}
.f-feed .fit,.f-x .fit{margin-top:40px}
.f-story .hd h1.t{font-size:58px}
.f-story .grid{gap:28px}.f-story .blk{padding:40px 36px}.f-story .bh{font-size:46px}.f-story .bt{font-size:38px}
.f-story .badge{width:72px;height:72px;font-size:36px}
.f-story .fit{margin-top:44px}
.f-x .blk{padding:26px 30px;flex-direction:column;gap:16px}.f-x .bh{font-size:32px}.f-x .bt{font-size:26px}.f-x .badge{width:50px;height:50px;font-size:26px}
"""


def _blocks(blocks, start=0):
    out = []
    for i, b in enumerate(blocks, start=start + 1):
        b = b if isinstance(b, dict) else {"h": b}
        out.append(f'<div class="blk"><div class="badge">{i}</div><div><div class="bh">{mk(b["h"])}</div>'
                   + (f'<div class="bt">{mk(b["t"])}</div>' if b.get("t") else "") + "</div></div>")
    return "".join(out)


def r2(spec, fmt):
    need(spec, "title", "blocks")
    blocks = spec["blocks"]
    if fmt == "story":
        k = int(spec.get("story_frames", 3))
        per = -(-len(blocks) // k)
        pages = []
        for f in range(k):
            chunk = blocks[f * per:(f + 1) * per]
            if not chunk: break
            sp = dict(spec); sp["subtitle"] = spec.get("subtitle") if f == 0 else None
            body = (progress(f, k) + header(sp) +
                    f'<div class="fit grow"><div class="in"><div class="grid" style="--cols:1">{_blocks(chunk, f * per)}</div></div></div>')
            pages.append({"html": page(fmt, body, CSS2)})
        return pages
    cols = spec.get("columns")
    if isinstance(cols, dict):
        cols = cols.get(fmt)
    cols = cols or (3 if fmt == "x" or len(blocks) >= 9 else 2)
    body = header(spec) + f'<div class="fit grow"><div class="in"><div class="grid" style="--cols:{cols}">{_blocks(blocks)}</div></div></div>'
    return [{"html": page(fmt, body, CSS2)}]


# ======================================================== 3. build-up (animated)
CSS3 = """
.f-feed .fit,.f-story .fit{margin-top:56px}.f-x .fit{margin-top:28px}
.path{position:relative;display:flex;flex-direction:column;gap:var(--gap)}
.step{display:flex;align-items:center;gap:34px;position:relative}
.step .num{flex:0 0 auto;width:var(--d);height:var(--d);border-radius:50%;background:var(--paper);border:5px solid var(--accent);color:var(--accent);font-weight:700;font-size:calc(var(--d)*.42);display:flex;align-items:center;justify-content:center;direction:ltr;position:relative;z-index:1}
.step.last .num{background:var(--accent);color:#fff}
.step .txt{font-size:var(--fs);font-weight:600;line-height:1.2}
.step .txt small{display:block;font-size:calc(var(--fs)*.62);font-weight:400;color:var(--soft);margin-top:6px}
.step:not(:last-child)::after{content:"";position:absolute;right:calc(var(--d)/2 - 3px);top:var(--d);height:var(--gap);width:6px;background:var(--rule)}
.step.lit:not(:last-child)::after{background:var(--accent)}
.step[data-hidden]{opacity:.14}
.f-feed{--d:112px;--fs:54px;--gap:70px}
.f-feed h1.t{font-size:84px}.f-story h1.t{font-size:86px}.f-x h1.t{font-size:66px}.f-story{--d:120px;--fs:58px;--gap:80px}.f-x{--d:84px;--fs:44px;--gap:34px}
.gridb{display:grid;grid-template-columns:repeat(var(--cols),1fr);grid-auto-flow:var(--flow);grid-template-rows:repeat(var(--rows),auto);gap:24px}
.gb{background:#FBF9F5;border:2px solid var(--rule);border-radius:22px;padding:30px;font-size:40px;font-weight:600;display:flex;gap:18px;align-items:center}
.gb .num{width:60px;height:60px;border-radius:50%;background:var(--accent);color:#fff;font-size:30px;display:flex;align-items:center;justify-content:center;flex:0 0 auto;direction:ltr}
.gb[data-hidden]{opacity:0}
.closing{margin-top:36px;border-right:10px solid var(--accent);background:#fff;border-radius:16px;padding:28px 34px;font-size:40px;font-weight:600;line-height:1.3}
.f-x .closing{font-size:32px;padding:18px 26px}
.closing[data-hidden]{opacity:0}
"""


def r3(spec, fmt):
    need(spec, "title", "steps")
    steps = [_s(x) for x in spec["steps"]]
    n = len(steps)
    layout = spec.get("layout", "path")
    pages = []
    total = n + (1 if spec.get("closing") else 0)
    for k in range(total + 1):
        vis = min(k, n)
        if layout == "path":
            inner = '<div class="path">'
            for i, st in enumerate(steps):
                cls = "step" + (" last" if i == n - 1 else "") + (" lit" if i + 1 < vis else "")
                hid = "" if i < vis else " data-hidden"
                inner += (f'<div class="{cls}"{hid}><div class="num">{i + 1}</div><div class="txt">{mk(st["t"])}'
                          + (f"<small>{mk(st['s'])}</small>" if st.get("s") else "") + "</div></div>")
            inner += "</div>"
        else:
            cols = min(n, 4) if fmt == "x" else (1 if fmt == "story" else 2)
            rows = -(-n // cols)
            flow = "column" if (fmt == "feed" and cols == 2) else "row"   # right column first on feed
            inner = f'<div class="gridb" style="--cols:{cols};--rows:{rows};--flow:{flow}">'
            for i, st in enumerate(steps):
                hid = "" if i < vis else " data-hidden"
                inner += f'<div class="gb"{hid}><div class="num">{i + 1}</div><div>{mk(st["t"])}</div></div>'
            inner += "</div>"
        body = header(spec) + f'<div class="fit grow"><div class="in">{inner}</div></div>'
        if spec.get("closing"):
            hid = "" if k > n else " data-hidden"
            body += f'<div class="closing"{hid}>{mk(spec["closing"])}</div>'
        dur = 3.0 if k == total else 1.0
        pages.append({"html": page(fmt, body, CSS3), "duration": dur})
    return _open_full(spec, pages)


# ======================================================== 4. workflow canvas
CSS4 = """
.f-feed .fit,.f-story .fit{margin-top:40px}.f-x .fit{margin-top:26px}
.flow{display:flex;flex-direction:column;align-items:center}
.f-x .flow{flex-direction:row;align-items:center;justify-content:center}
.wn{background:#fff;border:2px solid #D9D1C4;border-radius:22px;box-shadow:0 6px 0 #1C191610;display:flex;align-items:center;gap:22px;padding:22px 28px;width:720px;font-size:38px;font-weight:600;line-height:1.2}
.wn .ic{flex:0 0 auto;width:46px;height:46px;border-radius:12px;border:2px solid #D9D1C4;background:var(--paper)}
.wn small{display:block;font-size:24px;font-weight:400;color:var(--soft);margin-top:4px}
.wn .tag{font-size:20px;color:var(--soft);border:1px solid var(--rule);border-radius:8px;padding:2px 8px;margin-top:6px;display:inline-block}
.wn.trig{border:3px solid var(--accent)}.wn.trig .ic{background:var(--accent);border-color:var(--accent)}
.wn.out{background:var(--ink);color:var(--paper);border-color:var(--ink)}.wn.out .ic{background:#3A342E;border-color:#3A342E}
.arr{width:4px;height:46px;background:#BDB4A6;position:relative;flex:0 0 auto}
.arr::after{content:"";position:absolute;bottom:-4px;left:50%;transform:translateX(-50%);border:12px solid transparent;border-top:16px solid #BDB4A6;border-bottom:0}
.grp{border:3px dashed #C9BFB0;border-radius:28px;padding:56px 36px 30px;position:relative;display:flex;flex-direction:column;align-items:center;background:#F3EFE7cc}
.grp .lab{position:absolute;top:-24px;right:36px;background:var(--accent);color:#fff;font-size:28px;font-weight:600;padding:6px 20px;border-radius:12px}
.grp .wn{width:600px;padding:18px 26px;font-size:36px}
.grp .arr{height:30px}
.f-story .wn{width:620px;font-size:42px;padding:26px 32px}.f-story .grp .wn{width:500px;font-size:40px}
.f-story .arr{height:58px}.f-story .grp .arr{height:38px}
/* X: right to left */
.f-x .wn{width:300px;flex-direction:column;align-items:flex-start;gap:14px;padding:22px 22px;font-size:32px}
.f-x .grp{flex-direction:row;padding:50px 26px 26px}
.f-x .grp .wn{width:170px;font-size:30px;padding:18px}
.f-x .arr{width:50px;height:4px}
.f-x .grp .arr{width:30px}
.f-x .arr::after{bottom:auto;top:50%;left:-4px;transform:translateY(-50%);border:11px solid transparent;border-right:16px solid #BDB4A6;border-left:0}
"""


def _wn(node, cls=""):
    nd = _s(node)
    extra = (f"<small>{mk(nd['s'])}</small>" if nd.get("s") else "") + (f'<span class="tag ltr">{nd["tag"]}</span>' if nd.get("tag") else "")
    return f'<div class="wn {cls}"><span class="ic"></span><div>{mk(nd["t"])}{extra}</div></div>'


def r4(spec, fmt):
    need(spec, "title", "trigger", "output")
    grp = spec.get("group") or {"nodes": spec.get("steps", [])}
    arr = '<div class="arr"></div>'
    mid = arr.join(_wn(x) for x in grp["nodes"])
    g = (f'<div class="grp">' + (f'<div class="lab">{mk(grp["label"])}</div>' if grp.get("label") else "") + mid + "</div>")
    flow = f'<div class="flow">{_wn(spec["trigger"], "trig")}{arr}{g}{arr}{_wn(spec["output"], "out")}</div>'
    body = header(spec) + f'<div class="fit grow"><div class="in">{flow}</div></div>'
    return [{"html": page(fmt, body, CSS4, body_cls="dots")}]


# ======================================================== 5. before / after
CSS5 = """
.f-feed .fit,.f-x .fit{margin-top:44px}.f-story .fit{margin-top:36px}
.ba{display:grid;grid-template-columns:1fr 1fr;column-gap:28px;position:relative}
.ba .bg{grid-row:1/-1;border-radius:28px;z-index:0}
.ba .bg.a{grid-column:1;background:var(--panel)}.ba .bg.b{grid-column:2;background:var(--ink)}
.ba .c{position:relative;z-index:1;padding:0 40px}
.ba .c.b{color:var(--paper)}
.ba .h{padding-top:40px;padding-bottom:26px}
.lab{font-size:24px;color:var(--soft);margin-bottom:12px}.b .lab{color:var(--dsoft)}
.ttl{font-size:40px;font-weight:700;line-height:1.2}
.row{font-size:32px;line-height:1.35;padding:22px 40px;border-top:2px solid #1C191612}
.row.b{border-top-color:#ffffff22;color:var(--paper)}
.row.end{padding-bottom:40px}
.row.hl{color:#E8A27F}
.f-x .ttl{font-size:38px}.f-x .row{font-size:30px;padding:16px 40px}.f-x .ba .h{padding-top:30px;padding-bottom:18px}.f-x .row.end{padding-bottom:30px}
.stk{display:flex;flex-direction:column;gap:26px}
.pan{border-radius:28px;padding:34px 40px}.pan.a{background:var(--panel)}.pan.b{background:var(--ink);color:var(--paper)}
.pan .ttl{font-size:44px;margin-bottom:12px}.pan .row{padding:16px 0;font-size:36px}.pan.b .row{border-top-color:#ffffff22}
"""


def r5(spec, fmt):
    need(spec, "title", "before", "after")
    a, b = spec["before"], spec["after"]
    def head(side, c):
        return (f'<div class="lab">{mk(side["label"])}</div>' if side.get("label") else "") + f'<div class="ttl">{mk(side["title"])}</div>'
    def rowcls(side, i, n):
        return " hl" if side.get("highlight") == i else ""
    if fmt == "story":
        def pan(side, c):
            rows = "".join(f'<div class="row{rowcls(side, i, 0)}">{mk(r)}</div>' for i, r in enumerate(side["rows"]))
            return f'<div class="pan {c}">{head(side, c)}{rows}</div>'
        inner = f'<div class="stk">{pan(a, "a")}{pan(b, "b")}</div>'
    else:
        n = max(len(a["rows"]), len(b["rows"]))
        cells = '<div class="bg a"></div><div class="bg b"></div>'
        cells += f'<div class="c a h" style="grid-column:1;grid-row:1">{head(a, "a")}</div><div class="c b h" style="grid-column:2;grid-row:1">{head(b, "b")}</div>'
        for i in range(n):
            for col, side, c in ((1, a, "a"), (2, b, "b")):
                txt = side["rows"][i] if i < len(side["rows"]) else ""
                end = " end" if i == n - 1 else ""
                cells += f'<div class="row {c}{end}{rowcls(side, i, n)}" style="grid-column:{col};grid-row:{i + 2};position:relative;z-index:1">{mk(txt)}</div>'
        inner = f'<div class="ba" style="grid-template-rows:repeat({n + 1},auto)">{cells}</div>'
    body = header(spec) + f'<div class="fit grow"><div class="in">{inner}</div></div>'
    return [{"html": page(fmt, body, CSS5)}]


# ======================================================== 7. comparison table
CSS7 = """
.f-feed .fit,.f-x .fit,.f-story .fit{margin-top:44px}
table{width:100%;border-collapse:separate;border-spacing:0;font-size:32px;line-height:1.3}
th{font-size:26px;font-weight:600;color:var(--soft);text-align:right;padding:0 26px 18px;border-bottom:3px solid var(--ink)}
td{padding:26px 26px;text-align:right;vertical-align:middle}
td.rl{font-weight:700}
tbody tr:nth-child(even) td{background:var(--zebra)}
tr.hl td{background:var(--accent)!important;color:#fff}
tr.hl td:first-child{border-radius:0 18px 18px 0}tr.hl td:last-child{border-radius:18px 0 0 18px}
td.hc{background:#B4451A14;font-weight:600}th.hc{color:var(--accent)}
.note{margin-top:28px;font-size:26px;color:var(--soft)}
.f-x table{font-size:31px}.f-x td{padding:22px 28px}.f-x th{font-size:26px}
.f-story table{font-size:34px}.f-story td{padding:28px 20px}
"""


def r7(spec, fmt):
    need(spec, "title", "columns", "rows")
    hr, hc = spec.get("highlight_row"), spec.get("highlight_col")
    cols = spec["columns"]
    th = "".join(f'<th class="{"hc" if j == hc else ""}">{mk(c)}</th>' for j, c in enumerate(cols))
    trs = ""
    for i, r in enumerate(spec["rows"]):
        cells = [r["label"], *r["cells"]]
        tds = "".join(f'<td class="{"rl " if j == 0 else ""}{"hc" if j == hc else ""}">{mk(c)}</td>' for j, c in enumerate(cells))
        trs += f'<tr class="{"hl" if i == hr else ""}">{tds}</tr>'
    note = f'<div class="note">{mk(spec["note"])}</div>' if spec.get("note") else ""
    body = header(spec) + f'<div class="fit grow"><div class="in"><table><thead><tr>{th}</tr></thead><tbody>{trs}</tbody></table>{note}</div></div>'
    return [{"html": page(fmt, body, CSS7)}]


# ======================================================== 8. team evolution
CSS8 = """
.f-feed .fit,.f-x .fit{margin-top:40px}.f-story .fit{margin-top:30px}
.stages{display:flex;align-items:stretch;gap:0}
.stg{flex:1 1 0;min-width:0;display:flex;flex-direction:column;align-items:center;background:#FBF9F5;border:2px solid var(--rule);border-radius:26px;padding:28px 14px 34px}
.sep{flex:0 0 40px;display:flex;align-items:center;justify-content:center}
.sep svg{width:30px;height:30px}
.sn{width:58px;height:58px;border-radius:50%;background:var(--ink);color:var(--paper);font-weight:700;font-size:30px;display:flex;align-items:center;justify-content:center;direction:ltr;margin-bottom:10px}
.sl{font-size:26px;color:var(--soft);margin-bottom:6px;text-align:center}
.tree{display:flex;flex-direction:column;align-items:center;margin-top:18px;width:100%}
.ob{background:#fff;border:3px solid var(--ink);border-radius:18px;padding:16px 10px;overflow:hidden;font-size:28px;font-weight:600;line-height:1.25;text-align:center;width:100%;max-width:250px}
.ob.acc{border-color:var(--accent);background:var(--accent);color:#fff}
.ob.ghost{border-style:dashed;color:var(--soft);background:transparent}
.kids{display:flex;justify-content:center;gap:12px;position:relative;padding-top:36px;width:100%}
.kids::before{content:"";position:absolute;top:0;left:50%;width:3px;height:36px;background:var(--ink);transform:translateX(-50%)}
.kid{display:flex;flex-direction:column;align-items:center;flex:1;min-width:0}
.f-story .stg{padding:56px 40px 60px}.f-story .ob{font-size:46px;max-width:620px;padding:30px 24px}.f-story .sn{width:84px;height:84px;font-size:42px}
.f-story .kids{padding-top:64px}.f-story .kids::before{height:64px;width:4px}
.f-x .ob{max-width:340px;font-size:30px}
/* rows layout (feed default): stages stacked top to bottom, reporting line runs right to left */
.rows{display:flex;flex-direction:column;gap:0}
.rows .stg{flex-direction:row;align-items:center;padding:60px 30px;gap:30px}
.rows .sn{margin:0;flex:0 0 auto}
.rows .sepv{height:76px;align-items:center;display:flex;justify-content:center}
.rows .sepv svg{width:30px;height:30px;transform:rotate(-90deg)}
.rows .tree{flex-direction:row;margin:0;width:auto;align-items:center}
.rows .ob{width:auto;max-width:none;white-space:nowrap;font-size:30px;padding:26px 22px}
.rows .kids{flex-direction:column;padding:0 0 0 0;padding-right:44px;width:auto}
.rows .kids::before{top:50%;right:0;left:auto;width:44px;height:3px;transform:translateY(-50%)}
.rows .kid{flex-direction:row;align-items:center}
"""
ARROW = '<svg viewBox="0 0 30 30"><path d="M26 15H5M13 6l-9 9 9 9" fill="none" stroke="#B4451A" stroke-width="4" stroke-linecap="round" stroke-linejoin="round"/></svg>'


def _tree(nodes):
    by = {n["id"]: n for n in nodes}
    kids = {}
    for nd in nodes:
        kids.setdefault(nd.get("parent"), []).append(nd)
    def rec(nd):
        cls = "ob" + (" acc" if nd.get("accent") else "") + (" ghost" if nd.get("ghost") else "")
        h = f'<div class="{cls}">{mk(nd["t"])}</div>'
        ch = kids.get(nd["id"], [])
        if ch:
            h += '<div class="kids">' + "".join(f'<div class="kid">{rec(c)}</div>' for c in ch) + "</div>"
        return h
    roots = kids.get(None, [])
    return '<div class="tree">' + "".join(rec(r) for r in roots) + "</div>"


def _stage(i, st):
    lab = f'<div class="sl">{mk(st["label"])}</div>' if st.get("label") else ""
    return f'<div class="stg"><div class="sn">{i + 1}</div>{lab}{_tree(st["nodes"])}</div>'


def r8(spec, fmt):
    need(spec, "title", "stages")
    stages = spec["stages"]
    if fmt == "story":
        pages = []
        for i, st in enumerate(stages):
            body = progress(i, len(stages)) + header(spec) + f'<div class="fit grow"><div class="in">{_stage(i, st)}</div></div>'
            pages.append({"html": page(fmt, body, CSS8)})
        return pages
    if spec.get("layout", "rows" if fmt == "feed" else "columns") == "rows":
        sep = f'<div class="sepv">{ARROW}</div>'
        inner = '<div class="rows">' + sep.join(_stage(i, st) for i, st in enumerate(stages)) + "</div>"
    else:
        sep = f'<div class="sep">{ARROW}</div>'
        inner = '<div class="stages">' + sep.join(_stage(i, st) for i, st in enumerate(stages)) + "</div>"
    body = header(spec) + f'<div class="fit grow"><div class="in">{inner}</div></div>'
    return [{"html": page(fmt, body, CSS8)}]


# ======================================================== 9. quote card
CSS9 = """
.f-feed .stage,.f-story .stage{justify-content:center}
.f-x .stage{justify-content:center}
.tag{font-size:28px;color:var(--soft);margin-bottom:34px}
.card{background:#fff;border-radius:32px;padding:56px 56px 50px;box-shadow:0 2px 0 var(--rule),0 30px 60px #1C191612}
.who{display:flex;align-items:center;gap:22px;margin-bottom:40px}
.av{width:96px;height:96px;border-radius:50%;background:var(--ink);color:var(--paper);display:flex;align-items:center;justify-content:center;font-size:36px;font-weight:700}
.nm{font-size:34px;font-weight:700}.hdl{font-size:26px;color:var(--soft)}
.q{font-size:var(--qs,62px);font-weight:600;line-height:1.3;text-wrap:balance}
.meta{margin-top:44px;font-size:24px;color:var(--soft);border-top:2px solid #EEE8DE;padding-top:24px}
.f-feed .q{font-size:var(--qs,72px)}
.f-x .card{padding:56px 72px 60px}.f-x .q{font-size:var(--qs,76px)}
.f-story .q{font-size:var(--qs,78px)}
"""


def r9(spec, fmt):
    need(spec, "quote")
    who = (f'<div class="who"><div class="av"><span class="ltr">{spec.get("initials", BRAND.initials)}</span></div><div>'
           f'<div class="nm">{mk(spec.get("person", BRAND.owner_name))}</div><div class="hdl">{mk(spec.get("headline", BRAND.headline))}</div></div></div>')
    tag = f'<div class="tag">{mk(spec["tag"])}</div>' if spec.get("tag") else ""
    meta = f'<div class="meta">{mk(spec["meta"])}</div>' if spec.get("meta") else ""
    qs = f' style="--qs:{spec["quote_size"]}px"' if spec.get("quote_size") else ""
    body = f'{tag}<div class="fit" style="flex:0 1 auto"><div class="in"><div class="card">{who}<div class="q"{qs}>{mk(spec["quote"])}</div>{meta}</div></div></div>'
    return [{"html": page(fmt, body, CSS9)}]


# ======================================================== 10. meme (typographic scene)
CSS10 = """
.scene{position:relative;flex:1;min-height:0}
.desk{position:absolute;left:0;right:0;height:6px;background:var(--ink);border-radius:3px}
.pile{position:absolute;display:flex;flex-direction:column;align-items:center}
.sheets{position:relative}
.sheet{position:absolute;left:0;right:0;height:var(--sh);background:#fff;border:2px solid #CFC6B8;border-radius:4px}
.plab{position:absolute;text-align:center;font-weight:700;line-height:1.2}
.plab.big{color:var(--ink)}.plab.small{color:var(--accent)}
.fig{position:absolute;display:flex;flex-direction:column;align-items:center}
.head{border-radius:50%;background:var(--paper);border:5px solid var(--ink);position:relative}
.eye{position:absolute;background:#fff;border:3px solid var(--ink);border-radius:50%}
.pupil{position:absolute;background:var(--ink);border-radius:50%}
.torso{background:var(--ink);border-radius:60px 60px 18px 18px;margin-top:10px}
.flab{font-weight:600;color:var(--soft);margin-top:14px}
.scene svg{position:absolute;overflow:visible;z-index:0}
.fig,.sheets,.plab{z-index:1}
.sight{stroke:var(--accent);stroke-width:5;stroke-dasharray:2 14;stroke-linecap:round;fill:none}
.cap{font-size:34px;color:var(--soft);text-align:center;margin-top:20px}
"""
GEO10 = {
    "x": dict(W=1440, H=740, desk=600, big=(1010, 340, 440), small=(150, 320, 64), fig=(640, 280), head=150, lab=40, flab=34),
    "feed": dict(W=910, H=1000, desk=780, big=(560, 330, 540), small=(30, 300, 64), fig=(330, 400), head=130, lab=38, flab=32),
    "story": dict(W=910, H=1180, desk=900, big=(560, 330, 600), small=(30, 300, 70), fig=(330, 470), head=140, lab=40, flab=34),
}


def r10(spec, fmt):
    need(spec, "big", "small")
    g = GEO10[fmt]
    sh = 12
    tops = {}
    def pile(x, w, hpx, label, cls, nsheets):
        step = min((hpx - sh) / max(nsheets - 1, 1), sh + 3)
        hpx = round(step * (nsheets - 1) + sh)
        tops[cls] = hpx
        sheets = "".join(f'<div class="sheet" style="bottom:{round(i * step)}px;transform:translateX({(-1) ** i * (i % 3)}px)"></div>' for i in range(nsheets))
        top = g["desk"] - hpx
        return (f'<div class="sheets" style="position:absolute;left:{x}px;top:{top}px;width:{w}px;height:{hpx}px;--sh:{sh}px">{sheets}</div>'
                f'<div class="plab {cls}" style="left:{x - 40}px;width:{w + 80}px;top:{g["desk"] + 22}px;font-size:{g["lab"]}px">{mk(label)}</div>')
    big, small = _s(spec["big"]), _s(spec["small"])
    bx, bw, bh = g["big"]; sx, sw, shh = g["small"]
    scene = f'<div class="desk" style="top:{g["desk"]}px"></div>'
    scene += pile(bx, bw, bh, big["t"], "big", int(big.get("sheets", 30)))
    scene += pile(sx, sw, shh, small["t"], "small", int(small.get("sheets", 3)))
    fx, fy = g["fig"]; hd = g["head"]
    ew = hd * 0.3
    eyes = ""
    for ex in (hd * 0.18, hd * 0.52):
        eyes += (f'<div class="eye" style="left:{ex}px;top:{hd * 0.3}px;width:{ew}px;height:{ew}px">'
                 f'<div class="pupil" style="left:{ew * 0.02}px;top:{ew * 0.38}px;width:{ew * 0.48}px;height:{ew * 0.48}px"></div></div>')
    viewer = spec.get("viewer")
    fig = (f'<div class="fig" style="left:{fx}px;top:{fy}px;width:{hd * 1.6}px"><div class="head" style="width:{hd}px;height:{hd}px">{eyes}</div>'
           f'<div class="torso" style="width:{hd * 1.25}px;height:{g["desk"] - fy - hd - 10}px"></div></div>')
    scene += fig
    if viewer:
        scene += (f'<div class="plab" style="left:{fx - 40}px;width:{hd * 1.6 + 80}px;top:{g["desk"] + 22}px;font-size:{g["flab"]}px;color:var(--soft);font-weight:600">{mk(viewer)}</div>')
    # sight line: from the eyes to the top of the small pile
    x1, y1 = fx + hd * 0.3 + 6, fy + hd * 0.42
    x2, y2 = sx + sw / 2, g["desk"] - tops["small"] - 24
    scene += f'<svg width="{g["W"]}" height="{g["H"]}" style="left:0;top:0"><path class="sight" d="M{x1:.0f} {y1:.0f} Q {(x1 + x2) / 2:.0f} {min(y1, y2) - 90:.0f} {x2:.0f} {y2:.0f}"/></svg>'
    cap = f'<div class="cap">{mk(spec["caption"])}</div>' if spec.get("caption") else ""
    body = header(spec) + f'<div class="scene" style="width:{g["W"]}px;flex:0 0 {g["H"]}px;margin:auto 0">{scene}</div>{cap}'
    return [{"html": page(fmt, body, CSS10)}]


# ======================================================== 12. scorecard / checklist
CSS12 = """
.f-feed .fit,.f-x .fit{margin-top:44px}
.sheet{background:#fff;border-radius:26px;box-shadow:0 2px 0 var(--rule),0 24px 50px #1C191610;padding:20px 44px}
.qrow{display:flex;align-items:center;gap:26px;padding:34px 0;border-bottom:2px solid #EEE8DE}
.qrow:last-child{border-bottom:0}
.qn{flex:0 0 auto;width:52px;height:52px;border-radius:50%;border:3px solid var(--accent);color:var(--accent);font-weight:700;font-size:28px;display:flex;align-items:center;justify-content:center;direction:ltr}
.qt{flex:1;font-size:38px;font-weight:600;line-height:1.3}
.opts{flex:0 0 auto;display:flex;gap:22px;margin-right:auto}
.opt{display:flex;flex-direction:column;align-items:center;gap:8px;font-size:24px;color:var(--soft);min-width:70px}
.box{width:54px;height:54px;border:3px solid var(--ink);border-radius:8px;background:#fff}
.f-x .qrow{padding:22px 0}.f-x .qt{font-size:34px}
.one .qt{font-size:64px;line-height:1.25}
.one{display:flex;flex-direction:column;gap:70px;background:#fff;border-radius:30px;padding:60px 54px;box-shadow:0 2px 0 var(--rule),0 24px 50px #1C191610}
.one .qn{width:80px;height:80px;font-size:40px}
.one .opts{margin:0;gap:60px;justify-content:flex-start}
.one .opt{font-size:34px;gap:14px}.one .box{width:96px;height:96px;border-radius:14px}
.f-story .hd h1.t{font-size:52px}.f-story .fit{margin-top:40px}
"""


def _opts(opts):
    return '<div class="opts">' + "".join(f'<div class="opt"><div class="box"></div><span>{mk(o)}</span></div>' for o in opts) + "</div>"


def r12(spec, fmt):
    need(spec, "title", "rows")
    rows = [r if isinstance(r, dict) else {"q": r} for r in spec["rows"]]
    default = spec.get("options", ["כן", "לא"])
    if fmt == "story" and spec.get("story_mode", "per_question") == "per_question":
        pages = []
        for i, r in enumerate(rows):
            card = f'<div class="one"><div class="qn">{i + 1}</div><div class="qt">{mk(r["q"])}</div>{_opts(r.get("options", default))}</div>'
            body = progress(i, len(rows)) + header(spec) + f'<div class="fit grow"><div class="in">{card}</div></div>'
            pages.append({"html": page(fmt, body, CSS12)})
        return pages
    qs = "".join(f'<div class="qrow"><div class="qn">{i + 1}</div><div class="qt">{mk(r["q"])}</div>{_opts(r.get("options", default))}</div>'
                 for i, r in enumerate(rows))
    body = header(spec) + f'<div class="fit grow"><div class="in"><div class="sheet">{qs}</div></div></div>'
    return [{"html": page(fmt, body, CSS12)}]


ALL = ["feed", "story", "x"]
import templates_more as M  # noqa: E402


def _r1(spec, fmt):
    return r1(spec, fmt) if spec.get("motion") == "steps" else M.r1_smooth(spec, fmt)


def _r2(spec, fmt):
    return r2(spec, fmt) if spec.get("layout") == "blocks" else M.r2_rooms(spec, fmt)


def _r3(spec, fmt):
    return r3(spec, fmt) if spec.get("motion") == "steps" else M.r3_smooth(spec, fmt)


def _r8(spec, fmt):
    return r8(spec, fmt) if spec.get("style") == "classic" else M.r8_org(spec, fmt)


def _r10(spec, fmt):
    return M.r17(spec, fmt) if spec.get("variant") == "pov" else r10(spec, fmt)


REGISTRY = {
    1: {"name": "animated-stack-map", "render": _r1, "formats": ALL, "animated": True, "mp4_skip": 1},
    2: {"name": "cheat-sheet-rooms", "render": _r2, "formats": ALL},
    3: {"name": "build-up", "render": _r3, "formats": ALL, "animated": True, "mp4_skip": 1},
    4: {"name": "workflow-canvas", "render": r4, "formats": ALL},
    5: {"name": "before-after", "render": r5, "formats": ALL},
    7: {"name": "comparison-table", "render": r7, "formats": ALL},
    8: {"name": "team-evolution-org", "render": _r8, "formats": ALL},
    9: {"name": "quote-card", "render": r9, "formats": ALL},
    10: {"name": "meme", "render": _r10, "formats": ALL},
    12: {"name": "scorecard", "render": r12, "formats": ALL},
    15: {"name": "metaphor-scene", "render": M.r15, "formats": ALL, "animated": True},
    16: {"name": "role-org-chart", "render": M.r16, "formats": ALL, "animated": True},
    17: {"name": "pov-collage", "render": M.r17, "formats": ALL},
    18: {"name": "weekly-changelog", "render": M.r18, "formats": ALL + ["carousel"], "animated": "optional"},
    19: {"name": "cover-cta", "render": M.r19, "formats": ALL},
}


def validate(tid, spec):
    if tid in NOT_BUILT:
        raise SystemExit(f"template {tid}: {NOT_BUILT[tid]}")
