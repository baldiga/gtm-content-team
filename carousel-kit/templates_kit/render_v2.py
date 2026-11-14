#!/usr/bin/env python3
"""Render pieces from a week spec into week folders. Usage: render_v2.py SPEC [--week DIR] [--only LI-01,X-01]"""
import argparse, json, sys
from pathlib import Path
KIT = Path(__file__).resolve().parent
sys.path.insert(0, str(KIT))
import tk

ap = argparse.ArgumentParser()
ap.add_argument("spec")
ap.add_argument("--week", default="")
ap.add_argument("--only", default="")
a = ap.parse_args()
spec_path = Path(a.spec)
week = Path(a.week) if a.week else (KIT.parent.parent / "weeks" / "outputs")
week.mkdir(parents=True, exist_ok=True)
only = {x for x in a.only.split(",") if x}
for sp in json.loads(spec_path.read_text(encoding="utf-8")):
    if only and sp.get("piece") not in only:
        continue
    out = week / sp["name"]
    m = tk.build(sp, out, sp.get("formats"))
    print(f"== {sp.get('piece', sp['name'])} t{m['template']} -> {out}")
    for f in m["files"]:
        print("   ", f)
    print("   rule:", m["rule_errors"] or "clean", "| layout:", m["layout_flags"] or "clean", "| warn:", m["rule_warnings"])
