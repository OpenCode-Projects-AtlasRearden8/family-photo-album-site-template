# Family Photo Album Site Template

A copy-ready **static family album site**, built in one step by a single Python
script from a photos folder plus a captions CSV: warm year sections, caption and
"who's in it" labels, a click-to-enlarge lightbox (all CSS inline, one self-contained
`index.html`), a printable checklist per album year, and privacy defaults that
include joke-photo / sensitive-photo hide flags, no-index for search engines, and
photo copies saved **without EXIF, GPS or comment metadata**.

Built by [Asdale Dynamics, LLC](https://dylanasdale.github.io) — plain, warm,
local-first tools. MIT licensed; no accounts, no network, no secrets.

## Quick start

```bash
# 1. put your photos in a folder (subfolders are fine) and write captions.csv
python3 build_album.py --photos ./photos --captions ./captions.csv --out ./site

# 2. open the result in a browser or just copy the site/ folder to any host
open site/index.html
```

Try it immediately with the bundled fictional sample data:

```bash
python3 make_samples.py            # writes sample/photos + sample/captions.csv (needs Pillow)
python3 build_album.py --photos sample/photos --captions sample/captions.csv \
    --out demo_site --title "The Balde Family"
```

## The captions CSV

One row per photo. Only `filename` is required; anything missing is left blank.
Column names are forgiving (`file`/`path` → filename, `title`/`description` → caption,
`people` → who).

| Column      | Meaning                                                                 |
|-------------|-------------------------------------------------------------------------|
| `filename`  | path under the photos folder, e.g. `2019/brown-mountain.jpg` (case-insensitive) |
| `year`      | album section the photo belongs to. If omitted, the file's year is used |
| `caption`   | the story, e.g. `Snow settling on the porch swing`                       |
| `who`       | "who's in it" — shown as a little pill badge, e.g. `Mom, Dad`            |
| `joke`      | `yes`/`true`/`1` → **hidden** from the default build (the goofy ones)    |
| `sensitive` | `yes`/`true`/`1` → **hidden**, and not shown even in the print checklist |

See `captions.example.csv`. Rows whose filename isn't found in the photos folder
are listed as warnings in the build output — nothing is dropped silently.

Both flags exist so that one album covers the whole family: set `joke` on the
silly outtakes and `sensitive` on anything that shouldn't ship until
someone is ready. Either way the photos stay safe on your disk; they just don't
end up in `site/`.

## Privacy defaults (always on unless you ask otherwise)

- **No geotags, no raw EXIF**: copies placed in `site/photos/` are rewritten
  without EXIF (APP1+), GPS, Photoshop, IPTC, XMP or comment metadata for JPEG,
  and without `tEXt`/`zTXt`/`iTXt`/`eXIf`/`tIME` chunks for PNG. The originals
  in your photos folder are never touched.
- **Not indexed**: pages ship with `<meta name="robots" content="noindex, nofollow">`.
  Pass `--allow-index` if you truly want search engines.
- WebP/GIF are copied as-is (metadata formats vary widely); prefer JPEG/PNG for
  anything private.

## Deploying

The output is a plain static folder. Deploy anywhere:

- **GitHub Pages**: make a repo, copy everything from `site/` into it (or point
  Pages at the `site/` path — either way, the whole site is `index.html` plus
  the `photos/` folder). No JS build, no server, no dependencies.
- **Plain hosting**: upload `site/` to any web folder.

Remember that whatever you put up is public — check the joke/sensitive flags
belong to the right rows before you ship.

## Options

```
--photos DIR          photos folder (default ./photos)
--captions FILE       captions CSV (default ./captions.csv)
--out DIR             output folder (default ./site)
--title "The Balde Family"
--include-hidden      also include joke/sensitive photos, clearly flagged
--allow-index         allow search engine indexing (off by default)
```

## Testing

```bash
python3 -m pytest tests -q
```

16 tests validate the rendered album structure (year sections sorted newest
first, caption + who labels, inline lightbox CSS, one print checklist per year,
hide flags, unmatched-CSV warnings, HTML escaping) and the privacy handling
(JPEG EXIF/APP blocks removed in copies but not in originals, PNG text/metadata
chunks removed, `noindex` default, stale outputs cleaned).

## Limitations worth knowing

- `make_samples.py` (demo data) needs Pillow; the builder itself does not.
- Year fallback uses the file's modified time, so give important photos a `year`
  column for stable results.
- Stripping EXIF also drops orientation hints; pre-rotate anything whose camera
  relied on them.
- The grid shows the full-size file (scaled by CSS) rather than thumbnails; fine
  for family-sized albums, heavy at many hundreds of photos.

## License & credits

MIT — see [LICENSE](LICENSE). Copyright (c) 2026 Asdale Dynamics, LLC.
Part of the beginner-friendly, local-first toolset from
[Dylan Asdale / Asdale Dynamics, LLC](https://dylanasdale.github.io):
AI explained like a friend would, tools that run on your own machine, and no
secrets anywhere in the build. Related project: `ffxiv-screenshot-album-cli`
(for game screenshot albums) and `csv-to-table-site-template` (for plain data
tables) — this one is for family photos.
