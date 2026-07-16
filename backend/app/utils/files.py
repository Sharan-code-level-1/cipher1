"""Secure file validation and storage helpers."""
from __future__ import annotations

import hashlib
import io
import os
import re
from pathlib import Path
from typing import Optional, Tuple
from uuid import uuid4

from PIL import Image, ExifTags
import imagehash

from app.core.config import get_settings
from app.core.exceptions import ValidationAppError

ALLOWED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp"}
ALLOWED_MIME = {"image/jpeg", "image/png", "image/webp"}

# Magic bytes
MAGIC = {
    b"\xff\xd8\xff": "image/jpeg",
    b"\x89PNG\r\n\x1a\n": "image/png",
    b"RIFF": "image/webp",  # further validated
}

SAFE_NAME_RE = re.compile(r"[^A-Za-z0-9._-]+")


def sanitize_filename(name: str) -> str:
    base = os.path.basename(name)
    base = SAFE_NAME_RE.sub("_", base)
    return base[:180] or "upload.bin"


def detect_mime_magic(data: bytes) -> Optional[str]:
    for sig, mime in MAGIC.items():
        if data.startswith(sig):
            if mime == "image/webp":
                if len(data) > 12 and data[8:12] == b"WEBP":
                    return "image/webp"
                return None
            return mime
    return None


def validate_image_upload(filename: str, content_type: str, data: bytes) -> Tuple[str, str, int, int]:
    settings = get_settings()
    if len(data) > settings.max_upload_bytes:
        raise ValidationAppError(f"File exceeds {settings.max_upload_size_mb}MB limit")
    if len(data) < 100:
        raise ValidationAppError("File too small to be a valid image")

    ext = Path(filename).suffix.lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise ValidationAppError("File extension not allowed")

    magic_mime = detect_mime_magic(data)
    if not magic_mime or magic_mime not in ALLOWED_MIME:
        raise ValidationAppError("File content does not match an allowed image type")

    # Path traversal / zip-slip style names
    if ".." in filename or filename.startswith("/") or "\\" in filename:
        raise ValidationAppError("Invalid filename")

    try:
        img = Image.open(io.BytesIO(data))
        img.verify()
        img = Image.open(io.BytesIO(data))
        width, height = img.size
        if width < 64 or height < 64:
            raise ValidationAppError("Image resolution too low")
        if width > 8000 or height > 8000:
            raise ValidationAppError("Image resolution too high")
    except ValidationAppError:
        raise
    except Exception as exc:
        raise ValidationAppError("Corrupt or unreadable image") from exc

    return magic_mime, sanitize_filename(filename), width, height


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def perceptual_hash(data: bytes) -> str:
    img = Image.open(io.BytesIO(data))
    return str(imagehash.phash(img))


def extract_exif(data: bytes) -> dict:
    try:
        img = Image.open(io.BytesIO(data))
        raw = img._getexif() or {}
        out = {}
        for tag_id, value in raw.items():
            tag = ExifTags.TAGS.get(tag_id, str(tag_id))
            if isinstance(value, bytes):
                continue
            try:
                out[tag] = str(value)[:500]
            except Exception:
                continue
        return out
    except Exception:
        return {}


def store_file(data: bytes, *, subdir: str = "claims") -> str:
    settings = get_settings()
    root = Path(settings.file_storage_path)
    # Prevent path traversal in subdir
    safe_subdir = SAFE_NAME_RE.sub("", subdir) or "claims"
    dest_dir = root / safe_subdir
    dest_dir.mkdir(parents=True, exist_ok=True)
    key = f"{safe_subdir}/{uuid4().hex}.bin"
    path = root / key
    # Ensure final path is under root
    if not str(path.resolve()).startswith(str(root.resolve())):
        raise ValidationAppError("Invalid storage path")
    path.write_bytes(data)
    return key


def make_thumbnail(data: bytes, *, max_size: int = 320) -> bytes:
    img = Image.open(io.BytesIO(data))
    img.thumbnail((max_size, max_size))
    buf = io.BytesIO()
    fmt = "JPEG" if img.mode in ("RGB", "L") else "PNG"
    if img.mode not in ("RGB", "L", "RGBA"):
        img = img.convert("RGB")
        fmt = "JPEG"
    img.save(buf, format=fmt, quality=85)
    return buf.getvalue()


def resolve_storage_path(key: str) -> Path:
    settings = get_settings()
    root = Path(settings.file_storage_path).resolve()
    path = (root / key).resolve()
    if not str(path).startswith(str(root)):
        raise ValidationAppError("Path traversal blocked")
    return path
