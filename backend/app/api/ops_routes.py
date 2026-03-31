from fastapi import APIRouter
from pydantic import BaseModel
import logging

logger = logging.getLogger(__name__)
router = APIRouter()

class EscalationRequest(BaseModel):
    session_id: str
    risk_score: float
    reason: str

@router.post("/v1/ops/notify")
async def notify_bank_staff(request: EscalationRequest):
    """
    Accepts high-risk session IDs and simulates sending a notification to bank staff.
    """
    logger.critical(f"STAFF ESCALATION TRIGGERED for Session {request.session_id}")
    logger.critical(f"Reason: {request.reason} (Risk Score: {request.risk_score})")
    
    return {
        "status": "notified",
        "message": f"Bank staff have been alerted for session {request.session_id}"
    }
