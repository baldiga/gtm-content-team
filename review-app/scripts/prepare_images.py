#!/usr/bin/env python3
"""Resize source images to ~1080px-wide JPEGs for Cloudinary and the review app.

  python3 scripts/prepare_images.py MANIFEST.json

Each manifest item needs:
  source, piece, name, kind, label, used_by (list of piece codes)

Optional top-level keys: week, out_dir, folder (Cloudinary folder prefix).
Defaults come from WEEK, CLOUDINARY_FOLDER and the prepared/ directory.
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parent.parent
MAX_WIDTH = 1080
JPEG_QUALITY = 85


def to_jpeg(src: Path, dest: Path) -> tuple[int, int, int]:
    im = Image.open(src)
    if im.mode in ("RGBA", "P"):
        im = im.convert("RGB")
    elif im.mode != "RGB":
        im = im.convert("RGB")
    w, h = im.size
    if w > MAX_WIDTH:
        h = round(h * (MAX_WIDTH / w))
        w = MAX_WIDTH
        im = im.resize((w, h), Image.Resampling.LANCZOS)
    dest.parent.mkdir(parents=True, exist_ok=True)
    im.save(dest, "JPEG", quality=JPEG_QUALITY, optimize=True, progressive=True)
    return w, h, dest.stat().st_size


def main() -> None:
    if len(sys.argv) < 2:
        print("usage: prepare_images.py MANIFEST.json", file=sys.stderr)
        sys.exit(2)
    manifest = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
    week = manifest.get("week") or os.environ.get("WEEK") or "example-week"
    out_dir = Path(manifest["out_dir"]) if manifest.get("out_dir") else ROOT / "prepared"
    folder_root = manifest.get("folder") or os.environ.get("CLOUDINARY_FOLDER") or "content-review"
    out_dir.mkdir(parents=True, exist_ok=True)
    items = []
    missing = []
    for row in manifest.get("items", []):
        src = Path(row["source"])
        if not src.is_absolute():
            src = Path(sys.argv[1]).resolve().parent / src
        piece = row["piece"]
        name = row["name"]
        kind = row.get("kind") or "image"
        label = row.get("label") or name
        used_by = row.get("used_by") or [piece]
        if not src.exists():
            missing.append(str(src))
            continue
        dest = out_dir / piece / f"{name}.jpg"
        w, h, size = to_jpeg(src, dest)
        folder = f"{folder_root}/{week}/{piece}"
        public_id = f"{folder}/{name}"
        items.append(
            {
                "id": f"{piece}-{name}",
                "piece": piece,
                "used_by": used_by,
                "kind": kind,
                "label": label,
                "name": name,
                "folder": folder,
                "public_id": public_id,
                "local_jpeg": str(dest),
                "source": str(src),
                "width": w,
                "height": h,
                "bytes": size,
                "format": "jpg",
            }
        )
        print(f"ok {dest.relative_to(out_dir)} {w}x{h} {size}B")
    manifest_path = out_dir / "manifest.json"
    manifest_path.write_text(
        json.dumps({"week": week, "items": items, "missing": missing}, ensure_ascii=False, indent=2) + "\n"
    )
    print(f"wrote {len(items)} images, missing={len(missing)} -> {manifest_path}")
    if missing:
        for m in missing:
            print("MISSING", m)
        sys.exit(1)


if __name__ == "__main__":
    main()
