"""Validation engine (Layer 1).

Performs image-quality validation and duplicate detection. Quality checks use
real pixel analysis (resolution, blur, exposure); duplicate checks combine an
exact SHA-256 match with perceptual-hash (pHash Hamming distance) near-duplicate
detection, both within the current claim and across other claims in the DB.
"""
from __future__ import annotations

import io
from dataclasses import asdict, dataclass, field
from typing import Any, Dict, List, Optional

import cv2
import numpy as np
from PIL import Image
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.claim import ClaimImage


def _hamming(a: Optional[str], b: Optional[str]) -> Optional[int]:
    """Hamming distance between two hex pHash strings of equal length."""
    if not a or not b or len(a) != len(b):
        return None
    try:
        ia, ib = int(a, 16), int(b, 16)
    except ValueError:
        return None
    return bin(ia ^ ib).count("1")


@dataclass
class ValidationResult:
    is_valid: bool = True
    quality_score: float = 1.0
    issues: List[str] = field(default_factory=list)
    is_duplicate: bool = False
    duplicate_of: List[Dict[str, Any]] = field(default_factory=list)
    metrics: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class ValidationEngine:
    # pHash Hamming distance <= threshold is treated as a near-duplicate.
    PHASH_NEAR_DUP_THRESHOLD = 8

    def _quality(self, data: bytes) -> Dict[str, Any]:
        pil = Image.open(io.BytesIO(data)).convert("RGB")
        arr = cv2.cvtColor(np.array(pil), cv2.COLOR_RGB2BGR)
        gray = cv2.cvtColor(arr, cv2.COLOR_BGR2GRAY)
        h, w = gray.shape[:2]
        blur = float(cv2.Laplacian(gray, cv2.CV_64F).var())
        brightness = float(gray.mean())
        return {
            "width": w,
            "height": h,
            "megapixels": round((w * h) / 1_000_000, 2),
            "blur_variance": round(blur, 2),
            "brightness": round(brightness, 2),
        }

    async def validate(
        self,
        db: AsyncSession,
        *,
        claim_id: str,
        sha256: str,
        phash: Optional[str],
        data: bytes,
        seen_hashes: Optional[Dict[str, str]] = None,
    ) -> ValidationResult:
        result = ValidationResult()
        seen_hashes = seen_hashes if seen_hashes is not None else {}

        # ---- Quality checks -------------------------------------------
        m = self._quality(data)
        result.metrics = m
        score = 1.0
        if m["blur_variance"] < 40:
            result.issues.append("Image appears blurry (low focus variance)")
            score -= 0.3
        if m["brightness"] < 35:
            result.issues.append("Image is underexposed / too dark")
            score -= 0.2
        elif m["brightness"] > 225:
            result.issues.append("Image is overexposed / washed out")
            score -= 0.2
        if m["megapixels"] < 0.3:
            result.issues.append("Image resolution is low")
            score -= 0.2
        result.quality_score = round(max(0.0, score), 2)

        # ---- Duplicate within this upload batch -----------------------
        if sha256 in seen_hashes:
            result.is_duplicate = True
            result.duplicate_of.append({"scope": "same_claim_batch", "sha256": sha256})
        seen_hashes[sha256] = sha256

        # ---- Exact duplicate within claim / cross-claim ---------------
        exact = await db.execute(
            select(ClaimImage).where(ClaimImage.sha256 == sha256).limit(5)
        )
        for img in exact.scalars().all():
            scope = "same_claim" if img.claim_id == claim_id else "cross_claim"
            result.is_duplicate = True
            result.duplicate_of.append(
                {"scope": scope, "sha256": sha256, "image_id": img.id, "claim_id": img.claim_id}
            )

        # ---- Perceptual near-duplicate --------------------------------
        if phash:
            candidates = await db.execute(
                select(ClaimImage).where(ClaimImage.phash.isnot(None)).limit(500)
            )
            for img in candidates.scalars().all():
                dist = _hamming(phash, img.phash)
                if dist is not None and 0 <= dist <= self.PHASH_NEAR_DUP_THRESHOLD:
                    if img.sha256 == sha256:
                        continue  # already captured as exact match
                    scope = "same_claim" if img.claim_id == claim_id else "cross_claim"
                    result.is_duplicate = True
                    result.duplicate_of.append(
                        {
                            "scope": scope,
                            "phash_distance": dist,
                            "image_id": img.id,
                            "claim_id": img.claim_id,
                        }
                    )

        result.is_valid = result.quality_score >= 0.4
        return result
