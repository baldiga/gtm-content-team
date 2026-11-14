#!/usr/bin/env python3
"""Render a Hebrew RTL LinkedIn carousel from slides JSON or the week markdown.

Input is either:
  - a JSON list of slides (or {"slides": [...]})
  - a markdown file with "## Slide N" / Title: / Body: blocks

Each slide: type cover|content|cta, title, optional body, kicker, items.

Writes slide-01.png ... (1080x1350), carousel.pdf, and optionally
contact-sheet.png. With --stories, also writes 1080x1920 IG story
frames into OUT/stories/ (story-01.png ... and a contact sheet). Re-runs skip unchanged slides by content hash, so a
CTA-only edit only re-renders the last slide, then rebuilds the PDF
and contact sheet.

Brand footer on every slide comes from config/brand.json (name and domain).
Copy is rendered as written.

Requires /usr/bin/google-chrome (or /opt/google/chrome/chrome) and Rubik.
"""

from __future__ import annotations

import argparse
import hashlib
import html
import json
import os
import re
import socket
import subprocess
import sys
import tempfile
import time
import urllib.request
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from PIL import Image

CHROME_CANDIDATES = (
    "/opt/google/chrome/chrome",
    "/usr/bin/google-chrome",
    "/opt/google/chrome/google-chrome",
)
SLIDE_W = 1080
SLIDE_H = 1350
STORY_W = 1080
STORY_H = 1920
KIT_DIR = Path(__file__).resolve().parent
REPO_ROOT = KIT_DIR.parent
sys.path.insert(0, str(REPO_ROOT))
from config.brand import load_brand  # noqa: E402

BRAND = load_brand()
CSS_PATH = KIT_DIR / "carousel.css"
STORY_CSS_PATH = KIT_DIR / "story.css"
TZ = ZoneInfo(BRAND.timezone)

LATIN_RUN = re.compile(
    r"(?:"
    r"[A-Za-z][A-Za-z0-9+]*(?:\.[A-Za-z][A-Za-z0-9+-]+)+(?:/[A-Za-z0-9._~-]+)*"
    r"|"
    r"[A-Za-z][A-Za-z0-9&/+#]*(?:\s+[A-Za-z][A-Za-z0-9&/+#]*)*"
    r")"
)
NOWRAP_RUN = re.compile(r"\[\[(.+?)\]\]")
# Trailing punctuation that should stay in the Hebrew sentence, not
# stick to the left-to-right run.
PUNCT_AFTER_LTR = re.compile(
    r"(</span>)(" + "\u200f" + r"?)([.,!?])"
)
# Emoji (and the word before it) stay together at the RTL end of the line.
EMOJI_RUN = re.compile(
    r"(\S+\s+)?((?:["
    "\U0001F300-\U0001FAFF\U00002700-\U000027BF"
    r"]["
    "\uFE0F\u200D"
    r"]*)+)"
)

SWIPE_SVG = (
    '<svg class="chevron" viewBox="0 0 28 16" aria-hidden="true">'
    '<path d="M26 8H2M8 2L2 8l6 6"/></svg>'
)

FOOTER_HTML = f"""      <div class="byline" dir="ltr" lang="en">
        <span class="name">{html.escape(BRAND.owner_name)}</span>
        <span class="site">{html.escape(BRAND.domain)}</span>
      </div>"""

MD_SLIDE = re.compile(
    r"^##\s+Slide\s+(?P<n>\d+)\s*$"
    r"(?:\nType:\s*(?P<type>cover|content|cta)\s*)?"
    r"\nTitle:\s*(?P<title>.*?)\s*"
    r"\nBody:\s*(?P<body>.*?)(?=\n##\s+Slide\s+\d+|\n---\s*$|\Z)",
    re.MULTILINE | re.DOTALL,
)

FORBIDDEN_DASHES = {
    "\u2012": "figure dash",
    "\u2013": "en dash",
    "\u2014": "em dash",
    "\u2015": "horizontal bar",
    "\u2212": "minus sign",
}
NAME_HINTS = tuple(BRAND.blocked_terms)


def find_chrome() -> str:
    for path in CHROME_CANDIDATES:
        if Path(path).exists():
            return path
    raise SystemExit("Missing Chrome: tried " + ", ".join(CHROME_CANDIDATES))


def format_mtime(path: Path) -> str:
    ts = datetime.fromtimestamp(path.stat().st_mtime, TZ)
    return ts.strftime("%Y-%m-%d %H:%M:%S %Z") + f" ({BRAND.timezone})"


def load_markdown(path: Path) -> list[dict]:
    text = path.read_text(encoding="utf-8")
    found = list(MD_SLIDE.finditer(text))
    if not found:
        raise ValueError(f"No '## Slide N' blocks in {path}")
    slides: list[dict] = []
    for i, m in enumerate(found):
        stype = (m.group("type") or "").strip()
        if not stype:
            if i == 0:
                stype = "cover"
            elif i == len(found) - 1:
                stype = "cta"
            else:
                stype = "content"
        title = " ".join(m.group("title").strip().splitlines())
        body = " ".join(m.group("body").strip().splitlines())
        slides.append({"type": stype, "title": title, "body": body})
    return slides


def load_slides(path: Path) -> list[dict]:
    if path.suffix.lower() in {".md", ".markdown"}:
        return load_markdown(path)
    data = json.loads(path.read_text(encoding="utf-8"))
    if isinstance(data, list):
        return data
    if isinstance(data, dict) and "slides" in data:
        return data["slides"]
    raise ValueError("JSON must be a list of slides or an object with a 'slides' key")


def wrap_latin(text: str) -> str:
    # RLM after each Latin isolate so following Hebrew punctuation
    # and a trailing emoji stay in RTL order after line wraps.
    return LATIN_RUN.sub(
        lambda m: f'<span class="ltr" dir="ltr" lang="en">{m.group(0)}</span>\u200f',
        text,
    )


def markup(text: str | None) -> str:
    if not text:
        return ""
    escaped = html.escape(text, quote=False)
    # Explicit line breaks: placeholder so wrap_latin never sees the "br" tag.
    escaped = escaped.replace("\n", "\x00")
    # [[...]] keeps a phrase on one line (direction from its first strong char).
    escaped = NOWRAP_RUN.sub(lambda m: "\x01" + m.group(1) + "\x02", escaped)
    marked = wrap_latin(escaped)
    marked = re.sub("\x01(.*?)\x02", lambda m: "\x01" + m.group(1).replace("\u200f", "") + "\x02", marked)
    marked = (marked.replace("\x00", "<br>\n")
              .replace("\x01", '<span class="nw" dir="auto" style="white-space:nowrap;unicode-bidi:isolate">')
              .replace("\x02", "</span>"))
    marked = PUNCT_AFTER_LTR.sub(
        lambda m: f"{m.group(1)}{m.group(2)}<span class=\"punct\" dir=\"rtl\">{m.group(3)}</span>",
        marked,
    )
    def _emoji_wrap(m: re.Match) -> str:
        word = m.group(1) or ""
        glyph = m.group(2)
        return (
            f'<span class="cue" dir="rtl">{word}'
            f'<span class="point" dir="ltr">{glyph}</span>'
            f'</span>'
        )
    marked = EMOJI_RUN.sub(_emoji_wrap, marked)
    return marked + "\u200f"


def title_is_long(title: str) -> bool:
    return len(title.replace("\n", " ")) >= 42


def flag_rules(slides: list[dict]) -> list[str]:
    flags: list[str] = []
    for i, slide in enumerate(slides, start=1):
        for field in ("title", "body", "kicker"):
            value = slide.get(field) or ""
            if not value:
                continue
            label = f"slide {i} {field}"
            for ch, name in FORBIDDEN_DASHES.items():
                if ch in value:
                    flags.append(f"{label}: contains a {name}")
            for term in NAME_HINTS:
                if not term:
                    continue
                if re.search(rf"(?<![A-Za-z]){re.escape(term)}(?![A-Za-z])", value, re.I):
                    flags.append(f"{label}: contains blocked term '{term}'")
            if "\u25bc" in value or chr(0x1F447) in value:
                flags.append(f"{label}: contains a downward pointer emoji")
    return flags


def progress_html(index: int, total: int) -> str:
    segs = []
    for i in range(1, total + 1):
        cls = "seg"
        if i < index:
            cls += " is-past"
        elif i == index:
            cls += " is-current"
        segs.append(f'<span class="{cls}"></span>')
    return (
        '<div class="progress" dir="ltr" aria-hidden="true">'
        + "".join(segs)
        + "</div>"
    )


def render_html(
    slide: dict,
    index: int,
    total: int,
    css: str,
    kind: str = "carousel",
) -> str:
    stype = slide.get("type", "content")
    if stype not in {"cover", "content", "cta"}:
        raise ValueError(f"Unknown slide type: {stype!r}")
    if kind not in {"carousel", "story"}:
        raise ValueError(f"Unknown format: {kind!r}")

    title = slide.get("title") or ""
    body = slide.get("body") or ""
    kicker = slide.get("kicker") or ""
    items = slide.get("items") or []

    classes = [f"slide slide-{stype}", f"format-{kind}"]
    if stype == "content" and title_is_long(title):
        classes.append("title-long")

    parts: list[str] = []
    if kicker:
        parts.append(f'      <p class="kicker">{markup(kicker)}</p>')
    if title:
        parts.append(f'      <h1 class="title" dir="rtl">{markup(title)}</h1>')
    if body:
        parts.append(f'      <p class="body" dir="rtl">{markup(body)}</p>')
    if items:
        lis = "\n".join(f"        <li>{markup(item)}</li>" for item in items)
        parts.append(f'      <ul class="items">\n{lis}\n      </ul>')

    current = f"{index:02d}"
    total_s = f"{total:02d}"
    bg_num = ""
    if stype in {"content", "cta"}:
        bg_num = (
            f'  <div class="bg-num" dir="ltr" aria-hidden="true">{current}</div>\n'
        )

    if kind == "story":
        header = f"      {progress_html(index, total)}"
        extra_footer = ""
        if stype == "cover":
            extra_footer = '      <p class="tap">הקישו</p>\n'
    else:
        header = (
            f'      <div class="counter" dir="ltr">'
            f'<span class="current">{current}</span>'
            f'<span class="sep"> / </span>'
            f'<span class="total">{total_s}</span></div>'
        )
        extra_footer = ""
        if stype == "cover":
            extra_footer = f'      <p class="swipe">החליקו{SWIPE_SVG}</p>\n'

    label = "סטורי" if kind == "story" else "שקופית"
    return f"""<!DOCTYPE html>
<html lang="he" dir="rtl" class="format-{kind}">
<head>
  <meta charset="utf-8">
  <title>{label} {current}</title>
  <style>{css}</style>
</head>
<body class="{' '.join(classes)}">
  <div class="accent-bar"></div>
{bg_num}  <div class="frame">
    <header class="meta">
{header}
    </header>
    <main class="main">
{chr(10).join(parts)}
    </main>
    <footer class="footer">
{FOOTER_HTML}
{extra_footer}    </footer>
  </div>
</body>
</html>
"""




def render_path_html(title: str, steps: list[str], css: str, kind: str = "feed") -> str:
    """Single-image path post. steps[0] is the start (shown at the bottom)."""
    if kind not in {"feed", "story"}:
        raise ValueError(f"Unknown path kind: {kind!r}")
    lis = "\n".join(
        f'        <li dir="rtl">{markup(step)}</li>' for step in steps
    )
    cls = "format-story" if kind == "story" else "format-feed"
    return f"""<!DOCTYPE html>
<html lang="he" dir="rtl" class="{cls}">
<head>
  <meta charset="utf-8">
  <title>{markup(title)}</title>
  <style>{css}</style>
</head>
<body class="slide path-post">
  <div class="accent-bar"></div>
  <div class="frame">
    <main class="main">
      <h1 class="title" dir="rtl">{markup(title)}</h1>
      <ol class="path">
{lis}
      </ol>
    </main>
    <footer class="footer">
{FOOTER_HTML}
    </footer>
  </div>
</body>
</html>
"""


def content_hash(html_text: str) -> str:
    return hashlib.sha256(html_text.encode("utf-8")).hexdigest()[:16]


def write_pdf(pngs: list[Path], pdf_path: Path) -> None:
    images = [Image.open(p).convert("RGB") for p in pngs]
    images[0].save(
        pdf_path,
        "PDF",
        save_all=True,
        append_images=images[1:],
        resolution=72,
    )
    for im in images:
        im.close()


def write_contact_sheet(
    pngs: list[Path],
    out_path: Path,
    gap: int = 32,
    pad: int = 40,
    width: int = SLIDE_W,
    height: int = SLIDE_H,
) -> None:
    images = [Image.open(p).convert("RGB") for p in pngs]
    n = len(images)
    w = pad * 2 + n * width + (n - 1) * gap
    h = pad * 2 + height
    sheet = Image.new("RGB", (w, h), "#D4CDC2")
    x = pad
    for im in images:
        sheet.paste(im, (x, pad))
        x += width + gap
    sheet.save(out_path, "PNG", optimize=True)
    for im in images:
        im.close()


def normalize_png(path: Path, width: int = SLIDE_W, height: int = SLIDE_H) -> None:
    im = Image.open(path)
    if im.size != (width, height):
        bg = im.getpixel((0, 0))
        canvas = Image.new(im.mode, (width, height), bg)
        cropped = im.crop((0, 0, min(im.width, width), min(im.height, height)))
        canvas.paste(cropped, (0, 0))
        im = canvas
    if im.mode != "RGB":
        im = im.convert("RGB")
    im.save(path, "PNG", optimize=True)


def free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def wait_port(port: int, timeout: float = 20.0) -> dict:
    url = f"http://127.0.0.1:{port}/json/version"
    deadline = time.time() + timeout
    last_err: Exception | None = None
    while time.time() < deadline:
        try:
            with urllib.request.urlopen(url, timeout=1) as resp:
                return json.loads(resp.read().decode())
        except Exception as exc:  # noqa: BLE001
            last_err = exc
            time.sleep(0.15)
    raise RuntimeError(f"Chrome debug port {port} did not open: {last_err}")


class ChromeSession:
    """One headless Chrome, many screenshots, via DevTools or --screenshot."""

    def __init__(
        self,
        chrome: str,
        user_data: Path,
        width: int = SLIDE_W,
        height: int = SLIDE_H,
    ) -> None:
        self.chrome = chrome
        self.user_data = user_data
        self.width = width
        self.height = height
        self.proc: subprocess.Popen | None = None
        self.port: int | None = None
        self.mode = "cli"

    def start(self) -> None:
        self.port = free_port()
        env = os.environ.copy()
        env.pop("DISPLAY", None)
        env.pop("WAYLAND_DISPLAY", None)
        env.pop("BROWSER", None)
        log_path = self.user_data / "chrome.log"
        self.user_data.mkdir(parents=True, exist_ok=True)
        log_f = open(log_path, "wb")
        cmd = [
            self.chrome,
            "--headless=new",
            "--no-sandbox",
            "--disable-gpu",
            "--disable-dev-shm-usage",
            "--disable-extensions",
            "--disable-component-extensions-with-background-pages",
            "--disable-background-networking",
            "--disable-sync",
            "--disable-default-apps",
            "--disable-breakpad",
            "--disable-crash-reporter",
            "--disable-features=Translate,MediaRouter,OptimizationHints",
            "--no-first-run",
            "--no-default-browser-check",
            "--hide-scrollbars",
            "--force-device-scale-factor=1",
            f"--window-size={self.width},{self.height}",
            "--ozone-platform=headless",
            f"--ozone-override-screen-size={self.width},{self.height}",
            f"--user-data-dir={self.user_data}",
            f"--remote-debugging-address=127.0.0.1",
            f"--remote-debugging-port={self.port}",
            "about:blank",
        ]
        self.proc = subprocess.Popen(
            cmd,
            stdout=log_f,
            stderr=subprocess.STDOUT,
            stdin=subprocess.DEVNULL,
            env=env,
        )
        try:
            wait_port(self.port, timeout=20)
            self.mode = "cdp"
            print(f"Chrome CDP ready on 127.0.0.1:{self.port}", flush=True)
        except RuntimeError:
            # Fall back later to one-shot --screenshot if the debug port never opened.
            if self.proc.poll() is not None:
                log_f.flush()
                raise RuntimeError(
                    f"Chrome exited early (code {self.proc.returncode}). "
                    f"See {log_path}"
                )
            print("Chrome debug port did not open; will use --screenshot per slide", flush=True)
            self.mode = "cli"

    def screenshot(self, html_path: Path, png_path: Path) -> None:
        if self.mode == "cdp" and self.port is not None:
            self._screenshot_cdp(html_path, png_path)
            return
        self._screenshot_cli(html_path, png_path)

    def _screenshot_cli(self, html_path: Path, png_path: Path) -> None:
        env = os.environ.copy()
        env.pop("DISPLAY", None)
        env.pop("WAYLAND_DISPLAY", None)
        udd = self.user_data / "cli-shot"
        udd.mkdir(parents=True, exist_ok=True)
        log_path = udd / "shot.log"
        cmd = [
            self.chrome,
            "--headless=new",
            "--no-sandbox",
            "--disable-gpu",
            "--disable-dev-shm-usage",
            "--disable-extensions",
            "--no-first-run",
            "--hide-scrollbars",
            "--force-device-scale-factor=1",
            f"--window-size={self.width},{self.height}",
            "--ozone-platform=headless",
            f"--ozone-override-screen-size={self.width},{self.height}",
            f"--user-data-dir={udd}",
            f"--screenshot={png_path}",
            html_path.resolve().as_uri(),
        ]
        with open(log_path, "wb") as log_f:
            result = subprocess.run(
                cmd,
                stdout=log_f,
                stderr=subprocess.STDOUT,
                stdin=subprocess.DEVNULL,
                timeout=25,
                check=False,
                env=env,
            )
        if result.returncode != 0 or not png_path.exists():
            tail = log_path.read_text(errors="replace")[-2000:]
            raise RuntimeError(
                f"Chrome --screenshot failed for {html_path.name} "
                f"(exit {result.returncode})\n{tail}"
            )

    def _screenshot_cdp(self, html_path: Path, png_path: Path) -> None:
        helper = KIT_DIR / "cdp_screenshot.mjs"
        if not helper.exists():
            raise RuntimeError(f"Missing {helper}")
        cmd = [
            "node",
            str(helper),
            str(self.port),
            html_path.resolve().as_uri(),
            str(png_path),
            str(self.width),
            str(self.height),
        ]
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=30,
            check=False,
        )
        if result.returncode != 0 or not png_path.exists():
            raise RuntimeError(
                f"CDP screenshot failed for {html_path.name}:\n"
                f"{result.stdout}\n{result.stderr}"
            )

    def close(self) -> None:
        if self.proc and self.proc.poll() is None:
            self.proc.terminate()
            try:
                self.proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self.proc.kill()


def remove_stale_outputs(out_dir: Path, total: int, prefix: str = "slide") -> None:
    """Drop prefix-NN.png / html left over from a shorter previous render."""
    keep_png = {f"{prefix}-{i:02d}.png" for i in range(1, total + 1)}
    keep_html = {f"{prefix}-{i:02d}.html" for i in range(1, total + 1)}
    for path in sorted(out_dir.glob(f"{prefix}-*.png")):
        if path.name not in keep_png:
            path.unlink()
            print(f"removed stale {path}")
    html_dir = out_dir / "html"
    if html_dir.is_dir():
        for path in sorted(html_dir.glob(f"{prefix}-*.html")):
            if path.name not in keep_html:
                path.unlink()
                print(f"removed stale {path}")
    hash_path = out_dir / f".{prefix}-hashes.json"
    if hash_path.exists():
        try:
            prev = json.loads(hash_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            prev = {}
        keep_keys = {f"{i:02d}" for i in range(1, total + 1)}
        trimmed = {k: v for k, v in prev.items() if k in keep_keys}
        if trimmed != prev:
            hash_path.write_text(json.dumps(trimmed, indent=2) + "\n", encoding="utf-8")


def parse_only(spec: str, slides: list[dict]) -> set[int] | None:
    if not spec.strip():
        return None
    only: set[int] = set()
    for token in spec.split(","):
        token = token.strip().lower()
        if token in {"cta", "cover", "content"}:
            for i, slide in enumerate(slides, start=1):
                if slide.get("type", "content") == token:
                    only.add(i)
        else:
            only.add(int(token))
    return only


def render_variant(
    *,
    slides: list[dict],
    out_dir: Path,
    chrome: str,
    kind: str,
    force: bool,
    only: set[int] | None,
    contact_sheet: bool,
    write_pdf_too: bool,
) -> list[Path]:
    if kind == "story":
        width, height = STORY_W, STORY_H
        css_path = STORY_CSS_PATH
        prefix = "story"
    else:
        width, height = SLIDE_W, SLIDE_H
        css_path = CSS_PATH
        prefix = "slide"
    if not css_path.exists():
        raise SystemExit(f"Missing stylesheet: {css_path}")

    css = css_path.read_text(encoding="utf-8")
    total = len(slides)
    out_dir.mkdir(parents=True, exist_ok=True)
    remove_stale_outputs(out_dir, total, prefix=prefix)

    hash_path = out_dir / f".{prefix}-hashes.json"
    prev_hashes: dict[str, str] = {}
    if hash_path.exists():
        try:
            prev_hashes = json.loads(hash_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            prev_hashes = {}

    html_dir = out_dir / "html"
    html_dir.mkdir(parents=True, exist_ok=True)

    plan: list[tuple[int, Path, Path, str, bool]] = []
    for i, slide in enumerate(slides, start=1):
        html_path = html_dir / f"{prefix}-{i:02d}.html"
        png_path = out_dir / f"{prefix}-{i:02d}.png"
        html_text = render_html(slide, i, total, css, kind=kind)
        html_path.write_text(html_text, encoding="utf-8")
        digest = content_hash(html_text)
        skip = (
            not force
            and only is None
            and prev_hashes.get(f"{i:02d}") == digest
            and png_path.exists()
        )
        if only is not None and i not in only:
            skip = png_path.exists()
        plan.append((i, html_path, png_path, digest, skip))

    needed = [row for row in plan if not row[4]]
    print(
        f"{kind}: {total} frames, render: {len(needed)}, skip: {total - len(needed)}",
        flush=True,
    )

    if needed:
        with tempfile.TemporaryDirectory(prefix=f"carousel-kit-{kind}-") as tmp:
            session = ChromeSession(
                chrome, Path(tmp) / "chrome-user", width=width, height=height
            )
            try:
                session.start()
                for i, html_path, png_path, digest, _ in needed:
                    session.screenshot(html_path, png_path)
                    normalize_png(png_path, width, height)
                    print(f"wrote {png_path}")
            finally:
                session.close()
    else:
        for i, html_path, png_path, digest, _ in plan:
            if not png_path.exists():
                raise SystemExit(f"Missing {png_path} and nothing to render")

    for i, html_path, png_path, digest, skipped in plan:
        if skipped:
            print(f"kept  {png_path}")
        if not png_path.exists():
            raise SystemExit(f"Failed to produce {png_path}")
        prev_hashes[f"{i:02d}"] = digest
    hash_path.write_text(json.dumps(prev_hashes, indent=2) + "\n", encoding="utf-8")

    pngs = [row[2] for row in plan]
    if write_pdf_too:
        pdf_path = out_dir / "carousel.pdf"
        write_pdf(pngs, pdf_path)
        print(f"wrote {pdf_path}")
    if contact_sheet:
        sheet_name = "contact-sheet.png" if kind == "carousel" else "stories-contact-sheet.png"
        sheet_path = out_dir / sheet_name
        write_contact_sheet(pngs, sheet_path, width=width, height=height)
        print(f"wrote {sheet_path}")
    return pngs


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Render a Hebrew RTL carousel (and optional IG stories) to PNG + PDF"
    )
    parser.add_argument("source", type=Path, help="Path to slides JSON or markdown")
    parser.add_argument(
        "-o", "--out",
        type=Path,
        default=None,
        help="Output directory (default: same directory as the source file)",
    )
    parser.add_argument(
        "--contact-sheet",
        action="store_true",
        help="Also write contact-sheet.png (all slides side by side)",
    )
    parser.add_argument(
        "--keep-html",
        action="store_true",
        help="Keep the rendered HTML next to the PNGs under html/",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Re-render every slide, even if the content hash is unchanged",
    )
    parser.add_argument(
        "--only",
        default="",
        help="Only re-render some slides: 'cta', 'cover', or comma-separated numbers (e.g. 8)",
    )
    parser.add_argument(
        "--stories",
        action="store_true",
        help="Also render 1080x1920 Instagram story frames into OUT/stories/",
    )
    parser.add_argument(
        "--stories-out",
        type=Path,
        default=None,
        help="Stories output directory (default: OUT/stories)",
    )
    args = parser.parse_args()

    source = args.source.resolve()
    if not source.exists():
        raise SystemExit(f"Source not found: {source}")
    out_dir = (args.out or source.parent).resolve()
    out_dir.mkdir(parents=True, exist_ok=True)

    if not CSS_PATH.exists():
        raise SystemExit(f"Missing stylesheet: {CSS_PATH}")
    chrome = find_chrome()

    print(f"source: {source}")
    print(f"mtime:  {format_mtime(source)}")

    slides = load_slides(source)
    if not slides:
        raise SystemExit("No slides in source")

    flags = flag_rules(slides)
    if flags:
        print("RULE FLAGS:")
        for line in flags:
            print(f"  - {line}")
    else:
        print(
            "rule check: no em/en dashes, no blocked terms from brand config, "
            "downward pointer, or known names found"
        )

    only = parse_only(args.only, slides)

    render_variant(
        slides=slides,
        out_dir=out_dir,
        chrome=chrome,
        kind="carousel",
        force=args.force,
        only=only,
        contact_sheet=args.contact_sheet,
        write_pdf_too=True,
    )

    if args.stories:
        stories_dir = (args.stories_out or (out_dir / "stories")).resolve()
        if not STORY_CSS_PATH.exists():
            raise SystemExit(f"Missing stylesheet: {STORY_CSS_PATH}")
        render_variant(
            slides=slides,
            out_dir=stories_dir,
            chrome=chrome,
            kind="story",
            force=args.force,
            only=only,
            contact_sheet=args.contact_sheet,
            write_pdf_too=False,
        )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
