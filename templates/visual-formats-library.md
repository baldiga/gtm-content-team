# Visual formats library

Content Writer picks a template number for every piece and writes it in the piece header as `template: N (name)`. Carousel Designer renders to that template. Rotate shapes: no two pieces in a week use the same template unless the owner asks for it. Cap carousels at two per week.

These are design formats, not finished posts. Copy on a rendered sample still needs the writer's pass and the owner's approval.

## Standing rules for every visual

- **Ideas, not people.** No names, companies, numbers or deals of meeting participants. No clients. Framing when needed: "from several conversations with founders".
- **CTA, only where relevant.** Use the path in `config/brand.json` (`cta_path`), tracked per `utm-convention.md`. Default is no link. Mark each piece `link: none / body / first comment`.
- **Look:** the personal brand tokens in `config/brand.json` (font Rubik, paper, ink, one accent, footer `owner_name` / `domain`). Not a second brand system.
- **RTL:** Hebrew pages are `dir=rtl`. Latin runs are LTR isolates.
- **Every post has a graphic.** Domain stays on the image.

## Formats

### 1. Animated stack map (GIF)

- **Looks like:** a hub in the center and nodes that appear around it, one by one. Good for a role, a system or a stack of responsibilities (not a vendor logo parade).
- **When to use:** a process or a role with 4-7 distinct parts that should be seen as one job.
- **Sizes:** 1080x1350 feed (and a 7-frame GIF/MP4), 1080x1920 story, 1600x900 X.
- **Spec keys:** title, subtitle, hub, nodes, closing. See `carousel-kit/templates_kit/README.md`.

### 2. Dense cheat sheet (one-pager infographic)

- **Looks like:** a tight grid of short blocks, like rooms in a house or cards on a desk. Lots of information, still readable in a feed.
- **When to use:** a process with many small steps explained across a meeting.
- **Keep copy short.** This format punishes long sentences.
- **Sizes:** 1080x1350, plus optional story frames that show 2-3 blocks at a time, and 1600x900 X.

### 3. Build-up infographic (animated reveal)

- **Looks like:** steps that appear on a path, one after another, then hold.
- **When to use:** a sequence (hire stages, a workflow, a "grows with you" story) that needs motion.
- **Sizes:** 1080x1350 GIF/MP4, story, X.

### 4. Workflow canvas (node graph)

- **Looks like:** a trigger node, a cluster of work nodes, and an output node, in the spirit of a simple automation canvas. No product logos unless the owner has approved a specific tool mention.
- **When to use:** a process that already sounds like a flow (input, work, output).

### 5. Before / after split

- **Looks like:** two columns, a clear contrast, readable in one second.
- **When to use:** two profiles, two ways of working, two outcomes. The "bad" side must be written by you, never taken from a real company.

### 6. Red-pen teardown

- **Looks like:** a document with corrections marked on it, then a rewrite.
- **When to use:** the owner criticized or fixed something concrete (a job post, a brief, a process).
- **Status:** may still be marked not-built in the renderer; use template 5 as a fallback.

### 7. Comparison table

- **Looks like:** a small table (3-4 rows, 2-3 columns) with one highlighted row.
- **When to use:** types, options or segments that should be scanned, not told as a story.

### 8. Team evolution diagram (org chart over time)

- **Looks like:** the same org tree at two or three moments, with a KPI or a short tag on each node.
- **When to use:** how a team should grow, without naming real people.
- **Keep copy short.** Role labels have little room.

### 9. Text screenshot / quote card

- **Looks like:** a white post-style card with initials, name, title, and one line in large type. Nothing else.
- **When to use:** one sentence that can stand alone. Name and initials come from the brand config unless the spec overrides them (never put a third party's name here without approval).

### 10. Single-panel meme / reaction image

- **Looks like:** a typographic scene (a pile of papers, two piles, a viewer) rather than a stolen meme template.
- **When to use:** sparingly, at most once every two weeks. Never use someone else's characters or watermarked formats.

### 11. Whiteboard / napkin sketch

- **Looks like:** a photo of a real whiteboard or notebook, or a hand-drawn fallback (off-white paper, marker strokes).
- **When to use:** frameworks the owner actually drew or would draw while talking.
- **Production:** preferred: the owner snaps a photo, Carousel Designer only crops to 4:5 and fixes levels. Fallback: HTML with SVG jittered paths.
- **Status:** needs a real photo or a built fallback; may be marked not-built.

### 12. Scorecard / checklist

- **Looks like:** three or four checks, each with a short question and yes/no (or a/b) options.
- **When to use:** a list of tests the owner actually uses.

### 13. Simple chart (funnel, bar)

- **Looks like:** one chart, few numbers, large labels.
- **When to use:** only when the numbers are the owner's own and allowed. Never numbers from meeting participants. No market statistics without a source the owner has approved.
- **Status:** may be marked not-built; keep the numbers honest or skip the format.

### 14. "The exact prompt" terminal card

- **Looks like:** a dark code window, mono font, three neutral dots, no app logos, with 1 or 2 accent highlights on the key lines.
- **When to use:** only when the owner shares a prompt they actually use. Do not invent a prompt and claim it is theirs.
- **Status:** needs a real prompt; may be marked not-built.

### 15. Illustrated metaphor scene

- **Looks like:** one metaphor drawn as a simple scene (a house, a path, a machine), with short labels. Style only from the inspiration library; never copy another artist's characters.

### 16. Role org chart

- **Looks like:** a clean org chart for a role family, with a KPI under each node. Close cousin of template 8, used when you need one static chart rather than a time series.

### 17. POV collage

- **Looks like:** two or three "points of view" as stacked cards or frames (founder, hire, customer), each with one line.
- **When to use:** when the same idea looks different from more than one seat. No real faces other than an approved owner chip.

### 18. Weekly changelog card

- **Looks like:** the recurring "2.8 things I learned this week" card. See `brain/formats/weekly-recap.md`.
- **When to use:** only for the weekly recap series.

### 19. Cover / CTA card

- **Looks like:** a dark or paper cover with a short title and a CTA line (or the photo chip). Used as a carousel cover or a stand-alone closer.

### Photo chip (opt-in, hero pieces only)

- A round photo of the owner with the configured name and domain, replacing the text footer (the domain stays). Light and dark variants.
- At most 1 or 2 pieces a week. Off by default. Never on an image that quotes or shows someone else.
- How to turn it on: `"chip": true` (or `"light"` / `"dark"`) in a `templates_kit` spec, and `avatar_path` in `config/brand.json`.

## Choosing a template

| The piece is about... | First pick | Fallback | Notes |
|---|---|---|---|
| A role or a system with parts | 1 Stack map | 4 Workflow canvas | Motion if it helps |
| A many-step process | 2 Cheat sheet | 3 Build-up | Short labels |
| A contrast | 5 Before / after | 7 Table | |
| Something the owner fixed | 6 Red-pen | 5 Before / after | |
| Types or segments | 7 Table | 12 Scorecard | |
| Team growth | 8 or 16 Org chart | 3 Build-up | Short labels |
| One sentence | 9 Quote card | 19 Cover | |
| A wry observation | 10 Meme | 9 Quote card | Rare |
| A drawn framework | 11 Whiteboard | 4 Workflow | Needs a real photo if possible |
| Tests the owner uses | 12 Scorecard | 7 Table | |
| The owner's own numbers | 13 Chart | 7 Table | |
| A real prompt | 14 Prompt card | 4 Workflow | Only a real prompt |
| A metaphor | 15 Metaphor | 1 Stack map | |
| Weekly recap | 18 Changelog | 19 Cover | Series design |
| A carousel cover | 19 Cover | 9 Quote card | Chip is a good fit |

## Production notes

- Render with `carousel-kit/templates_kit`. Spec keys are in its README.
- Animate only when the format is built for motion (1, 3, 18). Hold the last frame long enough to read.
- Check RTL and Latin isolates on every size (feed, story, X).
- Run the rule check. Fix flags before upload.
- Memes (card 10) at most once every two weeks. Prompt cards (card 14) only with a real prompt from the owner.
