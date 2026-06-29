from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(
    title="Pub Entry AI Verification Service",
    description="Independent AI Microservice for Document Processing.",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

from fastapi.responses import JSONResponse
from fastapi.requests import Request
import logging

logger = logging.getLogger("ai_main")

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error(f"AI Service error: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={
            "success": False,
            "stage": "AI_INFERENCE_PIPELINE",
            "message": "An error occurred during AI processing pipeline",
            "error_code": "AI_PIPELINE_ERROR",
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
    return {"message": "AI Service is running."}

from app.api.v1_router import router as v1_router

app.include_router(v1_router)
