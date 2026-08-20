from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from backend.api.deps import get_db, get_current_active_user, RoleChecker
from backend.models.models import RoleEnum, User, Customer, Blacklist, Occupancy, Notification, AuditLog
from backend.schemas.schemas import BlacklistCreateByCustomerId
from backend.core.event_bus import event_bus, CH_SECURITY
from backend.services.session_service import session_service

router = APIRouter(prefix="/api/v1/blacklist", tags=["blacklist"], dependencies=[Depends(get_current_active_user)])
require_floor_staff = RoleChecker([RoleEnum.door_staff, RoleEnum.manager, RoleEnum.venue_admin, RoleEnum.super_admin])


@router.post("", dependencies=[Depends(require_floor_staff)])
def create_ban(
    req: BlacklistCreateByCustomerId,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """
    Standalone ban action, usable against any known customer whether or not
    they're mid-verification-session — including someone already inside the
    venue. This coexists with (and does not replace) finalize_session's
    inline ban-on-BLOCK path, which stays tied to the at-the-door decision
    flow. If the target is currently inside (an open Occupancy row for this
    venue), an ALERT notification is raised telling staff to escort them out.
    """
    customer = db.query(Customer).filter(Customer.id == req.customer_id).first()
    if not customer:
        raise HTTPException(status_code=404, detail="Customer not found")

    existing_ban = db.query(Blacklist).filter(Blacklist.customer_id == customer.id).first()
    if existing_ban:
        raise HTTPException(status_code=409, detail="This customer already has an active ban")

    expiry = None
    if req.expiry_date:
        try:
            from dateutil import parser as date_parser
            expiry = date_parser.parse(req.expiry_date)
        except Exception:
            raise HTTPException(status_code=400, detail="Invalid expiry_date format")

    ban = Blacklist(
        customer_id=customer.id,
        reason=req.reason,
        manager_notes=req.manager_notes,
        banned_by_id=current_user.id,
        expiry_date=expiry,
    )
    db.add(ban)

    occupancy = (
        db.query(Occupancy)
        .filter(
            Occupancy.customer_id == customer.id,
            Occupancy.venue_id == current_user.venue_id,
            Occupancy.exited_at.is_(None),
        )
        .first()
    )
    currently_inside = occupancy is not None

    if currently_inside:
        db.add(Notification(
            venue_id=current_user.venue_id,
            message=f"{customer.name} was just banned and is CURRENTLY INSIDE — escort them out immediately. Reason: {req.reason}",
            type="ALERT",
        ))
        event_bus.publish(CH_SECURITY, "IN_VENUE_BAN", {
            "customer_id": customer.id,
            "venue_id": current_user.venue_id,
            "reason": req.reason,
            "banned_by_id": current_user.id,
        })

    db.add(AuditLog(
        user_id=current_user.id,
        action="blacklist_created",
        details={
            "customer_id": customer.id,
            "reason": req.reason,
            "banned_by_id": current_user.id,
            "currently_inside": currently_inside,
        },
    ))
    db.commit()

    session_service.quarantine_customer_images(db, customer.id)

    return {
        "success": True,
        "blacklist_id": ban.id,
        "customer_id": customer.id,
        "currently_inside": currently_inside,
    }
