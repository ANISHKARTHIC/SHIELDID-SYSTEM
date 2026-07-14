from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime

class UserBase(BaseModel):
    email: str
    role: str

class UserCreate(UserBase):
    password: str

class UserResponse(UserBase):
    id: int
    is_active: bool
    created_at: datetime

    class Config:
        from_attributes = True

class Token(BaseModel):
    access_token: str
    token_type: str

class CustomerResponse(BaseModel):
    id: int
    unique_id: str
    name: str
    dob: datetime
    blacklist_status: str
    membership_status: str = "None"
    visit_count: int = 1
    incidents_count: int = 0
    vip_tier: str = "none"
    manager_notes: Optional[str] = None
    warnings: int = 0

    class Config:
        from_attributes = True

class BlacklistCreate(BaseModel):
    customer_name: str
    reason: str
    manager_notes: Optional[str] = None
    expiry_date: Optional[str] = None # format YYYY-MM-DD

class IncidentCreate(BaseModel):
    customer_id: int
    incident_type: str
    description: str
    staff_notes: Optional[str] = None

class VerificationDecision(BaseModel):
    ocr_name: str
    ocr_dob: str
    ocr_address: str
    doc_number: str
    doc_type: str
    expiry_date: str
    issue_date: str
    ocr_confidence: float
    quality_score: float
    authenticity_score: float
    risk_score: float
    ai_recommendation: str
    staff_decision: str # pass, deny, check
    notes: Optional[str] = None
