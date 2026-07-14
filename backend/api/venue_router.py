from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import Dict, Any

from backend.api.deps import get_db
from backend.services.venue_service import venue_service

router = APIRouter(prefix="/api/v1/venues", tags=["venues"])

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
        "theme_config": config.theme_config
    }

@router.put("/{venue_id}/config")
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

@router.put("/{venue_id}/policy")
def update_venue_policy(venue_id: int, updates: Dict[str, Any], db: Session = Depends(get_db)):
    policy = venue_service.update_policy(db, venue_id, updates)
    return {"message": "Policy updated successfully", "policy_id": policy.id}
