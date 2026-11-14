# templates_kit

Renders templates from `templates/visual-formats-library.md` in the personal brand look defined by `config/brand.json`. Pages are Hebrew RTL (`dir=rtl`). Latin runs are LTR isolates via `carousel-kit/render.markup`. Rendering uses headless Chrome over CDP (`tk_shot.mjs`).

## CLI

```bash
python3 tk.py SPEC.json [-o OUT_DIR] [--formats feed,story,x] [--no-html]
python3 tk.py --list
```

SPEC is one object or a list of objects. Each object needs `"template": N`.

Outputs (OUT_DIR):

- `feed-1080x1350.png`, `story-1080x1920.png` (or story-01..NN), `x-1600x900.png`
- animated templates: `<fmt>-WxH.gif` + `.mp4` + `-final.png`
- `manifest.json` (files, rule check, fit report), `html/` (sources)

Exit code 3 when the rule check or the layout check flags something.

Demo specs with placeholder copy: `specs/demo-week.json` and `specs/demo-single-posts.json`.

## Photo chip

In a spec add `"chip": true` (picks light or dark from the page theme), or `"chip": "light"` / `"chip": "dark"`. Default is off. Requires `avatar_path` in `config/brand.json` pointing at a circular PNG you provide. The chip shows the configured name and domain, so the footer check still passes. Use it only on hero pieces.

## Rule check

Visible text is checked for em and en dashes, blocked terms from the brand config, pointer emoji, the word בקיצור, more than one `..`, and URLs. Latin words outside the allowlist raise a warning so you can confirm they are not a person or a company.
