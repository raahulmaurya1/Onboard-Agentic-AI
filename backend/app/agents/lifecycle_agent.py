"""
lifecycle_agent.py — Strategy Pattern for Re-KYC and Account Reactivation flows.

These flows reuse the existing 7-step pipeline. The LifecycleOrchestrator is
responsible for:
1. Looking up an existing account by ID (no new ULIDs are created).
2. Force-resetting the internal flow state to the start of the pipeline,
   ignoring the DB `status` field (preventing the "already completed" skip-bug).
3. Persisting updates via SQL UPDATE only (never INSERT), with strict null-filtering
   to ensure unrelated columns are never overwritten.
"""
import logging
from datetime import datetime, timedelta
from typing import Optional, Dict, Any

from sqlalchemy import update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.db.models.user import UserInitial, AdditionalInfo
from app.storage.redis import redis_client

logger = logging.getLogger(__name__)

# Redis key TTL for lifecycle flow flags (4 hours)
LIFECYCLE_FLAG_TTL = 14400

# ── Masking Helpers ───────────────────────────────────────────────────────────

def mask_phone(phone: str) -> str:
    """Returns a masked phone string, e.g. '********6789'."""
    if not phone or len(phone) < 4:
        return "****"
    return "*" * (len(phone) - 4) + phone[-4:]


def mask_email(email: str) -> str:
    """Returns a masked email string, e.g. 'te***@gmail.com'."""
    if not email or "@" not in email:
        return "***@***.com"
    local, domain = email.split("@", 1)
    masked_local = local[:2] + "*" * (len(local) - 2) if len(local) > 2 else "***"
    return f"{masked_local}@{domain}"


# ── LifecycleOrchestrator Strategy Class ─────────────────────────────────────

class LifecycleOrchestrator:
    """
    Strategy handler for Re-KYC and Account Reactivation flows.

    Usage:
        orchestrator = LifecycleOrchestrator(intent="re_kyc")
        user = await orchestrator.lookup_account(account_id, db)
        action = orchestrator.get_initial_action(user)
    """

    SUPPORTED_INTENTS = {"re_kyc", "reactivation"}

    def __init__(self, intent: str):
        if intent not in self.SUPPORTED_INTENTS:
            raise ValueError(f"LifecycleOrchestrator only supports: {self.SUPPORTED_INTENTS}")
        self.intent = intent
        logger.info(f"[Lifecycle] Initialized LifecycleOrchestrator for intent='{intent}'")

    # ── Task 1: Account Lookup ────────────────────────────────────────────────

    async def lookup_account(self, account_id: str, db: AsyncSession) -> Optional[UserInitial]:
        """
        Queries user_initial by the provided account_id (primary key = ULID).
        Returns the UserInitial object if found, or None.
        """
        logger.info(f"[Lifecycle] Looking up account: {account_id}")
        result = await db.execute(
            select(UserInitial).where(UserInitial.id == account_id)
        )
        user = result.scalar_one_or_none()
        if user:
            logger.info(f"[Lifecycle] Account found: {account_id} | status={user.status}")
        else:
            logger.warning(f"[Lifecycle] Account not found: {account_id}")
        return user

    # ── Task 1 + 6: Get Initial Action (Always Reset to Step 1) ──────────────

    def get_initial_action(self, user: UserInitial) -> dict:
        """
        Regardless of the DB `status` (even 'COMPLETED'), always starts the
        flow at phone OTP. (Final Refinement for Frontend Timer & Schema).
        """
        masked = mask_phone(user.phone)
        label = "Re-KYC verification" if self.intent == "re_kyc" else "Account Reactivation"
        
        return {
            "ui_action": "RENDER_PHONE_AUTH",
            "session_ulid": user.id,
            "data_required": ["otp"], # Task 2: Verification Mode only
            "agent_message": (
                f"Welcome back! We found your account. To begin {label}, "
                f"we've sent an OTP to your registered number ending in {user.phone[-4:]} "
                f"({masked}). Please enter the code to continue."
            ),
            "extracted_data": {
                "contact": user.phone,          # Task 1 & 3: Full phone
                "masked_contact": masked,       # Task 1: e.g., *********1238
                "otp_expiry": 120,              # Task 1: Fixes 00:00 timer (Integer)
                "is_otp_sent": True,            # Task 1: Enables Verify button
                "otp_status": "sent",           # Task 1: Status string
                "lifecycle_intent": self.intent,
                "account_type": user.account_type
            },
            "current_state": {
                "phone": user.phone,
                "email": user.email,
                "contact": user.phone,          # Task 3: State Sync
                "isAuthenticated": True
            }
        }

    def get_not_found_response(self, account_id: str) -> dict:
        """Returns a standardised 'Record Not Found' error response."""
        return {
            "ui_action": "RENDER_CHAT",
            "session_ulid": account_id,
            "data_required": [],
            "agent_message": (
                f"We could not find any account associated with the ID '{account_id}'. "
                "Please double-check your account number and try again, or contact customer support."
            )
        }

    # ── Task 4: Update-Only Persistence (Data Guard) ─────────────────────────

    @staticmethod
    async def upsert_user_data(session_ulid: str, update_fields: Dict[str, Any], db: AsyncSession) -> bool:
        """
        Performs a SQL UPDATE on user_initial using update().where().
        NEVER inserts a new row.
        
        Data Guard: Filters out None values so unrelated columns are never
        overwritten with null. Only provided, non-null fields are updated.
        
        Uses SQLAlchemy's explicit update().where() pattern (per user's tip)
        to avoid accidental primary key conflicts with session.merge().
        """
        # Filter None values — critical data guard
        safe_fields = {k: v for k, v in update_fields.items() if v is not None}

        if not safe_fields:
            logger.info(f"[Lifecycle][Upsert] No non-null fields to update for {session_ulid}. Skipping.")
            return True

        logger.info(f"[Lifecycle][Upsert] Updating {session_ulid} with fields: {list(safe_fields.keys())}")

        stmt = (
            update(UserInitial)
            .where(UserInitial.id == session_ulid)
            .values(**safe_fields)
        )
        result = await db.execute(stmt)
        await db.commit()

        rows_affected = result.rowcount
        if rows_affected == 0:
            logger.error(f"[Lifecycle][Upsert] 0 rows updated for {session_ulid}. Account may not exist.")
            return False

        logger.info(f"[Lifecycle][Upsert] Successfully updated {rows_affected} row(s) for {session_ulid}.")
        return True

    @staticmethod
    async def upsert_additional_info(session_ulid: str, info_data: Dict[str, Any], db: AsyncSession) -> bool:
        """
        UPSERTs the AdditionalInfo record for a lifecycle session.
        If the record exists, merges new data into the existing JSON blob.
        If not, creates a new one (e.g., first time capturing business details).
        """
        result = await db.execute(
            select(AdditionalInfo).where(AdditionalInfo.session_ulid == session_ulid)
        )
        existing = result.scalar_one_or_none()

        if existing:
            # Merge new fields into existing data (non-destructive)
            merged = {**existing.data, **{k: v for k, v in info_data.items() if v is not None}}
            stmt = (
                update(AdditionalInfo)
                .where(AdditionalInfo.session_ulid == session_ulid)
                .values(data=merged)
            )
            await db.execute(stmt)
        else:
            new_info = AdditionalInfo(session_ulid=session_ulid, data=info_data)
            db.add(new_info)

        await db.commit()
        return True

    # ── Redis Lifecycle Flag Helpers ──────────────────────────────────────────

    @staticmethod
    async def set_lifecycle_flag(session_ulid: str, intent: str):
        """Sets a Redis flag to mark a session as a lifecycle flow."""
        key = f"lifecycle_flow:{session_ulid}"
        await redis_client.setex(key, LIFECYCLE_FLAG_TTL, intent)
        logger.info(f"[Lifecycle] Flag set: {key} = {intent}")

    @staticmethod
    async def get_lifecycle_flag(session_ulid: str) -> Optional[str]:
        """Returns the lifecycle intent if this session is a lifecycle flow, else None."""
        key = f"lifecycle_flow:{session_ulid}"
        val = await redis_client.get(key)
        if val:
            return val.decode("utf-8") if isinstance(val, bytes) else val
        return None

    @staticmethod
    async def clear_lifecycle_flag(session_ulid: str):
        """Clears the lifecycle flow flag after completion."""
        await redis_client.delete(f"lifecycle_flow:{session_ulid}")
        logger.info(f"[Lifecycle] Flag cleared for {session_ulid}")
