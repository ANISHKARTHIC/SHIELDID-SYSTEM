import os
from celery import Celery
from celery.schedules import crontab

redis_host = os.getenv("REDIS_HOST", "localhost")
redis_port = os.getenv("REDIS_PORT", "6379")
redis_url = f"redis://{redis_host}:{redis_port}/1"

celery_app = Celery(
    "pub_entry_tasks",
    broker=redis_url,
    backend=redis_url,
    include=["backend.tasks.retention_tasks"]
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
)

# Setup Celery Beat schedule for data retention
celery_app.conf.beat_schedule = {
    "daily-retention-cleanup": {
        "task": "backend.tasks.retention_tasks.cleanup_expired_records",
        "schedule": crontab(hour=3, minute=0), # Run every day at 3 AM UTC
    },
}
