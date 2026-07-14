import json
import logging
import time
from datetime import date
from sqlalchemy.orm import Session
from backend.db.session import SessionLocal
from backend.models.analytics_models import DailyVenueMetrics
from backend.models.models import SessionStateEnum

logger = logging.getLogger("analytics_worker")
logging.basicConfig(level=logging.INFO)

def process_event(event_type: str, data: dict, db: Session):
    venue_id = data.get("venue_id")
    if not venue_id:
        return
        
    today = date.today()
    metrics = db.query(DailyVenueMetrics).filter(
        DailyVenueMetrics.venue_id == venue_id,
        DailyVenueMetrics.record_date == today
    ).first()
    
    if not metrics:
        metrics = DailyVenueMetrics(venue_id=venue_id, record_date=today)
        db.add(metrics)
        db.commit()
        db.refresh(metrics)
        
    # Increment counts based on event_type
    if event_type == SessionStateEnum.CREATED.value:
        metrics.total_verifications += 1
    elif event_type == SessionStateEnum.APPROVED.value:
        metrics.approved_count += 1
    elif event_type == SessionStateEnum.DENIED.value:
        metrics.denied_count += 1
    elif event_type == SessionStateEnum.FRAUD_REVIEW.value:
        metrics.fraud_review_count += 1
    elif event_type == SessionStateEnum.MANUAL_REVIEW.value:
        metrics.manual_review_count += 1
        
    db.commit()

def run_worker():
    from backend.core.event_bus import event_bus, CH_VERIFICATIONS
    pubsub = event_bus.redis_client.pubsub()
    pubsub.subscribe(CH_VERIFICATIONS)
    
    logger.info(f"Analytics worker listening on channel: {CH_VERIFICATIONS}")
    
    for message in pubsub.listen():
        if message["type"] == "message":
            try:
                payload = json.loads(message["data"])
                event_type = payload.get("type")
                data = payload.get("data", {})
                
                logger.info(f"Received event: {event_type} for venue {data.get('venue_id')}")
                
                with SessionLocal() as db:
                    process_event(event_type, data, db)
            except Exception as e:
                logger.error(f"Error processing event: {e}")

if __name__ == "__main__":
    while True:
        try:
            run_worker()
        except Exception as e:
            logger.error(f"Worker crashed: {e}. Restarting in 5s...")
            time.sleep(5)
