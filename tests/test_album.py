"""Tests for build_album.py — validates the rendered album structure, privacy
stripping, hide flags, print checklists and the CLI.

Generated image fixtures are tiny handmade JPEG/PNG byte strings so the test
suite needs only pytest (no Pillow, no network).
"""

from __future__ import annotations

import struct
import zlib
from pathlib import Path

import pytest

import build_album as ba


SOI = b"\xff\xd8"
EOI = b"\xff\xd9"


def make_jpeg_bytes(exif_payload: bytes | None = None, app13: bool = False) -> bytes:
    def seg(marker: int, payload: bytes) -> bytes:
        return bytes([0xFF, marker]) + struct.pack(">H", len(payload) + 2) + payload

    app1 = seg(0xE1, b"Exif\x00\x00" + (b"MM\x00\x2a" + b"\x00" * 6)) if exif_payload else b""
    photoshop = seg(0xED, b"Photoshop 3.0\x00\x00\x00\x00\x00\x00") if app13 else b""
    dqt = seg(0xDB, b"\x00" + bytes(range(64)))
    sof0 = seg(0xC0, b"\x08\x00\x01\x00\x01\x01\x01\x11\x00")
    counts = b"\x00" * 15 + b"\x01"
    dht = seg(0xC4, b"\x00" + counts + b"\x05")
    sos = bytes([0xFF, 0xDA]) + struct.pack(">H", 8) + b"\x01\x01\x00\x00\x00"
    data = SOI + app1 + photoshop + dqt + sof0 + dht + sos + b"\x00\xfc\xaa" + EOI
    return data


def png_chunk(ctype: bytes, payload: bytes) -> bytes:
    return struct.pack(">I", len(payload)) + ctype + payload + struct.pack(
        ">I", zlib.crc32(ctype + payload) & 0xFFFFFFFF
    )


def make_png_bytes(text: bytes | None = None) -> bytes:
    ihdr = png_chunk(b"IHDR", struct.pack(">IIBBBBB", 1, 1, 8, 2, 0, 0, 0))
    idat = png_chunk(b"IDAT", zlib.compress(b"\x00\xff\x00\x00"))
    text_chunk = png_chunk(b"tEXt", text or b"Comment\x00this is a secret note")
    iend = png_chunk(b"IEND", b"")
    return b"\x89PNG\r\n\x1a\n" + ihdr + text_chunk + idat + iend


CAPTIONS = """filename,year,caption,who,joke,sensitive
2019/brown-mountain.jpg,2019,"Dusk over the hills","Mom, Dad",,
2024/poolside.png,2024,"A very lazy August afternoon","the cousins",,
2022/snow-fort.png,2022,"Fort Bluebell, complete with flag","Ava & Ben",,yes
2024/couch-pile.jpg,2024,"Eight seconds after 'go long'","the dog",yes,
"""


@pytest.fixture
def album(tmp_path: Path) -> tuple[Path, Path, ba.BuildReport]:
    photos = tmp_path / "photos"
    (photos / "2019").mkdir(parents=True)
    (photos / "2024").mkdir(parents=True)
    (photos / "2022").mkdir(parents=True)
    (photos / "2019" / "brown-mountain.jpg").write_bytes(
        make_jpeg_bytes(exif_payload=b"ok", app13=True)
    )
    (photos / "2022" / "snow-fort.png").write_bytes(make_png_bytes())
    (photos / "2024" / "poolside.png").write_bytes(make_png_bytes(text=b"Place\x00nowhere"))
    (photos / "2024" / "couch-pile.jpg").write_bytes(make_jpeg_bytes())
    captions = tmp_path / "captions.csv"
    captions.write_text(CAPTIONS, encoding="utf-8")
    out = tmp_path / "site"
    report = ba.build(photos, captions, out, title="Asdales")
    return photos, out, report


def test_build_writes_index_and_copies(album: tuple[Path, Path, ba.BuildReport]) -> None:
    _photos, out, report = album
    assert (out / "index.html").exists()
    assert (out / "photos" / "2019" / "brown-mountain.jpg").exists()
    assert report.photos_public == 2


def test_year_sections_sorted_desc(album: tuple[Path, Path, ba.BuildReport]) -> None:
    _photos, out, _report = album
    html = (out / "index.html").read_text(encoding="utf-8")
    ids = [f'id="y{year}"' for year in ("2019", "2022", "2024")]
    assert all(i in html for i in ids)
    assert html.index(ids[2]) < html.index(ids[1]) < html.index(ids[0])


def test_caption_and_who_labels(album: tuple[Path, Path, ba.BuildReport]) -> None:
    _photos, out, _report = album
    html = (out / "index.html").read_text(encoding="utf-8")
    assert 'data-caption="A very lazy August afternoon"' in html
    assert '<span class="ph-who">the cousins</span>' in html
    assert "</figure>" in html


def test_lightbox_css_is_inline(album: tuple[Path, Path, ba.BuildReport]) -> None:
    _photos, out, _report = album
    html = (out / "index.html").read_text(encoding="utf-8")
    assert "<style>" in html
    assert "#lightbox" in html
    assert "rel=\"stylesheet\"" not in html
    assert "<script>" in html


def test_joke_and_sensitive_hidden_by_default(album: tuple[Path, Path, ba.BuildReport]) -> None:
    _photos, out, report = album
    html = (out / "index.html").read_text(encoding="utf-8")
    assert "couch-pile.jpg" not in html
    assert "snow-fort.jpg" not in html
    assert not (out / "photos" / "2022").exists()
    assert report.photos_hidden == 2


def test_include_hidden_shows_flags(tmp_path: Path, album) -> None:
    photos, out, _report = album
    report = ba.build(tmp_path / "photos", tmp_path / "captions.csv", tmp_path / "site2",
                      title="Asdales", include_hidden=True)
    html = (tmp_path / "site2" / "index.html").read_text(encoding="utf-8")
    assert "snow-fort.png" in html
    assert "couch-pile.jpg" in html
    assert 'class="ph-flag">sensitive</span>' in html
    assert 'class="ph-flag">joke</span>' in html
    assert (tmp_path / "site2" / "photos" / "2022" / "snow-fort.png").exists()
    assert report.photos_public == 4


def test_jpeg_metadata_stripped_only_in_output(album: tuple[Path, Path, ba.BuildReport]) -> None:
    photos, out, report = album
    src = (photos / "2019" / "brown-mountain.jpg").read_bytes()
    dest = (out / "photos" / "2019" / "brown-mountain.jpg").read_bytes()
    assert src != dest
    for bad in (0xE1, 0xED):
        i = dest.find(bytes([0xFF, bad]))
        assert i == -1, f"JPEG marker 0x{bad:02X} survived stripping"
    i = src.find(bytes([0xFF, 0xE1]))
    assert i != -1
    assert report.stripped_count >= 1
    assert b"\xff\xdb" in dest and b"\xff\xc0" in dest and dest.endswith(EOI)


def test_png_metadata_stripped(album: tuple[Path, Path, ba.BuildReport]) -> None:
    _photos, out, _report = album
    dest = out / "photos" / "2024" / "poolside.png"
    data = dest.read_bytes()
    assert data[:8] == b"\x89PNG\r\n\x1a\n"
    assert b"tEXt" not in data
    assert b"IHDR" in data and b"IDAT" in data and data.endswith(b"IEND\xaeB`\x82")


def test_privacy_default_noindex(album: tuple[Path, Path, ba.BuildReport]) -> None:
    _photos, out, _report = album
    html = (out / "index.html").read_text(encoding="utf-8")
    assert '<meta name="robots" content="noindex, nofollow">' in html


def test_allow_index_flag(tmp_path: Path, album) -> None:
    photos, out, _ = album
    ba.build(tmp_path / "photos", tmp_path / "captions.csv", tmp_path / "site3",
             title="Public", allow_index=True)
    html = (tmp_path / "site3" / "index.html").read_text(encoding="utf-8")
    assert 'content="index, follow"' in html


def test_html_escaping(tmp_path: Path) -> None:
    photos = tmp_path / "photos"
    photos.mkdir()
    (photos / "sneak.jpg").write_bytes(make_png_bytes())
    captions = tmp_path / "captions.csv"
    captions.write_text(
        'filename,caption,who\n'
        'sneak.jpg,"</figure><script>alert(1)</script>","Eve <eve@example.com>"\n',
        encoding="utf-8",
    )
    out = tmp_path / "site"
    ba.build(photos, captions, out, title="Album </h1>")
    html = (out / "index.html").read_text(encoding="utf-8")
    assert "<script>alert(1)</script>" not in html
    assert "&lt;script&gt;" in html
    assert "Eve &lt;eve@example.com&gt;" in html
    assert "Album &lt;/h1&gt;" in html


def test_unmatched_row(tmp_path: Path) -> None:
    photos = tmp_path / "photos"
    photos.mkdir()
    (photos / "real.jpg").write_bytes(make_jpeg_bytes())
    captions = tmp_path / "captions.csv"
    captions.write_text(
        "filename,caption\nreal.jpg,hello\nghost.jpg,is not on disk\n", encoding="utf-8"
    )
    report = ba.build(photos, captions, tmp_path / "site", title="T")
    assert report.unmatched_csv == ["ghost.jpg"]


def test_print_checklist_per_album(album: tuple[Path, Path, ba.BuildReport]) -> None:
    _photos, out, _report = album
    html = (out / "index.html").read_text(encoding="utf-8")
    assert html.count('class="print-checklist"') == 2
    assert 'Print checklist for 2024' in html
    assert 'poolside.png' in html
    assert 'snow-fort.jpg' not in html
    assert html.count("checkbox") >= 2


def test_missing_captions_file_gives_nocaption_album(tmp_path: Path) -> None:
    photos = tmp_path / "photos"
    photos.mkdir()
    (photos / "a.jpg").write_bytes(make_jpeg_bytes())
    report = ba.build(photos, tmp_path / "nope.csv", tmp_path / "site", title="T")
    html = (tmp_path / "site" / "index.html").read_text(encoding="utf-8")
    assert "a.jpg" in html
    assert report.photos_public == 1


def test_stale_outputs_are_cleaned(album: tuple[Path, Path, ba.BuildReport], tmp_path: Path) -> None:
    photos, out, _report = album
    stale = out / "photos" / "orphan.png"
    stale.write_bytes(make_png_bytes())
    ba.build(photos, tmp_path / "captions.csv", out, title="Again")
    assert not stale.exists()
    assert (out / "photos" / "2024" / "poolside.png").exists()


def test_empty_photos_dir_renders_empty_state(tmp_path: Path) -> None:
    photos = tmp_path / "photos"
    photos.mkdir()
    captions = tmp_path / "captions.csv"
    captions.write_text("filename,caption\n", encoding="utf-8")
    report = ba.build(photos, captions, tmp_path / "site", title="Empty")
    html = (tmp_path / "site" / "index.html").read_text(encoding="utf-8")
    assert "Nothing here yet" in html
    assert report.photos_public == 0


def test_cli_main_end_to_end(tmp_path: Path) -> None:
    photos = tmp_path / "photos"
    photos.mkdir()
    (photos / "x.jpg").write_bytes(make_jpeg_bytes(exif_payload=b"exif"))
    captions = tmp_path / "captions.csv"
    captions.write_text("filename,year,caption\nx.jpg,2018,cli test\n", encoding="utf-8")
    out = tmp_path / "site"
    rc = ba.main(["--photos", str(photos), "--captions", str(captions), "--out", str(out)])
    assert rc == 0
    html = (out / "index.html").read_text(encoding="utf-8")
    assert 'id="y2018"' in html
    assert "cli test" in html
    assert (out / "photos" / "x.jpg").read_bytes().find(bytes([0xFF, 0xE1])) == -1
