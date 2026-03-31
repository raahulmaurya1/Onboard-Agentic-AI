from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from app.storage.postgres import get_db
from app.db.models.user import UserInitial
from app.db.models.session import OnboardingSession
from app.services.otp_service import send_phone_otp, verify_phone_otp, send_email_otp, verify_email_otp
from app.agents.entry_agent import register_user
from sqlalchemy.sql import func

router = APIRouter(prefix="/auth", tags=["auth"])

class SendPhoneOTPRequest(BaseModel):
    phone: str

class VerifyPhoneOTPRequest(BaseModel):
    phone: str
    code: str

class SendEmailOTPRequest(BaseModel):
    email: str
    pending_session_id: str

class VerifyEmailOTPRequest(BaseModel):
    email: str
    code: str
    pending_session_id: str

@router.post("/send-phone-otp")
async def send_phone_code(request: SendPhoneOTPRequest, db: AsyncSession = Depends(get_db)):
    """
    Step 1: Dispatches SMS OTP.
    Lookup-First Idempotency: Checks if user exists fully verified safely resuming session.
    """
    result = await db.execute(select(UserInitial).where((UserInitial.phone == request.phone) & (UserInitial.status == 'VERIFIED')))
    existing_user = result.scalars().first()
    
    if existing_user:
        # Check active session
        session_res = await db.execute(select(OnboardingSession).where(
            (OnboardingSession.user_id == existing_user.id) &
            (OnboardingSession.expires_at > func.now())
        ))
        active_session = session_res.scalars().first()
        if active_session:
             return {
                "status": "success",
                "message": "User verified natively. Active Session resumes.",
                "user_id": active_session.session_id,
                "phone": existing_user.phone
             }
             
    await send_phone_otp(request.phone)
    
    masked_phone = request.phone[:-4].replace(request.phone[3:-4], "*" * len(request.phone[3:-4])) + request.phone[-4:]
    return {"status": "success", "message": f"OTP sent to {masked_phone}", "expires_in": 180}

@router.post("/verify-phone-otp")
async def verify_phone_code(request: VerifyPhoneOTPRequest, db: AsyncSession = Depends(get_db)):
    """
    Step 2: Verifies Phone OTP safely mapping the temporary Pending ULID state to Redis natively.
    """
    res = await verify_phone_otp(phone=request.phone, code=request.code)
    pending_session_id = res["pending_session_id"]
    
    return {
        "status": "success",
        "message": "Phone verified. Proceed to email verification.",
        "pending_session_id": pending_session_id
    }

@router.post("/send-email-otp")
async def send_email_code(request: SendEmailOTPRequest, db: AsyncSession = Depends(get_db)):
    """
    Step 3: Dispatches Email OTP strictly verifying the phone was validated beforehand natively.
    """
    await send_email_otp(request.email, request.pending_session_id)
    
    return {"status": "success", "message": f"OTP sent to {request.email}", "expires_in": 180}

@router.post("/verify-email-otp")
async def verify_email_code(request: VerifyEmailOTPRequest, db: AsyncSession = Depends(get_db)):
    """
    Step 4: Central Convergence. Validates dual completion, registers UserInitial, drops pending cache safely.
    """
    result = await verify_email_otp(
        code=request.code,
        pending_session_id=request.pending_session_id
    )
    
    # Validation firmly succeeded. Native Convergence Logic:
    user = await register_user(db, phone=result["phone"], email=result["email"])
    
    # Cleanup Pending Redis Auth sequence
    from app.storage.redis import redis_client
    await redis_client.delete(f"pending_auth:{request.pending_session_id}")
    
    return {
        "status": "success",
        "message": "Dual Verification complete. Database routing hooked.",
        "user_id": user.id, # Needs to grab active session. User is returned by register_user but we really need the session ULID. register_user handles auth session generation inside it natively.
        "phone": user.phone,
        "email": user.email
    }
