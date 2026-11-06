#!/usr/bin/env python3
"""Generate the sample photos and captions used by the demo build.

Creates completely fictional images (simple shapes and patterns, no faces,
no locations, no personal data) plus a captions.csv that shows off every
feature: year sections, who's-in-it labels, joke and sensitive hide flags.

Requires Pillow (pip install pillow). The album builder itself does not.
"""

from __future__ import annotations

import csv
import struct
from pathlib import Path

from PIL import Image, ImageDraw

SAMPLES = [
    {"name": "winter-morning.jpg", "year": 2023, "caption": "Snow settling on the porch swing",
     "who": "Mom", "joke": "", "sensitive": "", "paint": "wintery"},
    {"name": "beach-day.jpg", "year": 2023, "caption": "The whole crew at the lake",
     "who": "Mom, Dad, Aunt Jo, the kids", "joke": "", "sensitive": "", "paint": "beachy"},
    {"name": "birthday-cake.jpg", "year": 2023, "caption": "Candles and a questionable frosting dam",
     "who": "Dad", "joke": "", "sensitive": "", "paint": "warm cake"},
    {"name": "spring-garden.jpg", "year": 2024, "caption": "First tulips of the year",
     "who": "Grandma Dot", "joke": "", "sensitive": "", "paint": "flowery"},
    {"name": "camp-fire.jpg", "year": 2024, "caption": "S'mores round two, somehow",
     "who": "Everyone", "joke": "", "sensitive": "", "paint": "embery"},
    {"name": "holiday-lights.jpg", "year": 2025, "caption": "The porch, all lit up",
     "who": "Dad, Uncle Ray", "joke": "", "sensitive": "", "paint": "twinkly"},
    {"name": "goofy-faces.jpg", "year": 2023, "caption": "Someone discovered the front camera",
     "who": "the cousins", "joke": "yes", "sensitive": "", "paint": "goofy"},
    {"name": "quiet-corner.jpg", "year": 2025, "caption": "Hidden until you're ready to share",
     "who": "", "joke": "", "sensitive": "yes", "paint": "calm"},
]

SIZE = (320, 240)


def paint_wintery(d: ImageDraw.ImageDraw) -> None:
    d.rectangle([0, 150, 320, 240], fill=(240, 240, 245))
    for x, y, r in [(40, 180, 14), (120, 170, 11), (210, 185, 16), (280, 168, 9), (80, 40, 22), (170, 70, 17), (250, 60, 25)]:
        d.ellipse([x - r, y - r, x + r, y + r], fill=(255, 255, 255))
    d.rectangle([0, 120, 320, 152], fill=(90, 100, 115))


def paint_beachy(d: ImageDraw.ImageDraw) -> None:
    d.rectangle([0, 0, 320, 120], fill=(150, 200, 230))
    d.rectangle([0, 120, 320, 240], fill=(235, 210, 160))
    d.ellipse([60, 20, 130, 90], fill=(250, 230, 90))
    d.polygon([(0, 120), (320, 130), (320, 120), (0, 112)], fill=(120, 180, 210))


def paint_warm_cake(d: ImageDraw.ImageDraw) -> None:
    d.rectangle([0, 0, 320, 240], fill=(255, 244, 235))
    d.ellipse([60, 90, 260, 210], fill=(200, 90, 60))
    d.ellipse([80, 110, 240, 190], fill=(250, 235, 245))
    for x in range(90, 250, 40):
        d.rectangle([x, 60, x + 6, 115], fill=(230, 170, 60))


def paint_flowery(d: ImageDraw.ImageDraw) -> None:
    d.rectangle([0, 0, 320, 240], fill=(220, 235, 210))
    for x, y in [(50, 60), (110, 110), (170, 50), (240, 100), (90, 180), (210, 190)]:
        for dx, dy in [(-14, 0), (14, 0), (0, -14), (0, 14), (-10, -10), (10, 10), (-10, 10), (10, -10)]:
            d.ellipse([x + dx - 8, y + dy - 8, x + dx + 8, y + dy + 8], fill=(230, 120, 150))
        d.ellipse([x - 6, y - 6, x + 6, y + 6], fill=(250, 210, 80))


def paint_embery(d: ImageDraw.ImageDraw) -> None:
    d.rectangle([0, 0, 320, 240], fill=(30, 25, 35))
    d.ellipse([120, 130, 200, 195], fill=(240, 120, 40))
    d.ellipse([140, 145, 180, 180], fill=(255, 210, 90))
    for x, y, r in [(60, 190, 10), (250, 185, 12), (40, 60, 3), (280, 40, 3), (200, 25, 2)]:
        d.ellipse([x - r, y - r, x + r, y + r], fill=(90, 70, 80))


def paint_twinkly(d: ImageDraw.ImageDraw) -> None:
    d.rectangle([0, 0, 320, 240], fill=(25, 30, 55))
    for x in range(20, 320, 40):
        d.line([(x, 0), (x, 40)], fill=(50, 55, 80))
        for bx in range(x - 20, x + 25, 10):
            color = (255, 240, 140) if bx % 20 else (140, 220, 190)
            d.ellipse([bx - 4, 44 + (x % 26), bx + 4, 52 + (x % 26)], fill=color)
    d.polygon([(150, 110), (185, 180), (115, 180)], fill=(40, 50, 80))
    d.rectangle([138, 180, 162, 210], fill=(60, 45, 40))
    d.polygon([(150, 110), (185, 180), (115, 180)], fill=(90, 110, 150))
    d.line([(150, 110), (150, 90)], fill=(70, 90, 120))


def paint_goofy(d: ImageDraw.ImageDraw) -> None:
    d.rectangle([0, 0, 320, 240], fill=(245, 235, 120))
    for x, y, r in [(90, 110, 55), (230, 110, 55)]:
        d.ellipse([x - r, y - r, x + r, y + r], fill=(250, 225, 200))
        d.ellipse([x - 22, y - 25, x - 6, y + 15], fill=(40, 35, 30))
        d.ellipse([x + 6, y - 25, x + 22, y + 15], fill=(40, 35, 30))
        d.arc([x - 30, y + 5, x + 30, y + 45], 0, 180, fill=(150, 60, 60), width=5)


def paint_calm(d: ImageDraw.ImageDraw) -> None:
    d.rectangle([0, 0, 320, 240], fill=(205, 220, 225))
    for y, h in [(140, 20), (165, 18), (190, 16), (212, 14)]:
        d.rectangle([0, y, 320, y + h], fill=(150, 175, 185))
    d.rectangle([0, 100, 320, 140], fill=(115, 135, 150))


PAINTERS = {
    "winter-morning.jpg": paint_wintery,
    "beach-day.jpg": paint_beachy,
    "birthday-cake.jpg": paint_warm_cake,
    "spring-garden.jpg": paint_flowery,
    "camp-fire.jpg": paint_embery,
    "holiday-lights.jpg": paint_twinkly,
    "goofy-faces.jpg": paint_goofy,
    "quiet-corner.jpg": paint_calm,
}


def dummy_exif_with_gps() -> bytes:
    """A minimal EXIF blob containing a GPS latitude ref, used to demo stripping."""
    tiff = bytearray(b"MM\x00\x2a\x00\x00\x00\x08")
    gps_ifd_offset_placeholder = b"\x00\x00\x00\x00"
    tiff += struct.pack(">H", 1)
    tiff += struct.pack(">HHI", 0x8825, 4, 1) + gps_ifd_offset_placeholder
    tiff += b"\x00\x00\x00\x00"
    gps_offset = len(tiff)
    tiff += struct.pack(">H", 1)
    tiff += struct.pack(">HHI", 0x0001, 2, 2) + b"N\x00\x00\x00"
    tiff += b"\x00\x00\x00\x00"
    tiff[10:14] = struct.pack(">I", gps_offset)
    return b"Exif\x00\x00" + bytes(tiff)


def make_samples(base: Path) -> None:
    photos_dir = base / "photos"
    photos_dir.mkdir(parents=True, exist_ok=True)
    rows = []
    for s in SAMPLES:
        name = s["name"]
        img = Image.new("RGB", SIZE, (235, 228, 220))
        d = ImageDraw.Draw(img)
        painter = PAINTERS.get(name)
        if painter:
            painter(d)
        d.text((12, 220), f"SAMPLE — {name}", fill=(60, 50, 45))
        path = photos_dir / name
        exif = dummy_exif_with_gps() if name == "winter-morning.jpg" else b""
        img.save(path, format="JPEG", quality=90, exif=exif)
        rows.append(s)
    with (base / "captions.csv").open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["filename", "year", "caption", "who", "joke", "sensitive"])
        w.writeheader()
        for s in rows:
            w.writerow({k: s[k] for k in w.fieldnames if k != "filename"}
                       | {"filename": s["name"]})
    print(f"sample data written to {base}")


if __name__ == "__main__":
    make_samples(Path("sample"))
