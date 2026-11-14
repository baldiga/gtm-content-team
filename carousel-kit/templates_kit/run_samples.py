#!/usr/bin/env python3
"""Render template samples into templates/samples/src/<run>/<name>/ and copy
deliverables (png/gif/mp4/pdf) into templates/samples/.

Usage: run_samples.py SPEC [--only name,...] [--run demo]
"""
import argparse, json, shutil, sys
from pathlib import Path
KIT = Path(__file__).resolve().parent
sys.path.insert(0, str(KIT))
import tk

ap = argparse.ArgumentParser()
ap.add_argument("spec", nargs="?", default=str(KIT / "specs" / "demo-week.json"))
ap.add_argument("--only", default="")
ap.add_argument("--run", default="demo")
a = ap.parse_args()
SAMPLES = KIT.parent.parent / "templates" / "samples"
only = {x for x in a.only.split(",") if x}
payload = json.loads(Path(a.spec).read_text(encoding="utf-8"))
specs = payload if isinstance(payload, list) else payload.get("pieces") or payload.get("specs")
for sp in specs:
    if only and sp["name"] not in only:
        continue
    out = SAMPLES / "src" / a.run / sp["name"]
    m = tk.build(sp, out, sp.get("formats"))
    print(f"== t{m['template']} {sp['name']}")
    for f in m["files"]:
        f = Path(f)
        dst = SAMPLES / (f.name if f.suffix != ".pdf" else f"{sp['name']}-carousel.pdf")
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy(f, dst)
        print("   ", dst.name, f"{dst.stat().st_size // 1024} KB")
    print("   rule:", m["rule_errors"] or "clean", "| layout:", m["layout_flags"] or "clean", "| warn:", m["rule_warnings"])
