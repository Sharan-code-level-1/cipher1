"""Image engine — ingestion, secure storage, hashing, and metadata extraction.

This is the entry layer of the evidence pipeline. It wraps the low-level
`app.utils.files` helpers behind a stable, engine-shaped interface so the rest
of the pipeline consumes a single `ImageArtifact` value object.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Dict, Optional

from app.utils.files import (
    extract_exif,
    make_thumbnail,
    perceptual_hash,
    resolve_storage_path,
    sha256_bytes,
    store_file,
    validate_image_upload,
)


@dataclass
class ImageArtifact:
    """Everything the pipeline needs to know about one stored image."""

    storage_key: str
    thumbnail_key: Optional[str]
    original_filename: str
    content_type: str
    size_bytes: int
    sha256: str
    phash: Optional[str]
    width: Optional[int]
    height: Optional[int]
    exif: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class ImageEngine:
    """Validates, fingerprints, and persists uploaded claim images."""

    def ingest(
        self,
        *,
        filename: str,
        content_type: str,
        data: bytes,
        subdir: str,
    ) -> ImageArtifact:
        """Validate + store a raw upload, returning a fingerprinted artifact."""
        mime, safe_name, width, height = validate_image_upload(filename, content_type, data)
        digest = sha256_bytes(data)
        phash = perceptual_hash(data)
        exif = extract_exif(data)

        storage_key = store_file(data, subdir=subdir)
        thumb = make_thumbnail(data)
        thumb_key = store_file(thumb, subdir=f"{subdir}/thumbs")

        return ImageArtifact(
            storage_key=storage_key,
            thumbnail_key=thumb_key,
            original_filename=safe_name,
            content_type=mime,
            size_bytes=len(data),
            sha256=digest,
            phash=phash,
            width=width,
            height=height,
            exif=exif,
        )

    def load_bytes(self, storage_key: str) -> bytes:
        """Read stored image bytes back for downstream analysis."""
        return resolve_storage_path(storage_key).read_bytes()

    def metadata(self, data: bytes) -> Dict[str, Any]:
        """Return a normalized metadata snapshot for an image payload."""
        exif = extract_exif(data)
        return {
            "sha256": sha256_bytes(data),
            "phash": perceptual_hash(data),
            "size_bytes": len(data),
            "exif": exif,
            "has_exif": bool(exif),
            "software": exif.get("Software"),
            "datetime_original": exif.get("DateTimeOriginal"),
            "gps": exif.get("GPSInfo"),
        }
