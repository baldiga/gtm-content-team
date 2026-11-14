#!/usr/bin/env python3
"""Render single 1080x1350 LinkedIn images + 1080x1920 stories."""
from __future__ import annotations

import json

import sys
import tempfile
from html.parser import HTMLParser
from pathlib import Path

# Allow `python3 render_single.py` from any cwd.
KIT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(KIT_DIR))

import render  # noqa: E402

CSS_PATH = KIT_DIR / "single-post.css"


def shell(kind: str, fmt: str, inner: str, title: str) -> str:
    css = CSS_PATH.read_text(encoding="utf-8")
    body_class = "slide"
    if kind == "path":
        body_class += " path-post"
    elif kind == "quote":
        body_class += " quote-post"
    elif kind == "checklist":
        body_class += " checklist-post"
    return f"""<!DOCTYPE html>
<html lang="he" dir="rtl" class="format-{fmt}">
<head>
  <meta charset="utf-8">
  <title>{render.markup(title)}</title>
  <style>{css}</style>
</head>
<body class="{body_class}">
  <div class="accent-bar"></div>
  <div class="frame">
    <main class="main">
{inner}
    </main>
    <footer class="footer">
{render.FOOTER_HTML}
    </footer>
  </div>
</body>
</html>
"""


def quote_inner(quote: str, lines: list[str]) -> str:
    # Keep every character; only break at the first sentence period
    # so the two clauses of the approved quote sit on two lines.
    raw = quote
    lead = trail = ""
    if raw.startswith('"') and raw.endswith('"') and len(raw) > 1:
        lead, trail, raw = '"', '"', raw[1:-1]
    if ". " in raw:
        first, second = raw.split(". ", 1)
        first = first + "."
        q_html = (
            f'<span class="q-line">{render.markup(lead + first)}</span>'
            f'<span class="q-line">{render.markup(second + trail)}</span>'
        )
    else:
        q_html = render.markup(quote)
    support_html = []
    for line in lines:
        tail = "לעשר הפגישות הראשונות."
        if line.endswith(tail) and line != tail:
            head = line[: -len(tail)].rstrip()
            html_line = (
                f"{render.markup(head)} "
                f'<span class="nowrap">{render.markup(tail)}</span>'
            )
        else:
            html_line = render.markup(line)
        support_html.append(f'      <p dir="rtl">{html_line}</p>')
    support = "\n".join(support_html)
    return f"""      <div class="quote-block">
        <div class="quote-mark" aria-hidden="true">”</div>
        <p class="quote-text" dir="rtl">{q_html}</p>
      </div>
      <div class="support">
{support}
      </div>"""


def phrase_with_nowrap(text: str, tail: str) -> str:
    """Keep an approved tail phrase on one line; do not change words."""
    if tail and text.endswith(tail) and text != tail:
        head = text[: -len(tail)].rstrip()
        return f"{render.markup(head)} " f'<span class="nowrap">{render.markup(tail)}</span>'
    return render.markup(text)


def checklist_inner(title: str, items: list[str]) -> str:
    # Break after the hook "3 בדיקות" so "מועמד GTM" is not split
    # across lines. Words stay exactly as approved.
    hook = "3 בדיקות"
    if title.startswith(hook + " "):
        rest = title[len(hook) + 1 :]
        title_html = (
            f'<span class="q-line">{render.markup(hook)}</span>'
            f'<span class="q-line">{render.markup(rest)}</span>'
        )
    else:
        title_html = render.markup(title)
    rows = []
    for i, item in enumerate(items, start=1):
        item_html = phrase_with_nowrap(item, "וסיקוונס סביב מוצר?")
        rows.append(
            "        <li dir=\"rtl\">"
            f'<span class="num" dir="ltr">{i}</span>'
            f'<span class="item">{item_html}</span>'
            "</li>"
        )
    return (
        f'      <h1 class="title" dir="rtl">{title_html}</h1>\n'
        f'      <ol class="checks">\n'
        + "\n".join(rows)
        + "\n      </ol>"
    )


def path_inner(title: str, steps: list[str]) -> str:
    # Break the approved title at the question mark so "30 vs 2 or 3"
    # reads as a two-line contrast, without changing a word.
    if "؟" in title:  # Arabic question mark, unused
        parts = None
    if "? " in title:
        first, second = title.split("? ", 1)
        title_html = (
            f'<span class="q-line">{render.markup(first + "?")}</span>'
            f'<span class="q-line">{render.markup(second)}</span>'
        )
    else:
        title_html = render.markup(title)
    items = "\n".join(
        f'        <li dir="rtl">{render.markup(step)}</li>' for step in steps
    )
    return (
        f'      <h1 class="title" dir="rtl">{title_html}</h1>\n'
        f'      <ol class="path">\n{items}\n      </ol>'
    )


def screenshot(html: str, html_path: Path, png_path: Path, w: int, h: int) -> None:
    html_path.parent.mkdir(parents=True, exist_ok=True)
    html_path.write_text(html, encoding="utf-8")
    chrome = render.find_chrome()
    with tempfile.TemporaryDirectory(prefix="single-post-", ignore_cleanup_errors=True) as tmp:
        session = render.ChromeSession(
            chrome, Path(tmp) / "chrome-user", width=w, height=h
        )
        try:
            session.start()
            session.screenshot(html_path, png_path)
            render.normalize_png(png_path, w, h)
        finally:
            session.close()
    print(f"wrote {png_path}", flush=True)


class VisibleText(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.parts: list[str] = []
        self.skip = 0

    def handle_starttag(self, tag, attrs):
        if tag in {"script", "style"}:
            self.skip += 1

    def handle_endtag(self, tag):
        if tag in {"script", "style"} and self.skip:
            self.skip -= 1

    def handle_data(self, data):
        if not self.skip:
            t = data.strip()
            if t and t != "”":
                self.parts.append(t)


def visible_text(path: Path) -> str:
    p = VisibleText()
    p.feed(path.read_text(encoding="utf-8"))
    return "\n".join(p.parts)


def rule_check(label: str, texts: list[str]) -> list[str]:
    payload = [{"title": label, "body": "\n".join(texts)}]
    return render.flag_rules(payload)



def inner_for(post: dict) -> str:
    kind = post["kind"]
    if kind == "quote":
        return quote_inner(post["quote"], post["lines"])
    if kind == "checklist":
        return checklist_inner(post["title"], post["items"])
    if kind == "path":
        return path_inner(post["title"], post["steps"])
    raise ValueError(kind)


def texts_for_rules(post: dict) -> list[str]:
    if post["kind"] == "quote":
        return [post["quote"], *post["lines"], render.BRAND.owner_name, render.BRAND.domain]
    if post["kind"] == "checklist":
        return [post["title"], *post["items"], render.BRAND.owner_name, render.BRAND.domain]
    return [post["title"], *post["steps"], render.BRAND.owner_name, render.BRAND.domain]


def load_posts(path: Path) -> list[dict]:
    data = json.loads(path.read_text(encoding="utf-8"))
    posts = data["posts"] if isinstance(data, dict) and "posts" in data else data
    root = path.parent
    for post in posts:
        if post.get("source"):
            src = Path(post["source"])
            post["source"] = src if src.is_absolute() else (root / src)
        out = Path(post["out"])
        post["out"] = out if out.is_absolute() else (root / out)
    return posts


def main() -> None:
    import argparse
    kit = Path(__file__).resolve().parent
    ap = argparse.ArgumentParser(description="Render single-image posts from a JSON spec")
    ap.add_argument("spec", nargs="?", default=str(kit / "templates_kit" / "specs" / "demo-single-posts.json"))
    args = ap.parse_args()
    posts = load_posts(Path(args.spec))
    all_flags: list[str] = []
    for post in posts:
        out: Path = post["out"]
        html_dir = out / "html"
        html_dir.mkdir(parents=True, exist_ok=True)
        print(f"==== {post['label']} ====")
        if post.get("source") and Path(post["source"]).exists():
            print("source:", post["source"])
            print("mtime: ", render.format_mtime(Path(post["source"])))
        flags = rule_check(post["label"], texts_for_rules(post))
        print(
            "rule check (copy):",
            flags
            or "no em/en dashes, no blocked terms, no downward pointer",
        )
        all_flags.extend(flags)
        inner = inner_for(post)
        for fmt, png_name, w, h in (
            ("feed", "image-1080x1350.png", 1080, 1350),
            ("story", "story-1080x1920.png", 1080, 1920),
        ):
            html = shell(post["kind"], fmt, inner, post["title_attr"])
            html_path = html_dir / f"{fmt}.html"
            png_path = out / png_name
            screenshot(html, html_path, png_path, w, h)
            vis = visible_text(html_path)
            vflags = rule_check(f"{post['label']} {fmt} visible", [vis])
            if vflags:
                print("VISIBLE FLAGS", vflags)
                all_flags.extend(vflags)
    print("==== ALL FLAGS ====")
    print(all_flags or "clean")


if __name__ == "__main__":
    main()
