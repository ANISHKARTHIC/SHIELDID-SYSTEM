import redis
import time
from backend.core.config import settings
from backend.core.logger import get_logger

logger = get_logger("redis")

class InMemoryRedis:
    """Lightweight in-memory Redis fallback for testing or local development without Redis."""
    _store = {}
    _expirations = {}

    def get(self, key: str):
        if key in self._expirations and time.time() > self._expirations[key]:
            self._store.pop(key, None)
            self._expirations.pop(key, None)
            return None
        return self._store.get(key)

    def set(self, key: str, value: str):
        self._store[key] = str(value)
        self._expirations.pop(key, None)
        return True

    def setex(self, key: str, time_seconds: int, value: str):
        self._store[key] = str(value)
        self._expirations[key] = time.time() + time_seconds
        return True

    def delete(self, *keys: str):
        for k in keys:
            self._store.pop(k, None)
            self._expirations.pop(k, None)
        return True

    def ping(self):
        return True

    def publish(self, channel: str, message: str):
        return 1

    def close(self):
        pass

_in_memory_redis = InMemoryRedis()

def get_redis():
    # Determine which client to hand out before yielding, so an exception
    # raised downstream by the route handler (e.g. a validation HTTPException)
    # is thrown back into this generator at most once. A try/except around
    # the yield itself would catch that downstream throw and attempt a
    # second yield, which Python forbids for single-yield generators used as
    # FastAPI dependencies ("generator didn't stop after throw()").
    try:
        client = redis.from_url(settings.REDIS_URL, decode_responses=True)
        client.ping()
    except Exception:
        client = _in_memory_redis

    yield client

    if client is not _in_memory_redis:
        client.close()

