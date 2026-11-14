"""Upgrade 2026-11-13 (inspiration library, R-08): smooth motion for 1 and 3, rooms grid (2),
org chart with KPI pills (8), POV collage (10 variant / 17), metaphor scene (15),
role org chart with KPIs (16), weekly changelog card (18), cover / CTA card (19).
Timeline pages: one HTML per format whose CSS animations loop over `duration`; tk_shot seeks
every animation to t and captures, so motion is smooth (10-15 fps) and the loop starts on the
complete frame (frame 1 = thumbnail)."""
from __future__ import annotations

import json

from tk import mk, page, progress
from icons import icon


def _s(x):
    return x if isinstance(x, dict) else {"t": x}


def need(spec, *keys):
    miss = [k for k in keys if not spec.get(k)]
    if miss:
        raise SystemExit(f"template {spec.get('template')}: spec is missing {miss}")


def header(spec, title_key="title", sub=True, cls="hd"):
    h = f'<h1 class="t">{mk(spec[title_key])}</h1>' if spec.get(title_key) else ""
    if sub and spec.get("subtitle"):
        h += f'<div class="sub">{mk(spec["subtitle"])}</div>'
    return f'<div class="{cls}">{h}</div>' if h else ""


def kf(name, D, points):
    """points [(t_seconds, css)] -> @keyframes over a loop of D seconds (0% and 100% added)."""
    pts = sorted(points, key=lambda p: p[0])
    if pts[0][0] > 0:
        pts = [(0, pts[0][1])] + pts
    if pts[-1][0] < D:
        pts = pts + [(D, pts[-1][1])]
    body = "".join(f"{min(100.0, max(0.0, t / D * 100)):.3f}%{{{css}}}" for t, css in pts)
    return f"@keyframes {name}{{{body}}}"


def anim(name, D, delay=0.0, ease="linear"):
    return f"animation:{name} {D}s {ease} {-delay if delay else 0}s infinite both;"


class Gate:
    """Reveal timing shared by the animated templates: full frame, fade to ghost, reveal one by one, hold."""
    def __init__(self, D, hold=1.4, fade=0.45, gap=0.5):
        self.D, self.hold, self.fade = D, hold, fade
        self.r0 = hold + fade + gap

    def item(self, name, t_on, ghost="opacity:.18;transform:scale(.97)", on="opacity:1;transform:scale(1)", pop=True):
        D, h, f = self.D, self.hold, self.fade
        pts = [(0, on), (h, on), (h + f, ghost), (t_on, ghost)]
        if pop:
            pts += [(t_on + .22, on.replace("scale(1)", "scale(1.045)")), (t_on + .45, on)]
        else:
            pts += [(t_on + .4, on)]
        return kf(name, D, pts)

    def gate(self, name, t_on, off="opacity:0", on="opacity:1"):
        D, h, f = self.D, self.hold, self.fade
        return kf(name, D, [(0, on), (h, on), (h + f * .6, off), (t_on, off), (t_on + .35, on)])


def tl(D, fps, check=0.5):
    return {"duration": D, "fps": fps, "check_at": check}


# ======================================================== 1. stack map, smooth (default)
CSS1S = """
.hdbox{position:absolute;top:0;right:0;left:0}
.cv{position:absolute;right:0;left:0}
.cv svg{position:absolute;inset:0;z-index:0;overflow:visible}
.cv line{stroke:var(--rule);stroke-width:5;stroke-dasharray:10 10}
.cv line.on{stroke:var(--accent)}
.hub{position:absolute;z-index:2;border-radius:28px;background:var(--ink);color:var(--paper);display:flex;flex-direction:column;align-items:center;justify-content:center;text-align:center;padding:0 24px}
.hub .a{font-size:40px;font-weight:700;line-height:1.2}.hub .b{font-size:28px;color:var(--dsoft);margin-top:8px}
.ring{position:absolute;z-index:1;border-radius:34px;border:4px solid var(--accent)}
.node{position:absolute;z-index:2;border-radius:22px;background:#fff;border:3px solid var(--accent);box-shadow:0 8px 0 #B4451A22;display:flex;flex-direction:column;align-items:center;justify-content:center;text-align:center;font-size:36px;font-weight:600;line-height:1.15;padding:0 14px}
.node small{font-size:22px;font-weight:400;color:var(--soft);margin-top:6px}
.node.fin{background:var(--accent);color:#fff}.node.fin small{color:var(--paper)}
.dot{position:absolute;z-index:1;width:16px;height:16px;margin:-8px 0 0 -8px;border-radius:50%;background:var(--accent);box-shadow:0 0 0 5px #B4451A26}
.close{position:absolute;right:0;left:0;text-align:center;font-size:32px;color:var(--soft);line-height:1.3}
.f-x .hub .a{font-size:36px}.f-x .node{font-size:32px}
"""


def r1_smooth(spec, fmt):
    from templates import GEO1, _stack_geo
    need(spec, "title", "hub", "nodes")
    nodes = [_s(x) for x in spec["nodes"]]
    n = len(nodes)
    if not 3 <= n <= 7:
        raise SystemExit("template 1: 3 to 7 nodes")
    D, fps = float(spec.get("loop", 10)), float(spec.get("fps", 12.5))
    G = Gate(D, hold=float(spec.get("open_hold", 1.4)))
    step = float(spec.get("step", .55))
    t_on = [G.r0 + i * step for i in range(n)]
    t_close = t_on[-1] + .55
    P = D / 4                                         # ambient period, divides the loop
    g = GEO1[fmt]
    rects, (hx, hy) = _stack_geo(n, g)
    hub = _s(spec["hub"])
    hcx, hcy = hx + g["hw"] / 2, hy + g["hh"] / 2
    css = [CSS1S]
    css.append(kf("pulse", P, [(0, "transform:scale(1);opacity:.5"), (P * .7, "transform:scale(1.13);opacity:0"), (P, "transform:scale(1.13);opacity:0")]))
    css.append(kf("travel", P, [(0, "transform:translate(0,0);opacity:0"), (P * .12, "opacity:1"), (P * .8, "opacity:1"),
                                (P * .92, "transform:translate(var(--dx),var(--dy));opacity:0"), (P, "transform:translate(var(--dx),var(--dy));opacity:0")]))
    body = (f'<div class="hdbox fit" data-id="title" style="height:{g["hd"]}px;justify-content:flex-start">'
            f'<div class="in">{header(spec)}</div></div>')
    body += f'<div class="cv" style="top:{g["top"]}px;height:{g["h"]}px"><svg width="{g["W"]}" height="{g["h"]}">'
    for i, (x, y) in enumerate(rects):
        css.append(G.gate(f"ln{i}", t_on[i] - .1, off="opacity:0", on="opacity:1"))
        x1, y1 = x + g["nw"] / 2, y + g["nh"] / 2
        body += f'<line x1="{x1}" y1="{y1}" x2="{hcx}" y2="{hcy}"/>'
        body += f'<line class="on" style="{anim(f"ln{i}", D)}" x1="{x1}" y1="{y1}" x2="{hcx}" y2="{hcy}"/>'
    body += "</svg>"
    for i, (x, y) in enumerate(rects):      # dots: node -> hub, gated with their node
        x1, y1 = x + g["nw"] / 2, y + g["nh"] / 2
        css.append(G.gate(f"dg{i}", t_on[i] + .5))
        body += (f'<div style="position:absolute;inset:0;{anim(f"dg{i}", D)}"><div class="dot" style="left:{x1}px;top:{y1}px;'
                 f'--dx:{hcx - x1:.0f}px;--dy:{hcy - y1:.0f}px;{anim("travel", P, delay=(i * P / n) % P)}"></div></div>')
    body += (f'<div class="ring" style="left:{hx - 6}px;top:{hy - 6}px;width:{g["hw"] + 12}px;height:{g["hh"] + 12}px;{anim("pulse", P)}"></div>'
             f'<div class="hub" style="left:{hx}px;top:{hy}px;width:{g["hw"]}px;height:{g["hh"]}px">'
             f'<div class="a">{mk(hub["t"])}</div>' + (f'<div class="b">{mk(hub["s"])}</div>' if hub.get("s") else "") + "</div>")
    for i, ((x, y), nd) in enumerate(zip(rects, nodes)):
        css.append(G.item(f"nd{i}", t_on[i]))
        fin = " fin" if (n % 2 == 1 and i == n - 1) else ""
        body += (f'<div class="node{fin}" style="left:{x}px;top:{y}px;width:{g["nw"]}px;height:{g["nh"]}px;{anim(f"nd{i}", D)}">'
                 f'{mk(nd["t"])}' + (f"<small>{mk(nd['s'])}</small>" if nd.get("s") else "") + "</div>")
    body += "</div>"
    if spec.get("closing"):
        css.append(G.gate("cl", t_close))
        body += f'<div class="close" style="top:{g["close"]}px;{anim("cl", D)}">{mk(spec["closing"])}</div>'
    return [{"html": page(fmt, body, "\n".join(css), timeline=tl(D, fps)), "timeline": tl(D, fps)}]


# ======================================================== 3. build-up, smooth (default)
CSS3S = """
.f-feed .fit,.f-story .fit{margin-top:56px}.f-x .fit{margin-top:28px}
.path{position:relative;display:flex;flex-direction:column;gap:var(--gap);margin:14px 16px 14px 0}
.step{display:flex;align-items:center;gap:34px;position:relative;z-index:1}
.step .num{flex:0 0 auto;width:var(--d);height:var(--d);border-radius:50%;background:var(--paper);border:5px solid var(--accent);color:var(--accent);font-weight:700;font-size:calc(var(--d)*.42);display:flex;align-items:center;justify-content:center;direction:ltr;position:relative;z-index:2}
.step.last .num{background:var(--accent);color:#fff}
.step .txt{font-size:var(--fs);font-weight:600;line-height:1.2;text-wrap:balance}
.step .txt small{display:block;font-size:calc(var(--fs)*.62);font-weight:400;color:var(--soft);margin-top:6px}
.seg{position:absolute;right:calc(var(--d)/2 - 3px);top:var(--d);height:var(--gap);width:6px;background:var(--rule);z-index:0}
.seg.on{background:var(--accent)}
.track{position:absolute;right:calc(var(--d)/2 - 9px);top:calc(var(--d)/2);bottom:calc(var(--d)/2);width:18px;z-index:1}
.track .dot{position:absolute;right:0;width:18px;height:18px;margin-top:-9px;border-radius:50%;background:var(--accent);box-shadow:0 0 0 6px #B4451A2E}
.glow{position:absolute;inset:-10px;border-radius:50%;border:4px solid var(--accent)}
.f-feed{--d:112px;--fs:54px;--gap:70px}
.f-feed h1.t{font-size:84px}.f-story h1.t{font-size:86px}.f-x h1.t{font-size:66px}.f-story{--d:120px;--fs:58px;--gap:80px}.f-x{--d:84px;--fs:44px;--gap:34px}
.gridb{display:grid;grid-template-columns:repeat(var(--cols),1fr);grid-auto-flow:var(--flow);grid-template-rows:repeat(var(--rows),auto);gap:24px}
.gb{background:#FBF9F5;border:2px solid var(--rule);border-radius:22px;padding:30px;font-size:40px;font-weight:600;display:flex;gap:18px;align-items:center}
.gb .num{width:60px;height:60px;border-radius:50%;background:var(--accent);color:#fff;font-size:30px;display:flex;align-items:center;justify-content:center;flex:0 0 auto;direction:ltr}
.closing{margin-top:36px;border-right:10px solid var(--accent);background:#fff;border-radius:16px;padding:28px 34px;font-size:40px;font-weight:600;line-height:1.3}
.f-x .closing{font-size:32px;padding:18px 26px}
"""


def r3_smooth(spec, fmt):
    need(spec, "title", "steps")
    steps = [_s(x) for x in spec["steps"]]
    n = len(steps)
    D, fps = float(spec.get("loop", 10)), float(spec.get("fps", 12.5))
    G = Gate(D, hold=float(spec.get("open_hold", 1.4)))
    step = float(spec.get("step", .8))
    t_on = [G.r0 + i * step for i in range(n)]
    t_close = t_on[-1] + .7
    t_full = (t_close if spec.get("closing") else t_on[-1]) + .5
    P = D / 2
    css = [CSS3S, kf("pulse", D / 4, [(0, "transform:scale(1);opacity:.6"), (D / 4 * .75, "transform:scale(1.35);opacity:0"), (D / 4, "opacity:0")])]
    layout = spec.get("layout", "path")
    if layout == "path":
        inner = '<div class="path">'
        for i, st in enumerate(steps):
            css.append(G.item(f"st{i}", t_on[i], ghost="opacity:.14;transform:scale(1)"))
            last = i == n - 1
            seg = ""
            if not last:
                css.append(G.gate(f"sg{i}", t_on[i + 1] - .15))
                seg = f'<i class="seg"></i><i class="seg on" style="{anim(f"sg{i}", D)}"></i>'
            glow = f'<i class="glow" style="{anim("pulse", D / 4)}"></i>' if last else ""
            inner += (f'<div class="step{" last" if last else ""}" style="{anim(f"st{i}", D)}">{seg}<div class="num">{i + 1}{glow}</div>'
                      f'<div class="txt">{mk(st["t"])}' + (f"<small>{mk(st['s'])}</small>" if st.get("s") else "") + "</div></div>")
        css.append(G.gate("tr", t_full))
        css.append(kf("down", P, [(0, "top:0%;opacity:0"), (P * .08, "opacity:1"), (P * .85, "opacity:1"), (P * .95, "top:100%;opacity:0"), (P, "top:100%;opacity:0")]))
        inner += f'<div class="track" style="{anim("tr", D)}"><i class="dot" style="{anim("down", P)}"></i></div></div>'
    else:
        cols = min(n, 4) if fmt == "x" else (1 if fmt == "story" else 2)
        rows = -(-n // cols)
        flow = "column" if (fmt == "feed" and cols == 2) else "row"
        css.append(kf("glint", P, [(0, "box-shadow:0 0 0 0 #B4451A00"), (P * .08, "box-shadow:0 0 0 5px #B4451A44"), (P * .22, "box-shadow:0 0 0 0 #B4451A00")]))
        inner = f'<div class="gridb" style="--cols:{cols};--rows:{rows};--flow:{flow}">'
        for i, st in enumerate(steps):
            css.append(G.item(f"st{i}", t_on[i], ghost="opacity:0;transform:scale(.97)"))
            inner += (f'<div style="{anim(f"st{i}", D)}"><div class="gb" style="height:100%;{anim("glint", P, delay=-(i * P / n))}">'
                      f'<div class="num">{i + 1}</div><div>{mk(st["t"])}</div></div></div>')
        inner += "</div>"
    body = header(spec) + f'<div class="fit grow"><div class="in">{inner}</div></div>'
    if spec.get("closing"):
        css.append(G.gate("cl", t_close))
        body += f'<div class="closing" style="{anim("cl", D)}">{mk(spec["closing"])}</div>'
    return [{"html": page(fmt, body, "\n".join(css), timeline=tl(D, fps)), "timeline": tl(D, fps)}]


# ======================================================== 2. rooms grid (cheat sheet v2)
CSS2R = """
.f-feed .fit,.f-x .fit{margin-top:36px}.f-story .fit{margin-top:40px}
.rooms{display:grid;grid-template-columns:repeat(var(--cols),1fr);grid-auto-rows:1fr;gap:20px}
.room{background:#FBF9F5;border:2px solid var(--rule);border-radius:22px;padding:26px 28px 28px;display:grid;grid-template-columns:1fr auto;grid-template-rows:auto auto 1fr;column-gap:18px;min-width:0}
.rl{grid-column:1;font-size:22px;font-weight:600;color:var(--accent);letter-spacing:.06em}
.rn{grid-column:1;font-size:38px;font-weight:700;line-height:1.15;margin-top:6px}
.ro{grid-column:1/-1;font-size:28px;line-height:1.35;color:var(--soft);margin-top:12px}
.ri{grid-column:2;grid-row:1/3;align-self:start;width:84px;height:84px;border-radius:20px;background:var(--paper);border:2px solid var(--rule);color:var(--ink);display:flex;align-items:center;justify-content:center}
.ri .ico{color:var(--accent)}
.f-x .room{padding:22px 24px}.f-x .rn{font-size:32px}.f-x .ro{font-size:24px}.f-x .ri{width:68px;height:68px}
.f-story .room{padding:40px 40px 44px}.f-story .rl{font-size:28px}.f-story .rn{font-size:52px}.f-story .ro{font-size:38px}.f-story .ri{width:110px;height:110px}
/* metaphor frame: house */
.house{position:relative;padding:0 26px 26px;border:6px solid var(--ink);border-top:0;border-radius:0 0 18px 18px;background:#EFE9DF}
.roof{display:block;width:calc(100% + 60px);margin:0 -30px;height:120px}
.f-x .roof{height:70px}
.ground{height:6px;background:var(--ink);margin:0 -50px;border-radius:3px}
"""


def _room(b, i, prefix, isize):
    b = b if isinstance(b, dict) else {"h": b}
    lab = b.get("label") or f'{prefix} <span class="ltr">{i:02d}</span>'
    ic = f'<div class="ri">{icon(b.get("icon", "check"), isize)}</div>'
    return (f'<div class="room"><div class="rl">{mk(lab) if b.get("label") else lab}</div><div class="rn">{mk(b["h"])}</div>{ic}'
            + (f'<div class="ro">{mk(b["t"])}</div>' if b.get("t") else "") + "</div>")


def r2_rooms(spec, fmt):
    need(spec, "title", "blocks")
    blocks = spec["blocks"]
    prefix = spec.get("label_prefix", "שלב")
    isize = {"feed": 50, "x": 42, "story": 64}[fmt]
    def wrap(grid):
        if spec.get("frame") == "house" and fmt != "story":
            roof = ('<svg class="roof" viewBox="0 0 1000 120" preserveAspectRatio="none"><path d="M20 118 L500 8 L980 118" fill="#E7E1D6" stroke="#1C1916" stroke-width="7" stroke-linejoin="round"/>'
                    '<rect x="740" y="30" width="56" height="62" fill="#1C1916"/></svg>')
            return f'{roof}<div class="house">{grid}</div><div class="ground"></div>'
        return grid
    if fmt == "story":
        k = int(spec.get("story_frames", 3))
        per = -(-len(blocks) // k)
        pages = []
        for f in range(k):
            chunk = blocks[f * per:(f + 1) * per]
            if not chunk:
                break
            sp = dict(spec); sp["subtitle"] = spec.get("subtitle") if f == 0 else None
            grid = '<div class="rooms" style="--cols:1">' + "".join(_room(b, f * per + j + 1, prefix, isize) for j, b in enumerate(chunk)) + "</div>"
            body = progress(f, k) + header(sp) + f'<div class="fit grow"><div class="in">{grid}</div></div>'
            pages.append({"html": page(fmt, body, CSS2R)})
        return pages
    cols = spec.get("columns")
    if isinstance(cols, dict):
        cols = cols.get(fmt)
    cols = cols or (3 if fmt == "x" or len(blocks) >= 9 else 2)
    grid = f'<div class="rooms" style="--cols:{cols}">' + "".join(_room(b, i + 1, prefix, isize) for i, b in enumerate(blocks)) + "</div>"
    body = header(spec) + f'<div class="fit grow"><div class="in">{wrap(grid)}</div></div>'
    return [{"html": page(fmt, body, CSS2R)}]


# ======================================================== shared: org cards (8, 16)
CSS_ORG = """
.hrow{display:flex;align-items:flex-start;gap:30px}
.hrow .hd{flex:1 1 auto;min-width:0}
.legend{flex:0 0 auto;display:flex;flex-direction:column;gap:10px;font-size:21px;color:var(--soft);background:#FBF9F5;border:2px solid var(--rule);border-radius:16px;padding:14px 18px;margin-top:6px}
.legend div{display:flex;align-items:center;gap:10px;white-space:nowrap}
.lg-node{width:30px;height:20px;border-radius:6px;border:2.5px solid var(--ink);background:#fff}
.lg-goal{width:30px;height:20px;border-radius:6px;background:var(--ink)}
.lg-ghost{width:30px;height:20px;border-radius:6px;border:2.5px dashed var(--soft)}
.lg-pill{width:30px;height:16px;border-radius:8px;background:var(--accent)}
.lg-tag{width:30px;height:16px;border-radius:5px;border:2px solid var(--rule);background:var(--paper)}
.oc{background:#fff;border:2.5px solid var(--ink);border-radius:18px;padding:14px 14px 16px;text-align:center;display:flex;flex-direction:column;align-items:center;gap:8px;width:100%;max-width:var(--cw,300px);position:relative;z-index:2;min-width:0}
.oc .ot{font-size:var(--ofs,28px);font-weight:700;line-height:1.2}
.kpi{display:inline-flex;align-items:center;gap:8px;background:var(--accent);color:#fff;border-radius:999px;padding:5px 14px 5px 7px;font-size:calc(var(--ofs,28px)*.7);font-weight:600;line-height:1.2;max-width:100%}
.kpi b{background:#fff;color:var(--accent);border-radius:999px;padding:1px 8px;font-size:.78em;font-weight:700;letter-spacing:.04em}
.tags{display:flex;flex-wrap:wrap;justify-content:center;gap:6px}
.tg{font-size:calc(var(--ofs,28px)*.62);color:var(--soft);border:1.5px solid var(--rule);background:var(--paper);border-radius:7px;padding:2px 9px;white-space:nowrap}
.oc.goal{background:var(--ink);border-color:var(--ink);color:var(--paper)}
.oc.goal .kpi{background:var(--paper);color:var(--ink)}.oc.goal .kpi b{background:var(--accent);color:#fff}
.oc.ghost{border-style:dashed;border-color:var(--soft);background:transparent;color:var(--soft)}
.oc.ghost .kpi{background:transparent;color:var(--soft);border:1.5px dashed var(--soft)}.oc.ghost .kpi b{background:var(--soft);color:var(--paper)}
.oc.acc{border-color:var(--accent);border-width:3.5px}
/* CSS tree (static): parent above, children below, elbow connectors */
.otree{display:flex;flex-direction:column;align-items:center;width:100%}
.okids{display:flex;justify-content:center;gap:var(--kg,16px);position:relative;padding-top:var(--cg,34px);width:100%}
.okid{display:flex;flex-direction:column;align-items:center;flex:1 1 0;min-width:0;position:relative;padding-top:var(--cg,34px)}
.css .okids::before{content:"";position:absolute;top:0;left:50%;height:var(--cg,34px);border-left:3px solid var(--ink);transform:translateX(-1.5px)}
.css .okid::before,.css .okid::after{content:"";position:absolute;top:var(--cg,34px);width:calc(50% + var(--kg,16px)/2);border-top:3px solid var(--ink)}
.css .okid::before{right:50%}.css .okid::after{left:50%}
.css .okid:first-child::before,.css .okid:last-child::after{display:none}
.css .okid:only-child::before,.css .okid:only-child::after{display:none}
.css .okid>.stub{position:absolute;top:var(--cg,34px);left:50%;height:var(--cg,34px);border-left:3px solid var(--ink);transform:translateX(-1.5px)}
.css .okids{padding-top:var(--cg,34px)}.css .okid{padding-top:var(--cg,34px)}
.band{flex:0 0 auto;background:var(--accent);color:#fff;font-size:34px;font-weight:700;line-height:1.3;text-align:center;padding:24px 85px;margin:26px -85px 0}
.f-x .band{font-size:28px;padding:16px 80px;margin:18px -80px 0}
.f-story .band{font-size:40px;padding:30px 85px}
"""

LEGEND_DEFAULT = [{"k": "node", "t": "תפקיד"}, {"k": "pill", "t": "KPI: מה הוא מודד"}, {"k": "ghost", "t": "הגיוס הבא"}]


def legend(items):
    if not items:
        return ""
    return '<div class="legend">' + "".join(f'<div><i class="lg-{it.get("k", "node")}"></i>{mk(it["t"])}</div>' for it in items) + "</div>"


def ocard(nd, extra_style=""):
    kind = nd.get("kind") or ("ghost" if nd.get("ghost") else ("acc" if nd.get("accent") else ""))
    kpi = f'<span class="kpi"><b><span class="ltr">KPI</span></b><span>{mk(nd["kpi"])}</span></span>' if nd.get("kpi") else ""
    tags = ('<div class="tags">' + "".join(f'<span class="tg">{mk(t)}</span>' for t in nd["tags"]) + "</div>") if nd.get("tags") else ""
    return f'<div class="oc {kind}" data-id="{nd["id"]}" style="{extra_style}"><div class="ot">{mk(nd["t"])}</div>{kpi}{tags}</div>'


def otree(nodes, css_lines=True, style_for=None):
    kids = {}
    for nd in nodes:
        kids.setdefault(nd.get("parent"), []).append(nd)
    def rec(nd):
        h = ocard(nd, style_for(nd) if style_for else "")
        ch = kids.get(nd["id"], [])
        if ch:
            h += '<div class="okids">' + "".join(f'<div class="okid"><i class="stub"></i>{rec(c)}</div>' for c in ch) + "</div>"
        return h
    return f'<div class="otree{" css" if css_lines else ""}">' + "".join(rec(r) for r in kids.get(None, [])) + "</div>"


def header_legend(spec, leg=True):
    return f'<div class="hrow">{header(spec)}{legend(spec.get("legend", LEGEND_DEFAULT)) if leg else ""}</div>'


# ======================================================== 8. team evolution v2 (org chart + KPI pills)
CSS8V = CSS_ORG + """
.f-feed .fit,.f-x .fit{margin-top:26px}.f-story .fit{margin-top:30px}
.stv{display:flex;flex-direction:column;gap:18px}
.sth{display:flex;flex-direction:row;gap:18px}
.stg2{background:#FBF9F5;border:2px solid var(--rule);border-radius:24px;padding:18px 22px 22px;display:flex;flex-direction:column;align-items:center;gap:6px;flex:1 1 0;min-width:0}
.stv .stg2{flex-direction:row;align-items:center;gap:22px}
.sgh{display:flex;align-items:center;gap:12px;flex:0 0 auto}
.stv .sgh{flex-direction:column;width:130px;text-align:center}
.sgn{width:52px;height:52px;border-radius:50%;background:var(--ink);color:var(--paper);font-weight:700;font-size:26px;display:flex;align-items:center;justify-content:center;direction:ltr;flex:0 0 auto}
.sgl{font-size:24px;font-weight:600;color:var(--soft);line-height:1.2}
.stv .otree{flex:1}
.f-feed{--ofs:26px;--cw:290px;--cg:22px}.f-x{--ofs:22px;--cw:230px;--cg:20px;--kg:10px}.f-story{--ofs:40px;--cw:620px;--cg:44px}
.f-story .stg2{padding:44px 30px}.f-story .sgn{width:76px;height:76px;font-size:38px}.f-story .sgl{font-size:34px}
"""


def r8_org(spec, fmt):
    need(spec, "title", "stages")
    stages = spec["stages"]
    def stage(i, st):
        lab = f'<div class="sgl">{mk(st["label"])}</div>' if st.get("label") else ""
        return f'<div class="stg2"><div class="sgh"><div class="sgn">{i + 1}</div>{lab}</div>{otree(st["nodes"])}</div>'
    band = f'<div class="band">{mk(spec["takeaway"])}</div>' if spec.get("takeaway") else ""
    if fmt == "story":
        pages = []
        for i, st in enumerate(stages):
            b = band if i == len(stages) - 1 else ""
            body = progress(i, len(stages)) + header_legend(spec, leg=(i == 0)) + f'<div class="fit grow"><div class="in">{stage(i, st)}</div></div>{b}'
            pages.append({"html": page(fmt, body, CSS8V)})
        return pages
    lay = spec.get("layout", "rows" if fmt == "feed" else "columns")
    inner = f'<div class="{"stv" if lay == "rows" else "sth"}">' + "".join(stage(i, st) for i, st in enumerate(stages)) + "</div>"
    body = header_legend(spec) + f'<div class="fit grow"><div class="in">{inner}</div></div>{band}'
    return [{"html": page(fmt, body, CSS8V)}]


# ======================================================== 16. role org chart with KPIs (animated)
CSS16 = CSS_ORG + """
.f-feed .fit,.f-x .fit{margin-top:30px}.f-story .fit{margin-top:30px}
.f-feed{--ofs:30px;--cw:400px;--cg:52px;--kg:22px}.f-x{--ofs:24px;--cw:330px;--cg:34px;--kg:16px}.f-story{--ofs:34px;--cw:440px;--cg:60px;--kg:20px}
.ov{position:absolute;inset:0;z-index:1;pointer-events:none}
.ov svg{position:absolute;inset:0;overflow:visible}
.ov path{fill:none;stroke-width:3.5;stroke-linecap:round;stroke-linejoin:round}
.ov path.base{stroke:#CFC6B8}.ov path.on{stroke:var(--ink)}
.odot{position:absolute;left:0;top:0;width:14px;height:14px;border-radius:50%;background:var(--accent);box-shadow:0 0 0 5px #B4451A2B;offset-rotate:0deg;offset-anchor:center}
.oc.goal::after{content:"";position:absolute;inset:-9px;border-radius:24px;border:4px solid var(--accent);animation:gpulse var(--P) linear 0s infinite both}
"""

HOOK16 = r"""
window.__tkHooks.push(function(){
  const ov=document.createElement('div');ov.className='ov';document.body.appendChild(ov);
  const W=innerWidth,H=innerHeight;
  let svg='<svg width="'+W+'" height="'+H+'">',dots='';
  const cards=[...document.querySelectorAll('.oc[data-parent]')];
  cards.forEach((c,i)=>{
    const p=document.querySelector('.oc[data-id="'+c.dataset.parent+'"]'); if(!p) return;
    const a=p.getBoundingClientRect(), b=c.getBoundingClientRect();
    const x1=a.left+a.width/2, y1=a.bottom, x2=b.left+b.width/2, y2=b.top, my=(y1+y2)/2;
    const d='M'+x1.toFixed(1)+' '+y1.toFixed(1)+' V'+my.toFixed(1)+' H'+x2.toFixed(1)+' V'+y2.toFixed(1);
    const lv=c.dataset.lv;
    svg+='<path class="base" d="'+d+'"/><path class="on" style="animation:ln'+lv+' var(--D) linear 0s infinite both" d="'+d+'"/>';
    const dl=-((i*0.37)%1)*parseFloat(getComputedStyle(document.documentElement).getPropertyValue('--P'));
    dots+='<div style="position:absolute;inset:0;animation:dg'+lv+' var(--D) linear 0s infinite both"><i class="odot" style="offset-path:path(\''+d+'\');animation:otravel var(--P) linear '+dl+'s infinite both"></i></div>';
  });
  ov.innerHTML=svg+'</svg>'+dots;
});
"""


def r16(spec, fmt):
    need(spec, "title", "nodes")
    nodes = [dict(n) for n in spec["nodes"]]
    by = {n["id"]: n for n in nodes}
    for n in nodes:
        d, p = 0, n.get("parent")
        while p:
            d += 1; p = by[p].get("parent")
        n["lv"] = d
    depth = max(n["lv"] for n in nodes)
    D, fps = float(spec.get("loop", 10)), float(spec.get("fps", 12.5))
    G = Gate(D, hold=float(spec.get("open_hold", 1.4)))
    step = float(spec.get("step", .9))
    t_lv = [G.r0 + k * step for k in range(depth + 1)]
    P = D / 4
    css = [CSS16, f":root{{--D:{D}s;--P:{P}s}}"]
    css.append(kf("gpulse", P, [(0, "transform:scale(1);opacity:.55"), (P * .7, "transform:scale(1.06);opacity:0"), (P, "opacity:0")]))
    css.append(kf("otravel", P, [(0, "offset-distance:0%;opacity:0"), (P * .1, "opacity:1"), (P * .8, "opacity:1"), (P * .92, "offset-distance:100%;opacity:0"), (P, "offset-distance:100%;opacity:0")]))
    for k in range(depth + 1):
        css.append(G.item(f"lv{k}", t_lv[k]))
        css.append(G.gate(f"ln{k}", t_lv[k] - .2))
        css.append(G.gate(f"dg{k}", t_lv[-1] + .6))
    def style_for(nd):
        return f"animation:lv{nd['lv']} {D}s linear 0s infinite both"
    tree = otree(nodes, css_lines=False, style_for=style_for)
    for n in nodes:     # parent + level attributes for the connector hook
        if n.get("parent"):
            tree = tree.replace(f'data-id="{n["id"]}"', f'data-id="{n["id"]}" data-parent="{n["parent"]}" data-lv="{n["lv"]}"', 1)
    for n in nodes:
        if n.get("kind") == "goal":
            pass
    band = f'<div class="band">{mk(spec["takeaway"])}</div>' if spec.get("takeaway") else ""
    if band:
        css.append(G.gate("bd", t_lv[-1] + .4))
        band = band.replace('class="band"', f'class="band" style="animation:bd {D}s linear 0s infinite both"')
    body = header_legend(spec) + f'<div class="fit grow"><div class="in">{tree}</div></div>{band}'
    return [{"html": page(fmt, body, "\n".join(css), hooks_js=HOOK16, timeline=tl(D, fps)), "timeline": tl(D, fps)}]


# ======================================================== 15. illustrated metaphor scene (animated)
CSS15 = """
body{background:#1C1916;color:var(--paper)}
.foot{color:var(--dsoft)}.foot b{color:var(--paper)}
.bar{background:var(--accent)}
.sky{position:absolute;inset:0;z-index:0;overflow:hidden}
.star{position:absolute;width:4px;height:4px;border-radius:50%;background:var(--paper)}
.moon{position:absolute;border-radius:50%;background:#F3EFE7;box-shadow:0 0 0 18px #F3EFE712,0 0 0 40px #F3EFE70A}
.moon i{position:absolute;border-radius:50%;background:#E4DCCD}
.hd h1.t{color:var(--paper);text-align:center}.hd .sub{color:var(--dsoft);text-align:center}
.scene{position:relative;z-index:2;display:flex;flex-direction:column;align-items:center}
.roof{display:block;width:100%;height:auto;overflow:visible}
.smoke{position:absolute;border-radius:50%;background:#F3EFE7}
.walls{width:calc(100% - 40px);background:#2A2520;border:6px solid #3A332C;border-top:0;padding:14px;display:grid;grid-template-columns:repeat(var(--cols),1fr);grid-auto-rows:1fr;gap:12px}
.rm{position:relative;background:#332C26;border-radius:10px;padding:16px 18px 0;display:flex;flex-direction:column;overflow:hidden;min-width:0;border:2px solid #40382F}
.rm .lab{font-size:19px;font-weight:600;letter-spacing:.08em;color:#E39A73}
.rm .nm{font-size:32px;font-weight:700;line-height:1.15;margin-top:4px;color:var(--paper)}
.rm .ow{font-size:22px;line-height:1.3;color:var(--dsoft);margin-top:6px}
.rm .flr{position:absolute;left:0;right:0;bottom:0;height:12px;background:#4A4038}
.rm .art{position:absolute;left:16px;bottom:12px;color:var(--paper);opacity:.92}
.rm .lamp{position:absolute;left:22px;top:0;width:3px;height:26px;background:#5A5047}
.rm .bulb{position:absolute;left:12px;top:24px;width:24px;height:16px;border-radius:12px 12px 4px 4px;background:var(--accent)}
.rm .light{position:absolute;left:-86px;top:30px;width:220px;height:200px;background:radial-gradient(ellipse 50% 50% at 50% 0%,#E8A27F4D,#E8A27F00)}
.base{width:calc(100% - 10px);height:16px;background:#3A332C;border-radius:0 0 8px 8px}
.lawn{width:100%;height:10px;background:#2E3A2A;border-radius:5px;margin-top:6px}
.f-x .rm .nm{font-size:28px}.f-x .rm .ow{font-size:19px}.f-x .rm .lab{font-size:16px}
.f-story .rm .nm{font-size:40px}.f-story .rm .ow{font-size:27px}.f-story .rm .lab{font-size:22px}
"""


def r15(spec, fmt):
    need(spec, "title", "rooms")
    rooms = [r if isinstance(r, dict) else {"h": r} for r in spec["rooms"]]
    n = len(rooms)
    if not 4 <= n <= 9:
        raise SystemExit("template 15: 4 to 9 rooms")
    D, fps = float(spec.get("loop", 8)), float(spec.get("fps", 12.5))
    cols = {"x": 3 if n <= 6 else 3, "feed": 2 if n <= 6 else 3, "story": 2}[fmt]
    if fmt == "x" and n in (4, 8):
        cols = 4
    prefix = spec.get("label_prefix", "חדר")
    css = [CSS15]
    css.append(kf("tw", D / 2, [(0, "opacity:.25"), (D / 4, "opacity:1"), (D / 2, "opacity:.25")]))
    css.append(kf("glow", D / 2, [(0, "opacity:.55"), (D / 4, "opacity:1"), (D / 2, "opacity:.55")]))
    css.append(kf("puff", D / 2, [(0, "transform:translate(0,0) scale(.5);opacity:0"), (D / 2 * .15, "opacity:.32"),
                                   (D / 2 * .85, "transform:translate(-26px,-120px) scale(1.5);opacity:0"), (D / 2, "transform:translate(-26px,-120px) scale(1.5);opacity:0")]))
    css.append(kf("bob", D / 2, [(0, "transform:translateY(0)"), (D / 4, "transform:translateY(-6px)"), (D / 2, "transform:translateY(0)")]))
    W, H = {"feed": (1080, 1350), "x": (1600, 900), "story": (1080, 1920)}[fmt]
    import random
    rnd = random.Random(7)
    stars = "".join(f'<i class="star" style="left:{rnd.randint(20, W - 20)}px;top:{rnd.randint(20, int(H * .32))}px;{anim("tw", D / 2, delay=rnd.uniform(0, D / 2))}"></i>' for _ in range(34))
    mx, my, mr = {"feed": (120, 190, 90), "x": (130, 110, 70), "story": (120, 300, 100)}[fmt]
    moon = f'<div class="moon" style="left:{mx}px;top:{my}px;width:{mr}px;height:{mr}px"><i style="left:22%;top:30%;width:18%;height:18%"></i><i style="left:55%;top:55%;width:12%;height:12%"></i></div>'
    sky = f'<div class="sky">{stars}{moon}</div>'
    art = {"feed": 70, "x": 58, "story": 86}[fmt]
    cells = ""
    for i, r in enumerate(rooms):
        lab = r.get("label") or f'{prefix} <span class="ltr">{i + 1:02d}</span>'
        cells += (f'<div class="rm"><div class="lamp"></div><div class="light" style="{anim("glow", D / 2, delay=i * .6)}"></div><div class="bulb"></div>'
                  f'<div class="lab" style="padding-left:46px">{lab}</div><div class="nm" style="padding-left:46px">{mk(r["h"])}</div>'
                  + (f'<div class="ow">{mk(r["t"])}</div>' if r.get("t") else "")
                  + f'<div style="flex:1;min-height:{art + 26}px"></div><div class="art" style="{anim("bob", D / 2, delay=i * .45)}">{icon(r.get("icon", "check"), art, 1.6)}</div><div class="flr"></div></div>')
    roof = ('<svg class="roof" viewBox="0 0 1000 170"><rect x="720" y="20" width="60" height="100" fill="#3A332C"/>'
            '<path d="M10 168 L500 12 L990 168 Z" fill="#B4451A" stroke="#8E3613" stroke-width="8" stroke-linejoin="round"/>'
            '<circle cx="500" cy="105" r="34" fill="#E8A27F"/><path d="M500 71v68M466 105h68" stroke="#8E3613" stroke-width="6"/></svg>')
    smoke = "".join(f'<i class="smoke" style="left:{75}%;top:4%;width:30px;height:30px;{anim("puff", D / 2, delay=k * D / 6)}"></i>' for k in range(3))
    scene = (f'<div class="scene"><div style="position:relative;width:100%">{roof}{smoke}</div>'
             f'<div class="walls" style="--cols:{cols}">{cells}</div><div class="base"></div><div class="lawn"></div></div>')
    body = sky + header(spec) + f'<div class="fit grow" style="margin-top:24px"><div class="in">{scene}</div></div>'
    return [{"html": page(fmt, body, "\n".join(css), body_cls="dark", timeline=tl(D, fps, check=0.0)), "timeline": tl(D, fps, check=0.0)}]


# ======================================================== 17. POV collage (also 10 variant "pov")
CSS17 = """
body{background:#FBF9F5}
.col{position:absolute;inset:0;z-index:1}
.it{position:absolute;transform:translate(-50%,-50%) rotate(var(--r,0deg));white-space:nowrap}
.ph{font-size:var(--pfs,30px);color:var(--ink);font-weight:400}
.chipx{font-size:var(--cfs,26px);background:#fff;border:2px solid var(--rule);border-radius:999px;padding:8px 20px;box-shadow:0 6px 16px #1C191612;font-weight:600}
.srch{display:flex;align-items:center;gap:12px;font-size:var(--cfs,26px);background:#fff;border:2px solid #E3DDD2;border-radius:999px;padding:10px 24px 10px 20px;box-shadow:0 8px 20px #1C191614;color:var(--ink)}
.srch .ico{color:var(--soft);flex:0 0 auto}
.obj{display:flex;flex-direction:column;align-items:center;gap:6px;color:var(--ink)}
.obj .ob2{background:#fff;border-radius:22px;padding:14px;box-shadow:0 10px 24px #1C191618;border:2px solid #ECE6DB;color:var(--accent);display:flex}
.obj span{font-size:20px;color:var(--soft)}
.pov{position:absolute;z-index:2;left:50%;top:var(--py,50%);transform:translate(-50%,-50%);width:var(--pw,760px);text-align:center;font-style:italic;font-weight:900;font-size:var(--hfs,76px);line-height:1.12;letter-spacing:-.01em;color:var(--ink)}
.pov em{color:var(--accent);font-style:italic}
"""
SLOTS17 = {   # (x%, y%, rotation) around a central exclusion box; RTL reading starts top right
    "feed": [(76, 9, -3), (30, 8, 4), (52, 17, -2), (14, 22, -5), (85, 24, 3), (63, 28, 2), (24, 33, -3),
             (82, 66, -4), (20, 67, 3), (55, 72, -2), (86, 80, 2), (33, 80, -4), (66, 87, 3), (14, 89, 5), (50, 93, -1), (88, 92, -3)],
    "x": [(85, 12, -3), (55, 10, 2), (22, 12, -4), (88, 33, 3), (12, 33, -2), (90, 58, -3), (10, 58, 4),
          (82, 81, 2), (58, 86, -2), (33, 84, 3), (13, 80, -4), (70, 30, 2), (30, 30, -3), (68, 66, 3), (32, 68, -2), (50, 92, 1)],
    "story": [(74, 17, -3), (30, 16, 4), (52, 23, -2), (16, 28, -5), (84, 30, 3), (62, 34, 2), (26, 38, -3),
              (80, 62, -4), (22, 63, 3), (56, 67, -2), (84, 72, 2), (30, 73, -4), (64, 78, 3), (18, 79, 5), (50, 83, -1), (84, 83, -3)],
}


def r17(spec, fmt):
    need(spec, "headline", "items")
    slots = SLOTS17[fmt]
    items = spec["items"][:len(slots)]
    sz = {"feed": dict(pfs=30, cfs=26, ico=58, hfs=74, pw=760, py=50), "x": dict(pfs=28, cfs=24, ico=50, hfs=66, pw=820, py=50),
          "story": dict(pfs=34, cfs=30, ico=64, hfs=84, pw=800, py=50)}[fmt]
    sz.update(spec.get("sizes", {}).get(fmt, {}))
    out = ""
    for (x, y, r), it in zip(slots, items):
        it = it if isinstance(it, dict) else {"type": "phrase", "t": it}
        x, y = it.get("x", x), it.get("y", y)
        st = f"left:{x}%;top:{y}%;--r:{it.get('rot', r)}deg"
        ty = it.get("type", "phrase")
        if ty == "chip":
            out += f'<div class="it chipx" style="{st}">{mk(it["t"])}</div>'
        elif ty == "search":
            out += f'<div class="it srch" style="{st}">{icon("search", 28, 2.2)}<span>{mk(it["t"])}</span></div>'
        elif ty == "object":
            lab = f'<span>{mk(it["t"])}</span>' if it.get("t") else ""
            out += f'<div class="it obj" style="{st}"><div class="ob2">{icon(it["icon"], sz["ico"], 1.7)}</div>{lab}</div>'
        else:
            out += f'<div class="it ph" style="{st}">{mk(it["t"])}</div>'
    vars_ = ";".join(f"--{k}:{v}{'%' if k == 'py' else 'px'}" for k, v in sz.items() if k != "ico")
    body = f'<div class="col" style="{vars_}">{out}<div class="pov">{mk(spec["headline"])}</div></div>'
    return [{"html": page(fmt, body, CSS17)}]


# ======================================================== 18. weekly changelog card ("2.8 דברים שלמדתי השבוע")
CSS18 = """
.top{display:flex;align-items:flex-start;gap:34px}
.big{flex:0 0 auto;text-align:center}
.big .n{font-size:var(--nfs,250px);font-weight:800;line-height:.86;color:var(--accent);letter-spacing:-.04em;direction:ltr}
.big .wk{font-size:var(--wfs,28px);font-weight:600;color:var(--soft);margin-top:14px;white-space:nowrap}
.ttl{flex:1;min-width:0;padding-top:14px}
.ttl h1{font-size:var(--tfs,70px);font-weight:800;line-height:1.08}
.ttl .hook{font-size:var(--hfs,32px);color:var(--soft);line-height:1.3;margin-top:14px}
.rws{display:flex;flex-direction:column;gap:20px}
.rw{position:relative;background:#fff;border:2.5px solid var(--rule);border-radius:22px;padding:24px 28px 26px;display:flex;flex-direction:column;gap:12px;overflow:hidden}
.rw .rh{font-size:var(--rfs,42px);font-weight:700;line-height:1.2}
.rw .rb{font-size:calc(var(--rfs,42px)*.68);line-height:1.35;color:var(--soft)}
.tagp{align-self:flex-start;font-size:24px;font-weight:700;border-radius:999px;padding:5px 18px;display:inline-flex;align-items:center;gap:10px}
.tagp .ix{font-weight:800;direction:ltr}
.tg-tried{background:var(--panel);color:var(--ink)}
.tg-worked{background:var(--accent);color:#fff}
.tg-failed{background:var(--ink);color:var(--paper)}
.tg-change{background:#fff;color:var(--accent);border:2.5px solid var(--accent)}
.rw.p8{border:3px dashed var(--accent);background:#FFFDF9}
.rw .m8{position:absolute;left:24px;top:20px;font-size:26px;font-weight:800;color:var(--accent);direction:ltr}
.bar8{height:12px;border-radius:6px;background:var(--zebra);overflow:hidden;margin-top:6px}
.bar8 i{display:block;height:100%;width:80%;background:var(--accent);border-radius:6px}
.data{display:flex;gap:16px;margin-top:22px}
.dt{flex:1;background:var(--ink);color:var(--paper);border-radius:18px;padding:16px 20px}
.dt b{display:block;font-size:44px;font-weight:800;line-height:1;direction:ltr;text-align:right}
.dt span{display:block;font-size:22px;margin-top:6px}
.dt small{display:block;font-size:15px;color:var(--dsoft);margin-top:6px}
.f-feed{--nfs:250px}.f-x{--nfs:190px;--tfs:58px;--hfs:26px;--rfs:32px;--wfs:24px}.f-story{--nfs:280px;--tfs:76px;--rfs:46px}
.f-x .xg{display:grid;grid-template-columns:minmax(0,.9fr) minmax(0,1.3fr);gap:44px;align-items:center;height:100%}
.f-x .top{flex-direction:column;gap:18px}.f-x .big{text-align:right}
.f-x .rws{gap:14px}.f-x .rw{padding:16px 22px 18px;gap:8px}.f-x .tagp{font-size:20px}
.slide .rh{font-size:64px}.slide .rb{font-size:40px}.slide .rw{padding:46px 44px;gap:28px}.slide .tagp{font-size:32px;padding:8px 26px}
.kick{display:flex;align-items:center;gap:18px;font-size:30px;font-weight:700;color:var(--soft)}
.kick .n{font-size:110px;color:var(--accent);font-weight:800;direction:ltr;line-height:1}
"""
TAGS18 = {"ניסיתי": "tried", "עבד": "worked", "לא עבד": "failed", "משנה": "change"}


def _row18(i, r, n, cls=""):
    tag = r.get("tag", "ניסיתי")
    k = TAGS18.get(tag, "tried")
    p8 = i == n - 1
    m8 = '<span class="m8">0.8</span>' if p8 else ""
    bar = '<div class="bar8"><i class="fill8"></i></div>' if p8 else ""
    body = f'<div class="rb">{mk(r["body"])}</div>' if r.get("body") and "slide" in cls else ""
    return (f'<div class="rw{" p8" if p8 else ""} {cls}">{m8}<span class="tagp tg-{k}"><span class="ix">{i + 1}</span>{mk(tag)}</span>'
            f'<div class="rh">{mk(r["h"])}</div>{body}{bar}</div>')


def _data18(data):
    if not data:
        return ""
    for d in data:
        if not d.get("src"):
            raise SystemExit("template 18: every data number needs its source ('src'); leave the strip out when data is missing")
    return '<div class="data">' + "".join(f'<div class="dt"><b>{mk(str(d["n"]))}</b><span>{mk(d["label"])}</span><small>{mk("מקור: " + d["src"])}</small></div>' for d in data[:3]) + "</div>"


def r18(spec, fmt):
    need(spec, "rows", "week", "date")
    rows = spec["rows"]
    if len(rows) != 3:
        raise SystemExit("template 18: exactly 3 learnings")
    title = spec.get("title", "דברים שלמדתי השבוע")
    wk = f'שבוע <span class="ltr">{spec["week"]}</span> · <span class="ltr">{spec["date"]}</span>'
    hook = f'<div class="hook">{mk(spec["hook"])}</div>' if spec.get("hook") else ""
    top = f'<div class="top"><div class="big"><div class="n" id="n28">2.8</div><div class="wk">{wk}</div></div><div class="ttl"><h1>{mk(title)}</h1>{hook}</div></div>'
    motion = bool(spec.get("motion")) and fmt in ("feed", "x")
    css = [CSS18]
    hooks = ""
    timeline = None
    if fmt == "carousel":
        pages = []
        cover = (top + '<div class="fit grow" style="margin-top:50px"><div class="in"><div class="rws">'
                 + "".join(_row18(i, r, 3) for i, r in enumerate(rows)) + f'</div>{_data18(spec.get("data"))}</div></div>')
        pages.append({"html": page(fmt, cover, CSS18)})
        for i, r in enumerate(rows):
            kick = f'<div class="kick"><span class="n">2.8</span><span>{mk(title)}<br>{wk}</span></div>'
            b = kick + f'<div class="fit grow" style="margin-top:60px"><div class="in">{_row18(i, r, 3, "slide")}</div></div>'
            pages.append({"html": page(fmt, b, CSS18)})
        return pages
    rws = '<div class="rws">' + "".join(
        _row18(i, r, 3).replace('<div class="rw', f'<div style="animation:rw{i} var(--D) linear 0s infinite both" class="rw', 1) if motion else _row18(i, r, 3)
        for i, r in enumerate(rows)) + "</div>"
    data = _data18(spec.get("data"))
    if fmt == "x":
        body = f'<div class="xg"><div>{top}</div><div class="fit grow"><div class="in">{rws}{data}</div></div></div>'
    else:
        body = top + f'<div class="fit grow" style="margin-top:44px"><div class="in">{rws}{data}</div></div>'
    if motion:
        D, fps = float(spec.get("loop", 8)), float(spec.get("fps", 12.5))
        G = Gate(D, hold=float(spec.get("open_hold", 1.5)))
        t0, t1 = G.r0 - .2, G.r0 + 1.2              # counter ticks 0.0 -> 2.8
        t_rows = [t1 + .35 + i * .6 for i in range(3)]
        css.append(f":root{{--D:{D}s}}")
        for i in range(3):
            css.append(G.item(f"rw{i}", t_rows[i], ghost="opacity:0;transform:translateY(16px) scale(1)", on="opacity:1;transform:translateY(0) scale(1)"))
        css.append(kf("fill8", D, [(0, "width:80%"), (G.hold, "width:80%"), (G.hold + G.fade, "width:0%"), (t_rows[2] + .3, "width:0%"), (t_rows[2] + 1.3, "width:80%")]))
        css.append(".fill8{animation:fill8 var(--D) linear 0s infinite both}")
        hooks = (f"window.__tkSeekHooks=[function(t){{const el=document.getElementById('n28');let v=2.8;"
                 f"if(t>={G.hold + G.fade * .5}&&t<{t0})v=0;else if(t>={t0}&&t<{t1})v=Math.floor((t-{t0})/({t1 - t0})*28)/10;"
                 f"el.textContent=v.toFixed(1);}}];")
        timeline = tl(D, fps)
    pg = {"html": page(fmt, body, "\n".join(css), hooks_js=hooks, timeline=timeline)}
    if timeline:
        pg["timeline"] = timeline
    return [pg]


# ======================================================== 19. cover / CTA card (light or dark)
CSS19 = """
.stage{justify-content:center}
.kicker{font-size:30px;font-weight:700;color:var(--accent);letter-spacing:.02em;margin-bottom:26px}
.cv1 h1{font-size:var(--cfs,100px);font-weight:800;line-height:1.06;letter-spacing:-.015em;text-wrap:balance}
.cv1 .sub{font-size:38px;margin-top:30px;line-height:1.35}
.cta{display:inline-flex;align-items:center;gap:14px;margin-top:44px;background:var(--accent);color:#fff;font-size:34px;font-weight:700;border-radius:999px;padding:16px 34px}
body.dark .sub{color:var(--dsoft)}body.dark .kicker{color:#E39A73}
.swipe{position:absolute;left:0;bottom:0;font-size:26px;color:var(--soft);display:flex;align-items:center;gap:10px}
.f-x .cv1 h1{font-size:var(--cfs,84px)}.f-story .cv1 h1{font-size:var(--cfs,110px)}
"""


def r19(spec, fmt):
    need(spec, "title")
    kick = f'<div class="kicker">{mk(spec["kicker"])}</div>' if spec.get("kicker") else ""
    sub = f'<div class="sub">{mk(spec["subtitle"])}</div>' if spec.get("subtitle") else ""
    cta = f'<div><span class="cta">{mk(spec["cta"])}</span></div>' if spec.get("cta") else ""
    sw = f'<div class="swipe">{mk(spec["swipe"])} &larr;</div>' if spec.get("swipe") else ""
    style = f' style="--cfs:{spec["title_size"]}px"' if spec.get("title_size") else ""
    body = f'<div class="fit" style="flex:0 1 auto"><div class="in cv1"{style}>{kick}<h1>{mk(spec["title"])}</h1>{sub}{cta}</div></div>{sw}'
    return [{"html": page(fmt, body, CSS19, body_cls="dark" if spec.get("theme") == "dark" else "")}]
