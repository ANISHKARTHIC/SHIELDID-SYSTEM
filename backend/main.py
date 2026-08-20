import os
import sys

# Ensure the parent directory of backend is in the python path
parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)

from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from sqlalchemy import text
from backend.api import deps
from backend.api.v1_router import router as v1_router
from backend.api.auth_router import router as auth_router
from backend.api.users_router import router as users_router
from backend.api.venue_router import router as venue_router
from backend.api.occupancy_router import router as occupancy_router
from backend.api.blacklist_router import router as blacklist_router
from backend.api.replay_router import router as replay_router
from backend.api.supervisor_router import router as supervisor_router
from backend.api.analytics_router import router as analytics_router
from backend.api.export_router import router as export_router
from backend.api.search_router import router as search_router
from backend.core.logger import get_logger

logger = get_logger("main")

# Auto-create tables and seed the default venue/admin on startup (works for
# SQLite and PostgreSQL). Shared with `python -m backend.seed`, which is the
# same logic run standalone — see backend/seed.py for credential env vars.
try:
    from backend.seed import seed
    seed()
except Exception as e:
    logger.error(f"Error initializing/seeding database: {e}")

from contextlib import asynccontextmanager
from backend.services.retention_cron import start_retention_cron
from backend.services.occupancy_cron import start_occupancy_cron

@asynccontextmanager
async def lifespan(app: FastAPI):
    start_retention_cron()
    start_occupancy_cron()
    yield

app = FastAPI(
    title="VenuePass Verification System API",
    description="Backend API for AI-assisted identity verification.",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(v1_router)
app.include_router(auth_router)
app.include_router(users_router)
app.include_router(venue_router)
app.include_router(occupancy_router)
app.include_router(blacklist_router)
app.include_router(replay_router)
app.include_router(supervisor_router)
app.include_router(analytics_router)
app.include_router(export_router)
app.include_router(search_router)

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

@app.get("/health", tags=["monitoring"])
def health_check():
    return {
        "status": "ok", 
        "service": "venuepass-backend",
        "version": "1.0.0"
    }

@app.get("/ready", tags=["monitoring"])
async def readiness_check(db: Session = Depends(deps.get_db)):
    health_status = {"status": "ready", "checks": {}}
    
    # Check Postgres
    try:
        db.execute(text("SELECT 1"))
        health_status["checks"]["database"] = "ok"
    except Exception as e:
        health_status["checks"]["database"] = f"error: {str(e)}"
        health_status["status"] = "not_ready"
        
    # Check Redis
    try:
        from backend.db.redis import get_redis
        redis_client = next(get_redis())
        redis_client.ping()
        health_status["checks"]["redis"] = "ok"
    except Exception as e:
        health_status["checks"]["redis"] = f"error: {str(e)}"
        health_status["status"] = "not_ready"
        
    # Check AI Service
    import httpx
    from backend.core.config import settings
    ai_url = f"{settings.AI_SERVICE_URL}/docs"
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.get(ai_url, timeout=5.0)
            health_status["checks"]["ai_service"] = (
                "ok" if resp.status_code == 200 else f"error: HTTP {resp.status_code} from {ai_url}"
            )
            if resp.status_code != 200:
                health_status["status"] = "not_ready"
    except Exception as e:
        # str(e) is often empty for connection-level failures (e.g.
        # httpx.ConnectTimeout) — include the exception type and the URL
        # actually being probed so this is still actionable, since
        # AI_SERVICE_URL misconfiguration is the most common cause of this
        # check failing (wrong host/port for the deployment topology, or
        # the ai-service process simply isn't up).
        health_status["checks"]["ai_service"] = f"error: {type(e).__name__}: {e} (probing {ai_url})"
        health_status["status"] = "not_ready"
        
    status_code = 200 if health_status["status"] == "ready" else 503
    return JSONResponse(status_code=status_code, content=health_status)

@app.get("/metrics", tags=["monitoring"])
def get_metrics():
    # In a real enterprise app, expose Prometheus format via prometheus_client
    # Here we mock system-level insight metrics.
    import psutil
    return {
        "system": {
            "cpu_percent": psutil.cpu_percent(),
            "memory_percent": psutil.virtual_memory().percent
        },
        "verifications_processed": 0, 
        "active_sessions": 0, 
        "errors": 0
    }

@app.get("/")
def read_root():
    return {"message": "VenuePass Verification System API is running."}
