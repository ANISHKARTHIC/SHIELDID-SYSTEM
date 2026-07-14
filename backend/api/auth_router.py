from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from pydantic import BaseModel
import uuid
import hashlib

from backend.api.deps import get_db
from backend.models.models import User, RoleEnum

router = APIRouter(prefix="/api/v1/auth", tags=["auth"])

class LoginRequest(BaseModel):
    username: str
    password: str

class RegisterRequest(BaseModel):
    username: str
    email: str
    password: str

def hash_password(password: str) -> str:
    return hashlib.sha256(password.encode()).hexdigest()

def create_fake_token() -> str:
    return f"fake-jwt-token-{uuid.uuid4()}"

@router.post("/register")
def register(req: RegisterRequest, db: Session = Depends(get_db)):
    # Check if user exists
    existing = db.query(User).filter(User.email == req.email).first()
    if existing:
        raise HTTPException(status_code=400, detail="Email already registered")
        
    user = User(
        email=req.email,
        hashed_password=hash_password(req.password),
        role=RoleEnum.door_staff
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    
    return {
        "id": user.id,
        "username": req.username,
        "email": user.email,
        "role": user.role.value if hasattr(user.role, 'value') else str(user.role),
        "token": create_fake_token()
    }

@router.post("/login")
def login(req: LoginRequest, db: Session = Depends(get_db)):
    # Support logging in with either username (mapped to email) or email directly
    # since Flutter sends 'username' field for login
    user = db.query(User).filter(User.email == req.username).first()
    
    if not user or user.hashed_password != hash_password(req.password):
        raise HTTPException(status_code=401, detail="Invalid credentials")
        
    # Just derive username from email for response
    username = user.email.split('@')[0]
    
    return {
        "id": user.id,
        "username": username,
        "email": user.email,
        "role": user.role.value if hasattr(user.role, 'value') else str(user.role),
        "token": create_fake_token()
    }
