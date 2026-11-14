#!/usr/bin/env python3
"""Talk to the review app from the box.

Examples:
  python3 sync.py pull
  python3 sync.py pull --out /tmp/feedback.json
  python3 sync.py status
  python3 sync.py reply LI-01 "תיקנו את הפסקה השנייה"
  python3 sync.py version LI-01 v2 --note "קוצר לפי ההערה" --body-file path.md
  python3 sync.py upload LI-01 path/to/image.jpg --kind feed
  python3 sync.py archive LI-04 --reason cut
  python3 sync.py archive LI-05 --reason idea-bank

Reads REVIEW_URL, TEAM_API_KEY, ACCESS_KEY from .env.local (or the environment).
Does not print those keys.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent
ENV_PATH = ROOT / ".env.local"

KIND_LABEL = {
    "feed": "תמונת פיד",
    "story": "סטורי",
    "slide": "שקף",
    "image": "תמונה",
}


def load_env() -> dict[str, str]:
    env = dict(os.environ)
    if ENV_PATH.exists():
        for line in ENV_PATH.read_text().splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, value = line.split("=", 1)
            env.setdefault(key.strip(), value.strip())
    return env


def require_config(env: dict[str, str]) -> tuple[str, str]:
    url = (env.get("REVIEW_URL") or "http://127.0.0.1:8787").rstrip("/")
    key = env.get("TEAM_API_KEY") or env.get("ACCESS_KEY") or ""
    if not key:
        print("Missing TEAM_API_KEY or ACCESS_KEY in .env.local", file=sys.stderr)
        sys.exit(2)
    return url, key


def request(url: str, key: str, path: str, method: str = "GET", payload: dict | None = None) -> dict:
    body = None
    headers = {"Accept": "application/json", "X-Team-Key": key, "Authorization": f"Bearer {key}"}
    if payload is not None:
        body = json.dumps(payload).encode("utf-8")
        headers["Content-Type"] = "application/json"
    req = urllib.request.Request(url + path, data=body, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=30) as res:
            raw = res.read().decode("utf-8")
            return json.loads(raw) if raw else {}
    except urllib.error.HTTPError as exc:
        err = exc.read().decode("utf-8", errors="replace")
        print(f"HTTP {exc.code} on {path}: {err[:400]}", file=sys.stderr)
        sys.exit(1)
    except urllib.error.URLError as exc:
        print(f"Could not reach {url}: {exc.reason}", file=sys.stderr)
        sys.exit(1)


def cmd_pull(url: str, key: str, out: str | None) -> None:
    data = request(url, key, "/api/feedback")
    text = json.dumps(data, ensure_ascii=False, indent=2) + "\n"
    if out:
        Path(out).write_text(text)
        print(f"wrote {out}")
    else:
        sys.stdout.write(text)


def cmd_status(url: str, key: str) -> None:
    data = request(url, key, "/api/feedback")
    for piece in data.get("pieces", []):
        n = len(piece.get("comments") or [])
        imgs = len(piece.get("images") or [])
        reason = piece.get("archive_reason") or ""
        extra = f"  reason={reason}" if reason else ""
        print(f"{piece['code']:6}  {piece.get('status_he', piece.get('status')):16}  v={piece.get('version')}  images={imgs}  comments={n}{extra}")



def cmd_archive(url: str, key: str, code: str, reason: str, note: str | None) -> None:
    payload = {"action": "archive", "code": code, "reason": reason}
    if note:
        payload["note"] = note
    data = request(url, key, "/api/team", "POST", payload)
    piece = next((p for p in data.get("pieces", []) if p["code"] == code), None)
    reason_he = (piece or {}).get("archive_reason_he") or reason
    print(f"ok {code} status={piece.get('status') if piece else '?'} reason={reason_he}")


def cmd_reply(url: str, key: str, code: str, text: str) -> None:
    data = request(url, key, "/api/team", "POST", {"action": "reply", "code": code, "text": text})
    piece = next((p for p in data.get("pieces", []) if p["code"] == code), None)
    print(f"ok {code} comments={len(piece.get('comments') or []) if piece else '?'}")


def cmd_version(args, url: str, key: str) -> None:
    payload = {"action": "version", "code": args.code, "version": args.version}
    if args.note:
        payload["note"] = args.note
    if args.body:
        payload["body"] = args.body
    if args.body_file:
        payload["body"] = Path(args.body_file).read_text().strip()
    if args.first_comment is not None:
        payload["first_comment"] = args.first_comment
    data = request(url, key, "/api/team", "POST", payload)
    piece = next((p for p in data.get("pieces", []) if p["code"] == args.code), None)
    print(f"ok {args.code} version={piece.get('version') if piece else args.version} status={piece.get('status') if piece else '?'}")


def to_jpeg(src: Path, dest: Path) -> tuple[int, int]:
    from PIL import Image

    im = Image.open(src)
    if im.mode != "RGB":
        im = im.convert("RGB")
    w, h = im.size
    if w > 1080:
        h = round(h * (1080 / w))
        w = 1080
        im = im.resize((w, h), Image.Resampling.LANCZOS)
    dest.parent.mkdir(parents=True, exist_ok=True)
    im.save(dest, "JPEG", quality=85, optimize=True, progressive=True)
    return w, h


def cloudinary_upload(env: dict[str, str], local: Path, public_id: str) -> dict | None:
    """Upload if Cloudinary credentials are present in the environment. Never prints secrets."""
    import hashlib
    import hmac
    import time
    from urllib.parse import urlparse

    cloud = env.get("CLOUDINARY_CLOUD_NAME") or ""
    api_key = env.get("CLOUDINARY_API_KEY") or ""
    secret = env.get("CLOUDINARY_API_SECRET") or ""
    url_env = env.get("CLOUDINARY_URL") or ""
    if url_env and (not cloud or not api_key or not secret):
        # Parse CLOUDINARY_URL when the split fields are not all set.
        parsed = urlparse(url_env)
        api_key = api_key or parsed.username or ""
        secret = secret or parsed.password or ""
        cloud = cloud or (parsed.hostname or "")
    if not (cloud and api_key and secret):
        return None

    ts = int(time.time())
    params = {"public_id": public_id, "overwrite": "true", "timestamp": str(ts), "unique_filename": "false"}
    to_sign = "&".join(f"{k}={params[k]}" for k in sorted(params)) + secret
    signature = hashlib.sha1(to_sign.encode()).hexdigest()
    # Use curl for multipart
    import subprocess

    endpoint = f"https://api.cloudinary.com/v1_1/{cloud}/image/upload"
    cmd = [
        "curl", "-sS", endpoint,
        "-F", f"file=@{local}",
        "-F", f"api_key={api_key}",
        "-F", f"signature={signature}",
        "-F", f"timestamp={ts}",
        "-F", f"public_id={public_id}",
        "-F", "overwrite=true",
        "-F", "unique_filename=false",
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"Cloudinary curl failed for {local.name}", file=sys.stderr)
        return None
    data = json.loads(result.stdout)
    if "error" in data:
        print(f"Cloudinary error for {local.name}: {data['error']}", file=sys.stderr)
        return None
    return data


def cmd_upload(args, url: str, key: str, env: dict[str, str]) -> None:
    week = env.get("WEEK") or "example-week"
    prepared = ROOT / "prepared" / args.code
    prepared.mkdir(parents=True, exist_ok=True)
    images = []
    staged = []
    uploaded = 0
    for index, raw in enumerate(args.files, start=1):
        src = Path(raw)
        if not src.exists():
            print(f"missing file: {src}", file=sys.stderr)
            sys.exit(1)
        kind = args.kind or "image"
        if kind == "slide":
            name = f"slide-{index:02d}"
            label = f"שקף {index}"
        elif kind == "story" and len(args.files) > 1:
            name = f"story-{index:02d}"
            label = f"סטורי {index}"
        elif kind == "story":
            name = "story"
            label = "סטורי"
        elif kind == "feed":
            name = "feed"
            label = "תמונת פיד"
        else:
            name = src.stem
            label = KIND_LABEL.get(kind, src.stem)
        dest = prepared / f"{name}.jpg"
        w, h = to_jpeg(src, dest)
        folder = env.get("CLOUDINARY_FOLDER") or "content-review"
        public_id = f"{folder}/{week}/{args.code}/{name}"
        cld = cloudinary_upload(env, dest, public_id)
        if cld and cld.get("secure_url"):
            src_url = cld["secure_url"]
            uploaded += 1
        else:
            src_url = f"/api/media/{args.code}-{name}.jpg"
            media_dest = ROOT / "data" / "images" / f"{args.code}-{name}.jpg"
            media_dest.parent.mkdir(parents=True, exist_ok=True)
            media_dest.write_bytes(dest.read_bytes())
            staged.append(str(dest))
        images.append(
            {
                "id": f"{args.code}-{name}",
                "kind": kind,
                "label": label,
                "name": name,
                "public_id": public_id,
                "src": src_url,
                "original": src_url,
                "width": w,
                "height": h,
            }
        )
    payload = {
        "action": "images",
        "code": args.code,
        "images": images,
        "mode": args.mode,
        "note": args.note or f"הועלו {len(images)} תמונות",
    }
    data = request(url, key, "/api/team", "POST", payload)
    piece = next((p for p in data.get("pieces", []) if p["code"] == args.code), None)
    print(f"ok {args.code} images={len(piece.get('images') or []) if piece else len(images)} cloudinary={uploaded} staged={len(staged)}")
    if staged and uploaded == 0:
        print("Cloudinary credentials were not set, so files were staged locally under prepared/ and data/images/. Re-run with CLOUDINARY_URL (or CLOUDINARY_API_KEY + SECRET + CLOUD_NAME) to host them on Cloudinary.")


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="Sync comments and images with the review app")
    sub = p.add_subparsers(dest="cmd", required=True)

    pull = sub.add_parser("pull", help="Download all feedback as JSON")
    pull.add_argument("--out", help="Write to this file instead of stdout")

    sub.add_parser("status", help="Print a one-line status per piece")

    reply = sub.add_parser("reply", help="Post a team reply on a piece")
    reply.add_argument("code")
    reply.add_argument("text")

    ver = sub.add_parser("version", help="Bump a piece version and optionally replace the copy")
    ver.add_argument("code")
    ver.add_argument("version")
    ver.add_argument("--note")
    ver.add_argument("--body")
    ver.add_argument("--body-file")
    ver.add_argument("--first-comment")

    arch = sub.add_parser("archive", help="Remove a piece from the live week (cut or idea bank)")
    arch.add_argument("code")
    arch.add_argument("--reason", choices=["cut", "idea-bank"], required=True)
    arch.add_argument("--note")

    up = sub.add_parser("upload", help="Prepare images and attach them to a piece")
    up.add_argument("code")
    up.add_argument("files", nargs="+")
    up.add_argument("--kind", choices=["feed", "story", "slide", "image"], default="image")
    up.add_argument("--mode", choices=["replace", "append"], default="replace")
    up.add_argument("--note")
    return p


def main() -> None:
    args = build_parser().parse_args()
    env = load_env()
    url, key = require_config(env)
    if args.cmd == "pull":
        cmd_pull(url, key, args.out)
    elif args.cmd == "status":
        cmd_status(url, key)
    elif args.cmd == "reply":
        cmd_reply(url, key, args.code, args.text)
    elif args.cmd == "version":
        cmd_version(args, url, key)
    elif args.cmd == "archive":
        cmd_archive(url, key, args.code, args.reason, args.note)
    elif args.cmd == "upload":
        cmd_upload(args, url, key, env)
    else:
        sys.exit(2)


if __name__ == "__main__":
    main()
