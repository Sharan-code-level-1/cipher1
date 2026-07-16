"""Lightweight security regression checks."""
from app.core.security import create_access_token, safe_decode
from app.utils.files import detect_mime_magic


def test_token_type_enforced():
    access = create_access_token("u1", role="admin")
    payload = safe_decode(access)
    assert payload["type"] == "access"


def test_magic_bytes_reject_html_polyglot():
    # HTML content should not look like image
    assert detect_mime_magic(b"<html><script>alert(1)</script>") is None


def test_jpeg_magic():
    assert detect_mime_magic(b"\xff\xd8\xff\xe0" + b"\x00" * 20) == "image/jpeg"
