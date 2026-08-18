import os
import sys
from starlette.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

# Add project root to sys.path
root_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if root_dir not in sys.path:
    sys.path.insert(0, root_dir)

from backend.db.base import Base
import backend.models.models as models
import backend.models.analytics_models as analytics_models
from backend.models.models import Venue, User, RoleEnum, VenueConfiguration, PolicySchema
from backend.api.deps import get_db
from backend.core.security import get_password_hash
from backend.main import app

# Test SQLite DB in-memory with StaticPool
TEST_DB_URL = "sqlite:///:memory:"
engine = create_engine(
    TEST_DB_URL, 
    connect_args={"check_same_thread": False},
    poolclass=StaticPool
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()

app.dependency_overrides[get_db] = override_get_db

def init_test_db():
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    db = TestingSessionLocal()
    try:
        # Seed test venue, config, policy and user
        venue = Venue(id=1, name="Test Pub", address="456 Test Lane")
        db.add(venue)
        db.commit()

        config = VenueConfiguration(venue_id=1, verification_mode="manual")
        policy = PolicySchema(venue_id=1, minimum_age=18)
        db.add(config)
        db.add(policy)
        db.commit()

        user = User(
            id=1,
            venue_id=1,
            email="testoperator@pub.com",
            hashed_password=get_password_hash("password"),
            role=RoleEnum.door_staff,
            is_active=True
        )
        db.add(user)

        supervisor = User(
            id=2,
            venue_id=1,
            email="testsupervisor@pub.com",
            hashed_password=get_password_hash("password"),
            role=RoleEnum.manager,
            is_active=True
        )
        db.add(supervisor)

        super_admin = User(
            id=3,
            venue_id=1,
            email="testadmin@pub.com",
            hashed_password=get_password_hash("password"),
            role=RoleEnum.super_admin,
            is_active=True
        )
        db.add(super_admin)

        db.commit()
    finally:
        db.close()

init_test_db()
client = TestClient(app)

def auth_headers(email: str = "testoperator@pub.com", password: str = "password") -> dict:
    """Logs in as a seeded test user and returns an Authorization header dict."""
    res = client.post("/api/v1/auth/login", json={"username": email, "password": password})
    token = res.json()["token"]
    return {"Authorization": f"Bearer {token}"}
