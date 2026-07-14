from sqlalchemy import Column, Integer, String, Float, DateTime, Date, Boolean, JSON
from datetime import date, datetime, timezone
from backend.db.base import Base

class DailyVenueMetrics(Base):
    __tablename__ = "daily_venue_metrics"
    id = Column(Integer, primary_key=True, index=True)
    venue_id = Column(Integer, index=True)
    record_date = Column(Date, default=date.today, index=True)
    
    total_verifications = Column(Integer, default=0)
    approved_count = Column(Integer, default=0)
    denied_count = Column(Integer, default=0)
    manual_review_count = Column(Integer, default=0)
    fraud_review_count = Column(Integer, default=0)
    
    avg_verification_time_ms = Column(Float, default=0.0)
    avg_ocr_time_ms = Column(Float, default=0.0)
    avg_face_time_ms = Column(Float, default=0.0)
    
    ocr_failure_count = Column(Integer, default=0)
    face_failure_count = Column(Integer, default=0)
    
    low_quality_image_count = Column(Integer, default=0)
    blacklist_hits = Column(Integer, default=0)
    
    # Store aggregated demographics/types as JSON mapping for fast UI rendering
    document_types = Column(JSON, default={})
    age_distribution = Column(JSON, default={})
    device_usage = Column(JSON, default={})
    
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
