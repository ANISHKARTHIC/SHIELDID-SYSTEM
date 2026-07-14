from fastapi import APIRouter, Depends, HTTPException, Body
from sqlalchemy.orm import Session
from typing import List, Optional

from backend.api.deps import get_db, get_current_active_user
from backend.models.models import VerificationSession, SessionStateEnum, SupervisorNote, User
from backend.services.session_service import session_service

router = APIRouter(prefix="/api/v1/supervisor", tags=["supervisor"])

@router.get("/queue")
async def get_fraud_queue(db: Session = Depends(get_db)): # Require auth in real usage
    """Lists sessions in FRAUD_REVIEW state."""
    sessions = db.query(VerificationSession).filter(VerificationSession.state == SessionStateEnum.FRAUD_REVIEW).all()
    # In a real app we'd return a Pydantic schema here, returning raw dicts for brevity
    return [{
        "session_id": s.id,
        "customer_id": s.customer_id,
        "risk_score": s.risk_score,
        "created_at": s.created_at,
        "operator_id": s.operator_id
    } for s in sessions]

@router.post("/{session_id}/notes")
async def add_supervisor_note(
    session_id: str,
    note_text: str = Body(..., embed=True),
    evidence_path: Optional[str] = Body(None, embed=True),
    db: Session = Depends(get_db)
):
    """Attach immutable notes to a session."""
    session = db.query(VerificationSession).filter(VerificationSession.id == session_id).first()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
        
    note = SupervisorNote(
        session_id=session_id,
        supervisor_id=1, # Mock supervisor ID
        note_text=note_text,
        evidence_path=evidence_path
    )
    db.add(note)
    db.commit()
    db.refresh(note)
    
    return {"success": True, "note_id": note.id}

@router.post("/{session_id}/decision")
async def make_supervisor_decision(
    session_id: str,
    decision: str = Body(..., embed=True), # 'APPROVE', 'REJECT', 'REVERIFY'
    db: Session = Depends(get_db)
):
    """Allows supervisors to make a final decision on a FRAUD_REVIEW session."""
    session = db.query(VerificationSession).filter(VerificationSession.id == session_id).first()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
        
    if session.state != SessionStateEnum.FRAUD_REVIEW:
        raise HTTPException(status_code=400, detail="Session is not in FRAUD_REVIEW state")
        
    if decision == 'APPROVE':
        new_state = SessionStateEnum.APPROVED
    elif decision == 'REJECT':
        new_state = SessionStateEnum.DENIED
    elif decision == 'REVERIFY':
        new_state = SessionStateEnum.CREATED # Send back to start
    else:
        raise HTTPException(status_code=400, detail="Invalid decision")
        
    try:
        # Unlock temporarily if we are sending back
        if decision == 'REVERIFY':
            session.is_locked = False
            db.commit()
            
        session_service.transition_state(db, session_id, new_state, operator_id=1)
        return {"success": True, "new_state": new_state.value}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
