"""Contact sheet of all PNGs in each given dir (for visual QA)."""
import sys
from pathlib import Path
from PIL import Image
for d in map(Path, sys.argv[1:]):
    ims = sorted(d.glob('*.png'))
    if not ims: continue
    H = 900; tiles = []
    for p in ims:
        im = Image.open(p).convert('RGB'); r = H / im.height; tiles.append(im.resize((int(im.width * r), H)))
    W = sum(t.width for t in tiles) + 20 * (len(tiles) + 1)
    sheet = Image.new('RGB', (W, H + 40), '#888'); x = 20
    for t in tiles: sheet.paste(t, (x, 20)); x += t.width + 20
    out = d.parent / f'_sheet-{d.name}.png'; sheet.save(out); print(out)
