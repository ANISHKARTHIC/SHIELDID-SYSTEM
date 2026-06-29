from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from backend.core.logger import get_logger

logger = get_logger("database")

# Use SQLite exclusively to ensure 100% out-of-the-box local execution
logger.info("Initializing SQLite database pub_entry.db.")
engine = create_engine("sqlite:///./pub_entry.db", connect_args={"check_same_thread": False})

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
