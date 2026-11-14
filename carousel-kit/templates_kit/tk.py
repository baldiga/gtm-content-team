#!/usr/bin/env python3
"""templates_kit: render visual-formats-library templates from a JSON spec.

CLI:
  python3 tk.py SPEC.json [-o OUT_DIR] [--formats feed,story,x] [--no-html]
  python3 tk.py --list
SPEC is one object or a list of objects. Each object needs "template": N.
See README.md for the spec of each template.

Outputs (OUT_DIR, default: specs dir/<name>):
  feed-1080x1350.png, story-1080x1920.png (or story-01..NN), x-1600x900.png
  animated templates: <fmt>-WxH.gif + .mp4 (H.264 yuv420p, silent) + -final.png
  manifest.json (files, rule check, fit report), html/ (sources)
Exit code 3 when the rule check or the layout check flags something.
"""
from __future__ import annotations

import argparse
import html as htmllib
import json
import re
import shutil
import subprocess
import sys
import tempfile
from html.parser import HTMLParser
from pathlib import Path

KIT = Path(__file__).resolve().parent
REPO_ROOT = KIT.parent.parent
sys.path.insert(0, str(KIT.parent))
sys.path.insert(0, str(REPO_ROOT))
import render  # noqa: E402  (carousel-kit/render.py: markup, ChromeSession, flag_rules)
from config.brand import load_brand  # noqa: E402

BRAND = load_brand()

FORMATS = {"feed": (1080, 1350), "story": (1080, 1920), "x": (1600, 900), "carousel": (1080, 1350)}
BASE_CSS = (KIT / "base.css").read_text(encoding="utf-8")
PAGE_JS = (KIT / "page.js").read_text(encoding="utf-8")

FOOTER = (
    f'<div class="foot"><b><span class="ltr" dir="ltr" lang="en">{htmllib.escape(BRAND.owner_name)}</span></b>'
    f'<span class="ltr" dir="ltr" lang="en">{htmllib.escape(BRAND.domain)}</span></div>'
)

TOKEN = re.compile(r"(\*[^*\n]+\*|\[\[[^\]]+\]\])")


def mk(text) -> str:
    """Spec text to RTL-safe HTML. Latin runs become LTR isolates (render.markup).
    *word* = accent colour, [[phrase]] = keep on one line, \\n = line break."""
    if text is None:
        return ""
    lines = str(text).split("\n")
    if len(lines) > 1:   # render.markup would wrap the "br" of its own <br> as Latin
        return "<br>".join(mk(l) for l in lines)
    out = []
    for part in TOKEN.split(str(text)):
        if not part:
            continue
        if part.startswith("*") and part.endswith("*") and len(part) > 2:
            out.append(f"<em>{mk(part[1:-1])}</em>")
        elif part.startswith("[[") and part.endswith("]]"):
            out.append(f'<span class="nowrap">{render.markup(part[2:-2])}</span>')
        else:
            out.append(render.markup(part))
    return "".join(out)


def plain(text) -> str:
    """Visible characters of a spec string (markers removed) for the rule check."""
    return TOKEN.sub(lambda m: m.group(0).strip("*[]"), str(text or ""))


def page(fmt: str, body: str, css: str = "", body_cls: str = "", hooks_js: str = "", timeline: dict | None = None) -> str:
    """timeline = {"duration": s, "fps": n, "check_at": s}: the page is one seekable CSS animation loop."""
    w, h = FORMATS[fmt]
    cls = "f-feed f-carousel" if fmt == "carousel" else f"f-{fmt}"
    if timeline:
        hooks_js = f"window.__tkTimeline={json.dumps(timeline)};" + hooks_js
    return (
        f'<!doctype html><html lang="he" dir="rtl" class="{cls}"><head><meta charset="utf-8">'
        f"<style>:root{{--W:{w}px;--H:{h}px}}\n{BASE_CSS}\n{css}</style></head>"
        f'<body class="{body_cls}"><div class="bar"></div><div class="stage">{body}</div>{FOOTER}'
        f"<script>window.__tkHooks=[];{hooks_js}</script><script>{PAGE_JS}</script></body></html>"
    )


CHIP_CSS = """
.chip{position:absolute;right:var(--chr,85px);bottom:var(--chb,34px);z-index:6;display:flex;align-items:center;gap:16px;background:#fff;border:2px solid #E6DFD3;border-radius:999px;padding:8px 30px 8px 8px;box-shadow:0 8px 22px #1C191614}
.chip img{width:var(--chs,74px);height:var(--chs,74px);border-radius:50%;display:block;background:var(--panel);object-fit:cover}
.chip .cn{display:flex;flex-direction:column;line-height:1.15}
.chip .cn b{font-size:var(--chf,27px);font-weight:700;color:var(--ink)}
.chip .cn>span{font-size:calc(var(--chf,27px)*.8);color:var(--accent);font-weight:600}
.chip.dk{background:#2A2520;border-color:#3A332C;box-shadow:none}.chip.dk .cn b{color:var(--paper)}.chip.dk .cn>span{color:#E39A73}
.f-x .chip{--chr:80px;--chb:22px;--chs:60px;--chf:23px}
.f-story .chip{--chb:330px;--chs:84px;--chf:30px}
"""


def apply_chip(html_text: str, chip) -> str:
    """Opt-in photo chip (spec "chip": true | "light" | "dark"): circular photo + name + domain,
    replaces the text footer (the domain stays on the image)."""
    variant = chip if chip in ("light", "dark") else ("dark" if re.search(r'<body class="[^"]*\bdark\b', html_text) else "light")
    name = BRAND.owner_name
    avatar = BRAND.avatar
    if avatar is None or not avatar.exists():
        raise SystemExit("chip requested but brand.avatar_path is missing. Add a circular avatar PNG and set avatar_path in config/brand.json")
    img = avatar.resolve().as_uri()
    el = (f'<div class="chip{" dk" if variant == "dark" else ""}"><img src="{img}" alt="">'
          f'<div class="cn"><b><span class="ltr" dir="ltr" lang="en">{htmllib.escape(name)}</span></b>'
          f'<span><span class="ltr" dir="ltr" lang="en">{htmllib.escape(BRAND.domain)}</span></span></div></div>')
    if FOOTER not in html_text:
        raise SystemExit("chip: footer not found in page")
    return html_text.replace(FOOTER, el).replace("</style></head>", CHIP_CSS + "</style></head>", 1)


def progress(i: int, n: int) -> str:
    return '<div class="progress" aria-hidden="true">' + "".join(
        f'<i class="{"on" if k <= i else ""}"></i>' for k in range(n)) + "</div>"


# ---------------------------------------------------------------- rule check
class _Visible(HTMLParser):
    def __init__(self):
        super().__init__(); self.parts, self.skip = [], 0
    def handle_starttag(self, tag, attrs):
        if tag in ("script", "style"): self.skip += 1
    def handle_endtag(self, tag):
        if tag in ("script", "style") and self.skip: self.skip -= 1
    def handle_data(self, data):
        t = data.replace("\u200f", "").replace("\u200e", "").strip()
        if t and not self.skip: self.parts.append(t)


def visible_text(html_text: str) -> str:
    p = _Visible(); p.feed(html_text); return "\n".join(p.parts)


DENY = list(BRAND.blocked_terms)
LATIN_OK = set(BRAND.latin_allowlist) | {"SDRים"}


def rule_check(texts: list[str], deny_extra: list[str] | None = None) -> tuple[list[str], list[str]]:
    """Return (errors, warnings) for all visible text of one piece."""
    joined = "\n".join(texts)
    errors = [f.replace("slide 1 body: ", "") for f in render.flag_rules([{"body": joined}])]
    for word in DENY + list(deny_extra or []):
        if re.search(rf"(?<![A-Za-z]){re.escape(word)}(?![A-Za-z])", joined, re.I):
            errors.append(f"contains blocked name '{word}'")
    for ch, label in (("\U0001F449", "right pointer emoji"), ("\U0001F446", "up pointer emoji"), ("\U0001F448", "left pointer emoji")):
        if ch in joined: errors.append(f"contains a {label}")
    if "בקיצור" in joined: errors.append("contains 'בקיצור'")
    if joined.count("..") > 1: errors.append("'..' used more than once")
    if re.search(r"https?://|www\.", joined): errors.append("URL in image text")
    warnings = []
    for tok in sorted(set(re.findall(r"[A-Za-z][A-Za-z.]+", joined))):
        if tok not in LATIN_OK and tok.rstrip(".") not in LATIN_OK:
            warnings.append(f"Latin word '{tok}' not in the allowlist: check it is not a person or company")
    return errors, warnings


# ---------------------------------------------------------------- rendering
def shoot(jobs: list[dict]) -> list[dict]:
    """jobs: [{html_path, png_path, w, h}] -> reports. One Chrome for the batch."""
    if not jobs:
        return []
    chrome = render.find_chrome()
    with tempfile.TemporaryDirectory(prefix="tk-", ignore_cleanup_errors=True) as tmp:
        sess = render.ChromeSession(chrome, Path(tmp) / "u", width=1600, height=1920)
        sess.start()
        try:
            if sess.mode != "cdp":
                raise SystemExit("Chrome DevTools port did not open; templates_kit needs CDP")
            jf = Path(tmp) / "jobs.json"
            jf.write_text(json.dumps([{"uri": Path(j["html_path"]).resolve().as_uri(), "out": str(j["png_path"]),
                                       "w": j["w"], "h": j["h"],
                                       **({"times": j["times"], "outs": [str(o) for o in j["outs"]]} if j.get("times") else {})}
                                      for j in jobs]))
            nshots = sum(len(j.get("times") or [1]) for j in jobs)
            res = subprocess.run(["node", str(KIT / "tk_shot.mjs"), str(sess.port), str(jf)],
                                 capture_output=True, text=True, timeout=60 + 10 * len(jobs) + 2 * nshots)
        finally:
            sess.close()
    reports = [json.loads(l[7:]) for l in res.stdout.splitlines() if l.startswith("REPORT ")]
    if res.returncode != 0 or len(reports) != len(jobs):
        raise SystemExit(f"screenshot batch failed:\n{res.stdout[-2000:]}\n{res.stderr[-2000:]}")
    for j in jobs:
        for o in (j.get("outs") or [j["png_path"]]):
            render.normalize_png(Path(o), j["w"], j["h"])
    return reports


def _sequence(tmp: Path, frames: list[Path], durations: list[float], fps: int) -> str:
    """Expand frames into an exact constant-rate image sequence (symlinks)."""
    tmp.mkdir(parents=True, exist_ok=True)
    i = 0
    for f, d in zip(frames, durations):
        for _ in range(max(1, round(d * fps))):
            (tmp / f"{i:05d}.png").symlink_to(f.resolve()); i += 1
    return str(tmp / "%05d.png")


def make_motion(frames: list[Path], durations: list[float], base: Path, w: int, h: int,
                mp4_skip: int = 0, mp4_first_hold: float = 1.0) -> list[Path]:
    """GIF (palette, loops, all frames) + MP4 (H.264 yuv420p, silent, faststart, 30 fps).
    The MP4 drops the first `mp4_skip` frames so it opens on title + first revealed
    state (Buffer/IG picks the thumbnail), held for at least `mp4_first_hold` s."""
    gif, mp4 = base.with_suffix(".gif"), base.with_suffix(".mp4")
    md = list(durations[mp4_skip:]); md[0] = max(md[0], mp4_first_hold)
    with tempfile.TemporaryDirectory(prefix="tk-seq-") as t:
        g = _sequence(Path(t) / "g", frames, durations, 10)
        m = _sequence(Path(t) / "m", frames[mp4_skip:], md, 10)
        subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-framerate", "10", "-i", g, "-vf",
                        "split[a][b];[a]palettegen=max_colors=96:stats_mode=full[p];[b][p]paletteuse=dither=none",
                        "-loop", "0", str(gif)], check=True)
        subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-framerate", "10", "-i", m, "-vf",
                        f"scale={w}:{h}:flags=lanczos,format=yuv420p", "-r", "30", "-c:v", "libx264",
                        "-profile:v", "high", "-level", "4.1", "-preset", "slow", "-crf", "18",
                        "-movflags", "+faststart", "-an", str(mp4)], check=True)
    return [gif, mp4]


def make_motion_seq(frames: list[Path], fps: int, base: Path, w: int, h: int) -> list[Path]:
    """Constant-rate frame sequence (timeline pages) -> looping GIF at `fps` + MP4 (30 fps, silent).
    The loop starts on the full frame, so the MP4 thumbnail is a complete image."""
    gif, mp4 = base.with_suffix(".gif"), base.with_suffix(".mp4")
    with tempfile.TemporaryDirectory(prefix="tk-seq-") as t:
        pat = _sequence(Path(t) / "g", frames, [1 / fps] * len(frames), fps)
        subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-framerate", str(fps), "-i", pat, "-vf",
                        "split[a][b];[a]palettegen=max_colors=128:stats_mode=diff[p];[b][p]paletteuse=dither=none:diff_mode=rectangle",
                        "-loop", "0", str(gif)], check=True)
        subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-framerate", str(fps), "-i", pat, "-vf",
                        f"scale={w}:{h}:flags=lanczos,format=yuv420p", "-r", "30", "-c:v", "libx264",
                        "-profile:v", "high", "-level", "4.1", "-preset", "slow", "-crf", "18",
                        "-movflags", "+faststart", "-an", str(mp4)], check=True)
    return [gif, mp4]


def write_pdf(pngs: list[Path], pdf: Path) -> None:
    render.write_pdf(pngs, pdf)


def build(spec: dict, out_dir: Path, formats: list[str] | None, keep_html: bool = True) -> dict:
    import templates as T
    tid = int(spec["template"])
    mod = T.REGISTRY.get(tid)
    if mod is None:
        raise SystemExit(f"template {tid} is not in this kit (have {sorted(T.REGISTRY)})")
    T.validate(tid, spec)
    fmts = formats or spec.get("formats") or mod["formats"]
    names = spec.get("names", {})
    out_dir.mkdir(parents=True, exist_ok=True)
    html_dir = out_dir / "html"; html_dir.mkdir(exist_ok=True)
    frames_dir = out_dir / "frames"
    jobs, plan = [], []
    for fmt in fmts:
        if fmt not in FORMATS: raise SystemExit(f"unknown format {fmt}")
        w, h = FORMATS[fmt]
        pages = mod["render"](spec, fmt)
        anim = mod.get("animated")
        if anim == "optional":
            anim = bool(spec.get("motion"))
        animated = anim and fmt not in ("story", "carousel")
        if anim and fmt == "story" and not pages[-1].get("timeline"):
            pages = pages[-1:]            # IG stories are image only: final frame
        stem = names.get(fmt, f"{fmt}-{w}x{h}")
        stem = re.sub(r"\.(png|gif|mp4)$", "", stem)
        items = []
        for i, pg in enumerate(pages):
            if spec.get("chip"):
                pg["html"] = apply_chip(pg["html"], spec["chip"])
            tl = pg.get("timeline")
            if tl:
                hp = html_dir / f"{stem}.html"
                hp.write_text(pg["html"], encoding="utf-8")
                if animated:
                    frames_dir.mkdir(exist_ok=True)
                    n = round(tl["duration"] * tl["fps"])
                    times = [round(k / tl["fps"], 4) for k in range(n)] + [tl.get("check_at", 0)]
                    outs = [frames_dir / f"{fmt}-{k:04d}.png" for k in range(n)] + [out_dir / f"{stem}-final.png"]
                    png = outs[-1]
                else:   # story / static use of an animated page: the full state
                    times, png = [tl.get("check_at", 0)], out_dir / f"{stem}.png"
                    outs = [png]
                jobs.append({"html_path": hp, "png_path": png, "w": w, "h": h, "times": times, "outs": outs})
                items.append((png, pg))
                continue
            if animated:
                frames_dir.mkdir(exist_ok=True)
                png = frames_dir / f"{fmt}-{i:02d}.png"
            elif len(pages) == 1:
                png = out_dir / f"{stem}.png"
            else:
                png = out_dir / (f"{stem}-{i + 1:02d}.png" if "{n}" not in stem else stem.replace("{n}", f"{i + 1:02d}") + ".png")
            hp = html_dir / (png.stem + ".html")
            hp.write_text(pg["html"], encoding="utf-8")
            jobs.append({"html_path": hp, "png_path": png, "w": w, "h": h})
            items.append((png, pg))
        plan.append((fmt, w, h, stem, animated, items))
    reports = shoot(jobs)
    # multi-frame static groups (story frames): reshoot with one shared zoom so text size matches
    redo = []
    rep_tmp = {r["out"]: r["report"] for r in reports}
    for fmt, w, h, stem, animated, items in plan:
        if len(items) < 2 or any(pg.get("timeline") for _, pg in items):
            continue
        zs = [[f["zoom"] for f in rep_tmp[str(p)].get("fit", [])] for p, _ in items]
        if not zs[0] or len({len(z) for z in zs}) != 1:
            continue
        common = [min(col) for col in zip(*zs)]
        if all(z == common for z in zs):
            continue
        for p, pg in items:
            k = iter(common)
            pg["html"] = re.sub(r'class="fit( grow)?"', lambda m: f'class="fit" data-zoom="{next(k)}"', pg["html"])
            hp = html_dir / (p.stem + ".html"); hp.write_text(pg["html"], encoding="utf-8")
            redo.append({"html_path": hp, "png_path": p, "w": w, "h": h})
    if redo:
        again = {r["out"]: r for r in shoot(redo)}
        reports = [again.get(r["out"], r) for r in reports]
    files, layout_flags = [], []
    rep_by = {r["out"]: r["report"] for r in reports}
    texts = []
    for fmt, w, h, stem, animated, items in plan:
        for png, pg in items:
            r = rep_by.get(str(png), {})
            for f in r.get("fit", []):
                if f.get("overflow"): layout_flags.append(f"{png.name}: text does not fit even at zoom {f['zoom']}")
                elif f.get("zoom", 1) < 0.8: layout_flags.append(f"{png.name}: text shrunk to zoom {f['zoom']} (check readability)")
            if r.get("outside"): layout_flags.append(f"{png.name}: text outside canvas: {r['outside'][:3]}")
            if r.get("unsafe"): layout_flags.append(f"{png.name}: text outside IG safe zone: {r['unsafe'][:3]}")
            if any(x != "ok" for x in r.get("hooks", [])): layout_flags.append(f"{png.name}: hook error {r['hooks']}")
            vt = visible_text(pg["html"]); texts.append(vt)
            if BRAND.owner_name not in vt or BRAND.domain not in vt:
                layout_flags.append(f"{png.name}: footer missing")
        tl = items[0][1].get("timeline") if items else None
        if animated and tl:
            n = round(tl["duration"] * tl["fps"])
            seq = [frames_dir / f"{fmt}-{k:04d}.png" for k in range(n)]
            files += [str(p) for p in make_motion_seq(seq, tl["fps"], out_dir / stem, w, h)] + [str(items[0][0])]
        elif animated:
            pngs = [p for p, _ in items]
            durs = [pg.get("duration", 1.0) for _, pg in items]
            final = out_dir / f"{stem}-final.png"
            shutil.copy(pngs[-1], final)
            files += [str(p) for p in make_motion(pngs, durs, out_dir / stem, w, h,
                                                              mp4_skip=0 if spec.get("open_full") else mod.get("mp4_skip", 1))] + [str(final)]
        else:
            files += [str(p) for p, _ in items]
            if (mod.get("carousel") and fmt == "feed") or fmt == "carousel":
                pdf = out_dir / "carousel.pdf"; write_pdf([p for p, _ in items], pdf); files.append(str(pdf))
    errors, warnings = rule_check(texts, spec.get("deny"))
    manifest = {"template": tid, "name": spec.get("name"), "formats": fmts, "files": files,
                "rule_errors": errors, "rule_warnings": warnings, "layout_flags": layout_flags,
                "fit": {Path(k).name: v.get("fit") for k, v in rep_by.items()}}
    (out_dir / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    if not keep_html:
        shutil.rmtree(html_dir, ignore_errors=True)
    return manifest


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("spec", nargs="?", type=Path)
    ap.add_argument("-o", "--out", type=Path)
    ap.add_argument("--formats", default="")
    ap.add_argument("--no-html", action="store_true")
    ap.add_argument("--list", action="store_true")
    a = ap.parse_args()
    import templates as T
    if a.list or not a.spec:
        for k, v in sorted(T.REGISTRY.items()):
            print(f"{k:>2}  {v['name']:<22} formats={','.join(v['formats'])}{'  animated' if v.get('animated') else ''}")
        for k, why in T.NOT_BUILT.items():
            print(f"{k:>2}  not built: {why}")
        return 0
    data = json.loads(a.spec.read_text(encoding="utf-8"))
    specs = data if isinstance(data, list) else [data]
    bad = 0
    for sp in specs:
        out = a.out if (a.out and len(specs) == 1) else (a.out or a.spec.parent) / sp.get("name", f"t{sp['template']}")
        if a.out and len(specs) == 1: out = a.out
        m = build(sp, out.resolve(), [f for f in a.formats.split(",") if f] or None, keep_html=not a.no_html)
        print(f"== template {m['template']} {m['name']} -> {out}")
        for f in m["files"]: print("  wrote", f)
        print("  rule check:", m["rule_errors"] or "clean")
        for wmsg in m["rule_warnings"]: print("  warn:", wmsg)
        print("  layout:", m["layout_flags"] or "clean")
        bad += bool(m["rule_errors"] or [f for f in m["layout_flags"] if "shrunk" not in f])
    return 3 if bad else 0


if __name__ == "__main__":
    raise SystemExit(main())
