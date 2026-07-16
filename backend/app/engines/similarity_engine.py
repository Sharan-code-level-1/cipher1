"""Similarity engine — pHash, embedding (DINOv2 stub), and vector search.

`embed` produces a deterministic, content-derived feature vector standing in for
a DINOv2 image embedding (a real ViT embedding would drop in here unchanged).
`search` finds visually similar images across the evidence store using both
pHash Hamming distance and cosine similarity over stored embeddings.
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

from app.utils.files import perceptual_hash


def _hamming(a: Optional[str], b: Optional[str]) -> Optional[int]:
    if not a or not b or len(a) != len(b):
        return None
    try:
        return bin(int(a, 16) ^ int(b, 16)).count("1")
    except ValueError:
        return None


def _cosine(a: List[float], b: List[float]) -> float:
    if not a or not b or len(a) != len(b):
        return 0.0
    va, vb = np.asarray(a, dtype=np.float32), np.asarray(b, dtype=np.float32)
    na, nb = np.linalg.norm(va), np.linalg.norm(vb)
    if na == 0 or nb == 0:
        return 0.0
    return float(np.dot(va, vb) / (na * nb))


@dataclass
class SimilarityResult:
    phash: Optional[str] = None
    embedding_dim: int = 0
    matches: List[Dict[str, Any]] = field(default_factory=list)
    max_similarity: float = 0.0
    has_near_duplicate: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class SimilarityEngine:
    EMBED_GRID = 16  # 16x16 grid -> 256-dim embedding
    PHASH_NEAR_DUP_THRESHOLD = 8
    COSINE_NEAR_DUP_THRESHOLD = 0.92

    def phash(self, data: bytes) -> str:
        return perceptual_hash(data)

    def embed(self, data: bytes) -> List[float]:
        """DINOv2 stub: deterministic embedding from normalized grayscale grid.

        Downsamples to an EMBED_GRID x EMBED_GRID intensity map and L2-normalizes
        it into a fixed-length vector. Deterministic and content-sensitive, so
        cosine similarity is meaningful without a heavyweight model download.
        """
        pil = Image.open(io.BytesIO(data)).convert("L")
        arr = cv2.resize(
            np.array(pil), (self.EMBED_GRID, self.EMBED_GRID), interpolation=cv2.INTER_AREA
        ).astype(np.float32)
        vec = arr.flatten()
        vec = vec - vec.mean()
        norm = np.linalg.norm(vec)
        if norm > 0:
            vec = vec / norm
        return [round(float(x), 6) for x in vec]

    async def search(
        self,
        db: AsyncSession,
        *,
        claim_id: str,
        phash: Optional[str],
        embedding: List[float],
        limit: int = 500,
    ) -> SimilarityResult:
        from app.models.evidence import EvidenceStore

        result = SimilarityResult(phash=phash, embedding_dim=len(embedding))
        rows = await db.execute(select(EvidenceStore).limit(limit))
        for ev in rows.scalars().all():
            if ev.claim_id == claim_id and not ev.embedding:
                continue
            phash_dist = _hamming(phash, ev.phash)
            cos = _cosine(embedding, ev.embedding or [])
            is_match = (
                (phash_dist is not None and phash_dist <= self.PHASH_NEAR_DUP_THRESHOLD)
                or cos >= self.COSINE_NEAR_DUP_THRESHOLD
            )
            if cos > result.max_similarity:
                result.max_similarity = round(cos, 4)
            if is_match:
                result.matches.append(
                    {
                        "evidence_id": ev.id,
                        "claim_id": ev.claim_id,
                        "cross_claim": ev.claim_id != claim_id,
                        "phash_distance": phash_dist,
                        "cosine_similarity": round(cos, 4),
                    }
                )
        result.has_near_duplicate = any(m["cross_claim"] for m in result.matches)
        return result
