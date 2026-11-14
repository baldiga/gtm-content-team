# UTM convention (meeting-to-content)

Base: `https://<YOUR_DOMAIN>/<path>?utm_source=<channel>&utm_medium=social&utm_campaign=<week>&utm_content=<day>-<format>`

Replace `<YOUR_DOMAIN>` with the domain in `config/brand.json`.

- utm_source: linkedin-personal | instagram | x | facebook (only channels you actually publish to)
- utm_medium: social
- utm_campaign: wk-YYYY-MM-DD (week folder date, for example wk-2026-01-05)
- utm_content: `<day>-<format>-<slug>`, for example mon-carousel-first-hire

Rules:

- One tracked URL per piece. Lowercase, hyphens, no spaces.
- Mark each piece `link: none / body / first comment`. Default is no link in the body.
- Publisher logs the exact final URL in `ledger.csv`.
