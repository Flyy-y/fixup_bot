"""Tests for the repost content builder (no Discord connection required)."""

from types import SimpleNamespace

from src.bot import _build_content


def _msg(content, attachment_urls=()):
    return SimpleNamespace(
        content=content,
        attachments=[SimpleNamespace(url=u) for u in attachment_urls],
    )


def test_transforms_text_only():
    assert _build_content(_msg("see https://x.com/a")) == "see https://fixupx.com/a"


def test_appends_attachment_urls():
    out = _build_content(_msg("https://x.com/a", ["https://cdn/img.png"]))
    assert out == "https://fixupx.com/a\nhttps://cdn/img.png"


def test_attachment_only_no_text():
    assert _build_content(_msg("", ["https://cdn/img.png"])) == "https://cdn/img.png"


def test_multiple_attachments():
    out = _build_content(_msg("hi", ["https://cdn/a", "https://cdn/b"]))
    assert out == "hi\nhttps://cdn/a\nhttps://cdn/b"
