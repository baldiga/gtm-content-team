# Carousel kit

Reusable pipeline for Hebrew RTL LinkedIn, Instagram and X graphics: carousels, single images, stories and short motion (GIF / MP4).

Brand values (name, domain, colors, photo chip) come from `config/brand.json`. Do not hard-code a person, a domain or a photo in the templates.

## What is in this folder

- `render.py` and `render_single.py`: older carousel and single-image renderers (Chrome over CDP, CSS in this folder).
- `templates_kit/`: the current renderer for the formats in `templates/visual-formats-library.md`. Start here.

## Requirements

- Google Chrome (`/usr/bin/google-chrome` or `/opt/google/chrome/chrome`)
- The Rubik font
- Python 3 with Pillow
- ffmpeg, for GIF/MP4 motion

## Quick start

```bash
# from the repository root, after you copy config/brand.example.json to config/brand.json
python3 carousel-kit/templates_kit/tk.py --list
python3 carousel-kit/templates_kit/tk.py carousel-kit/templates_kit/specs/demo-week.json -o outputs/demo
```

The demo specs use obviously fake placeholder copy. They are not real posts. After you change the brand config, re-render so the footer shows your name and domain.

To generate a fuller set of format samples for your own library:

```bash
python3 carousel-kit/templates_kit/run_samples.py carousel-kit/templates_kit/specs/demo-week.json --run demo
```

Outputs land under `templates/samples/` (gitignored). Do not commit rendered images that still show another person's name or domain.

## Design tokens

Defaults live in `config/brand.example.json` (paper, ink, soft ink, one accent). Override them in `config/brand.json`. Footer on every slide: `owner_name` / `domain`. Latin runs are LTR isolates. Pages are Hebrew RTL (`dir=rtl`).

Safe zones for stories: no text in the top 250px (profile bar) or the bottom 340px (reply box). The slide counter is a thin progress bar inside the safe zone.

The optional photo chip (`"chip": true` in a spec) replaces the text footer with a circular avatar plus name and domain. It stays off unless you set it and provide `avatar_path`. Use it only on selected hero pieces.

## Rule check

The renderer flags em and en dashes, blocked terms from `config/brand.json`, pointer emoji, more than one `..`, and URLs in the image text. It also warns on Latin words outside the allowlist. Fill `blocked_terms` with names, companies or product words you never want on an image.
