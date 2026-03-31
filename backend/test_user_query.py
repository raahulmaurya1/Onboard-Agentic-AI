import asyncio
from app.db.base import AsyncSessionLocal
from app.db.models.user import UserInitial
from sqlalchemy.future import select

async def check_user():
    ulid_val = "01KMFJPQ82QBE2SDMJNZXS5QY7"
    async with AsyncSessionLocal() as db:
        result = await db.execute(select(UserInitial).where(UserInitial.id == ulid_val))
        user = result.scalar_one_or_none()
        if user:
            print(f"FOUND USER: id={user.id}")
            print(f"phone={user.phone}")
            print(f"email={user.email}")
            print(f"account_type={user.account_type}")
        else:
            print("USER NOT FOUND IN DB!")
            
if __name__ == "__main__":
    asyncio.run(check_user())
