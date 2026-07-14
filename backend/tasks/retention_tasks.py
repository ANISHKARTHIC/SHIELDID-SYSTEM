import logging
from datetime import datetime, timezone
from backend.core.celery_app import celery_app
from backend.db.session import SessionLocal
from backend.models.models import Customer, VerificationSession, SessionStateEnum

logger = logging.getLogger("celery.retention")

@celery_app.task
def cleanup_expired_records():
    """
    Cron task running at 3 AM UTC daily.
    Deletes expired customers and their associated verification sessions 
    to comply with GDPR and Venue Data Retention Policies.
    """
    logger.info("Starting scheduled retention cleanup task")
    db = SessionLocal()
    try:
        now = datetime.now(timezone.utc)
        
        # Find all expired customers (GDPR 30 days or venue specific)
        expired_customers = db.query(Customer).filter(Customer.expires_at < now).all()
        
        count = 0
        for customer in expired_customers:
            # We would typically also delete their images from MinIO here using storage_service
            # Delete associated sessions
            db.query(VerificationSession).filter(VerificationSession.customer_id == customer.id).delete()
            # Delete customer
            db.delete(customer)
            count += 1
            
        db.commit()
        logger.info(f"Retention cleanup completed. Removed {count} expired records.")
        return {"status": "success", "removed_count": count}
    except Exception as e:
        db.rollback()
        logger.error(f"Retention cleanup failed: {e}")
        raise e
    finally:
        db.close()
