from pydantic import BaseModel
from typing import Optional, List

class QualityResponse(BaseModel):
    quality_score: int
    blur: bool
    lighting: str
    cropped: bool
    rotation: int

class ClassifyResponse(BaseModel):
    document_type: str
    confidence: float

class OCRResponse(BaseModel):
    name: Optional[str]
    dob: Optional[str]
    address: Optional[str]
    document_number: Optional[str]
    expiry_date: Optional[str]
    issue_date: Optional[str]
    confidence: float
    
    # Template-specific extensions
    document_type: Optional[str] = None
    fields: Optional[dict] = None
    confidences: Optional[dict] = None
    validation: Optional[dict] = None

class ValidationResponse(BaseModel):
    is_valid: bool
    missing_fields: List[str]
    age_verification: dict

class AuthenticityResponse(BaseModel):
    authenticity_score: int
    risk: str
    possible_issues: List[str]

class RiskRequest(BaseModel):
    ocr_confidence: float
    quality_score: float
    authenticity_score: float
    is_over_18: bool
    venue_status: dict

class RiskResponse(BaseModel):
    risk_score: int
    recommendation: str

class FullVerifyRequest(BaseModel):
    venue_status: dict

class FullVerifyResponse(BaseModel):
    quality: QualityResponse
    classification: ClassifyResponse
    ocr: OCRResponse
    validation: ValidationResponse
    authenticity: AuthenticityResponse
    risk: RiskResponse
