from fastapi import APIRouter, File, UploadFile, HTTPException, Form
from app.schemas.ai_schemas import (
    QualityResponse, ClassifyResponse, OCRResponse, ValidationResponse, 
    AuthenticityResponse, RiskRequest, RiskResponse, FullVerifyResponse
)
from app.services.image_quality import assess_image_quality
from app.services.document_classifier import classify_document
from app.services.ocr.factory import get_ocr_provider
from app.services.data_validation import validate_extracted_data
from app.services.document_authenticity import assess_authenticity
from app.services.risk_engine import calculate_risk
import json

router = APIRouter(prefix="/api/v1")

@router.post("/document-quality", response_model=QualityResponse)
async def analyze_document_quality(file: UploadFile = File(...)):
    contents = await file.read()
    try:
        result = assess_image_quality(contents)
        return result
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/document-classify", response_model=ClassifyResponse)
async def analyze_document_classification(file: UploadFile = File(...)):
    contents = await file.read()
    return classify_document(contents)

@router.post("/ocr", response_model=OCRResponse)
async def perform_ocr(file: UploadFile = File(...), document_type: str = Form(...)):
    contents = await file.read()
    ocr_provider = get_ocr_provider()
    return ocr_provider.extract_text(contents, document_type)

@router.post("/document-authenticity", response_model=AuthenticityResponse)
async def analyze_document_authenticity(
    file: UploadFile = File(...), 
    ocr_confidence: float = Form(...),
    quality_assessment: str = Form(...) # JSON string
):
    contents = await file.read()
    quality_dict = json.loads(quality_assessment)
    return assess_authenticity(contents, ocr_confidence, quality_dict)

@router.post("/risk", response_model=RiskResponse)
async def evaluate_risk(request: RiskRequest):
    return calculate_risk(
        ocr_confidence=request.ocr_confidence,
        quality_score=request.quality_score,
        authenticity_score=request.authenticity_score,
        is_over_18=request.is_over_18,
        venue_status=request.venue_status
    )

@router.post("/verify", response_model=FullVerifyResponse)
async def full_verify_pipeline(
    file: UploadFile = File(...),
    venue_status: str = Form(...) # JSON string
):
    contents = await file.read()
    venue_dict = json.loads(venue_status)
    
    # 1. Quality
    quality = assess_image_quality(contents)
    if quality["quality_score"] < 50:
        raise HTTPException(status_code=400, detail="Image quality too poor to process")
        
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
        venue_status=venue_dict
    )
    
    return {
        "quality": quality,
        "classification": classification,
        "ocr": ocr_result,
        "validation": validation,
        "authenticity": authenticity,
        "risk": risk
    }
