from fastapi import APIRouter, Depends, UploadFile, File, HTTPException, Form
from sqlalchemy.orm import Session
from datetime import datetime, timezone, timedelta
import httpx
import json
import uuid

from backend.api.deps import get_db
from backend.db.redis import get_redis
from backend.services.session_service import session_service
from backend.models.models import Customer, Document, VerificationSession, Blacklist, Incident, Membership, SessionStateEnum, DecisionEnum, Notification, SessionAuditLog, SupervisorNote
from backend.schemas.schemas import BlacklistCreate, IncidentCreate, VerificationDecision
from backend.services.storage_service import storage_service

router = APIRouter(prefix="/api/v1")
AI_SERVICE_URL = "http://localhost:8001"

@router.post("/session/start")
async def start_session(db: Session = Depends(get_db), redis_client = Depends(get_redis)):
    """Initialize a new verification session"""
    # For now, hardcode venue_id=1 and operator_id=1 for dev
    session = session_service.create_session(db, venue_id=1, operator_id=1)
    session_id = session.id
    redis_client.setex(f"session:{session_id}", 3600, json.dumps({"step": 1, "status": "started", "session_id": session_id}))
    return {"session_id": session_id}

@router.get("/operator/stats")
async def get_operator_stats(db: Session = Depends(get_db)):
    """Get the current shift stats for the operator"""
    # Hardcode operator 1 for dev
    today = datetime.now(timezone.utc).date()
    sessions = db.query(VerificationSession).filter(VerificationSession.operator_id == 1).all()
    
    verified = sum(1 for s in sessions if s.final_decision == DecisionEnum.pass_decision and s.created_at.date() == today)
    flagged = sum(1 for s in sessions if s.final_decision == DecisionEnum.deny_decision and s.created_at.date() == today)
    pending = sum(1 for s in sessions if s.final_decision == None and s.created_at.date() == today)
    
    return {
        "operator_name": "John Doe",
        "verified": verified,
        "pending": pending,
        "flagged": flagged
    }

@router.post("/session/{session_id}/classify")
async def classify_document(
    session_id: str,
    file: UploadFile = File(...),
    redis_client = Depends(get_redis),
    db: Session = Depends(get_db)
):
    """Step 1: Upload ID and classify"""
    session_data_str = redis_client.get(f"session:{session_id}")
    if not session_data_str:
        raise HTTPException(status_code=404, detail="Session not found or expired")
    session_data = json.loads(session_data_str)
    
    file_bytes = await file.read()
    
    # Save to MinIO for session duration
    object_name = f"{session_id}_id.jpg"
    import tempfile
    with tempfile.NamedTemporaryFile(delete=False) as tmp:
        tmp.write(file_bytes)
        tmp_path = tmp.name
    storage_service.upload_image(tmp_path, object_name)
    
    # Update state
    try:
        session_service.update_session_data(db, session_id, {"id_image_path": object_name})
        session_service.transition_state(db, session_id, SessionStateEnum.DOCUMENT_CLASSIFIED)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    
    # Call AI Service
    async with httpx.AsyncClient() as client:
        files = {'file': (file.filename, file_bytes, file.content_type)}
        response = await client.post(f"{AI_SERVICE_URL}/classify", files=files, timeout=10.0)
        
        if response.status_code == 200:
            result = response.json()
            if not result.get("is_valid"):
                return {"success": False, "message": result.get("reason")}
            
            session_data["id_image"] = object_name
            session_data["classification"] = result
            session_data["step"] = 2
            redis_client.setex(f"session:{session_id}", 3600, json.dumps(session_data))
            
            return {"success": True, "message": "Document classified successfully"}
        else:
            raise HTTPException(status_code=500, detail="AI classification failed")

@router.post("/session/{session_id}/ocr")
async def extract_ocr(
    session_id: str,
    file: UploadFile = File(...),
    redis_client = Depends(get_redis),
    db: Session = Depends(get_db)
):
    """Step 2: OCR Extract"""
    session_data_str = redis_client.get(f"session:{session_id}")
    if not session_data_str:
        raise HTTPException(status_code=404, detail="Session not found")
    session_data = json.loads(session_data_str)
    
    if session_data["step"] < 2:
        raise HTTPException(status_code=400, detail="Document must be classified first")
        
    file_bytes = await file.read()
    async with httpx.AsyncClient() as client:
        files = {'file': (file.filename, file_bytes, file.content_type)}
        response = await client.post(f"{AI_SERVICE_URL}/ocr", files=files, timeout=10.0)
        
        if response.status_code == 200:
            result = response.json()
            session_data["ocr"] = result["extracted_data"]
            session_data["validation"] = result["validation"]
            session_data["step"] = 3
            redis_client.setex(f"session:{session_id}", 3600, json.dumps(session_data))
            
            # Update state
            try:
                session_service.update_session_data(db, session_id, {"ocr_data": result["extracted_data"]})
                session_service.transition_state(db, session_id, SessionStateEnum.OCR_COMPLETED)
            except ValueError as e:
                pass # Ignoring errors for now
            
            return result
        else:
            raise HTTPException(status_code=500, detail="OCR extraction failed")

@router.post("/session/{session_id}/face")
async def face_match(
    session_id: str,
    file: UploadFile = File(...),
    redis_client = Depends(get_redis),
    db: Session = Depends(get_db)
):
    """Step 3: Capture Face & Match"""
    session_data_str = redis_client.get(f"session:{session_id}")
    if not session_data_str:
        raise HTTPException(status_code=404, detail="Session not found")
    session_data = json.loads(session_data_str)
    
    file_bytes = await file.read()
    
    # Save face to MinIO
    object_name = f"{session_id}_face.jpg"
    import tempfile
    with tempfile.NamedTemporaryFile(delete=False) as tmp:
        tmp.write(file_bytes)
        tmp_path = tmp.name
    storage_service.upload_image(tmp_path, object_name)
    session_data["face_image"] = object_name
    
    try:
        session_service.update_session_data(db, session_id, {"face_image_path": object_name})
        session_service.transition_state(db, session_id, SessionStateEnum.FACE_CAPTURED)
    except ValueError:
        pass
    
    async with httpx.AsyncClient() as client:
        files = {'file': (file.filename, file_bytes, file.content_type)}
        response = await client.post(f"{AI_SERVICE_URL}/face-match", files=files, timeout=10.0)
        
        if response.status_code == 200:
            result = response.json()
            embedding = result["embedding"]
            session_data["embedding"] = embedding
            
            # Check venue status via DB
            ocr = session_data["ocr"]
            unique_id = ocr.get("document_number")
            customer = db.query(Customer).filter(Customer.unique_id == unique_id).first()
            
            # Simulated Venue check
            blacklisted = False
            incidents = 0
            if customer:
                blacklisted = db.query(Blacklist).filter(Blacklist.customer_id == customer.id).first() is not None
                incidents = db.query(Incident).filter(Incident.customer_id == customer.id).count()
                
            session_data["venue_check"] = {
                "blacklisted": blacklisted,
                "incidents": incidents
            }
            
            # Decision engine
            explainability = {
                "ocr_confidence": 99.0, # Mocked for now until integrated with EasyOCR field confidences
                "image_quality": 95.0, # Mocked
                "face_similarity": float(result.get("similarity", 0.0)),
                "blacklist_hit": blacklisted,
                "policy_trigger": "PASS"
            }
            
            if blacklisted:
                decision = "BLOCKED"
                explainability["policy_trigger"] = "BLACKLIST"
                session_service.update_session_data(db, session_id, {"final_decision": "blocked", "customer_id": customer.id})
                session_service.transition_state(db, session_id, SessionStateEnum.DENIED)
            elif not session_data["validation"].get("is_valid"):
                decision = "CHECK"
                explainability["policy_trigger"] = "INVALID_DOCUMENT"
            else:
                decision = "PASS"
                
            session_data["decision"] = decision
            session_data["explainability"] = explainability
            session_data["step"] = 4
            redis_client.setex(f"session:{session_id}", 3600, json.dumps(session_data))
            
            try:
                session_service.update_session_data(db, session_id, {
                    "face_similarity": result.get("similarity", 0.0), 
                    "risk_score": 0.0,
                    "explainability_report": explainability
                })
                session_service.transition_state(db, session_id, SessionStateEnum.FACE_VERIFIED)
            except ValueError:
                pass
                
            return {
                "success": True,
                "decision": decision,
                "venue_check": session_data["venue_check"]
            }
        else:
            raise HTTPException(status_code=500, detail="Face matching failed")

@router.post("/session/{session_id}/finalize")
async def finalize_session(
    session_id: str,
    decision: VerificationDecision,
    db: Session = Depends(get_db),
    redis_client = Depends(get_redis)
):
    """Step 4: Finalize and save to PostgreSQL with expires_at"""
    session_data_str = redis_client.get(f"session:{session_id}")
    if not session_data_str:
        raise HTTPException(status_code=404, detail="Session not found")
    session_data = json.loads(session_data_str)
    
    ocr = session_data.get("ocr")
    if not ocr:
        raise HTTPException(status_code=400, detail="Incomplete session")
        
    unique_id = ocr.get("document_number")
    customer = db.query(Customer).filter(Customer.unique_id == unique_id).first()
    
    if not customer:
        dob_str = ocr.get("dob")
        dob_date = datetime.strptime(dob_str, "%Y-%m-%d") if dob_str else None
        # GDPR Retention: 30 days
        expires = datetime.now(timezone.utc) + timedelta(days=30)
        
        customer = Customer(
            unique_id=unique_id,
            name=ocr.get("name"),
            dob=dob_date,
            face_embedding=session_data.get("embedding"),
            expires_at=expires
        )
        db.add(customer)
        db.commit()
        db.refresh(customer)
        
    # State mapping
    final_decision_str = decision.staff_decision.lower()
    if final_decision_str == "pass":
        final_state = SessionStateEnum.APPROVED
    elif final_decision_str == "deny":
        final_state = SessionStateEnum.DENIED
    elif final_decision_str == "block":
        final_state = SessionStateEnum.DENIED
        # Create Blacklist record
        existing_ban = db.query(Blacklist).filter(Blacklist.customer_id == customer.id).first()
        if not existing_ban:
            new_ban = Blacklist(
                customer_id=customer.id,
                reason=decision.notes or "Manual RESTRICT by Operator",
                banned_by_id=1 # Hardcoded for now
            )
            db.add(new_ban)
            db.commit()
    else:
        final_state = SessionStateEnum.FRAUD_REVIEW
        
    try:
        session_service.update_session_data(db, session_id, {"final_decision": final_decision_str, "customer_id": customer.id})
        session_service.transition_state(db, session_id, final_state)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
        
    redis_client.delete(f"session:{session_id}")
    
    # Trigger Notification for DENY or CHECK
    if final_state in [SessionStateEnum.DENIED, SessionStateEnum.FRAUD_REVIEW]:
        # hardcoding venue_id 1 for now as per system
        notif = Notification(
            venue_id=1,
            message=f"Session {session_id[:8]} flagged as {final_decision_str.upper()}: {decision.notes or 'No reason provided'}",
            type="ALERT"
        )
        db.add(notif)
        db.commit()
    
    return {"success": True, "message": "Session finalized and locked as immutable package", "customer_id": customer.id}

@router.get("/visitors")
async def get_visitors(limit: int = 100, db: Session = Depends(get_db)):
    customers = db.query(Customer).order_by(Customer.created_at.desc()).limit(limit).all()
    results = []
    
    for c in customers:
        # Get latest session for images
        latest_session = db.query(VerificationSession).filter(VerificationSession.customer_id == c.id).order_by(VerificationSession.created_at.desc()).first()
        photo_url = ""
        id_url = ""
        doc_type = "other"
        
        if latest_session:
            if latest_session.face_image_path:
                photo_url = storage_service.get_presigned_url(latest_session.face_image_path)
            if latest_session.id_image_path:
                id_url = storage_service.get_presigned_url(latest_session.id_image_path)
                
        # Get latest document
        latest_doc = db.query(Document).filter(Document.customer_id == c.id).order_by(Document.created_at.desc()).first()
        if latest_doc:
            doc_type = latest_doc.doc_type
            
        results.append({
            "id": str(c.id),
            "name": c.name or "Unknown",
            "dob": c.dob.isoformat() if c.dob else "",
            "age": (datetime.now(timezone.utc).year - c.dob.year) if c.dob else 0,
            "documentType": doc_type,
            "documentNumber": c.unique_id,
            "expiryDate": latest_doc.expiry_date.isoformat() if latest_doc and latest_doc.expiry_date else "",
            "issueDate": latest_doc.issue_date.isoformat() if latest_doc and latest_doc.issue_date else "",
            "address": "",
            "nationality": latest_doc.nationality if latest_doc else "",
            "blacklistStatus": "permanent" if c.blacklist else "none",
            "blacklistReason": c.blacklist[0].reason if c.blacklist else "",
            "membership": c.membership[0].tier if c.membership else "None",
            "visitCount": len(c.sessions),
            "incidentsCount": len(c.incidents),
            "photoUrl": photo_url,
            "idScanUrl": id_url,
            "notes": c.notes,
            "vipTier": c.vip_tier,
            "managerNotes": c.manager_notes,
            "warnings": c.warnings
        })
        
    return results

@router.get("/sessions/history")
async def get_session_history(limit: int = 50, db: Session = Depends(get_db)):
    # Simple history query showing recent VerificationSession records
    sessions = db.query(VerificationSession).order_by(VerificationSession.created_at.desc()).limit(limit).all()
    
    results = []
    for s in sessions:
        results.append({
            "session_id": s.id,
            "status": s.state.value if s.state else "UNKNOWN",
            "created_at": s.created_at.isoformat(),
            "customer_id": s.customer_id,
            "final_decision": s.final_decision or "PENDING"
        })
    return results

@router.get("/notifications")
async def get_notifications(limit: int = 50, db: Session = Depends(get_db)):
    notifs = db.query(Notification).order_by(Notification.created_at.desc()).limit(limit).all()
    return [{
        "id": n.id,
        "message": n.message,
        "type": n.type,
        "is_read": n.is_read,
        "created_at": n.created_at.isoformat()
    } for n in notifs]

@router.post("/admin/flush")
async def flush_data(db: Session = Depends(get_db)):
    """Flushes all visitors and session data EXCEPT blacklisted users."""
    # Find all customer IDs that are blacklisted
    blacklisted_ids_query = db.query(Blacklist.customer_id).distinct()
    blacklisted_ids = [row[0] for row in blacklisted_ids_query.all()]
    
    # Query expendable customers
    if blacklisted_ids:
        expendable_customers = db.query(Customer).filter(~Customer.id.in_(blacklisted_ids)).all()
    else:
        expendable_customers = db.query(Customer).all()
        
    expendable_customer_ids = [c.id for c in expendable_customers]
    
    # Query expendable sessions
    expendable_sessions = db.query(VerificationSession).filter(
        (VerificationSession.customer_id.in_(expendable_customer_ids)) | 
        (VerificationSession.customer_id == None)
    ).all()
    expendable_session_ids = [s.id for s in expendable_sessions]
    
    try:
        # Delete related to sessions
        if expendable_session_ids:
            db.query(SessionAuditLog).filter(SessionAuditLog.session_id.in_(expendable_session_ids)).delete(synchronize_session=False)
            db.query(SupervisorNote).filter(SupervisorNote.session_id.in_(expendable_session_ids)).delete(synchronize_session=False)
            db.query(VerificationSession).filter(VerificationSession.id.in_(expendable_session_ids)).delete(synchronize_session=False)
            
        # Delete related to customers
        if expendable_customer_ids:
            db.query(Document).filter(Document.customer_id.in_(expendable_customer_ids)).delete(synchronize_session=False)
            db.query(Incident).filter(Incident.customer_id.in_(expendable_customer_ids)).delete(synchronize_session=False)
            db.query(Membership).filter(Membership.customer_id.in_(expendable_customer_ids)).delete(synchronize_session=False)
            db.query(Customer).filter(Customer.id.in_(expendable_customer_ids)).delete(synchronize_session=False)
            
        # Clear out notifications to reset dashboard state completely
        db.query(Notification).delete(synchronize_session=False)
        
        db.commit()
        return {"success": True, "message": f"Successfully flushed {len(expendable_customer_ids)} customers and {len(expendable_session_ids)} sessions.", "spared": len(blacklisted_ids)}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Database error during flush: {str(e)}")
