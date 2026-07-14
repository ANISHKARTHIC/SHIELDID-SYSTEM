from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from backend.core.logger import get_logger

logger = get_logger("database")

# Use PostgreSQL for vector storage and production readiness
logger.info("Initializing PostgreSQL database pub_entry_db on port 5433.")
engine = create_engine("postgresql+psycopg2://admin:adminpassword@localhost:5433/pub_entry_db")

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
