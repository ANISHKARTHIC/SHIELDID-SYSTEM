from sqlalchemy.orm import Session
from backend.models.models import VerificationSession, SessionAuditLog, SessionStateEnum
from backend.core.event_bus import event_bus, CH_VERIFICATIONS
from datetime import datetime, timezone
import uuid

class SessionService:
    def create_session(self, db: Session, venue_id: int, operator_id: int, device_info: str = None) -> VerificationSession:
        session_id = str(uuid.uuid4())
        session = VerificationSession(
            id=session_id,
            venue_id=venue_id,
            operator_id=operator_id,
            state=SessionStateEnum.CREATED
        )
        db.add(session)
        
        audit_log = SessionAuditLog(
            session_id=session_id,
            operator_id=operator_id,
            state_from=None,
            state_to=SessionStateEnum.CREATED.value,
            device_info=device_info
        )
        db.add(audit_log)
        
        db.commit()
        db.refresh(session)
        return session

    def transition_state(self, db: Session, session_id: str, new_state: SessionStateEnum, operator_id: int = None, device_info: str = None) -> VerificationSession:
        session = db.query(VerificationSession).filter(VerificationSession.id == session_id).first()
        if not session:
            raise ValueError("Session not found")
        if session.is_locked:
            raise ValueError("Session is locked and cannot be modified.")
            
        old_state = session.state.value
        session.state = new_state
        session.updated_at = datetime.now(timezone.utc)
        
        # If transitioning to a terminal state, lock the session to make it an Immutable Verification Package
        if new_state in [SessionStateEnum.APPROVED, SessionStateEnum.DENIED, SessionStateEnum.COMPLETED, SessionStateEnum.FAILED]:
            session.is_locked = True
            
        audit_log = SessionAuditLog(
            session_id=session_id,
            operator_id=operator_id or session.operator_id,
            state_from=old_state,
            state_to=new_state.value,
            device_info=device_info
        )
        db.add(audit_log)
        db.commit()
        db.refresh(session)
        
        # Publish to Event Bus
        event_bus.publish(
            channel=CH_VERIFICATIONS,
            event_type=new_state.value,
            payload={
                "session_id": session_id,
                "venue_id": session.venue_id,
                "operator_id": session.operator_id,
                "state_from": old_state,
                "state_to": new_state.value,
                "timestamp": session.updated_at.isoformat()
            }
        )
        
        return session

    def update_session_data(self, db: Session, session_id: str, updates: dict) -> VerificationSession:
        session = db.query(VerificationSession).filter(VerificationSession.id == session_id).first()
        if not session:
            raise ValueError("Session not found")
        if session.is_locked:
            raise ValueError("Session is locked and cannot be modified.")
            
        for key, value in updates.items():
            if hasattr(session, key):
                setattr(session, key, value)
                
        session.updated_at = datetime.now(timezone.utc)
        db.commit()
        db.refresh(session)
        return session

session_service = SessionService()
