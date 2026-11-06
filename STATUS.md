# STATUS.md — family-photo-album-site-template

**Built by:** Asdale Dynamics, LLC · **Date:** 2026-11-06 · **License:** MIT

## What was built

A copy-ready static template that turns a photos folder plus a captions CSV
into a warm, self-contained family photo album site — generated end-to-end by
one script, `build_album.py` (Python 3 standard library only, no runtime
dependencies, no network):

- **Year sections** — photos grouped into year albums, newest first, with a
  sticky year-nav and per-year photo counts (falls back to "Unknown" or the
  file's year if no `year` column is given).
- **Caption + who's-in-it labels** — `caption` under each photo, `who` shown as
  a pill badge; CSV headers are forgiving (`title`, `people`, `path` all work).
- **Lightbox CSS inline** — click any photo to enlarge; all CSS is a single
  inline `<style>` block and the lightbox JS is inline too: the whole site is
  one `index.html` plus a `photos/` folder.
- **Print checklist per album** — a collapsible, print-friendly checklist per
  year (`details.print-checklist`) with checkbox squares, filename, caption and
  who; `@media print` rules hide the nav/lightbox and page-break between years.
- **Joke/sensitive hide flags** — `joke` rows are omitted from the default
  build (and the checklist); `sensitive` rows are additionally never copied
  into the output. `--include-hidden` shows both, clearly flagged.
- **Privacy defaults** — copies in `site/photos/` are rewritten without EXIF /
  GPS / IPTC / Photoshop / XMP / comments (JPEG APP segments dropped, PNG
  `tEXt`/`zTXt`/`iTXt`/`eXIf`/`tIME` chunks dropped); pages default to
  `<meta name="robots" content="noindex, nofollow">` (`--allow-index` to opt
  out). Originals on disk are never modified.
- Warnings for CSV rows that don't match any photo; stale files in the output
  photos folder are cleaned each build.

Supporting files: `captions.example.csv`, `make_samples.py` (Pillow-only, makes
fictional demo photos — no real people, no locations), `sample/` (the demo data
it produces, committed), `tests/`, `README.md`, `LICENSE`.

## How to run

```bash
python3 build_album.py --photos ./photos --captions ./captions.csv --out ./site

# demo with bundled sample data
python3 make_samples.py                                  # needs Pillow
python3 build_album.py --photos sample/photos --captions sample/captions.csv \
    --out demo_site --title "The Balde Family"

# options: --title, --include-hidden, --allow-index
```

Deploy by copying `site/` to GitHub Pages or any plain hosting folder.

## Verification results

- `python3 -m pytest tests -q` → **17 passed** (structure: year sections sorted
  newest-first; caption/who labels; inline lightbox CSS; one print checklist
  per year; joke/sensitive hidden + `--include-hidden`; HTML escaping; noindex
  default; unmatched-CSV warning; stale-output cleanup; empty-state; CLI
  end-to-end; JPEG APP1/APP13 stripped in copies but intact in originals; PNG
  text chunks stripped; `build_album.main()` return code).
- `python3 -m pyflakes` on all project files → clean.
- Real build on `sample/` → `built: demo_site/index.html — 6 public photo(s),
  2 hidden, 1 re-saved without metadata`; every output photo opens and decodes
  in Pillow; the sample photo that ships with a fake GPS-bearing EXIF blob
  comes out with no `Exif` marker at all.

## Known gaps

- WebP/GIF are copied byte-for-byte (metadata stripping for those is out of
  scope); prefer JPEG/PNG for anything private.
- Dropping the JPEG APP1 block also drops the EXIF orientation hint —
  pre-rotate photos whose camera relied on it.
- No thumbnails: the grid loads full-size files scaled by CSS (fine for
  family-sized albums, heavy for many hundreds of photos).
- Year fallback uses the file's modified time, which can shift when files are
  copied; set the `year` column for anything important.
- `make_samples.py` is the only piece that needs Pillow.
- Privacy claim covers metadata in files and search indexing; it cannot stop a
  person who has access to the deployed folder.
