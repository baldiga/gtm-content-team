# Store adapters

The review UI is a static frontend. Persistence is swapped by setting `store` in `public/config.json`.

Every adapter must implement:

```js
{
  async getState()           // { title, week, pieces: [...merged], updated }
  async comment(code, text)
  async approve(code)
  async approveAll()
  async requestChanges(code, text)
}
```

The local team API (used by `sync.py`, not the UI) lives on the same backend:

- `GET /api/feedback`  all statuses, comments, versions, images
- `POST /api/team`     `{ action: "reply"|"version"|"images"|"body"|"archive", code, text?, version?, images? }`

## Adapters

| `store` value | File | Backend |
|---|---|---|
| `local` | `local.js` | The Python server in this folder (`server.py`). Default for development. |
| `github-issues` | not built yet | One GitHub Issue (or issue comments) per piece, for a GitHub Pages host. |
| `apps-script` | not built yet | A Google Apps Script Web App writing to a Sheet. |
| `vercel` (same API as `local`) | `local.js` | Vercel serverless routes in `api/` plus a private Vercel Blob store. Images stay on Cloudinary. Keep `store` as `local` in config.json; the HTTP API shape is the same. |

Adding an adapter should not require rewriting the UI, only a new file under `stores/` and a `config.json` change.
