from sqlalchemy import create_engine, event
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

        # Every DateTime column in this codebase is naive (no timezone=True)
        # and every write uses datetime.now(timezone.utc) — the app-wide
        # assumption is "naive columns store UTC". Postgres/psycopg2 convert
        # an aware datetime to the SESSION's timezone before dropping the
        # tzinfo on insert, so a role/server default other than UTC (e.g.
        # Asia/Kolkata) silently corrupts every stored timestamp by that
        # offset. Pin every connection's session timezone to UTC so the
        # naive-column round-trip actually matches what the app assumes.
        @event.listens_for(engine, "connect")
        def _set_utc_timezone(dbapi_connection, connection_record):
            cursor = dbapi_connection.cursor()
            cursor.execute("SET TIME ZONE 'UTC'")
            cursor.close()
            # psycopg2 connections default to autocommit=False, so without an
            # explicit commit here SQLAlchemy's own connection setup rolls
            # this back before the session is ever used.
            dbapi_connection.commit()

        with engine.connect():
            pass
        logger.info("Successfully connected to PostgreSQL.")
        return engine
    connect_args = {"check_same_thread": False} if "sqlite" in db_uri else {}
    return create_engine(db_uri, connect_args=connect_args)

engine = get_engine()
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

