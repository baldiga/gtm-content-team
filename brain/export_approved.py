#!/usr/bin/env python3
"""Write the approved-examples library for a week from the live review state + Cloudinary URL file.

  python3 export_approved.py YYYY-MM-DD [--notes notes-YYYY-MM-DD.json]

Uses raw/latest.json (run `brain.py pull` first). Only pieces whose live status is "approved" are written.
"""
import json, sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
from config.brand import load_brand

BRAND = load_brand()
OWNER_ID = BRAND.owner_id
week = sys.argv[1]
notes_path = HERE / "approved-examples" / f"notes-{week}.json"
notes = json.loads(notes_path.read_text()) if notes_path.exists() else {}
live = json.loads((HERE / "raw" / "latest.json").read_text())
urls_path = HERE.parent / "review" / f"cloudinary-urls-{week}.json"
urls = json.loads(urls_path.read_text()) if urls_path.exists() else {"by_piece": {}}
out = HERE / "approved-examples" / week
out.mkdir(parents=True, exist_ok=True)
rows = []
for p in live["pieces"]:
    if p.get("status") != "approved":
        continue
    code = p["code"]
    approvals = [c for c in p.get("comments") or [] if c.get("author") == OWNER_ID and c.get("type") == "approve"]
    cur = [a for a in urls["by_piece"].get(code, []) if a.get("current")]
    n = notes.get(code, {})
    lines = [
        f"# {code} · {p['platform_he']} · {p['day_he']} {p['date_he']} · {p['version']} · approved",
        "",
        f"- Platform: {p['platform']} ({p.get('account')})",
        f"- Day: {p['day']} {p['date']}",
        f"- Version approved: {p['version']}" + (f" (owner approved {approvals[-1]['at']})" if approvals else ""),
        f"- Topic: {n.get('topic', p.get('title'))}",
        f"- Audience: {n.get('audience', '')}",
        f"- Length: {p.get('chars')} chars" + (f" (limit {p.get('char_limit')})" if p.get('char_limit') else ""),
        f"- Link handling: {p.get('link')}",
        f"- Sibling pieces: {', '.join(n.get('siblings', []))}",
        "",
        "## Why it worked",
        "",
        n.get("why", ""),
        "",
        f"Lessons it embodies: {', '.join(n.get('lessons', []))}",
        "",
        "## Final approved copy (verbatim)",
        "",
        "```text",
        p["body"],
        "```",
        "",
    ]
    if p.get("first_comment"):
        lines += ["## First comment / first reply", "", "```text", p["first_comment"], "```", ""]
    lines += ["## Current visuals", ""]
    for a in cur:
        lines.append(f"- {a.get('label', a.get('kind'))} ({a.get('kind')}): {a['secure_url']}")
    (out / f"{code}.md").write_text("\n".join(lines) + "\n")
    rows.append((p["date"], code, p["platform_he"], p["version"], n.get("topic", p.get("title")), p.get("chars")))
rows.sort()
idx = [f"## Week {week}", "", "| Date | Piece | Platform | Version | Topic | Chars |", "|---|---|---|---|---|---|"]
idx += [f"| {d} | [{c}]({week}/{c}.md) | {pl} | {v} | {t} | {ch} |" for d, c, pl, v, t, ch in rows]
(out / "_index.md").write_text("\n".join(idx) + "\n")
print(f"wrote {len(rows)} approved examples to {out}")
