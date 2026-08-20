from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional

from backend.api.deps import get_db, get_current_active_user, RoleChecker
from backend.core.security import get_password_hash
from backend.models.models import User, RoleEnum, AuditLog
from backend.services.venue_admin_service import venue_admin_service

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
    venue_id: Optional[int] = None


class ResetPasswordRequest(BaseModel):
    new_password: str


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
    """Updates a staff account's role, active state, and/or venue
    assignment. Users are deactivated, never hard-deleted — many other
    tables (sessions, bans, incidents, audit logs) reference users.id by
    foreign key. Venue reassignment is super_admin-only — it crosses a
    privilege boundary a venue_admin should never be able to touch, even
    for staff currently within their own venue."""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    if current_user.role != RoleEnum.super_admin:
        if user.venue_id != current_user.venue_id:
            raise HTTPException(status_code=403, detail="Cannot modify a user from another venue")
        if req.role == RoleEnum.super_admin or user.role == RoleEnum.super_admin:
            raise HTTPException(status_code=403, detail="Only a super admin can grant or modify a super admin account")
        if req.venue_id is not None:
            raise HTTPException(status_code=403, detail="Only a super admin can reassign a user's venue")

    if req.role is not None:
        user.role = req.role
    if req.is_active is not None:
        user.is_active = req.is_active
    if req.venue_id is not None and req.venue_id != user.venue_id:
        target_venue = venue_admin_service.get_venue(db, req.venue_id)
        if not target_venue:
            raise HTTPException(status_code=404, detail="Target venue not found")
        old_venue_id = user.venue_id
        user.venue_id = req.venue_id
        db.add(AuditLog(
            user_id=current_user.id,
            action="user_venue_reassigned",
            details={"target_user_id": user.id, "old_venue_id": old_venue_id, "new_venue_id": req.venue_id},
        ))

    db.commit()
    db.refresh(user)
    return _user_summary(user)


@router.post("/{user_id}/reset-password", dependencies=[Depends(require_admin)])
def reset_password(
    user_id: int,
    req: ResetPasswordRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Admin-initiated password reset — sets a new password without
    requiring the old one. A dedicated POST route rather than folding this
    into PATCH, matching this codebase's convention of separate routes for
    sensitive stateful actions (POST /occupancy/{id}/checkout, POST
    /blacklist), and keeping it independently auditable."""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    if current_user.role != RoleEnum.super_admin:
        if user.venue_id != current_user.venue_id:
            raise HTTPException(status_code=403, detail="Cannot modify a user from another venue")
        if user.role == RoleEnum.super_admin:
            raise HTTPException(status_code=403, detail="Only a super admin can reset a super admin's password")

    user.hashed_password = get_password_hash(req.new_password)
    db.add(AuditLog(
        user_id=current_user.id,
        action="password_reset",
        details={"target_user_id": user.id},
    ))
    db.commit()
    return {"success": True}
