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

class VenueCreateRequest(BaseModel):
    name: str
    address: str
    max_capacity: Optional[int] = None

class VenueUpdateRequest(BaseModel):
    name: Optional[str] = None
    address: Optional[str] = None
    max_capacity: Optional[int] = None

class VenueResponse(BaseModel):
    id: int
    name: str
    address: str
    is_active: bool
    max_capacity: Optional[int] = None
    created_at: datetime

    class Config:
        from_attributes = True

class BlacklistCreate(BaseModel):
    customer_name: str
    reason: str
    manager_notes: Optional[str] = None
    expiry_date: Optional[str] = None # format YYYY-MM-DD

class BlacklistCreateByCustomerId(BaseModel):
    customer_id: int
    reason: str
    manager_notes: Optional[str] = None
    expiry_date: Optional[str] = None # format YYYY-MM-DD

class IncidentCreate(BaseModel):
    customer_id: int
    incident_type: str
    description: str
    staff_notes: Optional[str] = None

class VerificationDecision(BaseModel):
    # OCR/quality/risk fields are intentionally NOT accepted here: the
    # customer record and decision context are derived server-side from the
    # session data already captured during /classify, /ocr, and /face, never
    # trusted from the client at finalize time.
    staff_decision: str # pass, deny, check, block
    notes: Optional[str] = None
