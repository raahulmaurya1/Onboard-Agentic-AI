from ulid import ULID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy import text
from app.db.models.user import UserInitial
from app.db.models.session import OnboardingSession

async def register_user(db: AsyncSession, phone: str, email: str = None, session_ulid: str = None) -> UserInitial:
    """
    Registers a new verified user, optionally reusing an existing session_ulid.
    Returns the user natively if they already successfully exist preventing collisions.
    """
    # Only reuse a row that is still in initial 'draft' state with no account_type assigned.
    # Any row that has progressed (KYC_CONFIRMED, UNDER_REVIEW, FINALIZED, etc.) is a
    # completed or in-progress account and must NOT be overwritten.
    result = await db.execute(
        select(UserInitial).where(
            ((UserInitial.phone == phone) | 
             (UserInitial.email == email)) &
            (UserInitial.status == 'draft') &
            (UserInitial.account_type.is_(None))
        )
    )
    existing_user = result.scalars().first()
    
    # Always generate a fresh ULID for genuinely new accounts
    target_id = existing_user.id if existing_user else str(ULID())
    
    if not existing_user:
        new_user = UserInitial(id=target_id, phone=phone, email=email)
        db.add(new_user)
        await db.flush() # Secure native User record before mapping Crash-proof Session Foreign Keys
        user_obj = new_user
    else:
        user_obj = existing_user

    # Crash-proof Session creation or renewal checking conflict resolution identically
    stmt = insert(OnboardingSession).values(session_id=target_id, user_id=target_id)
    stmt = stmt.on_conflict_do_update(
        index_elements=['session_id'],
        set_=dict(expires_at=text("NOW() + INTERVAL '30 minutes'"))
    )
    await db.execute(stmt)
    await db.commit()
    
    if not existing_user:
        await db.refresh(user_obj)
        
    return user_obj
