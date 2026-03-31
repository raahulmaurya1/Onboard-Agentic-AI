import asyncio
import sys
import os

# Add the parent directory to sys.path to ensure imports work
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from sqlalchemy import text
from app.db.base import engine

async def verify_db():
    print("Verifying database tables...")
    async with engine.connect() as conn:
        result = await conn.execute(text("""
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema = 'public'
        """))
        tables = [row[0] for row in result.fetchall()]
        print(f"Tables found: {', '.join(tables)}")
        
        expected_tables = {'user_initial', 'additional_info', 'user_documents', 'agent_context', 'sessions'}
        missing = expected_tables - set(tables)
        
        if not missing:
            print("All expected tables are present.")
        else:
            print(f"Missing tables: {', '.join(missing)}")

if __name__ == "__main__":
    asyncio.run(verify_db())
