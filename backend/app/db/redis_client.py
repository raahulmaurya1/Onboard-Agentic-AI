import redis
import json
import os

REDIS_HOST = os.getenv("REDIS_HOST", "localhost")
REDIS_PORT = int(os.getenv("REDIS_PORT", 6379))
REDIS_DB = int(os.getenv("REDIS_DB", 0))

# Initialize synchronous Redis client for basic schema operations
redis_client = redis.Redis(host=REDIS_HOST, port=REDIS_PORT, db=REDIS_DB, decode_responses=True)

def save_temp_extraction(session_id: str, data: dict, expire_seconds: int = 3600):
    """Saves the unverified extraction struct and file MinIO paths for 1 hour."""
    redis_client.setex(f"extractor:{session_id}", expire_seconds, json.dumps(data))

def get_temp_extraction(session_id: str) -> dict:
    """Retrieves the pending extraction data waiting for human approval."""
    data = redis_client.get(f"extractor:{session_id}")
    if data:
        return json.loads(data)
    return None

def clear_temp_extraction(session_id: str):
    """Purges the cached extraction metadata post-confirmation."""
    redis_client.delete(f"extractor:{session_id}")
