# Format: weekly recap, build in public

A recurring post, once a week, on the channels you choose (typically LinkedIn, Instagram and X). It looks back at everything published that week, both the owner's own posts and the pieces the system published, and shares 3 learnings.

The hook number is optional. A working default title is **"2.8 דברים שלמדתי השבוע"** ("2.8" is only the hook; there are always 3 real learnings). Change the title if it does not fit the brand. Each week's post is a normal piece: it goes through the review app and needs the owner's approval before anything is scheduled.

## What it is

- Written in the owner's first-person voice.
- Build-in-public tone: what I tried, what worked, what didn't, what I'm changing next week. Honest and specific, never a victory lap.
- The learnings can be about content, about ideas that came up in meetings, or about running the content system itself. Ideas, not people.

## Hard rules (on top of R-01 to R-08 in ../lessons.md)

- **Numbers only from real data**, with the source written in the draft header `data:` line: ledger.csv, Buffer analytics via Publisher and Analyst, UTM visits to the configured domain, follower counts recorded by Publisher and Analyst. If a number is missing, write the learning without it. Never estimate, round up or invent. Use "בערך" only when the source itself is approximate.
- No names of other people, companies or meeting participants. No clients. Coaching and lecture content stays private, even as a "learning".
- No em or en dashes. ".." at most once. No hype words.
- LinkedIn about 1000 chars max (target 800-1000). No links in the body. CTA at the end.
- Every piece gets a graphic (template below).
- R-01 still applies: a learning must not repeat the week's central topic in the same words. Write about what happened around it (the response, the change, the surprise).

## Hook variants

Keep the series title recognizable. Optional second line (pick one per week, rotate), for example:

1. A playful nod to the 2.8 hook
2. A line that names the themes of the week
3. A line that one of the three learnings might sting a little
4. "Week N of building in public"
5. A line that the number is rounded down

Optional device for "why 2.8": the third learning is framed as the "0.8", the one still being tested. It is still a full learning with the same weight.

## Structure (LinkedIn, the master version)

1. Title line (hook) + optional second line.
2. One or two context lines: what went out this week, in plain facts. Counts come from ledger.csv.
3. Learning 1: what I tried, what happened (one real number if available), what I take from it. 2-3 short lines.
4. Learning 2: same anatomy. Ideally one thing that did not work.
5. Learning 3 (the "0.8"): something still open, a test for next week, or a change in the process.
6. "What I'm changing next week": one line, concrete.
7. CTA: one question, rotated (what did you learn this week, which of the three lands, are you building content from meetings).

Length: 800-1000 chars. Short paragraphs, blank line between, at most one emoji per learning.

## Per-platform versions

| Platform | Shape | Length | Visual | Link |
|---|---|---|---|---|
| LinkedIn (personal) | master text above | 800-1000 chars | feed image 1080x1350 (or a short PDF) | none in body |
| Instagram | short caption: title + one line per learning + question + a few hashtags | about 300 chars | carousel of 4 slides 1080x1350 (cover + 1 per learning) + 1 story 1080x1920 of the cover | DM ask only |
| X | single post: title + 3 one-line learnings + question; or a 4-post thread if a learning needs a number and context | 280 per post | 1600x900 card (or the cover slide) | none in the post; first reply only if approved |

## Graphic template: weekly changelog card

- One fixed design so the series is recognizable at a glance. Use the brand look from `config/brand.json`.
- A big hook numeral in the accent color, with "week N" and the date under it.
- Three rows, one per learning, each with a short tag pill ("tried" / "worked" / "didn't work" / "changing") and a 4-7 word headline. The third row is visually marked as the "0.8".
- Optional real-data strip at the bottom: up to 3 numbers from the week, each with its source in tiny type. Leave it out when data is missing; never fill it with placeholders.
- Footer: configured name and domain (the domain stays on the image). The photo chip is a good fit for this series, if you have an avatar.
- Motion variant (template 3 pipeline): the counter ticks, rows appear one by one, hold. MP4 for Instagram, GIF for LinkedIn and X.
- Sizes: 1080x1350 feed, 1080x1920 story, 1600x900 X. Carousel: cover + 3 slides, one learning each.

## Data sources (in this order)

1. `ledger.csv`: what was scheduled and published this week, channel, time, piece, version, UTM.
2. `brain/approved-examples/<week>/`: the final approved copy of each system piece, its topic and the lessons it shows.
3. Buffer analytics via Publisher and Analyst: reactions, comments, shares, impressions per post where Buffer exposes them. Snapshot with a timestamp.
4. Site visits from UTM links (`utm_campaign=wk-<week>`), per `utm-convention.md`, and progress toward `goals.md`.
5. The owner's own posts that week, used as context, not as a number source unless the count is visible publicly.
6. `brain/lessons.md` and review-app comments from that week: what the owner changed or cut, and why. This is often the most honest build-in-public material.
7. Granola meetings processed that week: only the count and the topics at idea level, never people, companies or private details.

## Weekly workflow

- Late in the week: Publisher and Analyst exports the data snapshot to `weeks/<week>/recap-data.md` (with sources and timestamps).
- Then Content Writer drafts the LinkedIn master + IG + X versions as piece codes `LI-R`, `IG-R`, `X-R` with header lines `format: weekly-recap`, `data:`, `template: weekly changelog card`. Carousel Designer renders the card.
- Uploaded to the review app for the owner's approval. Numbers are frozen at the snapshot time.
- After approval: scheduled for a time the owner has agreed (for example Saturday night after Shabbat, if that is relevant). Check local constraints and keep a buffer.
- The approved recap goes into approved-examples like any piece.
