"""Background tasks."""
from __future__ import annotations

import asyncio

from app.workers.celery_app import celery_app
from app.core.logging import get_logger

logger = get_logger("workers")


def _run(coro):
    return asyncio.get_event_loop().run_until_complete(coro)


@celery_app.task(name="claims.process_ai", bind=True, max_retries=3)
def process_claim_ai(self, claim_id: str, actor_id: str) -> dict:
    """Re-run AI pipeline asynchronously if needed."""
    logger.info("process_claim_ai", claim_id=claim_id)
    # Pipeline is also available inline; this task is for scale-out.
    return {"claim_id": claim_id, "status": "queued_complete"}


@celery_app.task(name="notifications.send_email")
def send_email(to: str, subject: str, body: str) -> dict:
    logger.info("send_email", to=to, subject=subject)
    # Console provider for local/dev; swap for SES/SendGrid in prod.
    print(f"[EMAIL] to={to} subject={subject}\n{body}")
    return {"to": to, "status": "sent"}


@celery_app.task(name="notifications.send_sms")
def send_sms(to: str, message: str) -> dict:
    logger.info("send_sms", to=to)
    print(f"[SMS] to={to} message={message}")
    return {"to": to, "status": "sent"}
