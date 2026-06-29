import os
import sys

# Ensure the parent directory of backend is in the python path
parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from backend.db.session import engine
from backend.db.base import Base
from backend.models import models
from backend.api.v1_router import router as v1_router
from backend.core.logger import get_logger

logger = get_logger("main")

# Auto-create tables on startup (works for SQLite and PostgreSQL)
try:
    Base.metadata.create_all(bind=engine)
    logger.info("Database tables initialized successfully.")
except Exception as e:
    logger.error(f"Error initializing database tables: {e}")

app = FastAPI(
    title="Pub Entry Verification System API",
    description="Backend API for AI-assisted identity verification.",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(v1_router)

from fastapi.responses import JSONResponse
from fastapi.requests import Request

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error(f"Unhandled exception: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={
            "success": False,
            "stage": "BACKEND_API",
            "message": "Internal Server Error in backend orchestration layer",
            "error_code": "INTERNAL_SERVER_ERROR",
            "detail": str(exc)
        },
        headers={
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Methods": "*",
            "Access-Control-Allow-Headers": "*",
        }
    )

@app.get("/")
def read_root():
    return {"message": "Pub Entry Verification System API is running."}
