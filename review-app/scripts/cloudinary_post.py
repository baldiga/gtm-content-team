#!/usr/bin/env python3
"""POST already-signed uploads to Cloudinary. Does not print secrets."""
from __future__ import annotations

import json
import sys
import urllib.error
import urllib.request
from pathlib import Path

# Use curl via subprocess for multipart, with no shell interpolation.


def post_one(cred: dict, local_path: Path) -> dict:
    import subprocess

    host = cred["host"]
    cloud = cred["cloud_name"]
    url = f"https://{host}/v1_1/{cloud}/image/upload"
    cmd = [
        "curl",
        "-sS",
        "-X",
        "POST",
        url,
        "-F",
        f"file=@{local_path}",
        "-F",
        f"api_key={cred['api_key']}",
        "-F",
        f"signature={cred['signature']}",
    ]
    for key, value in cred["upload_params"].items():
        if isinstance(value, bool):
            value = "true" if value else "false"
        cmd.extend(["-F", f"{key}={value}"])
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(f"curl failed for {local_path.name}: {result.stderr[-300:]}")
    try:
        data = json.loads(result.stdout)
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"non-JSON response for {local_path.name}: {result.stdout[:300]}") from exc
    if "error" in data:
        raise RuntimeError(f"cloudinary error for {local_path.name}: {data['error']}")
    return data


def main() -> None:
    if len(sys.argv) < 3:
        print("usage: cloudinary_post.py SIGNED.json MANIFEST.json [OUT.json]", file=sys.stderr)
        sys.exit(2)
    signed = json.loads(Path(sys.argv[1]).read_text())
    manifest = json.loads(Path(sys.argv[2]).read_text())
    out_path = Path(sys.argv[3]) if len(sys.argv) > 3 else Path("/tmp/cld-upload-out.json")

    by_public_id = {item["public_id"]: item for item in manifest["items"]}
    if not isinstance(signed, list):
        signed = [signed]

    existing = []
    if out_path.exists():
        try:
            existing = json.loads(out_path.read_text()).get("results", [])
        except Exception:
            existing = []
    done = {row["public_id"] for row in existing if "public_id" in row}

    results = list(existing)
    errors = []
    for cred in signed:
        public_id = cred["upload_params"]["public_id"]
        if public_id in done:
            print(f"skip {public_id}")
            continue
        item = by_public_id.get(public_id)
        if not item:
            errors.append({"public_id": public_id, "error": "not in manifest"})
            print(f"MISS {public_id}")
            continue
        local = Path(item["local_jpeg"])
        try:
            data = post_one(cred, local)
            row = {
                "id": item["id"],
                "piece": item["piece"],
                "used_by": item["used_by"],
                "kind": item["kind"],
                "label": item["label"],
                "name": item["name"],
                "folder": item["folder"],
                "public_id": data.get("public_id", public_id),
                "asset_id": data.get("asset_id"),
                "secure_url": data.get("secure_url"),
                "url": data.get("url"),
                "width": data.get("width"),
                "height": data.get("height"),
                "bytes": data.get("bytes"),
                "format": data.get("format"),
                "version": data.get("version"),
                "source": item["source"],
            }
            results.append(row)
            done.add(public_id)
            print(f"ok {public_id}")
            out_path.write_text(json.dumps({"results": results, "errors": errors}, ensure_ascii=False, indent=2) + "\n")
        except Exception as exc:
            errors.append({"public_id": public_id, "error": str(exc)})
            print(f"FAIL {public_id}")
            out_path.write_text(json.dumps({"results": results, "errors": errors}, ensure_ascii=False, indent=2) + "\n")

    print(f"done uploaded={len(results)} errors={len(errors)}")
    if errors:
        sys.exit(1)


if __name__ == "__main__":
    main()
