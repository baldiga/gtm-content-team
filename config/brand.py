"""Load brand settings from config/brand.json, brand.example.json, and env vars.

Copy brand.example.json to brand.json and fill in your name, domain, colors and handles.
brand.json is gitignored. Never put secrets here; secrets live in environment variables.
"""
from __future__ import annotations

import json
import os
import re
from dataclasses import dataclass, field
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
EXAMPLE = Path(__file__).resolve().parent / "brand.example.json"
LOCAL = Path(__file__).resolve().parent / "brand.json"


@dataclass
class Brand:
    owner_name: str = "Your Name"
    owner_id: str = "owner"
    owner_label: str = "את/ה"
    team_label: str = "הצוות"
    domain: str = "yourdomain.com"
    headline: str = "Your Title"
    initials: str = "YN"
    timezone: str = "Asia/Jerusalem"
    cloudinary_folder: str = "content-review"
    blob_prefix: str = "content-review"
    avatar_path: str = ""
    cta_path: str = ""
    colors: dict = field(default_factory=dict)
    handles: dict = field(default_factory=dict)
    blocked_terms: list = field(default_factory=list)
    latin_allowlist: list = field(default_factory=list)

    @property
    def avatar(self) -> Path | None:
        if not self.avatar_path:
            return None
        p = Path(self.avatar_path)
        if not p.is_absolute():
            p = ROOT / p
        return p


def _read_json(path: Path) -> dict:
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


_DEFAULTS = {
    "colors": {
        "paper": "#F3EFE7",
        "ink": "#1C1916",
        "ink_soft": "#5E584F",
        "accent": "#B4451A",
        "panel": "#E7E1D6",
        "review_accent": "#0F3D3E",
    },
    "handles": {
        "linkedin": "",
        "instagram": "",
        "x": "",
        "facebook": "",
    },
    "latin_allowlist": [
        "POV", "KPI", "CV", "SQL", "MQL", "GTM", "AE", "BDR", "SDR",
        "ICP", "CRM", "CRO", "CMO", "CEO", "AI", "RevOps", "Engineer",
        "Engineers", "Operations", "Sales", "PDF", "B2B",
    ],
}


def _name_tokens(name: str) -> list[str]:
    return [p for p in re.split(r"[^A-Za-z]+", name or "") if p]


def load_brand() -> Brand:
    data: dict = {
        "colors": dict(_DEFAULTS["colors"]),
        "handles": dict(_DEFAULTS["handles"]),
        "latin_allowlist": list(_DEFAULTS["latin_allowlist"]),
    }
    for path in (EXAMPLE, LOCAL):
        incoming = _read_json(path)
        if not incoming:
            continue
        for key, value in incoming.items():
            if key in ("colors", "handles") and isinstance(value, dict):
                data.setdefault(key, {}).update(value)
            elif key == "latin_allowlist" and isinstance(value, list):
                data["latin_allowlist"] = list(dict.fromkeys(data.get("latin_allowlist", []) + value))
            else:
                data[key] = value
    env_map = {
        "BRAND_NAME": "owner_name",
        "OWNER_NAME": "owner_name",
        "OWNER_ID": "owner_id",
        "OWNER_LABEL": "owner_label",
        "TEAM_LABEL": "team_label",
        "BRAND_DOMAIN": "domain",
        "BRAND_HEADLINE": "headline",
        "BRAND_INITIALS": "initials",
        "TIMEZONE": "timezone",
        "CLOUDINARY_FOLDER": "cloudinary_folder",
        "BLOB_PREFIX": "blob_prefix",
        "BRAND_AVATAR": "avatar_path",
        "CTA_PATH": "cta_path",
    }
    for env_key, field_name in env_map.items():
        val = os.environ.get(env_key)
        if val:
            data[field_name] = val
    allowed = set(Brand.__dataclass_fields__)
    brand = Brand(**{k: v for k, v in data.items() if k in allowed})
    extras = _name_tokens(brand.owner_name)
    if brand.initials:
        extras.append(brand.initials)
    if brand.domain:
        extras.append(brand.domain)
    brand.latin_allowlist = list(dict.fromkeys(list(brand.latin_allowlist) + extras))
    return brand
