from app.db.base import AsyncSessionLocal
from typing import AsyncGenerator

async def get_db() -> AsyncGenerator:
    """
    Dependency to yield an async database session for FastAPI endpoints.
    """
    async with AsyncSessionLocal() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()
