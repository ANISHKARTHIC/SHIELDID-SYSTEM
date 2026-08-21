from datetime import datetime, timezone, timedelta
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from backend.api.deps import get_db, get_current_active_user, RoleChecker
from backend.models.models import RoleEnum, User
from backend.services.occupancy_service import occupancy_service
from backend.services.venue_admin_service import venue_admin_service
from backend.services.venue_service import venue_service

router = APIRouter(prefix="/api/v1/occupancy", tags=["occupancy"], dependencies=[Depends(get_current_active_user)])
require_floor_staff = RoleChecker([RoleEnum.door_staff, RoleEnum.manager, RoleEnum.venue_admin, RoleEnum.super_admin])


def _occupant_summary(record, auto_expire_hours: int) -> dict:
    customer = record.customer
    minutes_inside = None
    auto_expire_at = None
    if record.entered_at:
        entered = record.entered_at if record.entered_at.tzinfo else record.entered_at.replace(tzinfo=timezone.utc)
        minutes_inside = int((datetime.now(timezone.utc) - entered).total_seconds() // 60)
        auto_expire_at = (entered + timedelta(hours=auto_expire_hours)).isoformat()
    return {
        "occupancy_id": record.id,
        "customer_id": record.customer_id,
        "customer_name": customer.name if customer else "Unknown",
        "entered_at": record.entered_at.isoformat() if record.entered_at else None,
        "minutes_inside": minutes_inside,
        "auto_expire_at": auto_expire_at,
    }


@router.get("/current")
def list_current_occupants(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    records = occupancy_service.get_current_occupants(db, current_user.venue_id)
    config = venue_service.get_venue_configuration(db, current_user.venue_id)
    hours = config.occupancy_auto_expire_hours or 6
    return [_occupant_summary(r, hours) for r in records]


@router.get("/count")
def get_live_count(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    count = occupancy_service.get_live_count(db, current_user.venue_id)
    venue = venue_admin_service.get_venue(db, current_user.venue_id)
    config = venue_service.get_venue_configuration(db, current_user.venue_id)
    max_capacity = venue.max_capacity if venue else None
    return {
        "current_count": count,
        "max_capacity": max_capacity,
        "at_capacity": max_capacity is not None and count >= max_capacity,
        "occupancy_auto_expire_hours": config.occupancy_auto_expire_hours or 6,
    }


@router.post("/{occupancy_id}/checkout", dependencies=[Depends(require_floor_staff)])
def manual_checkout(
    occupancy_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    try:
        record = occupancy_service.check_out(db, occupancy_id, current_user.id, current_user.venue_id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    if not record:
        raise HTTPException(status_code=404, detail="Occupancy record not found")
    return {"success": True, "occupancy_id": record.id, "exited_at": record.exited_at.isoformat()}
