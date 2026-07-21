import threading
from datetime import datetime, timezone
from sqlalchemy.orm import Session
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger

from backend.db.session import SessionLocal
from backend.models.models import Customer, VerificationSession
from backend.services.storage_service import storage_service
from backend.core.logger import get_logger

logger = get_logger(__name__)

def delete_expired_records():
    """Scans the database and deletes expired PII/face embeddings and MinIO images."""
    logger.info("Running GDPR data retention cron job...")
    db: Session = SessionLocal()
    try:
        now = datetime.now(timezone.utc)
        
        # 1. Find all expired customers (GDPR 30-day or custom retention)
        expired_customers = db.query(Customer).filter(Customer.expires_at <= now).all()
        for customer in expired_customers:
            logger.info(f"Anonymizing expired customer ID {customer.id}")
            customer.name = "Anonymized"
            customer.dob = None
            customer.face_embedding = None
            
            # Also find all logs for this customer and delete the images from MinIO
            sessions = db.query(VerificationSession).filter(VerificationSession.customer_id == customer.id).all()
            for session in sessions:
                if session.id_image_path:
                    storage_service.delete_image(session.id_image_path)
                    session.id_image_path = None
                if session.face_image_path:
                    storage_service.delete_image(session.face_image_path)
                    session.face_image_path = None
                    
            db.commit()
            
        logger.info(f"Deleted PII for {len(expired_customers)} expired records.")
    except Exception as e:
        db.rollback()
        logger.error(f"Error during retention cron: {e}")
    finally:
        db.close()

def start_retention_cron():
    scheduler = BackgroundScheduler()
    # Run every 24 hours in production, but for demo run every hour
    scheduler.add_job(
        delete_expired_records,
        trigger=IntervalTrigger(hours=1),
        id='retention_cron_job',
        name='Delete expired GDPR data',
        replace_existing=True
    )
    scheduler.start()
    logger.info("Retention cron scheduler started.")

