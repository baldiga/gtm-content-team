#!/usr/bin/env python3
"""Exercise the local server and sync.py against the sample catalog. Never prints secrets."""
from __future__ import annotations

import json
import os
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
ENV_PATH = ROOT / ".env.local"
STATE_PATH = ROOT / "data" / "state.json"


def load_env() -> dict[str, str]:
    env = dict(os.environ)
    if ENV_PATH.exists():
        for line in ENV_PATH.read_text().splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            k, v = line.split("=", 1)
            env.setdefault(k.strip(), v.strip())
    return env


def http(url: str, method="GET", headers=None, payload=None, timeout=8):
    body = None
    hdrs = dict(headers or {})
    if payload is not None:
        body = json.dumps(payload).encode()
        hdrs["Content-Type"] = "application/json"
    req = urllib.request.Request(url, data=body, headers=hdrs, method=method)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as res:
            raw = res.read()
            ctype = res.headers.get("Content-Type", "")
            data = json.loads(raw) if "json" in ctype or raw.startswith(b"{") else raw
            return res.status, dict(res.headers), data
    except urllib.error.HTTPError as exc:
        raw = exc.read()
        try:
            data = json.loads(raw)
        except Exception:
            data = raw
        return exc.code, dict(exc.headers), data


def fail(msg: str) -> None:
    print("FAIL", msg)
    sys.exit(1)


def main() -> None:
    env = load_env()
    key = env.get("ACCESS_KEY") or ""
    team = env.get("TEAM_API_KEY") or ""
    if not key or not team:
        fail("ACCESS_KEY and TEAM_API_KEY must be set in the environment or .env.local")
    port = env.get("PORT") or "8787"
    base = f"http://127.0.0.1:{port}"
    if STATE_PATH.exists():
        STATE_PATH.unlink()

    proc = subprocess.Popen(
        [sys.executable, str(ROOT / "server.py")],
        cwd=str(ROOT),
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        env={**os.environ, **{k: env[k] for k in ("ACCESS_KEY", "TEAM_API_KEY", "PORT", "OWNER_ID", "OWNER_LABEL", "TEAM_LABEL", "TIMEZONE") if k in env}},
    )
    try:
        for _ in range(40):
            try:
                http(f"{base}/robots.txt")
                break
            except Exception:
                time.sleep(0.1)
        else:
            fail("server did not start")

        status, _, _ = http(f"{base}/api/state")
        if status != 401:
            fail(f"unauthenticated /api/state should be 401, got {status}")

        headers = {"X-Team-Key": team, "Authorization": f"Bearer {team}"}
        status, _, data = http(f"{base}/api/feedback", headers=headers)
        if status != 200:
            fail(f"team feedback got {status}")
        if not data.get("pieces"):
            fail("catalog has no pieces")
        if data.get("owner_id") not in (env.get("OWNER_ID") or "owner",):
            fail("owner_id missing from state")
        code = data["pieces"][0]["code"]

        status, _, data = http(
            f"{base}/api/team",
            method="POST",
            headers=headers,
            payload={"action": "reply", "code": code, "text": "בדיקת צוות"},
        )
        if status != 200:
            fail(f"team reply got {status}: {data}")

        owner_headers = {"X-Access-Key": key}
        status, _, data = http(
            f"{base}/api/action",
            method="POST",
            headers=owner_headers,
            payload={"type": "comment", "code": code, "text": "הערה לדוגמה"},
        )
        if status != 200:
            fail(f"owner comment got {status}: {data}")

        print(f"ok pieces={len(data.get('pieces') or [])} api_ok=yes local_server=yes")
    finally:
        proc.terminate()
        try:
            proc.wait(timeout=5)
        except Exception:
            proc.kill()
        if STATE_PATH.exists():
            STATE_PATH.unlink()


if __name__ == "__main__":
    main()
