#!/usr/bin/env python3
"""Company brain: turns the owner's review comments into lasting lessons for the content agents.

Commands:
  python3 brain.py pull            # fetch feedback from the review app, capture new owner comments as draft lessons
  python3 brain.py drafts          # list lessons that still need a generalized rule
  python3 brain.py set L-012 --rule "..." --scope copy,topic [--platforms all] [--status active]
  python3 brain.py siblings LI-03  # pieces that must receive the same fix (same day, other platforms)
  python3 brain.py render          # rebuild lessons.md from lessons.json
  python3 brain.py check           # exit 1 if any captured comment has no rule yet (use as a gate)

Reuses review-app/sync.py for the API call (REVIEW_URL + TEAM_API_KEY from env or .env.local).
Never prints keys. Never writes to the review app: "captured" is tracked locally in captured.json.
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "review-app"))
import sync  # noqa: E402
from config.brand import load_brand  # noqa: E402

BRAND = load_brand()
OWNER_ID = BRAND.owner_id

LESSONS = HERE / "lessons.json"
CAPTURED = HERE / "captured.json"
MD = HERE / "lessons.md"
RAW_DIR = HERE / "raw"

PLATFORM_PREFIX = {"LI": "linkedin", "IG": "instagram", "X": "x", "FB": "facebook"}


def now() -> str:
    return datetime.now().astimezone().isoformat(timespec="seconds")


def load(path: Path, default):
    return json.loads(path.read_text()) if path.exists() else default


def save(path: Path, data) -> None:
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n")


def piece_num(code: str) -> str:
    return code.split("-", 1)[1] if "-" in code else code


def siblings(code: str, pieces: list[dict] | None = None) -> list[str]:
    """Same slot number on other platforms (LI-03 -> X-03, IG-03, FB-03)."""
    n = piece_num(code)
    if pieces is None:
        fb = load(RAW_DIR / "latest.json", {"pieces": []})
        pieces = fb.get("pieces", [])
    return [p["code"] for p in pieces if piece_num(p["code"]) == n and p["code"] != code]


def cmd_pull() -> None:
    env = sync.load_env()
    url, key = sync.require_config(env)
    data = sync.request(url, key, "/api/feedback")
    RAW_DIR.mkdir(exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    save(RAW_DIR / f"feedback-{stamp}.json", data)
    save(RAW_DIR / "latest.json", data)

    lessons = load(LESSONS, {"standing_rules": [], "lessons": []})
    captured = load(CAPTURED, {})
    next_id = 1 + max([int(l["id"].split("-")[1]) for l in lessons["lessons"]] or [0])
    new = 0
    for p in data.get("pieces", []):
        for c in p.get("comments") or []:
            if c.get("author") != OWNER_ID or c["id"] in captured:
                continue
            if c.get("type") in ("approve", "approve_all") or c.get("text", "").strip() in ("אושר", "אושר ✓"):
                # Plain approvals are not lessons; the piece goes to approved-examples instead.
                captured[c["id"]] = {"lesson": None, "kind": "approval", "piece": p["code"], "version": p.get("version"), "captured_at": now()}
                continue
            lid = f"L-{next_id:03d}"
            next_id += 1
            lessons["lessons"].append({
                "id": lid,
                "date": c.get("at", now())[:10],
                "week": data.get("week"),
                "source_piece": p["code"],
                "source_version": p.get("version"),
                "comment_id": c["id"],
                "comment_type": c.get("type"),
                "original_comment": c.get("text", ""),
                "rule": "",
                "scope": [],
                "platforms": "all",
                "apply_to": [p["code"]] + siblings(p["code"], data.get("pieces", [])),
                "status": "draft",
            })
            captured[c["id"]] = {"lesson": lid, "piece": p["code"], "captured_at": now()}
            new += 1
    save(LESSONS, lessons)
    save(CAPTURED, captured)
    render()
    print(f"pulled week={data.get('week')} new_comments={new} total_lessons={len(lessons['lessons'])}")
    if new:
        print("New draft lessons need a generalized rule: python3 brain.py drafts")


def cmd_drafts() -> None:
    for l in load(LESSONS, {"lessons": []})["lessons"]:
        if l["status"] == "draft" or not l["rule"]:
            print(f"{l['id']} {l['source_piece']} {l['source_version']}: {l['original_comment'][:160]!r}")


def cmd_set(args) -> None:
    data = load(LESSONS, {"standing_rules": [], "lessons": []})
    for l in data["lessons"]:
        if l["id"] == args.id:
            if args.rule:
                l["rule"] = args.rule
            if args.scope:
                l["scope"] = [s.strip() for s in args.scope.split(",")]
            if args.platforms:
                l["platforms"] = args.platforms
            if args.status:
                l["status"] = args.status
            elif l["status"] == "draft" and l["rule"]:
                l["status"] = "active"
            save(LESSONS, data)
            render()
            print(f"ok {l['id']} status={l['status']}")
            return
    print(f"no lesson {args.id}", file=sys.stderr)
    sys.exit(1)


def render() -> None:
    data = load(LESSONS, {"standing_rules": [], "lessons": []})
    out = [
        "# Company brain: lessons from the owner's reviews",
        "",
        "READ THIS BEFORE EVERY TASK (Content Writer, Carousel Designer, Publisher and Analyst).",
        "Every rule here came from a comment the owner already gave once. The owner must never need to repeat it.",
        "Apply each lesson to: (1) the piece it came from, (2) its sibling pieces on every other platform",
        "(same slot number: LI-03 -> X-03, IG-03, FB-03), (3) any similar piece this week, (4) every future week.",
        "Default scope is cross-platform unless the lesson says otherwise.",
        "",
        f"_Generated by brain.py from lessons.json, {now()}. Do not edit this file by hand; edit lessons.json or use `brain.py set`._",
        "",
        "## Standing rules",
        "",
    ]
    for r in data.get("standing_rules", []):
        out.append(f"- **{r['id']}** ({r.get('date','')}, {r.get('source','')}): {r['rule']}")
    out += ["", "## Lessons", ""]
    order = {"draft": 0, "active": 1, "superseded": 2, "retired": 3}
    for l in sorted(data["lessons"], key=lambda x: (order.get(x["status"], 9), x["id"])):
        out += [
            f"### {l['id']} · {l['status']} · {', '.join(l['scope']) or 'scope TBD'} · platforms: {l['platforms']}",
            "",
            f"- Source: {l['source_piece']} {l['source_version']} ({l['date']}, week {l.get('week')}, comment {l['comment_id']})",
            f"- Rule: {l['rule'] or '**NEEDS A GENERALIZED RULE**'}",
            f"- Apply now to: {', '.join(l.get('apply_to', []))}",
            "- Owner comment (verbatim):",
            "",
        ]
        out += ["  > " + line if line else "  >" for line in l["original_comment"].splitlines()]
        out.append("")
    MD.write_text("\n".join(out) + "\n")


def cmd_check() -> None:
    data = load(LESSONS, {"lessons": []})
    missing = [l["id"] for l in data["lessons"] if not l["rule"]]
    if missing:
        print("lessons without a rule: " + ", ".join(missing))
        sys.exit(1)
    print(f"ok {len(data['lessons'])} lessons, all have rules")


def main() -> None:
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("pull")
    sub.add_parser("drafts")
    sub.add_parser("render")
    sub.add_parser("check")
    s = sub.add_parser("siblings")
    s.add_argument("code")
    st = sub.add_parser("set")
    st.add_argument("id")
    st.add_argument("--rule")
    st.add_argument("--scope")
    st.add_argument("--platforms")
    st.add_argument("--status")
    a = ap.parse_args()
    if a.cmd == "pull":
        cmd_pull()
    elif a.cmd == "drafts":
        cmd_drafts()
    elif a.cmd == "render":
        render(); print(f"wrote {MD}")
    elif a.cmd == "check":
        cmd_check()
    elif a.cmd == "siblings":
        print(" ".join(siblings(a.code)))
    elif a.cmd == "set":
        cmd_set(a)


if __name__ == "__main__":
    main()
