from fastapi import APIRouter, Depends, UploadFile, File, HTTPException, Form
from sqlalchemy.orm import Session
from datetime import datetime, timezone, timedelta
import httpx
import json
import uuid

from backend.api.deps import get_db
from backend.db.redis import get_redis
from backend.services.session_service import session_service
from backend.models.models import Customer, Document, VerificationSession, Blacklist, Incident, Membership, SessionStateEnum
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
                blacklisted = db.query(Blacklist).filter(Blacklist.customer_id == customer.id).count() > 0
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
                decision = "DENY"
                explainability["policy_trigger"] = "BLACKLIST"
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
    final_decision_str = decision.decision.value
    if final_decision_str == "pass":
        final_state = SessionStateEnum.APPROVED
    elif final_decision_str == "deny":
        final_state = SessionStateEnum.DENIED
    else:
        final_state = SessionStateEnum.FRAUD_REVIEW
        
    try:
        session_service.update_session_data(db, session_id, {"final_decision": final_decision_str, "customer_id": customer.id})
        session_service.transition_state(db, session_id, final_state)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
        
    redis_client.delete(f"session:{session_id}")
    
    return {"success": True, "message": "Session finalized and locked as immutable package", "customer_id": customer.id}
