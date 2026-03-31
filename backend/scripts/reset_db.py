import asyncio
import sys
import os

# Add the parent directory to sys.path to ensure imports work
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from sqlalchemy import text
from app.db.base import engine, Base

# Import all models to register them with Base.metadata
from app.db.models.user import UserInitial, AdditionalInfo
from app.db.models.document import UserDocument
from app.db.models.agent import AgentContext
from app.db.models.session import OnboardingSession

async def reset_db():
    print("Connecting to the database...")
    async with engine.begin() as conn:
        # Check if vector extension exists and create it if not (required for AgentContext)
        print("Ensuring pgvector extension exists...")
        await conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector;"))

        print("Dropping all existing tables...")
        await conn.run_sync(Base.metadata.drop_all)
        
        print("Creating all tables...")
        await conn.run_sync(Base.metadata.create_all)
        
        print("Database reset complete.")

if __name__ == "__main__":
    try:
        asyncio.run(reset_db())
    except Exception as e:
        print(f"Error during database reset: {e}")
        sys.exit(1)
