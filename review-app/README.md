# Content review app

Mobile-first Hebrew review UI. The owner opens one page, sees every post and every image, leaves a comment or taps approve / needs changes, and the team reads that feedback with `sync.py`.

The frontend is static. Persistence is a pluggable store. The default `local` store is the Python server in this folder, for development. Production is the Vercel routes in `api/` plus a private Vercel Blob store, protected by a password login.

## How to run locally

```bash
cp ../.env.example .env.local   # then fill ACCESS_KEY and TEAM_API_KEY
python3 server.py
```

Open `http://127.0.0.1:8787/?k=...` using the access key from `.env.local` (never commit that file, never paste the key into a post). The page is RTL, mobile-first, and marked `noindex`.

A small sample catalog (`LI-DEMO`, `IG-DEMO`, `X-DEMO`) ships so the page is not empty. The pieces use obviously fake copy and placeholder images under `public/demo/`. Replace `lib/catalog.json` (and `public/data/catalog.json` if you keep a copy) with the week's pieces.

## How the team reads comments and pushes updates

`sync.py` talks to the authenticated JSON API.

```bash
python3 sync.py pull                  # all statuses, comments, versions, images
python3 sync.py pull --out /tmp/fb.json
python3 sync.py status                # one line per piece
python3 sync.py reply LI-DEMO "תיקנו את הפסקה השנייה"
python3 sync.py version LI-DEMO v2 --note "קוצר לפי ההערה" --body-file path.md
python3 sync.py upload LI-DEMO path/to/image.jpg --kind feed
python3 sync.py archive LI-DEMO --reason cut
```

`upload` resizes with Pillow to about 1080px wide JPEG. If Cloudinary credentials are in the environment, it uploads to `<CLOUDINARY_FOLDER>/<week>/<piece>/` and attaches the new URLs. Otherwise it stages files locally so the review page still works on the local server.

## Deploying to Vercel

Set at least `TEAM_API_KEY`, `ACCESS_KEY_SHA256`, `SESSION_SECRET`, `BLOB_READ_WRITE_TOKEN`, `OWNER_ID`, `OWNER_LABEL` and `TIMEZONE`. Hash the review password with:

```bash
python3 -c "import hashlib,getpass; print(hashlib.sha256(getpass.getpass('Review password: ').encode()).hexdigest())"
```

Do not store the plaintext password in the repo or in a Vercel env var that gets logged. The app is marked `noindex`. This is a private review tool, not a publishing surface. Approval here is only the owner's go-ahead for the Publisher bot to schedule later.

## API (authenticated)

- `GET /api/state` or `GET /api/feedback`  -  catalog plus live status and comment threads
- `POST /api/action`  -  owner actions: `{ "type": "comment"|"approve"|"changes"|"approve_all", "code"?, "text"? }`
- `POST /api/team`  -  team actions: `{ "action": "reply"|"version"|"images"|"body"|"archive", "code", ... }`

Send the team key as `Authorization: Bearer …`, `X-Team-Key`, or `X-Access-Key`.
