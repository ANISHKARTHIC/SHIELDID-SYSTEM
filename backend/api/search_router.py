from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy import or_

from backend.api.deps import get_db
from backend.models.models import Customer, VerificationSession, User

router = APIRouter(prefix="/api/v1/search", tags=["search"])

@router.get("/")
async def global_search(
    q: str = Query(..., min_length=2),
    db: Session = Depends(get_db)
):
    """Global search across multiple entities using ILIKE."""
    search_term = f"%{q}%"
    
    # 1. Search Customers by name or unique ID
    customers = db.query(Customer).filter(
        or_(
            Customer.name.ilike(search_term),
            Customer.unique_id.ilike(search_term)
        )
    ).limit(10).all()
    
    # 2. Search Verification Sessions by ID
    sessions = db.query(VerificationSession).filter(
        VerificationSession.id.ilike(search_term)
    ).limit(10).all()
    
    # 3. Search Users by email
    users = db.query(User).filter(
        User.email.ilike(search_term)
    ).limit(10).all()
    
    return {
        "customers": [{"id": c.id, "name": c.name, "unique_id": c.unique_id} for c in customers],
        "sessions": [{"id": s.id, "state": s.state.value, "decision": s.final_decision} for s in sessions],
        "users": [{"id": u.id, "email": u.email, "role": u.role.value} for u in users]
    }
