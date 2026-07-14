import redis
from backend.core.config import settings

def get_redis():
    client = redis.from_url(settings.REDIS_URL, decode_responses=True)
    try:
        yield client
    finally:
        client.close()
