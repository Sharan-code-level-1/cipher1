"""
Multi-signal fraud detection engine with explainable scoring.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.claim import Claim, ClaimImage
from app.models.vehicle import Vehicle, Policy


@dataclass
class Signal:
    signal_type: str
    severity: str
    weight: float
    message: str
    evidence: Dict[str, Any] = field(default_factory=dict)


@dataclass
class FraudResult:
    risk_score: float
    risk_level: str
    summary: str
    signals: List[Signal]
    explanation: Dict[str, Any]
    model_version: str = "fraud-engine-1.0"


class FraudEngine:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def assess(
        self,
        claim: Claim,
        images: List[ClaimImage],
        *,
        vehicle: Optional[Vehicle] = None,
        policy: Optional[Policy] = None,
    ) -> FraudResult:
        signals: List[Signal] = []

        signals.extend(await self._duplicate_image_signals(images, claim.id))
        signals.extend(self._exif_signals(images))
        signals.extend(self._metadata_consistency(claim, images))
        signals.extend(await self._repeat_claim_signals(claim))
        signals.extend(self._vin_policy_signals(claim, vehicle, policy))
        signals.extend(self._gps_timestamp_signals(claim, images))
        signals.extend(self._image_edit_signals(images))
        signals.extend(self._multi_angle_signals(images))

        score = min(100.0, sum(s.weight for s in signals))
        level = self._level(score)
        summary = self._summary(level, signals)
        explanation = {
            "risk_score": score,
            "risk_level": level,
            "signal_count": len(signals),
            "top_signals": [
                {"type": s.signal_type, "weight": s.weight, "message": s.message}
                for s in sorted(signals, key=lambda x: x.weight, reverse=True)[:5]
            ],
            "methodology": (
                "Weighted multi-signal ensemble: image hashing, EXIF integrity, "
                "policy/VIN consistency, temporal/geo checks, ELA-style edit cues, "
                "and claim history. Score is capped at 100."
            ),
        }
        return FraudResult(
            risk_score=round(score, 2),
            risk_level=level,
            summary=summary,
            signals=signals,
            explanation=explanation,
        )

    async def _duplicate_image_signals(self, images: List[ClaimImage], claim_id: str) -> List[Signal]:
        out: List[Signal] = []
        seen_sha: dict[str, str] = {}
        for img in images:
            if img.sha256 in seen_sha:
                out.append(
                    Signal(
                        "duplicate_images",
                        "high",
                        25,
                        "Identical image content uploaded more than once on this claim",
                        {"sha256": img.sha256},
                    )
                )
            seen_sha[img.sha256] = img.id

            # Cross-claim hash match
            q = await self.db.execute(
                select(ClaimImage).where(
                    ClaimImage.sha256 == img.sha256, ClaimImage.claim_id != claim_id
                ).limit(1)
            )
            if q.scalar_one_or_none():
                out.append(
                    Signal(
                        "image_hash_matching",
                        "critical",
                        40,
                        "Image SHA-256 matches a file from another claim",
                        {"sha256": img.sha256},
                    )
                )
            if img.phash:
                q2 = await self.db.execute(
                    select(ClaimImage).where(
                        ClaimImage.phash == img.phash, ClaimImage.claim_id != claim_id
                    ).limit(1)
                )
                if q2.scalar_one_or_none():
                    out.append(
                        Signal(
                            "image_similarity_search",
                            "high",
                            30,
                            "Perceptual hash collision with image from another claim",
                            {"phash": img.phash},
                        )
                    )
        return out

    def _exif_signals(self, images: List[ClaimImage]) -> List[Signal]:
        out: List[Signal] = []
        for img in images:
            exif = img.exif_json or {}
            if not exif:
                out.append(
                    Signal(
                        "metadata_tampering",
                        "medium",
                        8,
                        f"Image {img.original_filename} has stripped EXIF metadata",
                        {"image_id": img.id},
                    )
                )
                continue
            software = str(exif.get("Software", "")).lower()
            if any(x in software for x in ("photoshop", "gimp", "snapseed", "picsart")):
                out.append(
                    Signal(
                        "photoshop_detection",
                        "high",
                        20,
                        f"Editing software detected in EXIF: {exif.get('Software')}",
                        {"image_id": img.id, "software": exif.get("Software")},
                    )
                )
            if "DateTime" in exif and "DateTimeOriginal" in exif:
                if exif["DateTime"] != exif["DateTimeOriginal"]:
                    out.append(
                        Signal(
                            "exif_manipulation",
                            "medium",
                            12,
                            "EXIF DateTime differs from DateTimeOriginal",
                            {"image_id": img.id},
                        )
                    )
        return out

    def _metadata_consistency(self, claim: Claim, images: List[ClaimImage]) -> List[Signal]:
        out: List[Signal] = []
        if claim.incident_date:
            for img in images:
                dto = (img.exif_json or {}).get("DateTimeOriginal")
                if not dto:
                    continue
                # Soft check — format varies
                try:
                    # EXIF often "YYYY:MM:DD HH:MM:SS"
                    parsed = datetime.strptime(dto[:19], "%Y:%m:%d %H:%M:%S").replace(
                        tzinfo=timezone.utc
                    )
                    delta = abs((parsed - claim.incident_date).total_seconds())
                    if delta > 7 * 24 * 3600:
                        out.append(
                            Signal(
                                "timestamp_inconsistency",
                                "high",
                                18,
                                "Photo EXIF timestamp differs from incident date by >7 days",
                                {"image_id": img.id, "exif": dto},
                            )
                        )
                except Exception:
                    pass
        return out

    async def _repeat_claim_signals(self, claim: Claim) -> List[Signal]:
        out: List[Signal] = []
        q = await self.db.execute(
            select(Claim).where(
                Claim.customer_id == claim.customer_id,
                Claim.id != claim.id,
                Claim.status.notin_(["draft", "rejected", "closed"]),
            )
        )
        others = q.scalars().all()
        if len(others) >= 3:
            out.append(
                Signal(
                    "repeated_claims",
                    "medium",
                    15,
                    f"Customer has {len(others)} other open/historical claims",
                    {"count": len(others)},
                )
            )
        same_vehicle = [c for c in others if c.vehicle_id == claim.vehicle_id]
        if len(same_vehicle) >= 2:
            out.append(
                Signal(
                    "repeated_claims",
                    "high",
                    22,
                    "Multiple claims on the same vehicle",
                    {"vehicle_id": claim.vehicle_id, "count": len(same_vehicle)},
                )
            )
        return out

    def _vin_policy_signals(
        self, claim: Claim, vehicle: Optional[Vehicle], policy: Optional[Policy]
    ) -> List[Signal]:
        out: List[Signal] = []
        if not vehicle:
            out.append(Signal("vin_mismatch", "high", 20, "Vehicle record missing for claim", {}))
            return out
        if policy and policy.vehicle_id != vehicle.id:
            out.append(
                Signal(
                    "policy_mismatch",
                    "critical",
                    35,
                    "Policy is not linked to the claimed vehicle",
                    {"policy_id": policy.id, "vehicle_id": vehicle.id},
                )
            )
        if policy and policy.status != "active":
            out.append(
                Signal(
                    "policy_mismatch",
                    "high",
                    25,
                    f"Policy status is '{policy.status}'",
                    {"policy_id": policy.id},
                )
            )
        if policy and claim.incident_date:
            idate = claim.incident_date.date()
            if idate < policy.start_date or idate > policy.end_date:
                out.append(
                    Signal(
                        "policy_mismatch",
                        "critical",
                        40,
                        "Incident date outside policy coverage window",
                        {
                            "incident": str(idate),
                            "start": str(policy.start_date),
                            "end": str(policy.end_date),
                        },
                    )
                )
        if vehicle.vin and len(vehicle.vin) not in (11, 17):
            out.append(
                Signal("vin_mismatch", "medium", 10, "VIN length is non-standard", {"vin": vehicle.vin})
            )
        return out

    def _gps_timestamp_signals(self, claim: Claim, images: List[ClaimImage]) -> List[Signal]:
        out: List[Signal] = []
        if claim.incident_lat is not None and abs(claim.incident_lat) < 0.01 and abs(claim.incident_lng or 0) < 0.01:
            out.append(
                Signal(
                    "fake_gps",
                    "medium",
                    12,
                    "Incident GPS coordinates near null island (0,0)",
                    {"lat": claim.incident_lat, "lng": claim.incident_lng},
                )
            )
        return out

    def _image_edit_signals(self, images: List[ClaimImage]) -> List[Signal]:
        """Lightweight edit heuristics (ELA/noise proxies without heavy CV)."""
        out: List[Signal] = []
        for img in images:
            # Extremely small files relative to resolution can indicate re-compression artifacts
            if img.width and img.height and img.size_bytes:
                bpp = img.size_bytes / max(img.width * img.height, 1)
                if bpp < 0.05:
                    out.append(
                        Signal(
                            "image_editing",
                            "low",
                            6,
                            "Unusually high compression may indicate re-export/editing",
                            {"image_id": img.id, "bytes_per_pixel": round(bpp, 4)},
                        )
                    )
            if img.content_type == "image/png" and img.size_bytes > 8_000_000:
                out.append(
                    Signal(
                        "ai_generated_images",
                        "low",
                        5,
                        "Large PNG payload can correlate with synthetic imagery",
                        {"image_id": img.id},
                    )
                )
        return out

    def _multi_angle_signals(self, images: List[ClaimImage]) -> List[Signal]:
        if len(images) < 2:
            return [
                Signal(
                    "multi_angle_verification",
                    "medium",
                    10,
                    "Fewer than 2 images provided; multi-angle verification failed",
                    {"count": len(images)},
                )
            ]
        return []

    @staticmethod
    def _level(score: float) -> str:
        if score >= 70:
            return "critical"
        if score >= 45:
            return "high"
        if score >= 20:
            return "medium"
        return "low"

    @staticmethod
    def _summary(level: str, signals: List[Signal]) -> str:
        if not signals:
            return "No fraud signals detected. Risk is low."
        top = sorted(signals, key=lambda s: s.weight, reverse=True)[:3]
        parts = "; ".join(s.message for s in top)
        return f"Fraud risk level '{level}'. Key findings: {parts}."
