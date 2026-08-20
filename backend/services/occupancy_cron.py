from datetime import datetime, timezone, timedelta
from typing import Optional
from sqlalchemy.orm import Session
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger

from backend.db.session import SessionLocal
from backend.models.models import Occupancy, OccupancyStatusEnum, Venue, VenueConfiguration, AuditLog
from backend.services.venue_service import venue_service
from backend.core.logger import get_logger

logger = get_logger(__name__)

# More frequent than retention's 1h since occupancy drift is more
# time-sensitive for a live "currently inside" count.
OCCUPANCY_SWEEP_INTERVAL_MINUTES = 15


def auto_expire_occupancy(trigger: str = "scheduled", db: Optional[Session] = None) -> dict:
    """
    For every active venue, closes any open Occupancy row (exited_at IS NULL)
    whose entered_at is older than that venue's own
    VenueConfiguration.occupancy_auto_expire_hours (default 6h), so the live
    occupancy count doesn't drift upward forever if staff forget to manually
    check someone out. Writes one summary AuditLog row per run.

    `trigger`/`db` follow the same pattern as retention_cron.delete_expired_records
    — "scheduled" for the periodic APScheduler job, "manual" for an
    admin-triggered run; `db` lets callers (tests, the HTTP endpoint) inject
    their own session instead of always opening one against the production
    engine.
    """
    logger.info(f"Running occupancy auto-expire job (trigger={trigger})...")
    owns_session = db is None
    if db is None:
        db = SessionLocal()
    summary = {"trigger": trigger, "expired_count": 0, "occupancy_ids": []}
    try:
        now = datetime.now(timezone.utc)
        venues = db.query(Venue).filter(Venue.is_active.is_(True)).all()

        for venue in venues:
            config = venue_service.get_venue_configuration(db, venue.id)
            hours = config.occupancy_auto_expire_hours or 6
            cutoff = now - timedelta(hours=hours)

            stale_records = (
                db.query(Occupancy)
                .filter(
                    Occupancy.venue_id == venue.id,
                    Occupancy.exited_at.is_(None),
                    Occupancy.entered_at <= cutoff,
                )
                .all()
            )
            for record in stale_records:
                record.exited_at = now
                record.status = OccupancyStatusEnum.AUTO_EXPIRED
                summary["expired_count"] += 1
                summary["occupancy_ids"].append(record.id)

        db.add(AuditLog(user_id=None, action="occupancy_auto_expire", details=summary))
        db.commit()
        logger.info(f"Occupancy auto-expire complete: expired {summary['expired_count']} records.")
    except Exception as e:
        db.rollback()
        logger.error(f"Error during occupancy auto-expire job: {e}")
        summary["error"] = str(e)
    finally:
        if owns_session:
            db.close()

    return summary


def start_occupancy_cron():
    scheduler = BackgroundScheduler()
    scheduler.add_job(
        auto_expire_occupancy,
        trigger=IntervalTrigger(minutes=OCCUPANCY_SWEEP_INTERVAL_MINUTES),
        id='occupancy_auto_expire_job',
        name='Auto-expire stale occupancy records',
        replace_existing=True,
    )
    scheduler.start()
    logger.info(f"Occupancy auto-expire cron started (every {OCCUPANCY_SWEEP_INTERVAL_MINUTES}m).")
