from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional

from backend.api.deps import get_db, get_current_active_user, RoleChecker
from backend.core.security import get_password_hash
from backend.models.models import User, RoleEnum

router = APIRouter(prefix="/api/v1/users", tags=["users"], dependencies=[Depends(get_current_active_user)])

# Only super_admin/venue_admin may manage staff accounts — matches the bar
# already set for other admin-only mutations (venue_router.py's
# require_admin, v1_router.py's require_super_admin for /admin/flush).
require_admin = RoleChecker([RoleEnum.super_admin, RoleEnum.venue_admin])


class CreateUserRequest(BaseModel):
    email: str
    password: str
    role: RoleEnum = RoleEnum.door_staff
    venue_id: Optional[int] = None


class UpdateUserRequest(BaseModel):
    role: Optional[RoleEnum] = None
    is_active: Optional[bool] = None


def _user_summary(user: User) -> dict:
    return {
        "id": user.id,
        "email": user.email,
        "role": user.role.value if hasattr(user.role, "value") else str(user.role),
        "venue_id": user.venue_id,
        "is_active": user.is_active,
        "created_at": user.created_at.isoformat() if user.created_at else None,
    }


@router.get("", dependencies=[Depends(require_admin)])
def list_users(db: Session = Depends(get_db), current_user: User = Depends(get_current_active_user)):
    """Lists staff accounts. super_admin sees every venue; venue_admin sees
    only their own venue's staff."""
    query = db.query(User)
    if current_user.role != RoleEnum.super_admin:
        query = query.filter(User.venue_id == current_user.venue_id)
    return [_user_summary(u) for u in query.order_by(User.id).all()]


@router.post("", dependencies=[Depends(require_admin)])
def create_user(
    req: CreateUserRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Admin-only account creation. A venue_admin may only create staff for
    their own venue and may not grant super_admin; super_admin may create
    any role for any venue."""
    existing = db.query(User).filter(User.email == req.email).first()
    if existing:
        raise HTTPException(status_code=400, detail="Email already registered")

    target_venue_id = req.venue_id if req.venue_id is not None else current_user.venue_id
    if current_user.role != RoleEnum.super_admin:
        if req.role == RoleEnum.super_admin:
            raise HTTPException(status_code=403, detail="Only a super admin can create another super admin")
        if target_venue_id != current_user.venue_id:
            raise HTTPException(status_code=403, detail="Cannot create a user for another venue")

    user = User(
        venue_id=target_venue_id,
        email=req.email,
        hashed_password=get_password_hash(req.password),
        role=req.role,
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    return _user_summary(user)


@router.patch("/{user_id}", dependencies=[Depends(require_admin)])
def update_user(
    user_id: int,
    req: UpdateUserRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Updates a staff account's role and/or active state. Users are
    deactivated, never hard-deleted — many other tables (sessions, bans,
    incidents, audit logs) reference users.id by foreign key."""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    if current_user.role != RoleEnum.super_admin:
        if user.venue_id != current_user.venue_id:
            raise HTTPException(status_code=403, detail="Cannot modify a user from another venue")
        if req.role == RoleEnum.super_admin or user.role == RoleEnum.super_admin:
            raise HTTPException(status_code=403, detail="Only a super admin can grant or modify a super admin account")

    if req.role is not None:
        user.role = req.role
    if req.is_active is not None:
        user.is_active = req.is_active

    db.commit()
    db.refresh(user)
    return _user_summary(user)
