from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List, Dict, Any

from backend.api.deps import get_db, get_current_active_user
from backend.models.models import VerificationSession, SessionAuditLog, User

router = APIRouter(prefix="/api/v1/replay", tags=["replay"])

@router.get("/{session_id}")
async def get_session_replay(session_id: str, db: Session = Depends(get_db)):
    """Fetch the core immutable verification package."""
    session = db.query(VerificationSession).filter(VerificationSession.id == session_id).first()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
        
    return {
        "session_id": session.id,
        "venue_id": session.venue_id,
        "operator_id": session.operator_id,
        "customer_id": session.customer_id,
        "state": session.state.value,
        "is_locked": session.is_locked,
        "created_at": session.created_at,
        "updated_at": session.updated_at,
        "final_decision": session.final_decision,
        "risk_score": session.risk_score,
        "face_similarity": session.face_similarity,
        "quality_scores": session.quality_scores,
        "ocr_data": session.ocr_data
    }

@router.get("/{session_id}/timeline")
async def get_session_timeline(session_id: str, db: Session = Depends(get_db)):
    """Generates a chronological sequence of events for a session."""
    session = db.query(VerificationSession).filter(VerificationSession.id == session_id).first()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
        
    logs = db.query(SessionAuditLog).filter(SessionAuditLog.session_id == session_id).order_by(SessionAuditLog.created_at.asc()).all()
    
    timeline = []
    for log in logs:
        timeline.append({
            "id": log.id,
            "timestamp": log.created_at,
            "operator_id": log.operator_id,
            "state_from": log.state_from,
            "state_to": log.state_to,
            "duration_ms": log.duration_ms,
            "device_info": log.device_info,
            "event_details": log.event_details
        })
        
    return {"session_id": session_id, "timeline": timeline}

@router.get("/{session_id}/artifacts")
async def get_session_artifacts(session_id: str, db: Session = Depends(get_db)):
    """Returns stored artifacts such as image paths, metadata, and JSON OCR."""
    session = db.query(VerificationSession).filter(VerificationSession.id == session_id).first()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
        
    return {
        "session_id": session.id,
        "id_image_path": session.id_image_path,
        "face_image_path": session.face_image_path,
        "id_image_checksum": session.id_image_checksum,
        "face_image_checksum": session.face_image_checksum,
        "ocr_data": session.ocr_data,
        "quality_scores": session.quality_scores
    }
