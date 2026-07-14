import json
import logging
from backend.db.redis import get_redis

logger = logging.getLogger("event_bus")

class EventBus:
    def __init__(self):
        # In a real app we'd inject this, but for simplicity we instantiate a client here
        # or depend on the fast API dependency. Since this might be called globally,
        # we will use the connection pool from redis dependency.
        from redis import Redis
        import os
        redis_host = os.getenv("REDIS_HOST", "localhost")
        redis_port = int(os.getenv("REDIS_PORT", 6379))
        self.redis_client = Redis(host=redis_host, port=redis_port, db=0, decode_responses=True)

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
