from fastapi import FastAPI, File, UploadFile, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import logging
import re
import json
import numpy as np

from contextlib import asynccontextmanager
from app.core.model_registry import model_registry

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Load AI models on startup
    model_registry.initialize_models()
    yield
    # Clean up if needed
    pass

app = FastAPI(
    title="VenuePass AI Verification Service",
    description="Independent AI Microservice for Document Processing.",
    version="1.0.0",
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

logger = logging.getLogger("ai_main")

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error(f"AI Service error: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={
            "success": False,
            "stage": "AI_INFERENCE_PIPELINE",
            "message": "An error occurred during AI processing pipeline",
            "error_code": "AI_PIPELINE_ERROR",
            "detail": str(exc)
        },
        headers={
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Methods": "*",
            "Access-Control-Allow-Headers": "*",
        }
    )

@app.get("/")
def read_root():
    return {"message": "AI Service is running."}

@app.post("/scan/document")
async def scan_document_endpoint(file: UploadFile = File(...)):
    contents = await file.read()
    from app.services.image_utils import resize_image_for_ai
    contents = resize_image_for_ai(contents, max_dim=1024)

    from app.services.image_quality import assess_image_quality
    from app.services.document_classifier import classify_document
    from app.services.ocr.factory import get_ocr_provider
    from app.services.data_validation import validate_extracted_data
    from app.services.document_authenticity import assess_authenticity
    from app.services.risk_engine import calculate_risk
    
    # 1. Quality
    quality = assess_image_quality(contents)
    
    # 2. Classify
    classification = classify_document(contents, file.filename)
    
    # 3. OCR
    ocr_provider = get_ocr_provider()
    ocr_result = ocr_provider.extract_text(contents, classification["document_type"])
    
    # 4. Validation
    validation = validate_extracted_data(ocr_result)
    
    # 5. Authenticity
    authenticity = assess_authenticity(contents, ocr_result["confidence"], quality)
    
    # 6. Risk Engine
    is_over_18 = validation["age_verification"].get("is_over_18", False)
    risk = calculate_risk(
        ocr_confidence=ocr_result["confidence"],
        quality_score=quality["quality_score"],
        authenticity_score=authenticity["authenticity_score"],
        is_over_18=is_over_18,
        venue_status={"blacklisted": False, "incidents": 0}
    )
    
    # format name split
    full_name = ocr_result["name"]
    parts = full_name.split()
    if len(parts) > 1:
        first_name = " ".join(parts[:-1])
        last_name = parts[-1]
    elif len(parts) == 1:
        first_name = parts[0]
        last_name = ""
    else:
        first_name = ""
        last_name = ""
        
    extracted_data = {
        "first_name": first_name,
        "last_name": last_name,
        "date_of_birth": ocr_result["dob"],
        "document_number": ocr_result["document_number"],
        "expiry_date": ocr_result["expiry_date"],
        "nationality": "GBR" if classification["document_type"] == "uk_driving_licence" else "Unknown"
    }
    
    is_genuine = risk["recommendation"] == "PASS"
    
    ocr_validation_errors = ocr_result.get("validation", {}).get("errors", [])
    general_validation_errors = []
    if not validation["is_valid"]:
        if validation["missing_fields"]:
            general_validation_errors.append(f"Missing required fields: {', '.join(validation['missing_fields'])}")
        if validation["age_verification"].get("error"):
            general_validation_errors.append(f"Age check: {validation['age_verification']['error']}")
            
    return {
        "visitor_id": None,
        "status": "genuine" if is_genuine else "suspicious",
        "recommendation": risk["recommendation"],
        "risk_score": float(risk["risk_score"]) / 100.0,
        "extracted_data": extracted_data,
        "flags": authenticity["possible_issues"] + ocr_validation_errors + general_validation_errors
    }

from app.services.classifier import classify_document_real
from app.services.document_classifier import classify_document

@app.post("/classify")
async def classify_document_endpoint(file: UploadFile = File(...)):
    """Step 1: Determine if the uploaded image is a valid identity document,
    and which supported document type it is, so OCR can route correctly."""
    contents = await file.read()
    from app.services.image_utils import resize_image_for_ai
    contents = resize_image_for_ai(contents, max_dim=1024)
    result = classify_document_real(contents)
    if result["is_valid"]:
        type_result = classify_document(contents, file.filename or "")
        result["document_type"] = type_result["document_type"]
        result["type_confidence"] = type_result["confidence"]
        if type_result["document_type"] == "unknown":
            # A face was detected, but no real evidence of a supported
            # document (UK licence / passport marker text or number/MRZ
            # shape) was found in the image content — reject rather than
            # silently defaulting to a guessed document type.
            result["is_valid"] = False
            result["reason"] = (
                "Could not identify this as a supported document. "
                "Please scan a UK driving licence or passport."
            )
    return result

@app.post("/ocr")
async def extract_ocr_endpoint(file: UploadFile = File(...), document_type: str = "uk_driving_licence"):
    """Step 2: Extract text from the identity document, routed by the
    document_type determined during /classify (defaults to UK driving licence
    for backward compatibility if the caller omits it)."""
    contents = await file.read()
    from app.services.image_utils import resize_image_for_ai
    contents = resize_image_for_ai(contents, max_dim=1024)

    from app.services.ocr.factory import get_ocr_provider
    ocr_provider = get_ocr_provider()

    try:
        ocr_result = ocr_provider.extract_text(contents, document_type)
    except ValueError as e:
        # No legible text (out of focus, glare, wrong document, etc.) is an
        # expected user-recoverable outcome, not a server error.
        return JSONResponse(status_code=422, content={"success": False, "message": str(e)})

    from app.services.data_validation import validate_extracted_data
    validation = validate_extracted_data(ocr_result)

    return {
        "success": True,
        "extracted_data": ocr_result,
        "validation": validation
    }

from fastapi import Form

@app.post("/face-match")
async def face_match_endpoint(file: UploadFile = File(...), reference_embedding: str = Form(None)):
    """
    Step 3: Extract a real 512D ArcFace embedding for the captured face via
    InsightFace (RetinaFace detection + ArcFace recognition), and optionally
    compare it against a reference embedding (JSON-encoded list of floats)
    from a previously stored customer to produce a genuine similarity score.
    """
    import tempfile
    import os

    contents = await file.read()
    from app.services.image_utils import resize_image_for_ai
    contents = resize_image_for_ai(contents, max_dim=1024)
    face_provider = model_registry.get_provider('face')
    if face_provider is None or face_provider.app is None:
        raise HTTPException(status_code=503, detail="Face recognition model is not loaded")

    tmp_path = None
    try:
        with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as tmp:
            tmp.write(contents)
            tmp_path = tmp.name

        embedding = face_provider.extract_embedding(tmp_path)

        similarity = None
        if reference_embedding:
            ref = np.array(json.loads(reference_embedding), dtype=np.float32)
            similarity = face_provider.compare(embedding, ref)

        return {
            "success": True,
            "embedding": embedding.tolist(),
            "dimensions": len(embedding),
            "similarity": similarity
        }
    except ValueError as e:
        # No face detected in the captured image
        return JSONResponse(status_code=422, content={"success": False, "message": str(e)})
    finally:
        if tmp_path and os.path.exists(tmp_path):
            os.unlink(tmp_path)

from app.api.v1_router import router as v1_router
app.include_router(v1_router)
