from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy import or_

from backend.api.deps import get_db, get_current_active_user
from backend.models.models import Customer, VerificationSession, User, RoleEnum

router = APIRouter(prefix="/api/v1/search", tags=["search"], dependencies=[Depends(get_current_active_user)])

@router.get("/")
async def global_search(
    q: str = Query(..., min_length=2),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Global search across multiple entities using ILIKE."""
    search_term = f"%{q}%"
    is_super_admin = current_user.role == RoleEnum.super_admin

    # 1. Search Customers by name or unique ID — Customer is a deliberately
    # venue-agnostic shared table (a customer can visit multiple venues,
    # same as the global Blacklist), so this stays unscoped by design.
    customers = db.query(Customer).filter(
        or_(
            Customer.name.ilike(search_term),
            Customer.unique_id.ilike(search_term)
        )
    ).limit(10).all()

    # 2. Search Verification Sessions by ID — scoped to the caller's own
    # venue. A session belongs to exactly one venue and its OCR/decision
    # data is sensitive; unscoped search let any authenticated user
    # enumerate other venues' session IDs (useful for chaining into the
    # replay endpoints) and see their state/decision.
    sessions_query = db.query(VerificationSession).filter(
        VerificationSession.id.ilike(search_term)
    )
    if not is_super_admin:
        sessions_query = sessions_query.filter(VerificationSession.venue_id == current_user.venue_id)
    sessions = sessions_query.limit(10).all()

    # 3. Search Users by email — scoped to the caller's own venue. Staff
    # emails/roles at other venues are sensitive and were previously
    # visible to any authenticated user regardless of venue.
    users_query = db.query(User).filter(
        User.email.ilike(search_term)
    )
    if not is_super_admin:
        users_query = users_query.filter(User.venue_id == current_user.venue_id)
    users = users_query.limit(10).all()

    return {
        "customers": [{"id": c.id, "name": c.name, "unique_id": c.unique_id} for c in customers],
        "sessions": [{"id": s.id, "state": s.state.value, "decision": s.final_decision} for s in sessions],
        "users": [{"id": u.id, "email": u.email, "role": u.role.value} for u in users]
    }
