from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel

from backend.api.deps import get_db
from backend.core.security import get_password_hash, verify_password, create_access_token
from backend.models.models import User, RoleEnum

router = APIRouter(prefix="/api/v1/auth", tags=["auth"])

class LoginRequest(BaseModel):
    username: str
    password: str

class RegisterRequest(BaseModel):
    username: str
    email: str
    password: str

def _user_response(user: User) -> dict:
    return {
        "id": user.id,
        "username": user.email.split("@")[0],
        "email": user.email,
        "role": user.role.value if hasattr(user.role, "value") else str(user.role),
        "venue_id": user.venue_id,
        "token": create_access_token(subject=user.id),
    }

@router.post("/register")
def register(req: RegisterRequest, db: Session = Depends(get_db)):
    existing = db.query(User).filter(User.email == req.email).first()
    if existing:
        raise HTTPException(status_code=400, detail="Email already registered")

    user = User(
        venue_id=1,  # single-venue dev default until venue selection exists
        email=req.email,
        hashed_password=get_password_hash(req.password),
        role=RoleEnum.door_staff,
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    return _user_response(user)

@router.post("/login")
def login(req: LoginRequest, db: Session = Depends(get_db)):
    # Flutter sends the identifier as 'username'; we authenticate by email.
    user = db.query(User).filter(User.email == req.username).first()

    if not user or not verify_password(req.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    if not user.is_active:
        raise HTTPException(status_code=400, detail="Inactive user")

    return _user_response(user)
