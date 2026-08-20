from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import Dict, Any, Optional

from backend.api.deps import get_db, get_current_active_user, RoleChecker
from backend.models.models import RoleEnum, User
from backend.services.venue_service import venue_service
from backend.services.venue_admin_service import venue_admin_service
from backend.schemas.schemas import VenueCreateRequest, VenueUpdateRequest, VenueResponse

router = APIRouter(prefix="/api/v1/venues", tags=["venues"], dependencies=[Depends(get_current_active_user)])
require_admin = RoleChecker([RoleEnum.super_admin, RoleEnum.venue_admin])
require_super_admin_venues = RoleChecker([RoleEnum.super_admin])


@router.post("", response_model=VenueResponse, dependencies=[Depends(require_super_admin_venues)])
def create_venue(req: VenueCreateRequest, db: Session = Depends(get_db)):
    return venue_admin_service.create_venue(db, req.name, req.address, req.max_capacity)


@router.get("", response_model=list[VenueResponse])
def list_venues(
    include_inactive: bool = False,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    if current_user.role == RoleEnum.super_admin:
        return venue_admin_service.list_venues(db, include_inactive=include_inactive)
    venue = venue_admin_service.get_venue(db, current_user.venue_id)
    return [venue] if venue else []


@router.get("/{venue_id}", response_model=VenueResponse)
def get_venue(
    venue_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    if current_user.role != RoleEnum.super_admin and venue_id != current_user.venue_id:
        raise HTTPException(status_code=403, detail="Cannot access another venue")
    venue = venue_admin_service.get_venue(db, venue_id)
    if not venue:
        raise HTTPException(status_code=404, detail="Venue not found")
    return venue


@router.put("/{venue_id}", response_model=VenueResponse, dependencies=[Depends(require_admin)])
def update_venue(
    venue_id: int,
    req: VenueUpdateRequest,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    if current_user.role != RoleEnum.super_admin and venue_id != current_user.venue_id:
        raise HTTPException(status_code=403, detail="Cannot modify another venue")
    venue = venue_admin_service.update_venue(db, venue_id, req.model_dump(exclude_unset=True))
    if not venue:
        raise HTTPException(status_code=404, detail="Venue not found")
    return venue


@router.delete("/{venue_id}", response_model=VenueResponse, dependencies=[Depends(require_super_admin_venues)])
def deactivate_venue(venue_id: int, db: Session = Depends(get_db)):
    """Deactivates (soft-deletes) a venue. Never hard-deletes — many other
    tables reference venues.id by foreign key."""
    venue = venue_admin_service.deactivate_venue(db, venue_id)
    if not venue:
        raise HTTPException(status_code=404, detail="Venue not found")
    return venue


@router.get("/{venue_id}/config")
def get_venue_config(venue_id: int, db: Session = Depends(get_db)):
    config = venue_service.get_venue_configuration(db, venue_id)
    if not config:
        raise HTTPException(status_code=404, detail="Configuration not found")
    return {
        "allowed_documents": config.allowed_documents,
        "retention_days_success": config.retention_days_success,
        "retention_days_manual": config.retention_days_manual,
        "retention_days_incident": config.retention_days_incident,
        "verification_mode": config.verification_mode,
        "theme_config": config.theme_config,
        "occupancy_auto_expire_hours": config.occupancy_auto_expire_hours,
    }

@router.put("/{venue_id}/config", dependencies=[Depends(require_admin)])
def update_venue_config(venue_id: int, updates: Dict[str, Any], db: Session = Depends(get_db)):
    config = venue_service.update_configuration(db, venue_id, updates)
    return {"message": "Configuration updated successfully", "config_id": config.id}

@router.get("/{venue_id}/policy")
def get_venue_policy(venue_id: int, db: Session = Depends(get_db)):
    policy = venue_service.get_venue_policy(db, venue_id)
    if not policy:
        raise HTTPException(status_code=404, detail="Policy not found")
    return {
        "minimum_age": policy.minimum_age,
        "require_face_match": policy.require_face_match,
        "face_similarity_threshold": policy.face_similarity_threshold,
        "ocr_confidence_threshold": policy.ocr_confidence_threshold,
        "quality_threshold": policy.quality_threshold,
        "blacklist_policy": policy.blacklist_policy
    }

@router.put("/{venue_id}/policy", dependencies=[Depends(require_admin)])
def update_venue_policy(venue_id: int, updates: Dict[str, Any], db: Session = Depends(get_db)):
    policy = venue_service.update_policy(db, venue_id, updates)
    return {"message": "Policy updated successfully", "policy_id": policy.id}
