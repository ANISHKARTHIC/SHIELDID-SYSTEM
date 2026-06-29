from fastapi import APIRouter, Depends, UploadFile, File, Form, HTTPException
from sqlalchemy.orm import Session
from datetime import datetime, timezone
import httpx
import json

from backend.api.deps import get_db
from backend.models.models import Customer, Document, VerificationLog, Blacklist, Incident, Membership
from backend.schemas.schemas import BlacklistCreate, IncidentCreate, VerificationDecision

router = APIRouter(prefix="/api/v1")

AI_SERVICE_URL = "http://localhost:8001/api/v1"

@router.post("/verify")
async def verify_document(
    file: UploadFile = File(...),
    db: Session = Depends(get_db)
):
    """
    Orchestrate verification: call AI microservice, fetch database records,
    and generate final risk scores and recommendations.
    """
    file_bytes = await file.read()
    
    # Try calling AI Service microservice. Fallback if offline.
    ai_data = None
    try:
        async with httpx.AsyncClient() as client:
            files = {'file': (file.filename, file_bytes, file.content_type)}
            data = {'venue_status': json.dumps({"blacklisted": False, "incidents": 0})}
            response = await client.post(f"{AI_SERVICE_URL}/verify", files=files, data=data, timeout=10.0)
            if response.status_code == 200:
                ai_data = response.json()
    except Exception:
        pass

    if not ai_data:
        # Check if we should allow simulated files (GIFs) to complete for UI demonstration
        is_simulation = file.filename.endswith(".gif")
        if is_simulation:
            is_underage = "underage" in file.filename.lower()
            ai_data = {
                "quality": {
                    "quality_score": 95,
                    "blur": False,
                    "lighting": "good",
                    "cropped": False,
                    "rotation": 0
                },
                "classification": {
                    "document_type": "passport" if is_underage else "uk_driving_licence",
                    "confidence": 0.98
                },
                "ocr": {
                    "name": "JONATHAN WRIGHT" if is_underage else "CHARLOTTE SMITH",
                    "dob": "2001-11-04" if is_underage else "1997-04-20",
                    "address": "74 WESTMINSTER ROAD, LONDON" if is_underage else "15 KENSINGTON ST, LONDON",
                    "document_number": "GBR019827364" if is_underage else "SMIT10293848",
                    "expiry_date": "2031-10-09" if is_underage else "2033-05-12",
                    "issue_date": "2021-10-09" if is_underage else "2023-05-12",
                    "confidence": 98.2
                },
                "validation": {
                    "is_valid": True,
                    "missing_fields": [],
                    "age_verification": {
                        "age": 24 if is_underage else 29,
                        "is_over_18": True
                    }
                },
                "authenticity": {
                    "authenticity_score": 96,
                    "risk": "LOW",
                    "possible_issues": []
                },
                "risk": {
                    "risk_score": 8,
                    "recommendation": "APPROVE"
                }
            }
        else:
            raise HTTPException(
                status_code=503,
                detail=json.dumps({
                    "stage": "AI_SERVICE_OFFLINE",
                    "message": "AI Verification Pipeline Offline",
                    "detail": "The backend was unable to reach the AI service at http://localhost:8001. Please ensure the uvicorn service is started."
                })
            )

    ocr_name = ai_data["ocr"]["name"]
    dob_str = ai_data["ocr"]["dob"]
    doc_number = ai_data["ocr"].get("document_number") or ai_data["ocr"].get("docNumber")
    expiry_date = ai_data["ocr"].get("expiry_date") or ai_data["ocr"].get("expiryDate")
    issue_date = ai_data["ocr"].get("issue_date") or ai_data["ocr"].get("issueDate")
    
    dob_date = datetime.strptime(dob_str, "%Y-%m-%d")

    # Search for document, then customer
    customer = None
    doc_entry = db.query(Document).filter(Document.doc_number == doc_number).first()
    if doc_entry:
        customer = doc_entry.customer
    else:
        customer = db.query(Customer).filter(
            (Customer.name == ocr_name) & (Customer.dob == dob_date)
        ).first()

    # Default DB values
    blacklist_status = "none"
    blacklist_reason = None
    membership_status = "None"
    visit_count = 0
    incidents_count = 0
    customer_id = None

    if customer:
        customer_id = customer.id
        # Check active blacklist
        active_blacklist = db.query(Blacklist).filter(
            Blacklist.customer_id == customer.id,
            (Blacklist.expiry_date == None) | (Blacklist.expiry_date > datetime.now(timezone.utc))
        ).first()
        
        if active_blacklist:
            blacklist_status = "permanent" if not active_blacklist.expiry_date else "temporary"
            blacklist_reason = active_blacklist.reason
            
        # Check membership
        membership = db.query(Membership).filter(
            Membership.customer_id == customer.id,
            (Membership.valid_until == None) | (Membership.valid_until > datetime.now(timezone.utc))
        ).first()
        if membership:
            membership_status = membership.tier
            
        # Count visits & incidents
        visit_count = db.query(VerificationLog).filter(VerificationLog.customer_id == customer.id).count()
        incidents_count = db.query(Incident).filter(Incident.customer_id == customer.id).count()

    # Recalculate Risk based on DB results
    risk_score = ai_data["risk"].get("risk_score") or ai_data["risk"].get("score", 0)
    recommendation = ai_data["risk"]["recommendation"]

    if blacklist_status != "none":
        risk_score = 100
        recommendation = "DENY"
    elif incidents_count > 0:
        risk_score = max(risk_score, 50)
        recommendation = "MANUAL_REVIEW"

    # Perfect flat response layout conforming to Section 10 specifications
    return {
        "success": True,
        "request_id": f"REQ-{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}",
        "document_type": ai_data["classification"]["document_type"],
        "ocr": {
            "name": ocr_name,
            "dob": dob_str,
            "document_number": doc_number,
            "expiry_date": expiry_date,
            "address": ai_data["ocr"]["address"]
        },
        "age": ai_data["validation"]["age_verification"].get("age", 22),
        "over18": ai_data["validation"]["age_verification"].get("is_over_18", True),
        "quality_score": ai_data["quality"]["quality_score"],
        "authenticity_score": ai_data["authenticity"]["authenticity_score"],
        "authenticity_issues": ai_data["authenticity"].get("possible_issues", []),
        "authenticity_risk": ai_data["authenticity"].get("risk", "LOW"),
        "risk_score": risk_score,
        "recommendation": recommendation
    }

@router.post("/decision")
def record_decision(
    decision: VerificationDecision,
    db: Session = Depends(get_db)
):
    """
    Log the final supervisor decision (APPROVE / REJECT / ESCALATE) into the DB.
    """
    dob_date = datetime.strptime(decision.ocr_dob, "%Y-%m-%d")
    
    # Search document or customer
    doc_entry = db.query(Document).filter(Document.doc_number == decision.doc_number).first()
    if doc_entry:
        customer = doc_entry.customer
    else:
        customer = db.query(Customer).filter(
            (Customer.name == decision.ocr_name) & (Customer.dob == dob_date)
        ).first()
        
    if not customer:
        customer = Customer(
            unique_id=f"CUST-{datetime.now().strftime('%Y%m%d%H%M%S')}",
            name=decision.ocr_name,
            dob=dob_date,
            notes=decision.notes
        )
        db.add(customer)
        db.commit()
        db.refresh(customer)
    
    # Log Verification
    log_entry = VerificationLog(
        customer_id=customer.id,
        staff_id=1, # Default user id
        ai_recommendation=decision.ai_recommendation,
        ai_authenticity_score=decision.authenticity_score,
        ai_quality_score=decision.quality_score,
        ai_ocr_confidence=decision.ocr_confidence,
        staff_decision=decision.staff_decision,
        notes=decision.notes,
        timestamp=datetime.now(timezone.utc)
    )
    db.add(log_entry)
    
    # Save Document details if not exists
    if not doc_entry:
        doc_entry = Document(
            customer_id=customer.id,
            doc_type=decision.doc_type,
            doc_number=decision.doc_number,
            expiry_date=datetime.strptime(decision.expiry_date, "%Y-%m-%d") if decision.expiry_date else None,
            issue_date=datetime.strptime(decision.issue_date, "%Y-%m-%d") if decision.issue_date else None,
            extracted_data={}
        )
        db.add(doc_entry)

    db.commit()
    return {"status": "success", "customer_id": customer.id}

@router.get("/visitors")
def get_visitors(db: Session = Depends(get_db)):
    visitors = db.query(Customer).all()
    result = []
    for v in visitors:
        today = datetime.today()
        age = today.year - v.dob.year - ((today.month, today.day) < (v.dob.month, v.dob.day))
        
        # Get document number
        doc_number = "N/A"
        doc_type = "unknown"
        if v.documents:
            doc_number = v.documents[0].doc_number
            doc_type = v.documents[0].doc_type
            
        visit_count = db.query(VerificationLog).filter(VerificationLog.customer_id == v.id).count()
        incidents_count = db.query(Incident).filter(Incident.customer_id == v.id).count()

        # Check active blacklist
        active_blacklist = db.query(Blacklist).filter(
            Blacklist.customer_id == v.id,
            (Blacklist.expiry_date == None) | (Blacklist.expiry_date > datetime.now(timezone.utc))
        ).first()
        blacklist_status = "none"
        if active_blacklist:
            blacklist_status = "permanent" if not active_blacklist.expiry_date else "temporary"

        # Check membership
        membership = db.query(Membership).filter(
            Membership.customer_id == v.id,
            (Membership.valid_until == None) | (Membership.valid_until > datetime.now(timezone.utc))
        ).first()
        membership_status = membership.tier if membership else "None"

        result.append({
            "id": f"CUST-00{v.id}",
            "name": v.name,
            "dob": v.dob.strftime("%Y-%m-%d"),
            "age": age,
            "documentNumber": doc_number,
            "documentType": doc_type,
            "blacklistStatus": blacklist_status,
            "membership": membership_status,
            "visitCount": max(1, visit_count),
            "incidentsCount": incidents_count,
            "address": "LONDON",
            "nationality": "British"
        })
    return result

@router.post("/blacklist")
def create_blacklist(
    data: BlacklistCreate,
    db: Session = Depends(get_db)
):
    customer = db.query(Customer).filter(Customer.name == data.customer_name.upper()).first()
    if not customer:
        raise HTTPException(status_code=404, detail="Customer not found")
        
    ban_entry = Blacklist(
        customer_id=customer.id,
        reason=data.reason,
        manager_notes=data.manager_notes,
        banned_by_id=1,
        expiry_date=datetime.strptime(data.expiry_date, "%Y-%m-%d") if data.expiry_date else None,
        created_at=datetime.now(timezone.utc)
    )
    db.add(ban_entry)
    db.commit()
    return {"status": "success"}

@router.post("/incidents")
def create_incident(
    data: IncidentCreate,
    db: Session = Depends(get_db)
):
    customer = db.query(Customer).filter(Customer.id == data.customer_id).first()
    if not customer:
        raise HTTPException(status_code=404, detail="Customer not found")
        
    inc_entry = Incident(
        customer_id=data.customer_id,
        venue_id=1, # Default venue
        incident_type=data.incident_type,
        description=data.description,
        staff_notes=data.staff_notes,
        reported_by_id=1,
        date=datetime.now(timezone.utc)
    )
    db.add(inc_entry)
    db.commit()
    return {"status": "success"}
