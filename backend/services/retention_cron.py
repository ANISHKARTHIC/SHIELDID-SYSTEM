from datetime import datetime, timezone
from typing import Optional
from sqlalchemy.orm import Session
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger

from backend.db.session import SessionLocal
from backend.models.models import Customer, VerificationSession, Blacklist, AuditLog, Document
from backend.services.storage_service import storage_service
from backend.core.logger import get_logger

logger = get_logger(__name__)

# How often the retention job runs. Anonymizing within an hour of a record
# becoming eligible (rather than, say, once a day) keeps stale PII exposure
# short without needing a separate always-on worker process.
RETENTION_INTERVAL_HOURS = 1


def delete_expired_records(trigger: str = "scheduled", db: Optional[Session] = None) -> dict:
    """
    Anonymizes PII (and deletes MinIO images) for customers whose
    Customer.expires_at has passed, skipping anyone with an active
    (non-expired) blacklist entry. Writes one summary AuditLog row per run.

    `trigger` is "scheduled" for the periodic APScheduler job or "manual"
    when invoked via the admin-triggered endpoint, so the audit trail can
    distinguish the two.

    `db` lets callers (the HTTP endpoint, tests) supply their own session —
    e.g. so the endpoint uses the same request-scoped session FastAPI's
    dependency-injected/overridden `get_db` provides, rather than always
    opening a fresh one against the production engine directly. Falls back
    to a standalone SessionLocal() for the APScheduler job, which has no
    request context to inject from.
    """
    logger.info(f"Running data retention job (trigger={trigger})...")
    owns_session = db is None
    if db is None:
        db = SessionLocal()
    summary = {"trigger": trigger, "anonymized_count": 0, "skipped_blacklisted_count": 0, "customer_ids": []}
    try:
        now = datetime.now(timezone.utc)

        expired_customers = (
            db.query(Customer)
            .filter(Customer.expires_at <= now)
            .filter(Customer.is_anonymized.is_(False))
            .all()
        )

        for customer in expired_customers:
            active_ban = (
                db.query(Blacklist)
                .filter(Blacklist.customer_id == customer.id)
                .filter((Blacklist.expiry_date.is_(None)) | (Blacklist.expiry_date > now))
                .first()
            )
            if active_ban:
                summary["skipped_blacklisted_count"] += 1
                continue

            logger.info(f"Anonymizing expired customer ID {customer.id}")
            customer.name = "Anonymized"
            customer.dob = None
            customer.face_embedding = None
            customer.is_anonymized = True

            sessions = db.query(VerificationSession).filter(VerificationSession.customer_id == customer.id).all()
            for session in sessions:
                if session.id_image_path:
                    storage_service.delete_image(session.id_image_path)
                    session.id_image_path = None
                if session.face_image_path:
                    storage_service.delete_image(session.face_image_path)
                    session.face_image_path = None

            # Document.extracted_data is the full raw OCR dict (name, DOB,
            # address, licence number, ...) captured at finalize time — it
            # was never touched by this job, so a "successfully anonymized"
            # customer's actual name/DOB/licence number stayed retrievable
            # verbatim by joining Document.customer_id. doc_number carries
            # the same PII independently of extracted_data, so clear both.
            documents = db.query(Document).filter(Document.customer_id == customer.id).all()
            for document in documents:
                document.extracted_data = None
                document.doc_number = None

            summary["anonymized_count"] += 1
            summary["customer_ids"].append(customer.id)

        db.add(AuditLog(user_id=None, action="retention_cleanup", details=summary))
        db.commit()
        logger.info(
            f"Retention job complete: anonymized {summary['anonymized_count']}, "
            f"skipped {summary['skipped_blacklisted_count']} blacklisted."
        )
    except Exception as e:
        db.rollback()
        logger.error(f"Error during retention job: {e}")
        summary["error"] = str(e)
    finally:
        if owns_session:
            db.close()

    return summary


def start_retention_cron():
    scheduler = BackgroundScheduler()
    scheduler.add_job(
        delete_expired_records,
        trigger=IntervalTrigger(hours=RETENTION_INTERVAL_HOURS),
        id='retention_cron_job',
        name='Anonymize expired customer data',
        replace_existing=True,
    )
    scheduler.start()
    logger.info(f"Retention cron scheduler started (every {RETENTION_INTERVAL_HOURS}h).")
