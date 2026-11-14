# Brand config

Copy `brand.example.json` to `brand.json` and fill in your name, domain, colors, handles and any blocked terms.

`brand.json` is gitignored. Do not put API keys, tokens or passwords in this file. Those belong in environment variables (see the root `.env.example`).

The renderer, the review app and the brain tooling all read this config (or the matching env vars). After you change it, re-render any sample images so the footer shows your name and domain.

`avatar_path` is optional. Point it at a circular PNG if you want the photo chip on selected hero pieces. Do not commit someone else's photo. The chip stays off until a piece sets `"chip": true`.
