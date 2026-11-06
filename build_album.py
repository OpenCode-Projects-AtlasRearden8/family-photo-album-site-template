#!/usr/bin/env python3
"""Build a static family photo album site from a photos folder and a captions CSV.

Usage:
    python build_album.py --photos ./photos --captions ./captions.csv --out ./site

Standard library only. No network access. Privacy defaults stay on: metadata
(EXIF / GPS / comments) is stripped from the copies placed in the site folder,
and the generated page is marked noindex unless you pass --allow-index.
"""

from __future__ import annotations

import argparse
import csv
import dataclasses
import datetime
import html
import os
import shutil
import sys
from pathlib import Path

IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".webp", ".gif"}

TRUTHY = {"1", "true", "yes", "y", "on"}

KEPT_JPEG_MARKERS = {
    0xC0, 0xC1, 0xC2, 0xC3, 0xC4, 0xC5, 0xC6, 0xC7, 0xC9, 0xCA, 0xCB,
    0xDB, 0xDC, 0xDD, 0xDE, 0xDF,
}

STRIPPABLE_PNG_CHUNKS = {"tEXt", "zTXt", "iTXt", "eXIf", "tIME"}

CSS = """
:root {
  --bg: #faf6f0;
  --card: #ffffff;
  --ink: #35302b;
  --muted: #7a7168;
  --accent: #b3541e;
  --accent-soft: #f3e2d5;
  --line: #e8dfd4;
}
* { box-sizing: border-box; }
html { scroll-behavior: smooth; }
body {
  margin: 0;
  background: var(--bg);
  color: var(--ink);
  font-family: Georgia, "Times New Roman", serif;
  line-height: 1.55;
}
header.site-head {
  text-align: center;
  padding: 2.2rem 1rem 1.4rem;
  border-bottom: 1px solid var(--line);
}
header.site-head h1 {
  margin: .1rem 0;
  font-size: 2.1rem;
  color: var(--accent);
  letter-spacing: .02em;
}
header.site-head .tagline { color: var(--muted); margin: .35rem 0 .2rem; }
header.site-head .privacy-note {
  font-size: .85rem;
  color: var(--muted);
  background: var(--accent-soft);
  border: 1px solid var(--line);
  border-radius: 8px;
  display: inline-block;
  padding: .3rem .8rem;
  margin-top: .5rem;
}
nav.year-nav {
  position: sticky;
  top: 0;
  z-index: 5;
  background: rgba(250, 246, 240, .97);
  border-bottom: 1px solid var(--line);
  padding: .45rem 1rem;
  text-align: center;
}
nav.year-nav a {
  display: inline-block;
  margin: 0 .3rem;
  padding: .15rem .6rem;
  border-radius: 999px;
  text-decoration: none;
  color: var(--ink);
  font-size: .95rem;
}
nav.year-nav a:hover { background: var(--accent-soft); color: var(--accent); }
main { max-width: 1100px; margin: 0 auto; padding: 1rem 1rem 3rem; }
section.year { padding-top: 1rem; }
section.year h2 {
  font-size: 1.5rem;
  color: var(--accent);
  border-bottom: 2px solid var(--accent-soft);
  padding-bottom: .3rem;
  scroll-margin-top: 3.5rem;
}
section.year h2 .count {
  font-size: .85rem;
  color: var(--muted);
  font-weight: normal;
  font-family: system-ui, sans-serif;
}
.grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(220px, 1fr));
  gap: 1.1rem;
  margin: 1rem 0 1.6rem;
}
figure.card {
  margin: 0;
  background: var(--card);
  border: 1px solid var(--line);
  border-radius: 12px;
  overflow: hidden;
  cursor: zoom-in;
  box-shadow: 0 1px 3px rgba(60, 45, 30, .07);
}
figure.card img {
  display: block;
  width: 100%;
  height: 165px;
  object-fit: cover;
  background: var(--accent-soft);
}
figcaption { padding: .55rem .8rem .7rem; }
figcaption .ph-caption { display: block; font-style: italic; }
figcaption .ph-who {
  display: inline-block;
  margin-top: .35rem;
  font-size: .78rem;
  font-family: system-ui, sans-serif;
  color: var(--ink);
  background: var(--accent-soft);
  border-radius: 999px;
  padding: .1rem .55rem;
}
figure.card .ph-flag {
  display: inline-block;
  margin-left: .3rem;
  font-size: .72rem;
  font-family: system-ui, sans-serif;
  color: #7c2d12;
}
details.print-checklist {
  margin: 0 0 1.6rem;
  background: #fffdf9;
  border: 1px solid var(--line);
  border-radius: 12px;
  padding: .55rem .9rem;
}
details.print-checklist summary {
  cursor: pointer;
  font-family: system-ui, sans-serif;
  color: var(--accent);
  font-weight: 600;
}
details.print-checklist ul { list-style: none; padding: .2rem 0 0; margin: .4rem 0; }
details.print-checklist li {
  padding: .3rem 0;
  border-top: 1px dotted var(--line);
  font-size: .95rem;
}
details.print-checklist .checkbox {
  display: inline-block;
  width: 13px;
  height: 13px;
  border: 1.6px solid var(--ink);
  border-radius: 3px;
  margin-right: .5rem;
  vertical-align: -2px;
}
details.print-checklist .who { color: var(--muted); font-style: italic; }
details.print-checklist .clear-all {
  font-family: system-ui, sans-serif;
  font-size: .8rem;
  color: var(--muted);
}
footer.site-foot {
  text-align: center;
  color: var(--muted);
  font-size: .85rem;
  padding: 1.2rem;
  border-top: 1px solid var(--line);
}
#lightbox {
  position: fixed;
  inset: 0;
  z-index: 50;
  background: rgba(25, 18, 12, .88);
  display: none;
  align-items: center;
  justify-content: center;
  flex-direction: column;
  padding: 1rem;
  cursor: zoom-out;
}
#lightbox.open { display: flex; }
#lightbox img {
  max-width: 92vw;
  max-height: 78vh;
  border-radius: 10px;
  box-shadow: 0 8px 40px rgba(0, 0, 0, .55);
}
#lightbox .lb-caption {
  color: #f7ede4;
  font-style: italic;
  margin-top: .8rem;
  text-align: center;
  max-width: 92vw;
}
#lightbox .lb-who {
  color: #d8b79e;
  font-size: .85rem;
  font-family: system-ui, sans-serif;
  margin-top: .2rem;
}
#lightbox .lb-close {
  position: absolute;
  top: .8rem;
  right: 1.2rem;
  color: #fff;
  font-family: system-ui, sans-serif;
  font-size: 1.6rem;
}
@media print {
  nav.year-nav, #lightbox, footer.site-foot, header.site-head .privacy-note { display: none !important; }
  .grid { grid-template-columns: repeat(3, 1fr); page-break-inside: avoid; }
  section.year { break-before: page; }
  section.year:first-of-type { break-before: auto; }
  details.print-checklist { display: block !important; }
  details.print-checklist summary { list-style: none; }
  figure.card { box-shadow: none; }
}
"""


@dataclasses.dataclass
class Entry:
    name: str
    caption: str = ""
    who: str = ""
    year: str | None = None
    joke: bool = False
    sensitive: bool = False


@dataclasses.dataclass
class Photo:
    name: str
    src: Path
    caption: str = ""
    who: str = ""
    year: str = "Unknown"
    joke: bool = False
    sensitive: bool = False
    hidden_reason: str = ""
    stripped: bool = False


@dataclasses.dataclass
class BuildReport:
    out_dir: Path
    photos_public: int = 0
    photos_hidden: int = 0
    stripped_count: int = 0
    unmatched_csv: list[str] = dataclasses.field(default_factory=list)
    years: list[str] = dataclasses.field(default_factory=list)


HEADER_ALIASES = {
    "filename": "name", "file": "name", "name": "name", "path": "name",
    "caption": "caption", "title": "caption", "description": "caption",
    "who": "who", "people": "who", "whosinit": "who", "peopleinit": "who", "featuring": "who",
    "year": "year",
    "joke": "joke", "hidejoke": "joke", "jokephoto": "joke",
    "sensitive": "sensitive", "hidesensitive": "sensitive", "private": "sensitive",
}


def normalize_header(raw: str) -> str:
    key = raw.strip().lower().replace(" ", "").replace("-", "").replace("_", "")
    return HEADER_ALIASES.get(key, "")


def read_captions(captions_csv: Path) -> tuple[dict[str, Entry], list[str]]:
    entries: dict[str, Entry] = {}
    warnings: list[str] = []
    if not captions_csv.exists():
        return entries, [f"captions file not found: {captions_csv} (album will have no captions)"]
    with captions_csv.open(newline="", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        fieldmap = {raw: normalize_header(raw) for raw in (reader.fieldnames or []) if normalize_header(raw)}
        if "name" not in set(fieldmap.values()):
            warnings.append("captions CSV is missing a 'filename' column; no captions loaded")
            return entries, warnings
        for lineno, row in enumerate(reader, start=2):
            values = {mapped: (val or "").strip() for raw, val in row.items() for mapped in [fieldmap.get(str(raw))] if mapped}
            name = values.get("name", "").replace("\\", "/").lstrip("/")
            if not name:
                continue
            entry = Entry(
                name=name,
                caption=values.get("caption", ""),
                who=values.get("who", ""),
                year=values.get("year", "") or None,
                joke=values.get("joke", "").lower() in TRUTHY,
                sensitive=values.get("sensitive", "").lower() in TRUTHY,
            )
            if name in entries:
                warnings.append(f"CSV row {lineno}: duplicate entry for {name!r}; keeping the later one")
            entries[name] = entry
    return entries, warnings


def scan_photos(photos_dir: Path) -> dict[str, Path]:
    found: dict[str, Path] = {}
    if not photos_dir.is_dir():
        return found
    for root, _dirs, files in os.walk(photos_dir):
        for fname in sorted(files):
            p = Path(root) / fname
            if p.suffix.lower() in IMAGE_EXTS:
                key = p.relative_to(photos_dir).as_posix().lower()
                if key in found:
                    print(f"warning: two photos match {key!r} (case-insensitive); using the first")
                else:
                    found[key] = p
    return found


def strip_jpeg(data: bytes) -> bytes:
    if data[:2] != b"\xff\xd8":
        return data
    out = bytearray(b"\xff\xd8")
    i, n = 2, len(data)
    while i < n:
        if data[i] != 0xFF:
            return data
        marker = data[i + 1]
        if marker == 0xFF:
            i += 1
            continue
        if marker in (0x01, 0xD8, 0xD9):
            out += data[i:i + 2]
            i += 2
            continue
        if marker == 0xDA:
            out += data[i:]
            break
        if i + 4 > n:
            return data
        seg_len = int.from_bytes(data[i + 2:i + 4], "big")
        if seg_len < 2 or i + 2 + seg_len > n:
            return data
        if marker == 0xE0 or marker in KEPT_JPEG_MARKERS:
            out += data[i:i + 2 + seg_len]
        i += 2 + seg_len
    return bytes(out)


def strip_png(data: bytes) -> bytes:
    sig = b"\x89PNG\r\n\x1a\n"
    if data[:8] != sig:
        return data
    out = bytearray(sig)
    i, n = 8, len(data)
    while i + 8 <= n:
        length = int.from_bytes(data[i:i + 4], "big")
        chunk_type = data[i + 4:i + 8].decode("latin-1", errors="replace")
        if length > n - i - 12:
            return data
        if chunk_type not in STRIPPABLE_PNG_CHUNKS:
            out += data[i:i + 12 + length]
        i += 12 + length
    return bytes(out)


def strip_metadata(data: bytes, suffix: str) -> bytes:
    suffix = suffix.lower()
    if suffix in (".jpg", ".jpeg"):
        return strip_jpeg(data)
    if suffix == ".png":
        return strip_png(data)
    return data


def year_for(entry: Entry | None, photo_path: Path) -> str:
    if entry and entry.year:
        return entry.year
    try:
        return str(datetime.date.fromtimestamp(photo_path.stat().st_mtime).year)
    except OSError:
        return "Unknown"


def prepare(photos_dir: Path, captions_csv: Path, include_hidden: bool = False
            ) -> tuple[list[Photo], dict[str, list[Photo]], dict[str, str]]:
    entries, warnings = read_captions(captions_csv)
    for w in warnings:
        print(f"warning: {w}")
    entries_by_key = {k.lower(): e for k, e in entries.items()}
    photos: list[Photo] = []
    for key, src in sorted(scan_photos(photos_dir).items()):
        display_name = src.relative_to(photos_dir).as_posix()
        entry = entries_by_key.get(key)
        photo = Photo(
            name=display_name,
            src=src,
            caption=entry.caption if entry else "",
            who=entry.who if entry else "",
            year=year_for(entry, src),
            joke=bool(entry and entry.joke),
            sensitive=bool(entry and entry.sensitive),
        )
        if photo.sensitive and not include_hidden:
            photo.hidden_reason = "sensitive"
            photo.caption = "Hidden until you're ready to share"
        elif photo.joke and not include_hidden:
            photo.hidden_reason = "joke"
        photos.append(photo)
    unmatched = {
        e.name: "no photo with this filename was found in the photos folder"
        for key, e in entries_by_key.items()
        if key not in scan_keys(photos_dir)
    }
    by_year: dict[str, list[Photo]] = {}
    for p in sorted(photos, key=lambda x: x.name.lower()):
        by_year.setdefault(p.year, []).append(p)
    return photos, by_year, unmatched


def scan_keys(photos_dir: Path) -> set[str]:
    return set(scan_photos(photos_dir))


def visible(p: Photo) -> bool:
    return p.hidden_reason == ""


def card_flag(p: Photo) -> str:
    if p.sensitive:
        return '<span class="ph-flag">sensitive</span>'
    if p.joke:
        return '<span class="ph-flag">joke</span>'
    return ""


def card_html(p: Photo) -> str:
    cls = "card hidden-photo" if p.hidden_reason else "card"
    who_badge = f'<span class="ph-who">{html.escape(p.who)}</span>' if p.who else ""
    alt = html.escape(p.caption or p.name)
    caption = html.escape(p.caption) if p.caption else "&nbsp;"
    return (
        f'<figure class="{cls}" data-lb data-caption="{html.escape(p.caption)}" '
        f'data-who="{html.escape(p.who)}">'
        f'<img loading="lazy" decoding="async" src="photos/{html.escape(p.name, quote=True)}" alt="{alt}">'
        f'<figcaption><span class="ph-caption">{caption}</span>{who_badge}{card_flag(p)}</figcaption>'
        f'</figure>'
    )


def checklist_item(p: Photo) -> str:
    who = f' &mdash; <span class="who">with {html.escape(p.who)}</span>' if p.who else ""
    caption = html.escape(p.caption) if p.caption else "(no caption yet)"
    return (f'<li><span class="checkbox"></span>'
            f'<span class="phname">{html.escape(p.name)}</span>'
            f' &mdash; {caption}{who}</li>')


def year_section(year: str, photos: list[Photo]) -> str:
    shown = [p for p in photos if visible(p)]
    hidden_count = len(photos) - len(shown)
    count = f"({len(shown)} photo{'s' if len(shown) != 1 else ''}"
    if hidden_count:
        count += f", {hidden_count} hidden"
    parts = [
        f'<section class="year" id="y{html.escape(year, quote=True)}">\n'
        f'<h2>{html.escape(year)} <span class="count">{count})</span></h2>\n'
        '<div class="grid">\n'
    ]
    parts += [card_html(p) + "\n" for p in shown]
    parts.append("</div>\n")
    if shown:
        items = "".join(checklist_item(p) for p in photos if visible(p))
        parts.append(
            f'<details class="print-checklist">\n'
            f'<summary>Print checklist for {html.escape(year)}</summary>\n'
            f'<ul>{items}</ul>\n'
            '<p class="clear-all">Check off each photo as you grade it for the lab. '
            'Joke and sensitive photos are left off this list on purpose.</p>\n'
            '</details>\n'
        )
    parts.append("</section>\n")
    return "".join(parts)


def empty_state() -> str:
    return ('<section class="year">\n<h2>Nothing here yet</h2>\n'
            '<p>Add photos to the photos folder and rows to captions.csv, '
            'then run build_album.py again.</p>\n</section>\n')


LIGHTBOX_JS = (
    "(function () {"
    "var lb = document.getElementById('lightbox');"
    "var img = lb.querySelector('img');"
    "var cap = lb.querySelector('.lb-caption');"
    "var who = lb.querySelector('.lb-who');"
    "function close() { lb.classList.remove('open'); document.body.style.overflow = ''; }"
    "document.addEventListener('click', function (ev) {"
    "var card = ev.target.closest('[data-lb]');"
    "if (card) {"
    "img.src = card.querySelector('img').getAttribute('src');"
    "cap.textContent = card.getAttribute('data-caption') || '';"
    "who.textContent = card.getAttribute('data-who') ? 'with ' + card.getAttribute('data-who') : '';"
    "lb.classList.add('open');"
    "document.body.style.overflow = 'hidden';"
    "return;"
    "}"
    "if (lb.classList.contains('open')) close();"
    "});"
    "document.addEventListener('keydown', function (ev) { if (ev.key === 'Escape') close(); });"
    "})();"
)


def render_html(title: str, by_year: dict[str, list[Photo]], allow_index: bool) -> str:
    years = sorted(by_year, key=lambda y: (y != "Unknown", y), reverse=True)
    robots = "noindex, nofollow" if not allow_index else "index, follow"
    parts = [
        "<!DOCTYPE html>\n<html lang=\"en\">\n<head>\n"
        '<meta charset="utf-8">\n'
        '<meta name="viewport" content="width=device-width, initial-scale=1">\n'
        f'<meta name="robots" content="{robots}">\n'
        f"<title>{html.escape(title)}</title>\n"
        f"<style>{CSS}</style>\n"
        "</head>\n<body>\n"
        f'<header class="site-head">\n<h1>{html.escape(title)}</h1>\n'
        '<p class="tagline">A warm little album &mdash; click any photo to see it big.</p>\n'
        '<p class="privacy-note">Privacy by default: the photo files here hold no EXIF, '
        'GPS or comment metadata, and this page is not indexed by search engines.</p>\n'
        "</header>\n",
    ]
    if years:
        links = " ".join(
            f'<a href="#y{html.escape(y, quote=True)}">{html.escape(y)}</a>' for y in years
        )
        parts.append(f'<nav class="year-nav">{links}</nav>\n')
    parts.append("<main>\n")
    if years:
        parts.extend(year_section(y, by_year[y]) for y in years)
    else:
        parts.append(empty_state())
    parts.append("</main>\n")
    parts.append(
        '<footer class="site-foot">Built with build_album.py &mdash; a plain, local-first '
        'album builder. The photo files copied into this folder had their metadata removed.</footer>\n'
        f"<script>{LIGHTBOX_JS}</script>\n"
        "</body>\n</html>\n"
    )
    return "".join(parts)


def build(photos_dir: Path, captions_csv: Path, out_dir: Path, title: str = "Family Album",
          include_hidden: bool = False, allow_index: bool = False) -> BuildReport:
    photos, by_year, unmatched = prepare(photos_dir, captions_csv, include_hidden)
    out_photos = out_dir / "photos"
    out_dir.mkdir(parents=True, exist_ok=True)
    if out_photos.exists():
        shutil.rmtree(out_photos)
    out_photos.mkdir(parents=True)
    stripped_count = 0
    included = 0
    for p in photos:
        if p.hidden_reason:
            continue
        included += 1
        data = p.src.read_bytes()
        new = strip_metadata(data, p.src.suffix)
        p.stripped = new != data
        if p.stripped:
            stripped_count += 1
        dest = out_photos / p.name
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(new)
    html_text = render_html(title, by_year, allow_index)
    (out_dir / "index.html").write_text(html_text, encoding="utf-8")
    report = BuildReport(
        out_dir=out_dir,
        photos_public=included,
        photos_hidden=len(photos) - included,
        stripped_count=stripped_count,
        unmatched_csv=sorted(unmatched),
        years=list(by_year),
    )
    print(f"built: {out_dir / 'index.html'} — {included} public photo(s), "
          f"{len(photos) - included} hidden, {stripped_count} re-saved without metadata")
    if unmatched:
        print("warning: CSV rows with no matching photo file:")
        for name, why in sorted(unmatched.items()):
            print(f"  - {name}: {why}")
    return report


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    p = argparse.ArgumentParser(
        prog="build_album",
        description="Build a warm static family-album site from a photos folder and a captions CSV.",
    )
    p.add_argument("--photos", default="photos", help="folder containing photos (default: ./photos)")
    p.add_argument("--captions", default="captions.csv", help="captions CSV (default: ./captions.csv)")
    p.add_argument("--out", default="site", help="output folder for the site (default: ./site)")
    p.add_argument("--title", default="Family Album", help="site title")
    p.add_argument("--include-hidden", action="store_true",
                   help="also include joke/sensitive photos, clearly labeled")
    p.add_argument("--allow-index", action="store_true",
                   help="allow search engines to index the site (default: noindex for privacy)")
    return p.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    build(
        photos_dir=Path(args.photos),
        captions_csv=Path(args.captions),
        out_dir=Path(args.out),
        title=args.title,
        include_hidden=args.include_hidden,
        allow_index=args.allow_index,
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
