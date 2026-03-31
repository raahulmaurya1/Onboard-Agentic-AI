from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from pydantic import BaseModel
from typing import Dict, Any

from app.storage.postgres import get_db
from app.db.models.document import UserDocument
from app.db.models.user import UserInitial
from app.agents.validation_agent import revalidate_corrections
from app.db.redis_client import get_temp_extraction

router = APIRouter()
security = HTTPBearer()

class CorrectionRequest(BaseModel):
    corrections: Dict[str, Any]

@router.get("/v1/orchestrator/review/{session_ulid}")
async def check_extraction_status(session_ulid: str, db: AsyncSession = Depends(get_db)):
    """
    Polling endpoint for the React frontend to check if Celery has finished document extraction.
    Returns:
      - 200 {ui_action: RENDER_DATA_REVIEW, extracted_data: {validation: {combined_data: {...}}}}
        when Celery has saved the data to Redis.
      - 200 {ui_action: RENDER_KYC_UPLOAD} if Celery saved an extraction error.
      - 200 {ui_action: RENDER_PROCESSING} if not yet saved (frontend can keep polling).
    """
    print(f"[OnboardAI][POLL] Polling extraction status for session: {session_ulid}")

    # 1. Check Redis first — this is where Celery saves results
    temp_extraction = get_temp_extraction(session_ulid)
    print(f"[OnboardAI][POLL] Redis result: {temp_extraction is not None} | keys={list(temp_extraction.keys()) if temp_extraction else []}")

    if temp_extraction and "validation" in temp_extraction:
        validation = temp_extraction["validation"]
        combined_data = validation.get("combined_data", {})
        gst_data      = validation.get("gst_data", {})
        print(f"[OnboardAI][POLL] ✓ Data found in Redis. combined_data keys: {list(combined_data.keys())} | GST present: {bool(gst_data)}")

        # Guard: combined_data may exist but be empty if Celery hasn't finished yet
        if not combined_data:
            print(f"[OnboardAI][POLL] ⏳ combined_data is empty — Celery still processing, returning RENDER_PROCESSING")
            return {"ui_action": "RENDER_PROCESSING", "agent_message": "Still processing..."}

        # ── Return full validation block, keeping both KYC and GST intact ─────
        # DB sync is intentionally NOT done here to avoid repeated writes on every poll.
        # The authoritative DB commit happens when the user sends USER_CONFIRMED_DATA
        # in the /chat endpoint, which is the correct authoritative moment.
        return {
            "ui_action": "RENDER_DATA_REVIEW",
            "extracted_data": {
                "combined_data": combined_data,
                "gst_data":      gst_data,
                "valid":         bool(validation.get("valid", True)),
                "flags":         list(validation.get("flags", []))
            }
        }

    # Celery saved an error state
    if temp_extraction and temp_extraction.get("error"):
        print(f"[OnboardAI][POLL] ✗ Celery saved an error: {temp_extraction.get('error')}")
        return {
            "ui_action": "RENDER_KYC_UPLOAD",
            "extracted_data": {},
            "agent_message": "Extraction failed, please try uploading again."
        }

    # 2. Fallback: check SQL for any permanently saved record
    result = await db.execute(select(UserDocument).where(UserDocument.session_id == session_ulid))
    extraction = result.scalars().first()

    if extraction and extraction.extracted_data:
        print(f"[OnboardAI][POLL] ✓ Data found in SQL database (fallback)")
        return {
            "ui_action": "RENDER_DATA_REVIEW",
            "extracted_data": {
                "combined_data": extraction.extracted_data,
                "gst_data":      {},
                "valid":         True,
                "flags":         []
            }
        }

    # 3. Not ready yet — frontend should keep polling
    print(f"[OnboardAI][POLL] ⏳ No data yet for session {session_ulid}, returning RENDER_PROCESSING")
    return {
        "ui_action": "RENDER_PROCESSING",
        "agent_message": "Still processing..."
    }


@router.post("/review/{session_id}")
async def submit_corrections(session_id: str, payload: CorrectionRequest, db: AsyncSession = Depends(get_db), token: str = Depends(security)):
    """
    Submit manual user corrections.
    Triggers the validation sanity check to see if critical fields were changed.
    """
    result = await db.execute(select(UserDocument).where(UserDocument.session_id == session_id))
    extraction = result.scalars().first()
    
    if not extraction:
        raise HTTPException(status_code=404, detail="Session or extraction not found")
    
    original_data = extraction.extracted_data or {}
    corrections = payload.corrections
    
    # Merge corrections natively
    merged_data = {**original_data, **corrections}
    
    # Run dynamic rulebook evaluation 
    revalidation_result = revalidate_corrections(merged_data)
    
    extraction.extracted_data = merged_data
    extraction.status = "REVIEWED_WITH_FLAG" if not revalidation_result["valid"] else "REVIEWED"
    
    await db.commit()
    
    return {
        "status": "success",
        "valid": revalidation_result["valid"],
        "flags": revalidation_result["flags"],
        "message": "Corrections saved and dynamically re-validated successfully"
    }
