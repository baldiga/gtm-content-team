"""Neutral line icons (24x24, stroke). Drawn for this kit: no tool logos, no brand marks."""
P = {
    "target": '<circle cx="12" cy="12" r="9"/><circle cx="12" cy="12" r="5"/><circle cx="12" cy="12" r="1.4" fill="currentColor"/>',
    "list": '<path d="M9 6h11M9 12h11M9 18h11"/><circle cx="4.5" cy="6" r="1.2"/><circle cx="4.5" cy="12" r="1.2"/><circle cx="4.5" cy="18" r="1.2"/>',
    "user": '<circle cx="12" cy="8" r="4"/><path d="M4 21c1.2-4.2 4.3-6 8-6s6.8 1.8 8 6"/>',
    "users": '<circle cx="9" cy="8" r="3.4"/><path d="M2.5 20c1-3.6 3.6-5.2 6.5-5.2s5.5 1.6 6.5 5.2"/><circle cx="17" cy="9" r="2.6"/><path d="M16.5 14.4c2.4.2 4.2 1.7 5 4.6"/>',
    "chat": '<path d="M4 5h16v11H9l-5 4z"/><path d="M8 9.5h8M8 12.5h5"/>',
    "task": '<rect x="5" y="4" width="14" height="17" rx="2"/><path d="M9 4V2.8h6V4"/><path d="M8.5 11l2 2 4-4M8.5 17h7"/>',
    "door": '<path d="M5 21V3h11v18"/><path d="M3 21h18"/><circle cx="13" cy="12" r="1" fill="currentColor"/><path d="M16 5l3 1v15"/>',
    "phone": '<path d="M6.5 3h3l1.5 4.5-2.2 1.4a11 11 0 0 0 6.3 6.3l1.4-2.2L21 14.5v3A2.5 2.5 0 0 1 18.5 20 15.5 15.5 0 0 1 4 5.5 2.5 2.5 0 0 1 6.5 3z"/>',
    "search": '<circle cx="10.5" cy="10.5" r="6.5"/><path d="M15.5 15.5L21 21"/>',
    "funnel": '<path d="M3 4h18l-7 8.5V19l-4 2v-8.5z"/>',
    "calendar": '<rect x="3.5" y="5" width="17" height="15" rx="2"/><path d="M3.5 10h17M8 3v4M16 3v4"/><path d="M8 14h2M12 14h2M8 17h2"/>',
    "star": '<path d="M12 3l2.7 5.6 6.1.8-4.5 4.2 1.1 6.1L12 16.8 6.6 19.7l1.1-6.1L3.2 9.4l6.1-.8z"/>',
    "gear": '<circle cx="12" cy="12" r="3.2"/><path d="M12 2.5v3M12 18.5v3M2.5 12h3M18.5 12h3M5.3 5.3l2.1 2.1M16.6 16.6l2.1 2.1M5.3 18.7l2.1-2.1M16.6 7.4l2.1-2.1"/>',
    "chart": '<path d="M4 20V4M4 20h16"/><path d="M8 16v-4M12 16V8M16 16v-6"/>',
    "mail": '<rect x="3" y="5" width="18" height="14" rx="2"/><path d="M3.5 6l8.5 7 8.5-7"/>',
    "doc": '<path d="M6 3h8l4 4v14H6z"/><path d="M14 3v4h4M9 12h6M9 15.5h6M9 9h3"/>',
    "cup": '<path d="M5 8h11v6a5 5 0 0 1-5 5h-1a5 5 0 0 1-5-5z"/><path d="M16 10h1.5a2.5 2.5 0 0 1 0 5H16M8 3.5c0 1 1 1 1 2M11.5 3.5c0 1 1 1 1 2"/>',
    "laptop": '<rect x="5" y="5" width="14" height="10" rx="1.5"/><path d="M2.5 19h19l-2-4h-15z"/>',
    "rocket": '<path d="M12 2.5c3.5 2.5 5 6.5 4.5 11l-2.5 2.5h-4L7.5 13.5C7 9 8.5 5 12 2.5z"/><circle cx="12" cy="9.5" r="1.8"/><path d="M8 14l-3 3 1 3 3-2M16 14l3 3-1 3-3-2"/>',
    "bolt": '<path d="M13 2.5L5 13.5h6l-1 8 8-11h-6z"/>',
    "home": '<path d="M3 11l9-7.5 9 7.5"/><path d="M5.5 9.5V20h13V9.5"/><path d="M10 20v-6h4v6"/>',
    "check": '<circle cx="12" cy="12" r="9"/><path d="M7.5 12.5l3 3 6-6.5"/>',
    "layers": '<path d="M12 3l9 5-9 5-9-5z"/><path d="M3 13l9 5 9-5"/>',
    "headset": '<path d="M4 14v-2a8 8 0 0 1 16 0v2"/><rect x="3" y="13" width="4" height="6" rx="1.5"/><rect x="17" y="13" width="4" height="6" rx="1.5"/><path d="M19 19c0 1.5-1.5 2.5-4 2.5h-2"/>',
    "key": '<circle cx="8" cy="15" r="4.5"/><path d="M11.2 11.8L20 3M16 7l2.5 2.5M18 5l2 2"/>',
    "megaphone": '<path d="M3 10v4h3l9 5V5L6 10z"/><path d="M18 9.5a3.5 3.5 0 0 1 0 5M7 14l1.5 5h2.5L10 15"/>',
    "pen": '<path d="M4 20l1-4.5L15.5 5a2.1 2.1 0 0 1 3 3L8 18.5z"/><path d="M13.5 7l3 3"/>',
    "handshake": '<path d="M2.5 11l4-4 4 2 3-1.5 4 1.5 4 4"/><path d="M6.5 7L3 13l5 5 2-1 2 1.5 2-1 2 1 4-5.5"/><path d="M10 13l2 2M12.5 11.5l2.5 2.5"/>',
    "clock": '<circle cx="12" cy="12" r="9"/><path d="M12 7v5l3.5 2"/>',
    "cv": '<rect x="5" y="3" width="14" height="18" rx="2"/><circle cx="12" cy="9" r="2.6"/><path d="M8.2 15.5c.7-1.8 2.1-2.6 3.8-2.6s3.1.8 3.8 2.6M8.5 18.5h7"/>',
}


def icon(name: str, size: int = 48, stroke: float = 1.8, cls: str = "") -> str:
    body = P.get(name)
    if body is None:
        raise SystemExit(f"unknown icon '{name}' (have {', '.join(sorted(P))})")
    return (f'<svg class="ico {cls}" width="{size}" height="{size}" viewBox="0 0 24 24" fill="none" stroke="currentColor" '
            f'stroke-width="{stroke}" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">{body}</svg>')
