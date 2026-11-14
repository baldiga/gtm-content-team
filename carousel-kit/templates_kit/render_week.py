#!/usr/bin/env python3
"""Render the pieces of one week from a JSON spec into a week folder.

Usage: python3 render_week.py specs/demo-week.json [--week ../../weeks/example] [--only LI-DEMO]
"""
from __future__ import annotations
import argparse, json, sys
from pathlib import Path
KIT = Path(__file__).resolve().parent
sys.path.insert(0, str(KIT))
import tk  # noqa: E402

CE = KIT.parent.parent


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("spec", nargs="?", default=str(KIT / "specs" / "demo-week.json"))
    ap.add_argument("--week", default="")
    ap.add_argument("--only", default="")
    a = ap.parse_args()
    spec_path = Path(a.spec)
    week_name = spec_path.stem.replace("week-", "")
    week = Path(a.week) if a.week else (CE / "weeks" / week_name)
    week.mkdir(parents=True, exist_ok=True)
    only = {x for x in a.only.split(",") if x}
    results = []
    payload = json.loads(spec_path.read_text(encoding="utf-8"))
    specs = payload if isinstance(payload, list) else payload.get("pieces") or payload.get("specs")
    for sp in specs:
        if only and sp.get("piece") not in only:
            continue
        m = tk.build(sp, week / sp["name"], sp.get("formats"))
        m["piece"] = sp.get("piece", sp["name"])
        results.append(m)
    for m in results:
        print(f"== {m['piece']} template {m['template']} -> {m['name']}")
        for f in m["files"]:
            print("   ", f)
        print("   rule check:", m["rule_errors"] or "clean", "| layout:", m["layout_flags"] or "clean")
        for w in m.get("rule_warnings", []):
            print("   warn:", w)


if __name__ == "__main__":
    main()
