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
    try:
        client = redis.from_url(settings.REDIS_URL, decode_responses=True)
        client.ping()
        yield client
        client.close()
    except Exception:
        yield _in_memory_redis

