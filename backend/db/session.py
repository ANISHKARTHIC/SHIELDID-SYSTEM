from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from backend.core.logger import get_logger
from backend.core.config import settings

logger = get_logger("database")

def get_engine():
    db_uri = settings.SQLALCHEMY_DATABASE_URI
    if "postgresql" in db_uri:
        logger.info(f"Connecting to database at {db_uri.split('@')[-1]}...")
        # No SQLite fallback: Customer.face_embedding is a pgvector column and
        # is fundamentally incompatible with SQLite, so a silent fallback here
        # would corrupt the face-matching feature rather than degrade it.
        engine = create_engine(db_uri, pool_pre_ping=True)
        with engine.connect():
            pass
        logger.info("Successfully connected to PostgreSQL.")
        return engine
    connect_args = {"check_same_thread": False} if "sqlite" in db_uri else {}
    return create_engine(db_uri, connect_args=connect_args)

engine = get_engine()
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

