import json
import logging
from backend.db.redis import get_redis

logger = logging.getLogger("event_bus")

from backend.core.config import settings

class EventBus:
    def __init__(self):
        self._client = None

    @property
    def redis_client(self):
        if self._client is None:
            from redis import Redis
            import os
            url = os.getenv("REDIS_URL") or settings.REDIS_URL
            if os.getenv("POSTGRES_SERVER") == "db" and "localhost" in url:
                url = url.replace("localhost", "redis")
            self._client = Redis.from_url(url, decode_responses=True)
        return self._client

    def publish(self, channel: str, event_type: str, payload: dict):
        """
        Publishes an event to a Redis channel.
        Format: {"type": event_type, "data": payload}
        """
        message = {
            "type": event_type,
            "data": payload
        }
        try:
            self.redis_client.publish(channel, json.dumps(message))
            logger.info(f"Published event '{event_type}' to channel '{channel}'")
        except Exception as e:
            logger.error(f"Failed to publish event '{event_type}' to '{channel}': {e}")

event_bus = EventBus()

# Predefined Channels
CH_VERIFICATIONS = "verifications"
CH_ANALYTICS = "analytics"
CH_SECURITY = "security"

# Predefined Event Types
EV_SESSION_STARTED = "SESSION_STARTED"
EV_DOCUMENT_CLASSIFIED = "DOCUMENT_CLASSIFIED"
EV_OCR_COMPLETED = "OCR_COMPLETED"
EV_FACE_VERIFIED = "FACE_VERIFIED"
EV_DECISION_MADE = "DECISION_MADE"
EV_FRAUD_ESCALATED = "FRAUD_ESCALATED"
