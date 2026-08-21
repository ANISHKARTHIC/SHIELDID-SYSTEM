from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import func
from datetime import date, timedelta
from typing import List, Optional

from backend.api.deps import get_db, get_current_active_user, RoleChecker
from backend.models.analytics_models import DailyVenueMetrics
from backend.models.models import Venue, User, RoleEnum

router = APIRouter(prefix="/api/v1/analytics", tags=["analytics"], dependencies=[Depends(get_current_active_user)])
require_super_admin = RoleChecker([RoleEnum.super_admin])

@router.get("/dashboard")
async def get_dashboard_metrics(
    venue_id: Optional[int] = None,
    days: int = Query(7, ge=1, le=365),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Aggregate metrics for the main dashboard over a time window."""
    start_date = date.today() - timedelta(days=days)

    # Defaults to the caller's own venue; only super_admin may request
    # another venue's (or, by omitting the check, all venues') metrics.
    # Previously any authenticated user — including door_staff — could
    # pass any venue_id, or omit it entirely to aggregate every venue's
    # fraud/approval counts system-wide.
    if current_user.role != RoleEnum.super_admin:
        venue_id = current_user.venue_id

    query = db.query(
        func.sum(DailyVenueMetrics.total_verifications).label("total"),
        func.sum(DailyVenueMetrics.approved_count).label("approved"),
        func.sum(DailyVenueMetrics.denied_count).label("denied"),
        func.sum(DailyVenueMetrics.manual_review_count).label("manual_review"),
        func.sum(DailyVenueMetrics.fraud_review_count).label("fraud_review"),
        func.avg(DailyVenueMetrics.avg_verification_time_ms).label("avg_time_ms")
    ).filter(DailyVenueMetrics.record_date >= start_date)

    if venue_id:
        query = query.filter(DailyVenueMetrics.venue_id == venue_id)

    result = query.first()
    
    return {
        "period_days": days,
        "total_verifications": result.total or 0,
        "approved": result.approved or 0,
        "denied": result.denied or 0,
        "fraud_reviews": result.fraud_review or 0,
        "manual_reviews": result.manual_review or 0,
        "average_verification_time_ms": float(result.avg_time_ms or 0)
    }

@router.get("/venues", dependencies=[Depends(require_super_admin)])
async def get_venue_performance(
    days: int = Query(30, ge=1, le=365),
    db: Session = Depends(get_db)
):
    """Compare performance metrics across all venues. Super-admin only —
    this is inherently a cross-venue comparison (every venue's name mapped
    to its fraud-attempt count), which a single venue's own staff have no
    legitimate need to see about other businesses."""
    start_date = date.today() - timedelta(days=days)
    
    results = db.query(
        Venue.name,
        func.sum(DailyVenueMetrics.total_verifications).label("total"),
        func.sum(DailyVenueMetrics.fraud_review_count).label("fraud")
    ).join(DailyVenueMetrics, Venue.id == DailyVenueMetrics.venue_id)\
     .filter(DailyVenueMetrics.record_date >= start_date)\
     .group_by(Venue.name).all()
     
    return [{"venue": r.name, "total_verifications": r.total, "fraud_attempts": r.fraud} for r in results]
