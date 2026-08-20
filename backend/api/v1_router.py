from fastapi import APIRouter, Depends, UploadFile, File, HTTPException, Form
from sqlalchemy.orm import Session
from datetime import datetime, timezone, timedelta
import httpx
import json
import uuid

from backend.api.deps import get_db, get_current_active_user
from backend.db.redis import get_redis
from backend.services.session_service import session_service
from backend.models.models import Customer, Document, VerificationSession, Blacklist, Incident, Membership, SessionStateEnum, DecisionEnum, Notification, SessionAuditLog, SupervisorNote, User, AuditLog, Occupancy
from backend.schemas.schemas import BlacklistCreate, IncidentCreate, VerificationDecision
from backend.services.storage_service import storage_service
from backend.services.venue_service import venue_service
from backend.core.config import settings

router = APIRouter(prefix="/api/v1", dependencies=[Depends(get_current_active_user)])
AI_SERVICE_URL = settings.AI_SERVICE_URL

@router.post("/session/start")
async def start_session(
    db: Session = Depends(get_db),
    redis_client = Depends(get_redis),
    current_user: User = Depends(get_current_active_user)
):
    """Initialize a new verification session for the authenticated operator's venue"""
    session = session_service.create_session(db, venue_id=current_user.venue_id, operator_id=current_user.id)
    session_id = session.id
    redis_client.setex(f"session:{session_id}", 3600, json.dumps({"step": 1, "status": "started", "session_id": session_id}))
    return {"session_id": session_id}

@router.get("/operator/stats")
async def get_operator_stats(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Get the current shift stats for the operator"""
    today = datetime.now(timezone.utc).date()
    sessions = db.query(VerificationSession).filter(VerificationSession.operator_id == current_user.id).all()

    verified = sum(1 for s in sessions if str(s.final_decision or "").lower() == "pass" and s.created_at and s.created_at.date() == today)
    flagged = sum(1 for s in sessions if str(s.final_decision or "").lower() in ["deny", "blocked", "restricted"] and s.created_at and s.created_at.date() == today)
    pending = sum(1 for s in sessions if s.final_decision is None and s.created_at and s.created_at.date() == today)

    return {
        "operator_name": current_user.email.split("@")[0],
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

    # Save to S3 for session duration. Ban status isn't known yet at this
    # step (OCR/face-match haven't run), so this always lands under
    # normal/ — quarantine_customer_images moves it to banned/ later if
    # this turns out to be a repeat offender.
    object_name = f"{session_id}_id.jpg"
    import tempfile
    with tempfile.NamedTemporaryFile(delete=False) as tmp:
        tmp.write(file_bytes)
        tmp_path = tmp.name
    object_name = storage_service.upload_image(tmp_path, object_name) or object_name

    # Update state
    try:
        session_service.update_session_data(db, session_id, {"id_image_path": object_name})
        session_service.transition_state(db, session_id, SessionStateEnum.DOCUMENT_CLASSIFIED)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    
    # Call AI Service
    async with httpx.AsyncClient() as client:
        files = {'file': (file.filename, file_bytes, file.content_type)}
        try:
            response = await client.post(f"{AI_SERVICE_URL}/classify", files=files, timeout=20.0)
        except httpx.TimeoutException:
            raise HTTPException(status_code=503, detail="Document classification is taking too long. Please try again.")
        except httpx.ConnectError:
            raise HTTPException(status_code=503, detail="Unable to connect to the verification service. Please try again shortly.")

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
    document_type = session_data.get("classification", {}).get("document_type", "uk_driving_licence")
    async with httpx.AsyncClient() as client:
        files = {'file': (file.filename, file_bytes, file.content_type)}
        try:
            response = await client.post(f"{AI_SERVICE_URL}/ocr", files=files, params={"document_type": document_type}, timeout=30.0)
        except httpx.TimeoutException:
            raise HTTPException(status_code=503, detail="Text extraction is taking too long. Please try again.")
        except httpx.ConnectError:
            raise HTTPException(status_code=503, detail="Unable to connect to the verification service. Please try again shortly.")

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
        elif response.status_code == 422:
            raise HTTPException(status_code=422, detail=response.json().get("message", "No legible text could be extracted from the document."))
        else:
            raise HTTPException(status_code=500, detail="OCR extraction failed")

@router.post("/session/{session_id}/face")
async def face_match(
    session_id: str,
    file: UploadFile = File(...),
    redis_client = Depends(get_redis),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Step 3: Capture Face & Match"""
    session_data_str = redis_client.get(f"session:{session_id}")
    if not session_data_str:
        raise HTTPException(status_code=404, detail="Session not found")
    session_data = json.loads(session_data_str)

    file_bytes = await file.read()

    # Save face to S3, under normal/ — blacklist status is resolved further
    # down in this same request; quarantine_customer_images moves this to
    # banned/ if it turns out the customer is blacklisted.
    object_name = f"{session_id}_face.jpg"
    import tempfile
    with tempfile.NamedTemporaryFile(delete=False) as tmp:
        tmp.write(file_bytes)
        tmp_path = tmp.name
    object_name = storage_service.upload_image(tmp_path, object_name) or object_name
    session_data["face_image"] = object_name

    try:
        session_service.update_session_data(db, session_id, {"face_image_path": object_name})
        session_service.transition_state(db, session_id, SessionStateEnum.FACE_CAPTURED)
    except ValueError:
        pass

    # Look up any existing customer by document number so we can pass their
    # stored face embedding as a real comparison reference, rather than
    # always returning a placeholder similarity of 0.0.
    ocr = session_data["ocr"]
    unique_id = ocr.get("document_number")
    customer = db.query(Customer).filter(Customer.unique_id == unique_id).first()
    reference_embedding = None
    if customer is not None and customer.face_embedding is not None:
        reference_embedding = json.dumps([float(x) for x in customer.face_embedding])

    async with httpx.AsyncClient() as client:
        files = {'file': (file.filename, file_bytes, file.content_type)}
        data = {'reference_embedding': reference_embedding} if reference_embedding else {}
        try:
            response = await client.post(f"{AI_SERVICE_URL}/face-match", files=files, data=data, timeout=20.0)
        except httpx.TimeoutException:
            raise HTTPException(status_code=503, detail="Face verification is taking too long. Please try again.")
        except httpx.ConnectError:
            raise HTTPException(status_code=503, detail="Unable to connect to the verification service. Please try again shortly.")

        if response.status_code == 200:
            result = response.json()
            embedding = result["embedding"]
            session_data["embedding"] = embedding

            # Venue check: blacklist + incident history, scoped to this venue
            blacklisted = False
            incidents = 0
            if customer:
                active_ban = db.query(Blacklist).filter(
                    Blacklist.customer_id == customer.id
                ).filter(
                    (Blacklist.expiry_date.is_(None)) | (Blacklist.expiry_date > datetime.now(timezone.utc))
                ).first()
                blacklisted = active_ban is not None
                incidents = db.query(Incident).filter(
                    Incident.customer_id == customer.id,
                    Incident.venue_id == current_user.venue_id
                ).count()

            session_data["venue_check"] = {
                "blacklisted": blacklisted,
                "incidents": incidents
            }

            # Real values from upstream steps instead of mocked constants
            ocr_confidence = float(ocr.get("confidence", 0.0))
            quality_score = float(session_data.get("classification", {}).get("type_confidence", 0.0)) * 100

            # Policy engine: consult the venue's configured thresholds. Age is
            # recalculated server-side from OCR'd DOB against this venue's
            # configured minimum_age, never trusting a client-supplied age
            # or the AI service's own hardcoded 18+ check.
            policy = venue_service.get_venue_policy(db, current_user.venue_id)
            face_similarity = result.get("similarity")
            face_similarity = float(face_similarity) if face_similarity is not None else None

            age_info = session_data["validation"].get("age_verification", {})
            age = age_info.get("age")
            meets_minimum_age = age is not None and age >= policy.minimum_age

            explainability = {
                "ocr_confidence": ocr_confidence,
                "image_quality": quality_score,
                "face_similarity": face_similarity,
                "blacklist_hit": blacklisted,
                "age": age,
                "minimum_age": policy.minimum_age,
                "meets_minimum_age": meets_minimum_age,
                "policy_trigger": "PASS"
            }

            if blacklisted:
                decision = "BLOCKED"
                explainability["policy_trigger"] = "BLACKLIST"
                session_service.update_session_data(db, session_id, {"final_decision": "blocked", "customer_id": customer.id})
                session_service.transition_state(db, session_id, SessionStateEnum.DENIED)
                # Known repeat offender caught mid-session — move this and
                # any past session's images into banned/ immediately.
                session_service.quarantine_customer_images(db, customer.id)
            elif not session_data["validation"].get("is_valid"):
                decision = "CHECK"
                explainability["policy_trigger"] = "INVALID_DOCUMENT"
            elif not meets_minimum_age:
                decision = "DENY"
                explainability["policy_trigger"] = "UNDERAGE"
            elif ocr_confidence < policy.ocr_confidence_threshold * 100:
                decision = "CHECK"
                explainability["policy_trigger"] = "LOW_OCR_CONFIDENCE"
            elif policy.require_face_match and (face_similarity is None or face_similarity < policy.face_similarity_threshold):
                decision = "CHECK"
                explainability["policy_trigger"] = "FACE_MISMATCH"
            else:
                decision = "PASS"

            session_data["decision"] = decision
            session_data["explainability"] = explainability
            session_data["step"] = 4
            redis_client.setex(f"session:{session_id}", 3600, json.dumps(session_data))

            try:
                session_service.update_session_data(db, session_id, {
                    "face_similarity": face_similarity,
                    "risk_score": 1.0 if blacklisted else (0.5 if decision == "CHECK" else 0.0),
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
        elif response.status_code == 422:
            raise HTTPException(status_code=422, detail="No face detected in the captured image")
        else:
            raise HTTPException(status_code=500, detail="Face matching failed")

@router.post("/session/{session_id}/finalize")
async def finalize_session(
    session_id: str,
    decision: VerificationDecision,
    db: Session = Depends(get_db),
    redis_client = Depends(get_redis),
    current_user: User = Depends(get_current_active_user)
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

    # State mapping (computed early so retention window can vary by outcome)
    final_decision_str = decision.staff_decision.lower()

    if not customer:
        dob_str = ocr.get("dob")
        dob_date = None
        if dob_str:
            try:
                from dateutil import parser as date_parser
                dob_date = date_parser.parse(dob_str)
            except Exception:
                dob_date = None

        # Retention window comes from the venue's own policy, not a
        # hardcoded constant: a clean PASS uses the shorter
        # retention_days_success window (default 7), anything requiring a
        # manual decision (CHECK/DENY/BLOCK) uses the longer
        # retention_days_manual window (default 30) since those records are
        # more likely to matter for a later dispute/review.
        venue_config = venue_service.get_venue_configuration(db, current_user.venue_id)
        retention_days = (
            venue_config.retention_days_success
            if final_decision_str == "pass"
            else venue_config.retention_days_manual
        )
        expires = datetime.now(timezone.utc) + timedelta(days=retention_days)

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

    # Persist the real OCR extraction as a Document row so the admin
    # console (GET /visitors) can show the actual document type/number/
    # expiry instead of always falling back to "other"/blank.
    def _parse_doc_date(value):
        if not value:
            return None
        try:
            from dateutil import parser as date_parser
            return date_parser.parse(value)
        except Exception:
            return None

    classification = session_data.get("classification", {})
    document = Document(
        customer_id=customer.id,
        doc_type=ocr.get("document_type") or classification.get("document_type") or "other",
        doc_number=unique_id,
        expiry_date=_parse_doc_date(ocr.get("expiry_date")),
        issue_date=_parse_doc_date(ocr.get("issue_date")),
        nationality=ocr.get("nationality"),
        extracted_data=ocr,
    )
    db.add(document)
    db.commit()
    new_ban_created = False
    if final_decision_str == "pass":
        final_state = SessionStateEnum.APPROVED
    elif final_decision_str == "deny":
        final_state = SessionStateEnum.DENIED
    elif final_decision_str in ["block", "restrict"]:
        final_state = SessionStateEnum.DENIED
        # Create Blacklist record
        existing_ban = db.query(Blacklist).filter(Blacklist.customer_id == customer.id).first()
        if not existing_ban:
            new_ban = Blacklist(
                customer_id=customer.id,
                reason=decision.notes or "Manual RESTRICT by Operator",
                banned_by_id=current_user.id
            )
            db.add(new_ban)
            db.commit()
            new_ban_created = True
    else:
        final_state = SessionStateEnum.FRAUD_REVIEW

    try:
        # customer_id must be linked to this session before quarantining,
        # since quarantine_customer_images looks up images by customer_id —
        # this session's own id/face images wouldn't otherwise be found yet.
        session_service.update_session_data(db, session_id, {"final_decision": final_decision_str, "customer_id": customer.id})
        session_service.transition_state(db, session_id, final_state)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    if new_ban_created:
        session_service.quarantine_customer_images(db, customer.id)

    if final_state == SessionStateEnum.APPROVED:
        # Person is now inside the venue — separate table from
        # VerificationSession since occupancy needs to keep changing
        # (checkout, auto-expire) after the session itself is locked.
        db.add(Occupancy(
            venue_id=current_user.venue_id,
            customer_id=customer.id,
            session_id=session_id,
        ))
        db.commit()

    redis_client.delete(f"session:{session_id}")
    
    # Trigger Notification for DENY or CHECK
    if final_state in [SessionStateEnum.DENIED, SessionStateEnum.FRAUD_REVIEW]:
        notif = Notification(
            venue_id=current_user.venue_id,
            message=f"Session {session_id[:8]} flagged as {final_decision_str.upper()}: {decision.notes or 'No reason provided'}",
            type="ALERT"
        )
        db.add(notif)
        db.commit()
    
    return {"success": True, "message": "Session finalized and locked as immutable package", "customer_id": customer.id}

@router.get("/visitors")
async def get_visitors(
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    # Scope to customers who have visited the caller's venue, so one venue
    # never sees another venue's restricted customer data (spec section 29).
    customer_ids = db.query(VerificationSession.customer_id).filter(
        VerificationSession.venue_id == current_user.venue_id,
        VerificationSession.customer_id.isnot(None)
    ).distinct()
    customers = db.query(Customer).filter(Customer.id.in_(customer_ids)).order_by(Customer.created_at.desc()).limit(limit).all()
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
            
        now = datetime.now(timezone.utc)
        age = (now.year - c.dob.year - ((now.month, now.day) < (c.dob.month, c.dob.day))) if c.dob else 0
        
        results.append({
            "id": str(c.id),
            "name": c.name or "Unknown",
            "dob": c.dob.isoformat() if c.dob else "",
            "age": age,
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
async def get_session_history(
    limit: int = 50,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    # Simple history query showing recent VerificationSession records for the caller's venue
    sessions = db.query(VerificationSession).filter(
        VerificationSession.venue_id == current_user.venue_id
    ).order_by(VerificationSession.created_at.desc()).limit(limit).all()

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
async def get_notifications(
    limit: int = 50,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    notifs = db.query(Notification).filter(
        Notification.venue_id == current_user.venue_id
    ).order_by(Notification.created_at.desc()).limit(limit).all()
    return [{
        "id": n.id,
        "message": n.message,
        "type": n.type,
        "is_read": n.is_read,
        "created_at": n.created_at.isoformat()
    } for n in notifs]

from backend.api.deps import RoleChecker
from backend.models.models import RoleEnum
require_super_admin = RoleChecker([RoleEnum.super_admin])

@router.post("/admin/flush", dependencies=[Depends(require_super_admin)])
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

    # Delete the S3 objects themselves before dropping the DB rows that
    # reference them — otherwise a flush only clears Postgres and leaves
    # every non-banned image sitting in the normal/ prefix forever. Banned
    # customers are already excluded above, so nothing under banned/ is
    # ever touched here.
    for session in expendable_sessions:
        if session.id_image_path:
            storage_service.delete_image(session.id_image_path)
        if session.face_image_path:
            storage_service.delete_image(session.face_image_path)

    try:
        # Occupancy rows reference both customers and sessions via FK, so
        # they must go first — otherwise deleting the sessions/customers
        # below violates occupancy_records_session_id_fkey /
        # occupancy_records_customer_id_fkey.
        if expendable_customer_ids:
            db.query(Occupancy).filter(Occupancy.customer_id.in_(expendable_customer_ids)).delete(synchronize_session=False)

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

@router.post("/admin/retention/run", dependencies=[Depends(require_super_admin)])
async def run_retention_now(db: Session = Depends(get_db)):
    """Manually triggers the data retention job immediately, outside its
    normal hourly schedule. Runs synchronously since the job is lightweight
    (one query plus a per-row anonymize) and returns the same summary it
    writes to the audit log."""
    from backend.services.retention_cron import delete_expired_records
    summary = delete_expired_records(trigger="manual", db=db)
    if "error" in summary:
        raise HTTPException(status_code=500, detail=f"Retention job failed: {summary['error']}")
    return {"success": True, **summary}

@router.get("/admin/retention/logs", dependencies=[Depends(require_super_admin)])
async def get_retention_logs(limit: int = 50, db: Session = Depends(get_db)):
    """Returns the audit trail of past retention job runs (scheduled and
    manually-triggered), most recent first."""
    logs = (
        db.query(AuditLog)
        .filter(AuditLog.action == "retention_cleanup")
        .order_by(AuditLog.timestamp.desc())
        .limit(limit)
        .all()
    )
    return [
        {
            "id": log.id,
            "timestamp": log.timestamp.isoformat(),
            "details": log.details,
        }
        for log in logs
    ]
