import redis.asyncio as redis
from typing import AsyncGenerator
from app.config import settings

# Create a global Redis connection pool
redis_client = redis.from_url(settings.REDIS_URL, decode_responses=True)

async def get_redis() -> AsyncGenerator[redis.Redis, None]:
    """
    Dependency to yield the Redis client for FastAPI routes or services.
    """
    try:
        yield redis_client
    finally:
        pass # The global pool manages connections automatically
