"""Risk engine — explainable evidence-risk scoring.

Combines image metadata analysis, layered-engine evidence (validation duplicates,
verification plate match, cross-claim similarity), and claim/policy consistency
rules into a weighted, capped risk score with human-readable signals.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.claim import Claim, ClaimImage
from app.models.vehicle import Policy, Vehicle


@dataclass
class RiskSignal:
    signal_type: str
    severity: str
    weight: float
    message: str
    evidence: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class RiskResult:
    risk_score: float
    risk_level: str
    summary: str
    signals: List[RiskSignal] = field(default_factory=list)
    metadata_findings: Dict[str, Any] = field(default_factory=dict)
    rules_fired: List[str] = field(default_factory=list)
    explanation: Dict[str, Any] = field(default_factory=dict)
    model_version: str = "risk-engine-1.0"


@dataclass
class EvidenceInput:
    """One image's evidence, as produced by the evidence engine."""

    image: ClaimImage
    validation: Dict[str, Any] = field(default_factory=dict)
    verification: Dict[str, Any] = field(default_factory=dict)
    similarity: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)


class RiskEngine:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def assess(
        self,
        claim: Claim,
        evidence: List[EvidenceInput],
        *,
        vehicle: Optional[Vehicle] = None,
        policy: Optional[Policy] = None,
    ) -> RiskResult:
        signals: List[RiskSignal] = []
        rules_fired: List[str] = []

        signals += self._duplicate_signals(evidence, rules_fired)
        signals += self._verification_signals(evidence, rules_fired)
        signals += self._metadata_signals(claim, evidence, rules_fired)
        signals += self._quality_signals(evidence, rules_fired)
        signals += await self._repeat_claim_signals(claim, rules_fired)
        signals += self._policy_signals(claim, vehicle, policy, rules_fired)
        signals += self._gps_signals(claim, rules_fired)
        signals += self._multi_angle_signals(evidence, rules_fired)

        score = min(100.0, sum(s.weight for s in signals))
        level = self._level(score)
        summary = self._summary(level, signals)

        metadata_findings = {
            "images_analyzed": len(evidence),
            "images_missing_exif": sum(1 for e in evidence if not e.metadata.get("has_exif")),
            "editing_software_detected": [
                e.metadata.get("software")
                for e in evidence
                if e.metadata.get("software")
                and any(
                    x in str(e.metadata.get("software")).lower()
                    for x in ("photoshop", "gimp", "snapseed", "picsart")
                )
            ],
            "cross_claim_duplicates": sum(
                1 for e in evidence if e.similarity.get("has_near_duplicate")
            ),
        }
        explanation = {
            "risk_score": round(score, 2),
            "risk_level": level,
            "signal_count": len(signals),
            "top_signals": [
                {"type": s.signal_type, "weight": s.weight, "message": s.message}
                for s in sorted(signals, key=lambda x: x.weight, reverse=True)[:5]
            ],
            "methodology": (
                "Weighted multi-signal ensemble over layered evidence: validation "
                "duplicates, verification plate match, EXIF/metadata integrity, "
                "cross-claim similarity, policy/VIN consistency, temporal/geo checks, "
                "and claim history. Score capped at 100."
            ),
        }
        return RiskResult(
            risk_score=round(score, 2),
            risk_level=level,
            summary=summary,
            signals=signals,
            metadata_findings=metadata_findings,
            rules_fired=rules_fired,
            explanation=explanation,
        )

    # ---- rule groups -------------------------------------------------
    def _duplicate_signals(
        self, evidence: List[EvidenceInput], fired: List[str]
    ) -> List[RiskSignal]:
        out: List[RiskSignal] = []
        for e in evidence:
            val = e.validation or {}
            sim = e.similarity or {}
            for dup in val.get("duplicate_of", []):
                scope = dup.get("scope")
                if scope == "cross_claim":
                    fired.append("cross_claim_hash_match")
                    out.append(RiskSignal(
                        "image_hash_matching", "critical", 40,
                        "Image matches a file from another claim",
                        {"detail": dup},
                    ))
                elif scope in ("same_claim", "same_claim_batch"):
                    fired.append("duplicate_within_claim")
                    out.append(RiskSignal(
                        "duplicate_images", "high", 20,
                        "Identical image uploaded more than once on this claim",
                        {"detail": dup},
                    ))
            for m in sim.get("matches", []):
                if m.get("cross_claim"):
                    fired.append("cross_claim_similarity")
                    out.append(RiskSignal(
                        "image_similarity_search", "high", 30,
                        "Perceptually similar image found on another claim",
                        {"match": m},
                    ))
        return out

    def _verification_signals(
        self, evidence: List[EvidenceInput], fired: List[str]
    ) -> List[RiskSignal]:
        out: List[RiskSignal] = []
        any_plate = False
        for e in evidence:
            ver = e.verification or {}
            if ver.get("plate_detected"):
                any_plate = True
            if ver.get("vehicle_match") is False:
                fired.append("plate_mismatch")
                out.append(RiskSignal(
                    "vehicle_verification", "high", 25,
                    "Detected number plate does not match the claimed vehicle registration",
                    {"match_score": ver.get("match_score"), "plate_text": ver.get("plate_text")},
                ))
        if evidence and not any_plate:
            fired.append("no_plate_detected")
            out.append(RiskSignal(
                "vehicle_verification", "low", 6,
                "No number plate detected in any image to verify vehicle identity",
                {"image_count": len(evidence)},
            ))
        return out

    def _metadata_signals(
        self, claim: Claim, evidence: List[EvidenceInput], fired: List[str]
    ) -> List[RiskSignal]:
        out: List[RiskSignal] = []
        for e in evidence:
            meta = e.metadata or {}
            exif = meta.get("exif") or {}
            if not meta.get("has_exif"):
                fired.append("stripped_exif")
                out.append(RiskSignal(
                    "metadata_tampering", "medium", 8,
                    f"Image {e.image.original_filename} has stripped EXIF metadata",
                    {"image_id": e.image.id},
                ))
                continue
            software = str(meta.get("software") or "").lower()
            if any(x in software for x in ("photoshop", "gimp", "snapseed", "picsart")):
                fired.append("editing_software")
                out.append(RiskSignal(
                    "photoshop_detection", "high", 20,
                    f"Editing software detected in EXIF: {meta.get('software')}",
                    {"image_id": e.image.id, "software": meta.get("software")},
                ))
            dto = meta.get("datetime_original")
            if dto and claim.incident_date:
                try:
                    parsed = datetime.strptime(str(dto)[:19], "%Y:%m:%d %H:%M:%S").replace(
                        tzinfo=timezone.utc
                    )
                    if abs((parsed - claim.incident_date).total_seconds()) > 7 * 24 * 3600:
                        fired.append("timestamp_inconsistency")
                        out.append(RiskSignal(
                            "timestamp_inconsistency", "high", 18,
                            "Photo EXIF timestamp differs from incident date by >7 days",
                            {"image_id": e.image.id, "exif": dto},
                        ))
                except Exception:
                    pass
        return out

    def _quality_signals(
        self, evidence: List[EvidenceInput], fired: List[str]
    ) -> List[RiskSignal]:
        out: List[RiskSignal] = []
        low_quality = [e for e in evidence if not (e.validation or {}).get("is_valid", True)]
        if low_quality:
            fired.append("low_quality_evidence")
            out.append(RiskSignal(
                "evidence_quality", "low", 5,
                f"{len(low_quality)} image(s) failed quality validation",
                {"count": len(low_quality)},
            ))
        return out

    async def _repeat_claim_signals(self, claim: Claim, fired: List[str]) -> List[RiskSignal]:
        out: List[RiskSignal] = []
        q = await self.db.execute(
            select(Claim).where(
                Claim.customer_id == claim.customer_id,
                Claim.id != claim.id,
                Claim.status.notin_(["draft", "rejected", "closed"]),
            )
        )
        others = q.scalars().all()
        if len(others) >= 3:
            fired.append("repeated_claims")
            out.append(RiskSignal(
                "repeated_claims", "medium", 15,
                f"Customer has {len(others)} other open/historical claims",
                {"count": len(others)},
            ))
        same_vehicle = [c for c in others if c.vehicle_id == claim.vehicle_id]
        if len(same_vehicle) >= 2:
            fired.append("repeated_vehicle_claims")
            out.append(RiskSignal(
                "repeated_claims", "high", 22,
                "Multiple claims on the same vehicle",
                {"vehicle_id": claim.vehicle_id, "count": len(same_vehicle)},
            ))
        return out

    def _policy_signals(
        self,
        claim: Claim,
        vehicle: Optional[Vehicle],
        policy: Optional[Policy],
        fired: List[str],
    ) -> List[RiskSignal]:
        out: List[RiskSignal] = []
        if not vehicle:
            fired.append("missing_vehicle")
            out.append(RiskSignal("vin_mismatch", "high", 20, "Vehicle record missing for claim", {}))
            return out
        if policy and policy.vehicle_id != vehicle.id:
            fired.append("policy_vehicle_mismatch")
            out.append(RiskSignal(
                "policy_mismatch", "critical", 35,
                "Policy is not linked to the claimed vehicle",
                {"policy_id": policy.id, "vehicle_id": vehicle.id},
            ))
        if policy and policy.status != "active":
            fired.append("policy_inactive")
            out.append(RiskSignal(
                "policy_mismatch", "high", 25, f"Policy status is '{policy.status}'",
                {"policy_id": policy.id},
            ))
        if policy and claim.incident_date:
            idate = claim.incident_date.date()
            if idate < policy.start_date or idate > policy.end_date:
                fired.append("incident_outside_coverage")
                out.append(RiskSignal(
                    "policy_mismatch", "critical", 40,
                    "Incident date outside policy coverage window",
                    {"incident": str(idate), "start": str(policy.start_date), "end": str(policy.end_date)},
                ))
        if vehicle.vin and len(vehicle.vin) not in (11, 17):
            fired.append("vin_length")
            out.append(RiskSignal("vin_mismatch", "medium", 10, "VIN length is non-standard", {"vin": vehicle.vin}))
        return out

    def _gps_signals(self, claim: Claim, fired: List[str]) -> List[RiskSignal]:
        out: List[RiskSignal] = []
        if (
            claim.incident_lat is not None
            and abs(claim.incident_lat) < 0.01
            and abs(claim.incident_lng or 0) < 0.01
        ):
            fired.append("null_island_gps")
            out.append(RiskSignal(
                "fake_gps", "medium", 12, "Incident GPS coordinates near null island (0,0)",
                {"lat": claim.incident_lat, "lng": claim.incident_lng},
            ))
        return out

    def _multi_angle_signals(
        self, evidence: List[EvidenceInput], fired: List[str]
    ) -> List[RiskSignal]:
        if len(evidence) < 2:
            fired.append("insufficient_angles")
            return [RiskSignal(
                "multi_angle_verification", "medium", 10,
                "Fewer than 2 images provided; multi-angle verification failed",
                {"count": len(evidence)},
            )]
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
    def _summary(level: str, signals: List[RiskSignal]) -> str:
        if not signals:
            return "No risk signals detected. Evidence risk is low."
        top = sorted(signals, key=lambda s: s.weight, reverse=True)[:3]
        return f"Evidence risk level '{level}'. Key findings: {'; '.join(s.message for s in top)}."
