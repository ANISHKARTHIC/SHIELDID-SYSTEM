from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey, Enum, Float, Text, JSON
from sqlalchemy.orm import relationship
import enum
from datetime import datetime, timezone
from backend.db.base import Base

class RoleEnum(str, enum.Enum):
    super_admin = "super_admin"
    venue_admin = "venue_admin"
    manager = "manager"
    door_staff = "door_staff"
    viewer = "viewer"

class DecisionEnum(str, enum.Enum):
    approve = "approve"
    reject = "reject"
    manual_escalation = "manual_escalation"

class IncidentTypeEnum(str, enum.Enum):
    violence = "violence"
    fake_id = "fake_id"
    property_damage = "property_damage"
    drug_related = "drug_related"
    other = "other"

class Venue(Base):
    __tablename__ = "venues"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True)
    address = Column(String)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    
    users = relationship("User", back_populates="venue")
    incidents = relationship("Incident", back_populates="venue")

class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    venue_id = Column(Integer, ForeignKey("venues.id"), nullable=True)
    email = Column(String, unique=True, index=True)
    hashed_password = Column(String)
    role = Column(Enum(RoleEnum), default=RoleEnum.door_staff)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    
    venue = relationship("Venue", back_populates="users")
    logs = relationship("VerificationLog", back_populates="staff_member")

class Customer(Base):
    __tablename__ = "customers"
    id = Column(Integer, primary_key=True, index=True)
    unique_id = Column(String, unique=True, index=True)
    name = Column(String)
    dob = Column(DateTime)
    face_embedding = Column(JSON, nullable=True) # Storing array of floats
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    notes = Column(Text, nullable=True)
    
    documents = relationship("Document", back_populates="customer")
    logs = relationship("VerificationLog", back_populates="customer")
    blacklist = relationship("Blacklist", back_populates="customer")
    incidents = relationship("Incident", back_populates="customer")
    membership = relationship("Membership", back_populates="customer")

class Document(Base):
    __tablename__ = "documents"
    id = Column(Integer, primary_key=True, index=True)
    customer_id = Column(Integer, ForeignKey("customers.id"))
    doc_type = Column(String) # e.g., "driving_licence", "passport"
    doc_number = Column(String, index=True)
    expiry_date = Column(DateTime, nullable=True)
    issue_date = Column(DateTime, nullable=True)
    nationality = Column(String, nullable=True)
    extracted_data = Column(JSON) # Raw OCR data
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    
    customer = relationship("Customer", back_populates="documents")

class VerificationLog(Base):
    __tablename__ = "verification_logs"
    id = Column(Integer, primary_key=True, index=True)
    customer_id = Column(Integer, ForeignKey("customers.id"))
    staff_id = Column(Integer, ForeignKey("users.id"))
    ai_recommendation = Column(String) # e.g., Low Risk, Medium Risk, High Risk
    ai_authenticity_score = Column(Float)
    ai_quality_score = Column(Float)
    ai_ocr_confidence = Column(Float)
    staff_decision = Column(Enum(DecisionEnum))
    notes = Column(Text, nullable=True)
    timestamp = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    
    customer = relationship("Customer", back_populates="logs")
    staff_member = relationship("User", back_populates="logs")

class Blacklist(Base):
    __tablename__ = "blacklists"
    id = Column(Integer, primary_key=True, index=True)
    customer_id = Column(Integer, ForeignKey("customers.id"))
    reason = Column(String)
    manager_notes = Column(Text, nullable=True)
    banned_by_id = Column(Integer, ForeignKey("users.id"))
    expiry_date = Column(DateTime, nullable=True) # Null = permanent
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    
    customer = relationship("Customer", back_populates="blacklist")

class Incident(Base):
    __tablename__ = "incidents"
    id = Column(Integer, primary_key=True, index=True)
    customer_id = Column(Integer, ForeignKey("customers.id"))
    venue_id = Column(Integer, ForeignKey("venues.id"))
    incident_type = Column(Enum(IncidentTypeEnum))
    description = Column(Text)
    staff_notes = Column(Text, nullable=True)
    reported_by_id = Column(Integer, ForeignKey("users.id"))
    date = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    
    customer = relationship("Customer", back_populates="incidents")
    venue = relationship("Venue", back_populates="incidents")

class Membership(Base):
    __tablename__ = "memberships"
    id = Column(Integer, primary_key=True, index=True)
    customer_id = Column(Integer, ForeignKey("customers.id"))
    tier = Column(String) # e.g., VIP, Regular, Guest List, Staff
    valid_until = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    
    customer = relationship("Customer", back_populates="membership")

class AuditLog(Base):
    __tablename__ = "audit_logs"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    action = Column(String)
    details = Column(JSON)
    timestamp = Column(DateTime, default=lambda: datetime.now(timezone.utc))

class Session(Base):
    __tablename__ = "sessions"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    refresh_token = Column(String, index=True)
    expires_at = Column(DateTime)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
