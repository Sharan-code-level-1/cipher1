"""Claim lifecycle orchestration."""
from __future__ import annotations

from datetime import datetime, timezone
from typing import List, Optional, Tuple

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.ai.cost_estimator import CostEstimator
from app.ai.damage_detector import DamageDetector
from app.ai.fraud_engine import FraudEngine
from app.core.exceptions import ForbiddenError, NotFoundError, ValidationAppError
from app.models.claim import (
    Claim,
    ClaimImage,
    ClaimStatusHistory,
    CostEstimate,
    DamageDetection,
)
from app.models.fraud import FraudAssessment, FraudSignal
from app.models.user import User
from app.models.vehicle import Policy, Vehicle
from app.services.audit import write_audit
from app.utils.files import (
    extract_exif,
    make_thumbnail,
    perceptual_hash,
    sha256_bytes,
    store_file,
    validate_image_upload,
)
from app.utils.ids import generate_claim_number

VALID_TRANSITIONS = {
    "draft": {"submitted"},
    "submitted": {"ai_processing"},
    "ai_processing": {"fraud_review", "surveyor_review"},
    "fraud_review": {"surveyor_review", "rejected"},
    "surveyor_review": {"approved", "rejected"},
    "approved": {"payment_pending"},
    "payment_pending": {"paid"},
    "paid": {"closed"},
    "rejected": {"closed"},
}


class ClaimService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.detector = DamageDetector()
        self.cost_estimator = CostEstimator()

    async def create_claim(self, user: User, data: dict, *, ip=None, ua=None) -> Claim:
        vehicle = await self.db.get(Vehicle, data["vehicle_id"])
        if not vehicle or (vehicle.owner_id != user.id and user.role == "customer"):
            raise ForbiddenError("Vehicle not accessible")
        if data.get("policy_id"):
            policy = await self.db.get(Policy, data["policy_id"])
            if not policy or policy.vehicle_id != vehicle.id:
                raise ValidationAppError("Policy does not belong to vehicle")

        claim = Claim(
            claim_number=generate_claim_number(),
            customer_id=user.id if user.role == "customer" else vehicle.owner_id,
            vehicle_id=vehicle.id,
            policy_id=data.get("policy_id"),
            status="draft",
            incident_date=data.get("incident_date"),
            incident_location=data.get("incident_location"),
            incident_lat=data.get("incident_lat"),
            incident_lng=data.get("incident_lng"),
            description=data.get("description"),
            metadata_json={},
        )
        self.db.add(claim)
        await self.db.flush()
        self.db.add(
            ClaimStatusHistory(
                claim_id=claim.id, from_status=None, to_status="draft", actor_id=user.id
            )
        )
        await write_audit(
            self.db,
            action="claim.create",
            resource_type="claim",
            resource_id=claim.id,
            actor_id=user.id,
            actor_email=user.email,
            ip_address=ip,
            user_agent=ua,
            after_state={"claim_number": claim.claim_number},
        )
        return claim

    async def get_claim(self, claim_id: str, user: User) -> Claim:
        result = await self.db.execute(
            select(Claim)
            .options(
                selectinload(Claim.images),
                selectinload(Claim.detections),
                selectinload(Claim.cost_estimates),
                selectinload(Claim.fraud_assessments).selectinload(FraudAssessment.signals),
            )
            .where(Claim.id == claim_id)
            .execution_options(populate_existing=True)
        )
        claim = result.scalar_one_or_none()
        if not claim:
            raise NotFoundError("Claim not found")
        self._authorize_read(claim, user)
        return claim

    def _authorize_read(self, claim: Claim, user: User) -> None:
        if user.role == "customer" and claim.customer_id != user.id:
            raise ForbiddenError("Not allowed to access this claim")

    def _authorize_write(self, claim: Claim, user: User) -> None:
        if user.role == "customer":
            if claim.customer_id != user.id or claim.status not in {"draft", "submitted"}:
                raise ForbiddenError("Cannot modify claim in current state")

    async def list_claims(
        self, user: User, *, page: int = 1, page_size: int = 20, status: Optional[str] = None
    ) -> Tuple[List[Claim], int]:
        page = max(1, page)
        page_size = min(100, max(1, page_size))
        q = select(Claim).options(selectinload(Claim.images))
        count_q = select(func.count(Claim.id))
        if user.role == "customer":
            q = q.where(Claim.customer_id == user.id)
            count_q = count_q.where(Claim.customer_id == user.id)
        if status:
            q = q.where(Claim.status == status)
            count_q = count_q.where(Claim.status == status)
        total = (await self.db.execute(count_q)).scalar_one()
        result = await self.db.execute(
            q.order_by(Claim.created_at.desc()).offset((page - 1) * page_size).limit(page_size)
        )
        return list(result.scalars().all()), total

    async def add_image(
        self,
        claim_id: str,
        user: User,
        *,
        filename: str,
        content_type: str,
        data: bytes,
        angle_label: Optional[str] = None,
        ip=None,
        ua=None,
    ) -> ClaimImage:
        claim = await self.get_claim(claim_id, user)
        self._authorize_write(claim, user)
        if claim.status not in {"draft", "submitted"}:
            raise ValidationAppError("Cannot upload images after processing starts")

        mime, safe_name, width, height = validate_image_upload(filename, content_type, data)
        digest = sha256_bytes(data)
        phash = perceptual_hash(data)
        exif = extract_exif(data)
        key = store_file(data, subdir=f"claims/{claim.id}")
        thumb = make_thumbnail(data)
        thumb_key = store_file(thumb, subdir=f"claims/{claim.id}/thumbs")

        image = ClaimImage(
            claim_id=claim.id,
            storage_key=key,
            original_filename=safe_name,
            content_type=mime,
            size_bytes=len(data),
            sha256=digest,
            phash=phash,
            thumbnail_key=thumb_key,
            width=width,
            height=height,
            exif_json=exif,
            angle_label=angle_label,
            virus_scan_status="clean",  # hook for real scanner
        )
        self.db.add(image)
        await self.db.flush()
        await write_audit(
            self.db,
            action="claim.image_upload",
            resource_type="claim_image",
            resource_id=image.id,
            actor_id=user.id,
            actor_email=user.email,
            ip_address=ip,
            user_agent=ua,
            metadata={"claim_id": claim.id, "sha256": digest},
        )
        return image

    async def submit(self, claim_id: str, user: User, *, ip=None, ua=None) -> Claim:
        claim = await self.get_claim(claim_id, user)
        self._authorize_write(claim, user)
        if claim.status != "draft":
            raise ValidationAppError("Only draft claims can be submitted")
        imgs = (
            await self.db.execute(select(ClaimImage).where(ClaimImage.claim_id == claim.id))
        ).scalars().all()
        if not imgs:
            raise ValidationAppError("Upload at least one image before submitting")
        await self._transition(claim, "submitted", user, note="Claim submitted")
        claim.submitted_at = datetime.now(timezone.utc)
        # Kick AI pipeline synchronously for reliability in demo; Celery in workers
        await self.run_ai_pipeline(claim, user)
        await write_audit(
            self.db,
            action="claim.submit",
            resource_type="claim",
            resource_id=claim.id,
            actor_id=user.id,
            actor_email=user.email,
            ip_address=ip,
            user_agent=ua,
        )
        return await self.get_claim(claim.id, user)

    async def run_ai_pipeline(self, claim: Claim, user: User) -> None:
        await self._transition(claim, "ai_processing", user, note="AI pipeline started")
        images = (
            await self.db.execute(select(ClaimImage).where(ClaimImage.claim_id == claim.id))
        ).scalars().all()

        from app.utils.files import resolve_storage_path

        all_damages = []
        max_area = 0.0
        confs = []
        for img in images:
            path = resolve_storage_path(img.storage_key)
            data = path.read_bytes()
            result = self.detector.detect(data, filename=img.original_filename)
            all_damages.extend(result.damages)
            max_area = max(max_area, result.damage_area_pct)
            confs.append(result.confidence)
            det = DamageDetection(
                claim_id=claim.id,
                image_id=img.id,
                model_version=result.model_version,
                parts=result.parts,
                damages=result.damages,
                severity=result.severity,
                damage_area_pct=result.damage_area_pct,
                confidence=result.confidence,
                explanation=result.explanation,
            )
            self.db.add(det)

        from app.ai.severity import classify_severity

        severity = classify_severity(all_damages, max_area)
        claim.severity = severity
        claim.fraud_score = None

        vehicle = await self.db.get(Vehicle, claim.vehicle_id)
        policy = await self.db.get(Policy, claim.policy_id) if claim.policy_id else None

        cost = self.cost_estimator.estimate(
            severity=severity,
            damages=all_damages,
            make=vehicle.make if vehicle else "Generic",
        )
        ce = CostEstimate(
            claim_id=claim.id,
            currency=cost.currency,
            parts_total=cost.parts_total,
            labour_total=cost.labour_total,
            painting_total=cost.painting_total,
            taxes_total=cost.taxes_total,
            grand_total=cost.grand_total,
            repair_days=cost.repair_days,
            line_items=cost.line_items,
            invoice_json=cost.invoice_json,
            explanation=cost.explanation,
        )
        self.db.add(ce)
        claim.estimated_cost = cost.grand_total

        engine = FraudEngine(self.db)
        fraud = await engine.assess(claim, list(images), vehicle=vehicle, policy=policy)
        assessment = FraudAssessment(
            claim_id=claim.id,
            risk_score=fraud.risk_score,
            risk_level=fraud.risk_level,
            summary=fraud.summary,
            explanation=fraud.explanation,
            model_version=fraud.model_version,
        )
        self.db.add(assessment)
        await self.db.flush()
        for s in fraud.signals:
            self.db.add(
                FraudSignal(
                    assessment_id=assessment.id,
                    signal_type=s.signal_type,
                    severity=s.severity,
                    weight=s.weight,
                    message=s.message,
                    evidence=s.evidence,
                )
            )
        claim.fraud_score = fraud.risk_score

        if fraud.risk_level in {"high", "critical"}:
            await self._transition(claim, "fraud_review", user, note=fraud.summary)
        else:
            await self._transition(claim, "surveyor_review", user, note="Ready for surveyor")

    async def update_status(
        self,
        claim_id: str,
        user: User,
        *,
        status: str,
        note: Optional[str] = None,
        approved_amount: Optional[float] = None,
        rejection_reason: Optional[str] = None,
        ip=None,
        ua=None,
    ) -> Claim:
        claim = await self.get_claim(claim_id, user)
        if user.role == "customer":
            raise ForbiddenError("Customers cannot change claim status")
        allowed = VALID_TRANSITIONS.get(claim.status, set())
        if status not in allowed and user.role not in {"admin", "super_admin"}:
            raise ValidationAppError(f"Cannot transition from {claim.status} to {status}")
        if status == "approved" and approved_amount is not None:
            claim.approved_amount = approved_amount
        if status == "rejected":
            claim.rejection_reason = rejection_reason or note
        if status == "surveyor_review" and user.role == "surveyor":
            claim.assigned_surveyor_id = user.id
        if note and user.role in {"surveyor", "insurance_officer", "admin", "super_admin"}:
            claim.surveyor_notes = note
        await self._transition(claim, status, user, note=note)
        await write_audit(
            self.db,
            action="claim.status_change",
            resource_type="claim",
            resource_id=claim.id,
            actor_id=user.id,
            actor_email=user.email,
            ip_address=ip,
            user_agent=ua,
            after_state={"status": status},
            message=note,
        )
        return await self.get_claim(claim.id, user)

    async def _transition(
        self, claim: Claim, to_status: str, user: User, note: Optional[str] = None
    ) -> None:
        history = ClaimStatusHistory(
            claim_id=claim.id,
            from_status=claim.status,
            to_status=to_status,
            actor_id=user.id,
            note=note,
        )
        self.db.add(history)
        claim.status = to_status
        if to_status == "closed":
            claim.closed_at = datetime.now(timezone.utc)
        await self.db.flush()
