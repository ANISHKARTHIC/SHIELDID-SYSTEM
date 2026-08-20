"""
Idempotent database seed: creates the default venue and a super_admin
account if they don't already exist. Safe to run on every container start —
existing rows are left untouched.

Credentials come from env vars so the same seed works across environments
without editing code:
    SEED_ADMIN_EMAIL      (default: admin@venuepass.local)
    SEED_ADMIN_PASSWORD   (default: ChangeMe123! — change this in any
                            environment reachable from outside your own
                            machine; it is a known, publicly-documented
                            default, not a secret)

Run directly: python -m backend.seed
"""
import os
import sys

parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)

from backend.db.session import engine, SessionLocal
from backend.db.base import Base
from backend.models.models import Venue, User, RoleEnum
from backend.core.security import get_password_hash
from backend.core.logger import get_logger

logger = get_logger("seed")

DEFAULT_ADMIN_EMAIL = "admin@venuepass.local"
DEFAULT_ADMIN_PASSWORD = "ChangeMe123!"


def seed():
    Base.metadata.create_all(bind=engine)

    admin_email = os.getenv("SEED_ADMIN_EMAIL", DEFAULT_ADMIN_EMAIL)
    admin_password = os.getenv("SEED_ADMIN_PASSWORD", DEFAULT_ADMIN_PASSWORD)

    db = SessionLocal()
    try:
        venue = db.query(Venue).filter(Venue.id == 1).first()
        if not venue:
            venue = Venue(id=1, name="Default Venue", address="123 Main St")
            db.add(venue)
            db.commit()
            db.refresh(venue)
            logger.info("Default Venue (ID=1) seeded.")
        else:
            logger.info("Default Venue (ID=1) already exists, skipping.")

        existing_admin = db.query(User).filter(User.email == admin_email).first()
        if not existing_admin:
            admin = User(
                venue_id=venue.id,
                email=admin_email,
                hashed_password=get_password_hash(admin_password),
                role=RoleEnum.super_admin,
                is_active=True,
            )
            db.add(admin)
            db.commit()
            logger.warning(
                f"Seeded super_admin: {admin_email} / {admin_password} "
                "— log in and change this password immediately, especially "
                "if SEED_ADMIN_PASSWORD was left at its default."
            )
        else:
            logger.info(f"Admin account {admin_email} already exists, skipping.")
    except Exception as e:
        logger.error(f"Error seeding database: {e}")
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    seed()
