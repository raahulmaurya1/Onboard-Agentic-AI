import asyncio
from app.db.base import AsyncSessionLocal
from sqlalchemy.future import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy import text
from app.db.models.user import UserInitial
from app.db.models.session import OnboardingSession

async def test_db():
    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(UserInitial).where(
                (UserInitial.phone == '+917991881238') & 
                (UserInitial.email == 'rm6028365@gmail.com')
            )
        )
        existing_user = result.scalars().first()
        print('User found:', existing_user)

        try:
            stmt = insert(OnboardingSession).values(session_id=existing_user.id, user_id=existing_user.id)
            stmt = stmt.on_conflict_do_update(
                index_elements=['session_id'],
                set_=dict(expires_at=text("NOW() + INTERVAL '30 minutes'"))
            )
            await db.execute(stmt)
            await db.commit()
            print('UPSERT successful')
        except Exception as e:
            print('500 ERROR:', repr(e))

asyncio.run(test_db())
