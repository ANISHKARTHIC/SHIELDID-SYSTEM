from fastapi import APIRouter, Depends, UploadFile, File, HTTPException, Form
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
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
from backend.core.logger import get_logger
from backend.core.datetime_utils import to_utc_iso

logger = get_logger("ocr_extraction")

router = APIRouter(prefix="/api/v1", dependencies=[Depends(get_current_active_user)])

def get_ai_service_url() -> str:
    # settings.AI_SERVICE_URL already resolves the right value for both
    # cases: it defaults to http://localhost:8001 for local dev, and
    # docker-compose.yml sets the AI_SERVICE_URL env var explicitly to
    # http://ai-service:8001 (the compose network service name) for the
    # backend container — no runtime rewriting needed either way.
    return settings.AI_SERVICE_URL

@router.post("/session/start")
async def start_session(
    db: Session = Depends(get_db),
    redis_client = Depends(get_redis),
    current_user: User = Depends(get_current_active_user)
):
    """Initialize a new verification session for the authenticated operator's venue"""
    session = session_service.create_session(db, venue_id=current_user.venue_id, operator_id=current_user.id)
    session_id = session.id
    redis_client.set(f"session:{session_id}", json.dumps({"step": 1, "status": "started", "session_id": session_id}), ex=3600)
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
    # "Pending" means a decision was actually computed (the operator
    # reached the review screen) and is awaiting their confirm tap —
    # not merely "a session row exists with no final_decision yet". A
    # session that never got past document scan/OCR (closed early,
    # backgrounded, or simply the last few seconds of an in-progress
    # scan) previously counted here forever, since nothing ever expires
    # or finalizes it — inflating this number with abandoned scans that
    # were never really awaiting review.
    _reached_decision_states = {
        SessionStateEnum.FACE_VERIFIED,
        SessionStateEnum.DATABASE_CHECKED,
        SessionStateEnum.RISK_EVALUATED,
        SessionStateEnum.MANUAL_REVIEW,
        SessionStateEnum.FRAUD_REVIEW,
        SessionStateEnum.DENIED,
    }
    pending = sum(
        1 for s in sessions
        if s.final_decision is None
        and s.state in _reached_decision_states
        and s.created_at and s.created_at.date() == today
    )

    return {
        "operator_name": current_user.email.split("@")[0],
        "venue_name": current_user.venue.name if current_user.venue else None,
        "verified": verified,
        "pending": pending,
        "flagged": flagged
    }

@router.post("/session/{session_id}/scan")
async def scan_document(
    session_id: str,
    file: UploadFile = File(...),
    redis_client = Depends(get_redis),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Steps 1+2 combined: classify the document, then OCR it, in one call.

    Previously these were two separate endpoints — the mobile client
    uploaded the same photo twice (once to /classify, again to /ocr),
    paying for two full network round-trips plus two independent
    ai-service inference passes back-to-back before the operator saw any
    result. Since the OCR step's document_type routing comes directly from
    the classify step's own result, there's no cross-request dependency
    that actually requires a separate client round-trip in between — doing
    both server-side in one call removes one full upload+response cycle
    per scan entirely, which matters most exactly when it hurts most: a
    slow mobile uplink talking to a small/CPU-constrained server.
    """
    try:
        session_service.assert_session_venue(db, session_id, current_user.venue_id)
    except ValueError:
        raise HTTPException(status_code=404, detail="Session not found or expired")

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

    try:
        session_service.update_session_data(db, session_id, {"id_image_path": object_name})
        session_service.transition_state(db, session_id, SessionStateEnum.DOCUMENT_CLASSIFIED)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    ai_url = get_ai_service_url()
    async with httpx.AsyncClient() as client:
        files = {'file': (file.filename, file_bytes, file.content_type)}
        try:
            classify_response = await client.post(f"{ai_url}/classify", files=files, timeout=180.0)
        except httpx.TimeoutException:
            raise HTTPException(status_code=503, detail="Document classification is taking too long. Please try again.")
        except httpx.ConnectError:
            raise HTTPException(status_code=503, detail="Unable to connect to the verification service. Please try again shortly.")

        if classify_response.status_code != 200:
            raise HTTPException(status_code=500, detail="AI classification failed")

        classification = classify_response.json()
        if not classification.get("is_valid"):
            return {"success": False, "message": classification.get("reason")}

        session_data["id_image"] = object_name
        session_data["classification"] = classification
        if classification.get("face_embedding"):
            session_data["id_face_embedding"] = classification["face_embedding"]
        # step 2 (classified) is transient within this single call — no
        # client round-trip happens between classify and OCR anymore, so
        # this only matters if the OCR call below fails partway through
        # and a retry needs to know classification already succeeded.
        session_data["step"] = 2
        redis_client.set(f"session:{session_id}", json.dumps(session_data), ex=3600)

        document_type = classification.get("document_type", "uk_driving_licence")
        files = {'file': (file.filename, file_bytes, file.content_type)}
        try:
            ocr_response = await client.post(f"{ai_url}/ocr", files=files, params={"document_type": document_type}, timeout=180.0)
        except httpx.TimeoutException:
            raise HTTPException(status_code=503, detail="Text extraction is taking too long. Please try again.")
        except httpx.ConnectError:
            raise HTTPException(status_code=503, detail="Unable to connect to the verification service. Please try again shortly.")

        if ocr_response.status_code == 422:
            raise HTTPException(status_code=422, detail=ocr_response.json().get("message", "No legible text could be extracted from the document."))
        elif ocr_response.status_code != 200:
            raise HTTPException(status_code=500, detail="OCR extraction failed")

        result = ocr_response.json()
        session_data["ocr"] = result["extracted_data"]
        session_data["validation"] = result["validation"]
        session_data["step"] = 3
        redis_client.set(f"session:{session_id}", json.dumps(session_data), ex=3600)

        # Log exactly what was extracted vs. how confident/valid it was,
        # per-field — this is the primary tool for diagnosing bad
        # extractions (wrong surname, mismatched DOB, etc.) after the
        # fact: grep the backend log for the session_id to see the full
        # field/confidence/validation picture ai-service returned,
        # without needing to reproduce the scan.
        extracted = result.get("extracted_data", {})
        fields = extracted.get("fields", extracted)
        confidences = extracted.get("confidences", {})
        validation = result.get("validation", {})
        logger.info(
            "OCR extraction session=%s doc_type=%s fields=%s confidences=%s "
            "avg_confidence=%s valid=%s errors=%s",
            session_id,
            document_type,
            json.dumps(fields, default=str),
            json.dumps(confidences, default=str),
            extracted.get("confidence"),
            validation.get("is_valid"),
            validation.get("errors"),
        )

        try:
            session_service.update_session_data(db, session_id, {"ocr_data": result["extracted_data"]})
            session_service.transition_state(db, session_id, SessionStateEnum.OCR_COMPLETED)
        except ValueError:
            pass  # Ignoring errors for now

        return {"success": True, **result}

@router.post("/session/{session_id}/face")
async def face_match(
    session_id: str,
    file: UploadFile = File(...),
    redis_client = Depends(get_redis),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Step 3: Capture Face & Match"""
    try:
        session_service.assert_session_venue(db, session_id, current_user.venue_id)
    except ValueError:
        raise HTTPException(status_code=404, detail="Session not found")

    session_data_str = redis_client.get(f"session:{session_id}")
    if not session_data_str:
        raise HTTPException(status_code=404, detail="Session not found")
    session_data = json.loads(session_data_str)

    if session_data.get("step", 0) < 3:
        # ocr further down reads session_data["ocr"], which only exists
        # once /ocr has run — without this guard, calling /face out of
        # order raised a raw KeyError that surfaced as an opaque 500
        # instead of a clear, client-recoverable 400 like /ocr's own
        # step-order check.
        raise HTTPException(status_code=400, detail="OCR must be completed first")

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
    # stored face embedding as a real comparison reference, falling back to
    # the embedding extracted from the ID document itself for first-time visitors.
    ocr = session_data["ocr"]
    unique_id = ocr.get("document_number")
    customer = db.query(Customer).filter(Customer.unique_id == unique_id).first() if unique_id else None
    reference_embedding = None
    if customer is not None and customer.face_embedding is not None:
        reference_embedding = json.dumps([float(x) for x in customer.face_embedding])
    elif session_data.get("id_face_embedding"):
        reference_embedding = json.dumps([float(x) for x in session_data["id_face_embedding"]])

    ai_url = get_ai_service_url()
    async with httpx.AsyncClient() as client:
        files = {'file': (file.filename, file_bytes, file.content_type)}
        data = {'reference_embedding': reference_embedding} if reference_embedding else {}
        try:
            response = await client.post(f"{ai_url}/face-match", files=files, data=data, timeout=180.0)
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
                reason = "Customer is on the venue blacklist."
                risk_score = 1.0
                session_service.update_session_data(db, session_id, {"final_decision": "blocked", "customer_id": customer.id if customer else None})
                session_service.transition_state(db, session_id, SessionStateEnum.DENIED)
                # Known repeat offender caught mid-session — move this and
                # any past session's images into banned/ immediately.
                if customer:
                    session_service.quarantine_customer_images(db, customer.id)
            elif not session_data["validation"].get("is_valid"):
                decision = "CHECK"
                explainability["policy_trigger"] = "INVALID_DOCUMENT"
                reason = "Document failed critical authenticity or format validation."
                risk_score = 0.85
            elif not meets_minimum_age:
                decision = "DENY"
                explainability["policy_trigger"] = "UNDERAGE"
                reason = f"Visitor age ({age if age is not None else 'Unknown'}) is under the minimum age requirement ({policy.minimum_age})."
                risk_score = 1.0
            elif quality_score < policy.quality_threshold * 100:
                decision = "CHECK"
                explainability["policy_trigger"] = "LOW_IMAGE_QUALITY"
                reason = f"Image quality ({quality_score:.1f}%) is below venue requirement ({policy.quality_threshold * 100:.0f}%)."
                risk_score = 0.60
            elif ocr_confidence < policy.ocr_confidence_threshold * 100:
                decision = "CHECK"
                explainability["policy_trigger"] = "LOW_OCR_CONFIDENCE"
                reason = f"OCR confidence ({ocr_confidence:.1f}%) is below venue requirement ({policy.ocr_confidence_threshold * 100:.0f}%)."
                risk_score = 0.50
            elif policy.require_face_match and face_similarity is None:
                decision = "CHECK"
                explainability["policy_trigger"] = "NO_REFERENCE_FACE"
                reason = "No reference face photo found on document for comparison."
                risk_score = 0.50
            elif policy.require_face_match and face_similarity < policy.face_similarity_threshold:
                decision = "CHECK"
                explainability["policy_trigger"] = "FACE_MISMATCH"
                reason = f"Face similarity ({face_similarity * 100:.1f}%) is below venue requirement ({policy.face_similarity_threshold * 100:.0f}%)."
                risk_score = 0.70
            else:
                decision = "PASS"
                explainability["policy_trigger"] = "PASS"
                reason = "All identity, document, and venue policy checks passed."
                risk_score = round(max(0.0, (1.0 - (face_similarity if face_similarity is not None else 1.0)) * 0.2), 3)

            session_data["decision"] = decision
            session_data["explainability"] = explainability
            session_data["risk_score"] = risk_score
            session_data["reason"] = reason
            session_data["step"] = 4
            redis_client.set(f"session:{session_id}", json.dumps(session_data), ex=3600)

            try:
                session_service.update_session_data(db, session_id, {
                    "face_similarity": face_similarity,
                    "risk_score": risk_score,
                    "explainability_report": explainability
                })
                session_service.transition_state(db, session_id, SessionStateEnum.FACE_VERIFIED)
            except ValueError:
                pass

            return {
                "success": True,
                "decision": decision,
                "risk_score": risk_score,
                "face_similarity": face_similarity,
                "policy_trigger": explainability["policy_trigger"],
                "reason": reason,
                "explainability": explainability,
                "venue_check": session_data["venue_check"]
            }
        elif response.status_code == 422:
            # Surface the ai-service's specific reason (no face detected vs.
            # face detected but too low-confidence/small to trust) instead
            # of a single generic message — the operator needs to know
            # whether to reposition the ID or retake the selfie.
            detail = "No face detected in the captured image"
            try:
                detail = response.json().get("message", detail)
            except Exception:
                pass
            raise HTTPException(status_code=422, detail=detail)
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
    try:
        session_service.assert_session_venue(db, session_id, current_user.venue_id)
    except ValueError:
        raise HTTPException(status_code=404, detail="Session not found")

    session_data_str = redis_client.get(f"session:{session_id}")
    if not session_data_str:
        raise HTTPException(status_code=404, detail="Session not found")
    session_data = json.loads(session_data_str)

    ocr = session_data.get("ocr")
    if not ocr:
        raise HTTPException(status_code=400, detail="Incomplete session")

    # The face-capture/match step (/session/{id}/face) must have run before
    # a session can be finalized as "pass" — without this, an operator (or
    # a client that crashes/drops after OCR) could call /finalize directly
    # from step 3, approving entry with zero face verification and, since
    # the blacklist lookup only happens inside /face, with zero blacklist
    # check either. CHECK/DENY/BLOCK outcomes don't need this guard since
    # they're already the safe/restrictive path.
    if decision.staff_decision.lower() == "pass" and session_data.get("step", 0) < 4:
        raise HTTPException(status_code=400, detail="Face verification must be completed before approving entry")

    unique_id = ocr.get("document_number")
    customer = db.query(Customer).filter(Customer.unique_id == unique_id).first()

    # Safety-net blacklist check: /face already checks this and blocks the
    # session, but finalize must not trust the client to have taken that
    # path faithfully — re-check directly against the DB before honoring a
    # "pass" so a stale/replayed session_data blob or a decision issued
    # after a ban was created mid-session can't slip through.
    if customer and decision.staff_decision.lower() == "pass":
        active_ban = db.query(Blacklist).filter(
            Blacklist.customer_id == customer.id
        ).filter(
            (Blacklist.expiry_date.is_(None)) | (Blacklist.expiry_date > datetime.now(timezone.utc))
        ).first()
        if active_ban:
            raise HTTPException(status_code=409, detail="Customer has an active venue restriction and cannot be approved")

    # State mapping (computed early so retention window can vary by outcome)
    final_decision_str = decision.staff_decision.lower()

    if not customer:
        dob_str = ocr.get("dob")
        dob_date = None
        if dob_str:
            try:
                from dateutil import parser as date_parser
                # dayfirst=True: UK documents use DD/MM/YYYY; dateutil
                # defaults to month-first for ambiguous numeric dates
                # otherwise (e.g. "03/04/1990" would parse as March 4th).
                dob_date = date_parser.parse(dob_str, dayfirst=True)
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
    else:
        # Returning visitor: extend data retention window from this visit
        venue_config = venue_service.get_venue_configuration(db, current_user.venue_id)
        retention_days = (
            venue_config.retention_days_success
            if final_decision_str == "pass"
            else venue_config.retention_days_manual
        )
        new_expires = datetime.now(timezone.utc) + timedelta(days=retention_days)
        cur_expires = customer.expires_at
        if cur_expires is not None and cur_expires.tzinfo is None:
            cur_expires = cur_expires.replace(tzinfo=timezone.utc)
        if cur_expires is None or cur_expires < new_expires:
            customer.expires_at = new_expires
        if session_data.get("embedding"):
            customer.face_embedding = session_data.get("embedding")
        db.commit()

    # Persist the real OCR extraction as a Document row so the admin
    # console (GET /visitors) can show the actual document type/number/
    # expiry instead of always falling back to "other"/blank.
    def _parse_doc_date(value):
        if not value:
            return None
        try:
            from dateutil import parser as date_parser
            # dayfirst=True: same UK DD/MM/YYYY convention as the DOB parse
            # above — avoids month/day ambiguity for issue/expiry dates.
            return date_parser.parse(value, dayfirst=True)
        except Exception:
            return None

    classification = session_data.get("classification", {})
    existing_doc = db.query(Document).filter(
        Document.customer_id == customer.id,
        Document.doc_number == unique_id
    ).first()
    if existing_doc:
        existing_doc.doc_type = ocr.get("document_type") or classification.get("document_type") or existing_doc.doc_type
        existing_doc.expiry_date = _parse_doc_date(ocr.get("expiry_date")) or existing_doc.expiry_date
        existing_doc.issue_date = _parse_doc_date(ocr.get("issue_date")) or existing_doc.issue_date
        existing_doc.nationality = ocr.get("nationality") or existing_doc.nationality
        existing_doc.extracted_data = ocr
        db.commit()
    else:
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
        # Create Blacklist record if not already actively banned
        existing_ban = db.query(Blacklist).filter(
            Blacklist.customer_id == customer.id
        ).filter(
            (Blacklist.expiry_date.is_(None)) | (Blacklist.expiry_date > datetime.now(timezone.utc))
        ).first()
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
        # (checkout, auto-expire) after the session itself is locked. The
        # DB enforces at most one open (exited_at IS NULL) row per
        # (venue_id, customer_id) via uq_occupancy_open_per_venue_customer —
        # a concurrent duplicate finalize for the same customer raises
        # IntegrityError here rather than silently creating a second open
        # row, so surface that as a clear conflict instead of a raw 500.
        db.add(Occupancy(
            venue_id=current_user.venue_id,
            customer_id=customer.id,
            session_id=session_id,
        ))
        try:
            db.commit()
        except IntegrityError:
            db.rollback()
            raise HTTPException(status_code=409, detail="Customer is already checked in at this venue")

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
        
        # Check for active (non-expired) ban
        active_ban = None
        for b in c.blacklist:
            b_exp = b.expiry_date
            if b_exp and b_exp.tzinfo is None:
                b_exp = b_exp.replace(tzinfo=timezone.utc)
            if b.expiry_date is None or b_exp > now:
                active_ban = b
                break

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
            "blacklistStatus": ("permanent" if active_ban.expiry_date is None else "temporary") if active_ban else "none",
            "blacklistReason": active_ban.reason if active_ban else "",
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
            "created_at": to_utc_iso(s.created_at),
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
        "created_at": to_utc_iso(n.created_at)
    } for n in notifs]

from backend.api.deps import RoleChecker
from backend.models.models import RoleEnum
require_super_admin = RoleChecker([RoleEnum.super_admin])

@router.post("/admin/flush", dependencies=[Depends(require_super_admin)])
async def flush_data(db: Session = Depends(get_db)):
    """Flushes all visitors and session data EXCEPT blacklisted users."""
    # Find all customer IDs that have active non-expired blacklists
    now = datetime.now(timezone.utc)
    blacklisted_ids_query = db.query(Blacklist.customer_id).filter(
        (Blacklist.expiry_date.is_(None)) | (Blacklist.expiry_date > now)
    ).distinct()
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
            "timestamp": to_utc_iso(log.timestamp),
            "details": log.details,
        }
        for log in logs
    ]
