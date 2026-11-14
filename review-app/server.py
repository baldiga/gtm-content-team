#!/usr/bin/env python3
"""Local review-app server: static frontend + pluggable local JSON store.

Not a production host. Serves public/ and persists comments to data/state.json.
"""
from __future__ import annotations

import json
import os
import posixpath
import re
import secrets
import sys
import tempfile
import uuid
from datetime import datetime
from http import HTTPStatus
from http.cookies import SimpleCookie
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, unquote, urlparse
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parent
PUBLIC = ROOT / "public"
DATA = ROOT / "data"
STATE_PATH = DATA / "state.json"
IMAGES_DIR = DATA / "images"
CATALOG_PATH = ROOT / "lib" / "catalog.json"
CATALOG_PATH_FALLBACK = PUBLIC / "data" / "catalog.json"
ENV_PATH = ROOT / ".env.local"

STATUS_HE = {
    "pending": "ממתין לאישור",
    "changes": "ביקשת שינויים",
    "approved": "מאושר",
    "archived": "הוסר מהשבוע",
}

ARCHIVE_REASONS = {
    "cut": "נגזר",
    "idea-bank": "עבר לבנק רעיונות",
}

PUBLIC_UNAUTH = {
    "/",
    "/index.html",
    "/styles.css",
    "/app.js",
    "/config.json",
    "/robots.txt",
    "/stores/local.js",
    "/stores/README.md",
    "/favicon.ico",
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


ENV = load_env()
ACCESS_KEY = ENV.get("ACCESS_KEY", "")
TEAM_API_KEY = ENV.get("TEAM_API_KEY", "")
PORT = int(ENV.get("PORT") or 8787)
OWNER_ID = ENV.get("OWNER_ID") or "owner"
OWNER_LABEL = ENV.get("OWNER_LABEL") or "את/ה"
TEAM_LABEL = ENV.get("TEAM_LABEL") or "הצוות"
TIMEZONE_NAME = ENV.get("TIMEZONE") or "Asia/Jerusalem"
TZ = ZoneInfo(TIMEZONE_NAME)


def now_iso() -> str:
    return datetime.now(TZ).isoformat(timespec="seconds")


def safe_equal(a: str, b: str) -> bool:
    if not a or not b:
        return False
    # secrets.compare_digest requires same type and does not throw on length mismatch in 3.13? it does if lengths differ.
    ba = a.encode()
    bb = b.encode()
    if len(ba) != len(bb):
        secrets.compare_digest(ba, ba)
        return False
    return secrets.compare_digest(ba, bb)


def load_json(path: Path, default):
    if not path.exists():
        return default
    return json.loads(path.read_text())


def atomic_write(path: Path, data) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=str(path.parent), prefix=".tmp-")
    try:
        with os.fdopen(fd, "w") as fh:
            json.dump(data, fh, ensure_ascii=False, indent=2)
            fh.write("\n")
        os.replace(tmp, path)
    except Exception:
        try:
            os.unlink(tmp)
        except OSError:
            pass
        raise


def load_catalog() -> dict:
    path = CATALOG_PATH if CATALOG_PATH.exists() else CATALOG_PATH_FALLBACK
    return load_json(path, {"pieces": [], "title": "תוכן לאישור"})


def load_state() -> dict:
    state = load_json(STATE_PATH, {"updated": now_iso(), "pieces": {}})
    state.setdefault("pieces", {})
    return state


def save_state(state: dict) -> None:
    state["updated"] = now_iso()
    atomic_write(STATE_PATH, state)


def merge(catalog: dict, state: dict) -> dict:
    out_pieces = []
    for piece in catalog.get("pieces", []):
        overlay = state.get("pieces", {}).get(piece["code"], {})
        merged = dict(piece)
        status = overlay.get("status") or "pending"
        merged["status"] = status
        merged["status_he"] = overlay.get("status_he") or STATUS_HE.get(status, status)
        merged["version"] = overlay.get("version") or piece.get("version") or "v1"
        if overlay.get("body") is not None:
            merged["body"] = overlay["body"]
            merged["chars"] = len(overlay["body"])
        if overlay.get("first_comment") is not None:
            merged["first_comment"] = overlay["first_comment"]
        if overlay.get("images") is not None:
            merged["images"] = overlay["images"]
            merged["image_pending"] = len(overlay["images"]) == 0
        merged["comments"] = overlay.get("comments") or []
        if overlay.get("archive_reason"):
            merged["archive_reason"] = overlay["archive_reason"]
            merged["archive_reason_he"] = overlay.get("archive_reason_he") or ARCHIVE_REASONS.get(
                overlay["archive_reason"], overlay["archive_reason"]
            )
        out_pieces.append(merged)
    return {
        "title": catalog.get("title"),
        "week": catalog.get("week"),
        "week_label": catalog.get("week_label"),
        "updated": state.get("updated") or catalog.get("updated"),
        "timezone": TIMEZONE_NAME,
        "owner_id": OWNER_ID,
        "owner_label": OWNER_LABEL,
        "pieces": out_pieces,
    }


def add_comment(state: dict, code: str, author: str, text: str, typ: str, version: str | None = None) -> None:
    piece = state.setdefault("pieces", {}).setdefault(code, {})
    comments = list(piece.get("comments") or [])
    comments.append(
        {
            "id": uuid.uuid4().hex[:12],
            "at": now_iso(),
            "author": author,
            "author_he": OWNER_LABEL if author == OWNER_ID else TEAM_LABEL,
            "text": text,
            "type": typ,
            "version": version or piece.get("version"),
        }
    )
    piece["comments"] = comments


def set_status(state: dict, code: str, status: str) -> None:
    piece = state.setdefault("pieces", {}).setdefault(code, {})
    piece["status"] = status
    piece["status_he"] = STATUS_HE[status]


def catalog_codes(catalog: dict) -> list[str]:
    return [p["code"] for p in catalog.get("pieces", [])]


class Handler(BaseHTTPRequestHandler):
    server_version = "ContentReview/1.0"

    def log_message(self, fmt, *args):
        sys.stderr.write("%s - %s\n" % (self.address_string(), fmt % args))

    def _token_from_request(self) -> str:
        parsed = urlparse(self.path)
        qs = parse_qs(parsed.query)
        if qs.get("k"):
            return qs["k"][0]
        cookie = SimpleCookie()
        if "Cookie" in self.headers:
            cookie.load(self.headers.get("Cookie") or "")
        if "review_key" in cookie:
            return cookie["review_key"].value
        for header in ("X-Access-Key", "X-Team-Key"):
            if self.headers.get(header):
                return self.headers.get(header)
        auth = self.headers.get("Authorization") or ""
        if auth.lower().startswith("bearer "):
            return auth[7:].strip()
        return ""

    def _authorized(self, token: str) -> bool:
        return safe_equal(token, ACCESS_KEY) or safe_equal(token, TEAM_API_KEY)

    def _is_team(self, token: str) -> bool:
        return safe_equal(token, TEAM_API_KEY) or safe_equal(token, ACCESS_KEY)

    def _set_common(self, status: int, content_type: str, extra: list[tuple[str, str]] | None = None, set_cookie: str | None = None):
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("X-Robots-Tag", "noindex, nofollow")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Referrer-Policy", "no-referrer")
        self.send_header("Cache-Control", "no-store")
        if set_cookie:
            self.send_header("Set-Cookie", set_cookie)
        if extra:
            for k, v in extra:
                self.send_header(k, v)
        self.end_headers()

    def _cookie_for(self, token: str) -> str | None:
        if not (ACCESS_KEY and safe_equal(token, ACCESS_KEY)):
            return None
        return f"review_key={token}; Path=/; HttpOnly; SameSite=Lax; Max-Age=31536000"

    def _json(self, status: int, payload: dict, token: str = ""):
        raw = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self._set_common(status, "application/json; charset=utf-8", set_cookie=self._cookie_for(token) if token else None)
        self.wfile.write(raw)

    def _deny(self, api: bool):
        if api:
            self._json(HTTPStatus.UNAUTHORIZED, {"error": "unauthorized"})
        else:
            self._set_common(HTTPStatus.UNAUTHORIZED, "text/plain; charset=utf-8")
            self.wfile.write("unauthorized\n".encode())

    def _read_json(self) -> dict:
        length = int(self.headers.get("Content-Length") or 0)
        if length == 0:
            return {}
        raw = self.rfile.read(length)
        if not raw:
            return {}
        return json.loads(raw.decode("utf-8"))

    def do_GET(self):
        parsed = urlparse(self.path)
        path = unquote(parsed.path)
        token = self._token_from_request()
        authorized = self._authorized(token)
        api = path.startswith("/api/")

        if path in ("/api/state", "/api/feedback"):
            if not authorized:
                return self._deny(True)
            self._json(200, merge(load_catalog(), load_state()), token=token)
            return

        if path.startswith("/api/media/"):
            if not authorized:
                return self._deny(True)
            name = path.split("/api/media/", 1)[1]
            name = posixpath.basename(name)
            file_path = IMAGES_DIR / name
            if not file_path.exists() or not file_path.resolve().is_relative_to(IMAGES_DIR.resolve()):
                self._json(404, {"error": "not found"})
                return
            data = file_path.read_bytes()
            ctype = "image/jpeg" if name.lower().endswith((".jpg", ".jpeg")) else "application/octet-stream"
            self._set_common(200, ctype, extra=[("Content-Length", str(len(data)))], set_cookie=self._cookie_for(token))
            self.wfile.write(data)
            return

        if path.startswith("/data/") and not authorized:
            return self._deny(False)

        # static
        if path == "/":
            rel = "index.html"
        else:
            rel = path.lstrip("/")
        target = (PUBLIC / rel).resolve()
        if not str(target).startswith(str(PUBLIC.resolve())) or not target.is_file():
            self._set_common(404, "text/plain; charset=utf-8")
            self.wfile.write(b"not found\n")
            return
        if path not in PUBLIC_UNAUTH and not path.startswith("/stores/") and not authorized:
            # Protect catalog and anything unexpected
            if path.startswith("/data/"):
                return self._deny(False)
        ctype = {
            ".html": "text/html; charset=utf-8",
            ".css": "text/css; charset=utf-8",
            ".js": "text/javascript; charset=utf-8",
            ".json": "application/json; charset=utf-8",
            ".txt": "text/plain; charset=utf-8",
            ".svg": "image/svg+xml",
            ".png": "image/png",
            ".jpg": "image/jpeg",
            ".jpeg": "image/jpeg",
        }.get(target.suffix, "application/octet-stream")
        data = target.read_bytes()
        cookie = self._cookie_for(token) if authorized else None
        extra = [("Content-Length", str(len(data)))]
        if path == "/robots.txt":
            extra.append(("Cache-Control", "no-store"))
        self._set_common(200, ctype, extra=extra, set_cookie=cookie)
        self.wfile.write(data)

    def do_POST(self):
        parsed = urlparse(self.path)
        path = unquote(parsed.path)
        token = self._token_from_request()
        if not self._authorized(token):
            return self._deny(True)
        if path == "/api/action":
            return self._action(token)
        if path == "/api/team":
            if not self._is_team(token):
                return self._deny(True)
            return self._team(token)
        self._json(404, {"error": "not found"})

    def _action(self, token: str):
        body = self._read_json()
        typ = body.get("type")
        code = body.get("code")
        text = (body.get("text") or "").strip()
        catalog = load_catalog()
        codes = catalog_codes(catalog)
        state = load_state()
        if typ == "approve_all":
            for c in codes:
                current = (state.get("pieces") or {}).get(c, {}).get("status")
                if current not in ("approved", "archived"):
                    set_status(state, c, "approved")
                    add_comment(state, c, OWNER_ID, "אושר הכל", "approve", (state["pieces"][c].get("version")))
            save_state(state)
            return self._json(200, merge(catalog, state), token=token)
        if code not in codes:
            return self._json(400, {"error": "unknown piece"})
        if typ == "comment":
            if not text:
                return self._json(400, {"error": "empty comment"})
            add_comment(state, code, OWNER_ID, text, "comment")
        elif typ == "approve":
            set_status(state, code, "approved")
            add_comment(state, code, OWNER_ID, text or "אושר", "approve")
        elif typ == "changes":
            if not text:
                return self._json(400, {"error": "empty comment"})
            set_status(state, code, "changes")
            add_comment(state, code, OWNER_ID, text, "request_changes")
        else:
            return self._json(400, {"error": "unknown action"})
        save_state(state)
        return self._json(200, merge(catalog, state), token=token)

    def _team(self, token: str):
        body = self._read_json()
        action = body.get("action")
        code = body.get("code")
        catalog = load_catalog()
        codes = catalog_codes(catalog)
        if code not in codes:
            return self._json(400, {"error": "unknown piece"})
        state = load_state()
        piece = state.setdefault("pieces", {}).setdefault(code, {})
        if action == "reply":
            text = (body.get("text") or "").strip()
            if not text:
                return self._json(400, {"error": "empty comment"})
            add_comment(state, code, "team", text, "reply", body.get("version") or piece.get("version"))
        elif action == "version":
            version = (body.get("version") or "").strip()
            if not version:
                return self._json(400, {"error": "missing version"})
            piece["version"] = version
            if body.get("body") is not None:
                piece["body"] = body["body"]
            if body.get("first_comment") is not None:
                piece["first_comment"] = body["first_comment"]
            if body.get("images") is not None:
                piece["images"] = body["images"]
                piece["image_pending"] = len(body["images"]) == 0
            note = (body.get("note") or body.get("text") or f"עודכן ל{version}").strip()
            # After a team revision, send it back to pending review
            if piece.get("status") != "approved":
                set_status(state, code, "pending")
            add_comment(state, code, "team", note, "version", version)
        elif action == "images":
            images = body.get("images")
            if not isinstance(images, list):
                return self._json(400, {"error": "images must be a list"})
            existing = list(piece.get("images") or [])
            # If the overlay is empty, start from catalog images
            if not existing:
                cat_piece = next((p for p in catalog["pieces"] if p["code"] == code), {})
                existing = list(cat_piece.get("images") or [])
            mode = body.get("mode") or "replace"
            if mode == "append":
                piece["images"] = existing + images
            else:
                piece["images"] = images
            piece["image_pending"] = len(piece["images"]) == 0
            note = (body.get("note") or body.get("text") or "עודכנו תמונות").strip()
            add_comment(state, code, "team", note, "images", piece.get("version"))
            if piece.get("status") != "approved":
                set_status(state, code, "pending")
        elif action == "body":
            if body.get("body") is None:
                return self._json(400, {"error": "missing body"})
            piece["body"] = body["body"]
            if body.get("first_comment") is not None:
                piece["first_comment"] = body["first_comment"]
            if body.get("version"):
                piece["version"] = body["version"]
            add_comment(state, code, "team", body.get("note") or body.get("text") or "עודכן הטקסט", "version", piece.get("version"))
            if piece.get("status") not in ("approved", "archived"):
                set_status(state, code, "pending")
        elif action == "archive":
            reason = (body.get("reason") or "").strip()
            if reason not in ARCHIVE_REASONS:
                return self._json(400, {"error": "reason must be cut or idea-bank"})
            set_status(state, code, "archived")
            piece["archive_reason"] = reason
            piece["archive_reason_he"] = ARCHIVE_REASONS[reason]
            fallback = "הועבר לבנק רעיונות" if reason == "idea-bank" else "הוסר מהשבוע (נגזר)"
            note = (body.get("note") or body.get("text") or fallback).strip()
            add_comment(state, code, "team", note, "archive", piece.get("version"))
        else:
            return self._json(400, {"error": "unknown action"})
        save_state(state)
        return self._json(200, merge(catalog, state), token=token)

    def do_OPTIONS(self):
        self._set_common(204, "text/plain")


def main() -> None:
    if not ACCESS_KEY:
        print("ACCESS_KEY is missing. Put it in .env.local", file=sys.stderr)
        sys.exit(1)
    DATA.mkdir(parents=True, exist_ok=True)
    IMAGES_DIR.mkdir(parents=True, exist_ok=True)
    addr = ("127.0.0.1", PORT)
    httpd = ThreadingHTTPServer(addr, Handler)
    print(f"Review app listening on http://127.0.0.1:{PORT}")
    print("Open it with the access key from .env.local as ?k=...")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nbye")
        httpd.server_close()


if __name__ == "__main__":
    main()
