from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey, Enum, Float, Text, JSON, Index
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
    pass_decision = "pass"
    deny_decision = "deny"
    check_decision = "check"

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
    is_active = Column(Boolean, default=True, nullable=False)
    max_capacity = Column(Integer, nullable=True)  # None = uncapped
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    
    users = relationship("User", back_populates="venue")
    incidents = relationship("Incident", back_populates="venue")
    configuration = relationship("VenueConfiguration", back_populates="venue", uselist=False)
    policy = relationship("PolicySchema", back_populates="venue", uselist=False)

class VenueConfiguration(Base):
    __tablename__ = "venue_configurations"
    id = Column(Integer, primary_key=True, index=True)
    venue_id = Column(Integer, ForeignKey("venues.id"), unique=True)
    allowed_documents = Column(JSON, default=["uk_driving_licence", "passport"])
    retention_days_success = Column(Integer, default=7)
    retention_days_manual = Column(Integer, default=30)
    retention_days_incident = Column(Integer, default=365)
    verification_mode = Column(String, default="manual") # manual, ai_assisted
    theme_config = Column(JSON, nullable=True)
    occupancy_auto_expire_hours = Column(Integer, default=6)
    
    venue = relationship("Venue", back_populates="configuration")

class PolicySchema(Base):
    __tablename__ = "policy_schemas"
    id = Column(Integer, primary_key=True, index=True)
    venue_id = Column(Integer, ForeignKey("venues.id"), unique=True)
    minimum_age = Column(Integer, default=18)
    # Defaults True: a freshly provisioned venue whose policy row is
    # auto-created (venue_service.get_venue_policy) must not silently skip
    # face-match enforcement in the decision logic in v1_router.face_match —
    # that would let a session PASS on OCR/age/blacklist alone with no
    # check that the captured face matches the ID photo.
    require_face_match = Column(Boolean, default=True)
    face_similarity_threshold = Column(Float, default=0.75)
    ocr_confidence_threshold = Column(Float, default=0.85)
    quality_threshold = Column(Float, default=0.7)
    blacklist_policy = Column(String, default="strict") # strict, warning
    
    venue = relationship("Venue", back_populates="policy")

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
    sessions = relationship("VerificationSession", back_populates="operator")

from pgvector.sqlalchemy import Vector

class Customer(Base):
    __tablename__ = "customers"
    id = Column(Integer, primary_key=True, index=True)
    unique_id = Column(String, unique=True, index=True)
    name = Column(String)
    dob = Column(DateTime)
    face_embedding = Column(Vector(512), nullable=True) # Storing 512D pgvector
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    expires_at = Column(DateTime, nullable=True) # For GDPR retention policy
    is_anonymized = Column(Boolean, default=False, nullable=False) # Set by the retention job once PII has been scrubbed
    notes = Column(Text, nullable=True)
    vip_tier = Column(String, default="none")
    manager_notes = Column(Text, nullable=True)
    warnings = Column(Integer, default=0)
    
    documents = relationship("Document", back_populates="customer")
    blacklist = relationship("Blacklist", back_populates="customer")
    incidents = relationship("Incident", back_populates="customer")
    membership = relationship("Membership", back_populates="customer")
    sessions = relationship("VerificationSession", back_populates="customer")

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


class SessionStateEnum(str, enum.Enum):
    CREATED = "CREATED"
    WAITING_FOR_DOCUMENT = "WAITING_FOR_DOCUMENT"
    DOCUMENT_CLASSIFIED = "DOCUMENT_CLASSIFIED"
    DOCUMENT_VALIDATED = "DOCUMENT_VALIDATED"
    OCR_COMPLETED = "OCR_COMPLETED"
    AGE_VERIFIED = "AGE_VERIFIED"
    FACE_CAPTURED = "FACE_CAPTURED"
    FACE_VERIFIED = "FACE_VERIFIED"
    DATABASE_CHECKED = "DATABASE_CHECKED"
    RISK_EVALUATED = "RISK_EVALUATED"
    APPROVED = "APPROVED"
    MANUAL_REVIEW = "MANUAL_REVIEW"
    FRAUD_REVIEW = "FRAUD_REVIEW"
    DENIED = "DENIED"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"

class VerificationSession(Base):
    __tablename__ = "verification_sessions"
    id = Column(String, primary_key=True, index=True) # UUID string
    venue_id = Column(Integer, ForeignKey("venues.id"))
    operator_id = Column(Integer, ForeignKey("users.id"))
    customer_id = Column(Integer, ForeignKey("customers.id"), nullable=True)
    state = Column(Enum(SessionStateEnum), default=SessionStateEnum.CREATED)
    
    id_image_path = Column(String, nullable=True)
    face_image_path = Column(String, nullable=True)
    id_image_checksum = Column(String, nullable=True)
    face_image_checksum = Column(String, nullable=True)
    
    ocr_data = Column(JSON, nullable=True)
    quality_scores = Column(JSON, nullable=True)
    face_similarity = Column(Float, nullable=True)
    risk_score = Column(Float, nullable=True)
    explainability_report = Column(JSON, nullable=True)
    final_decision = Column(String, nullable=True)
    
    is_locked = Column(Boolean, default=False) # Immutable verification package flag
    
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
    
    customer = relationship("Customer", back_populates="sessions")
    operator = relationship("User", back_populates="sessions")
    notes = relationship("SupervisorNote", back_populates="session", cascade="all, delete")

class OccupancyStatusEnum(str, enum.Enum):
    INSIDE = "INSIDE"
    CHECKED_OUT = "CHECKED_OUT"     # manual checkout by staff
    AUTO_EXPIRED = "AUTO_EXPIRED"   # auto-expire job closed it

class Occupancy(Base):
    """
    Tracks who is currently inside a venue. Deliberately a separate table
    from VerificationSession, which becomes immutable (is_locked=True) once
    it reaches a terminal state — occupancy needs to keep changing (checkout,
    auto-expire) long after the entry session is locked.
    """
    __tablename__ = "occupancy_records"
    id = Column(Integer, primary_key=True, index=True)
    venue_id = Column(Integer, ForeignKey("venues.id"), index=True)
    customer_id = Column(Integer, ForeignKey("customers.id"), index=True)
    session_id = Column(String, ForeignKey("verification_sessions.id"), nullable=True)
    entered_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    exited_at = Column(DateTime, nullable=True)  # NULL = currently inside
    status = Column(Enum(OccupancyStatusEnum), default=OccupancyStatusEnum.INSIDE)
    checked_out_by_id = Column(Integer, ForeignKey("users.id"), nullable=True)

    venue = relationship("Venue")
    customer = relationship("Customer")
    session = relationship("VerificationSession")
    checked_out_by = relationship("User")

Index('ix_occupancy_venue_open', Occupancy.venue_id, Occupancy.exited_at)

# Partial unique index: a customer can only have one OPEN (exited_at IS
# NULL) occupancy row per venue at a time. Without this, two concurrent
# finalize_session calls for the same customer at the same venue (e.g. a
# duplicate submit, or two operator devices scanning the same person in
# quick succession) can each independently pass the "not already inside"
# check-less insert and create two simultaneous open rows — inflating the
# live occupancy count, and a single checkout only closes one of the two
# (occupancy_service.check_out_by_customer uses .first()), permanently
# leaking a phantom occupant. A customer being inside two *different*
# venues at once is legitimate and must remain allowed, so this is scoped
# per (venue_id, customer_id), not per customer_id alone.
Index(
    'uq_occupancy_open_per_venue_customer',
    Occupancy.venue_id,
    Occupancy.customer_id,
    unique=True,
    postgresql_where=(Occupancy.exited_at.is_(None)),
)

class SupervisorNote(Base):
    __tablename__ = "supervisor_notes"
    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(String, ForeignKey("verification_sessions.id"))
    supervisor_id = Column(Integer, ForeignKey("users.id"))
    note_text = Column(String)
    evidence_path = Column(String, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    
    session = relationship("VerificationSession", back_populates="notes")
    supervisor = relationship("User")

class SessionAuditLog(Base):
    __tablename__ = "session_audit_logs"
    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(String, ForeignKey("verification_sessions.id"))
    operator_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    state_from = Column(String, nullable=True)
    state_to = Column(String)
    duration_ms = Column(Integer, nullable=True)
    device_info = Column(String, nullable=True)
    timestamp = Column(DateTime, default=lambda: datetime.now(timezone.utc))

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

class Notification(Base):
    __tablename__ = "notifications"
    id = Column(Integer, primary_key=True, index=True)
    venue_id = Column(Integer, ForeignKey("venues.id"))
    message = Column(String)
    type = Column(String) # ALERT, INFO, SUCCESS
    is_read = Column(Boolean, default=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    
    venue = relationship("Venue")
