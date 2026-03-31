import logging
from fastapi import APIRouter, Depends, HTTPException, Request, UploadFile, File
from fastapi.security import HTTPBearer
from pydantic import BaseModel
from typing import Dict, Any, List, Annotated

from app.agents.intent_agent import classify_intent, IntentClassificationResult
from app.agents.extraction_agent import extract_document_data
from app.agents.validation_agent import cross_check_documents
from app.workers.tasks.extraction import process_and_standardize_file
from app.services.geoip_service import verify_ip_prefix
from app.agents.finalization_agent import execute_hybrid_freeze
from app.storage.minio import save_to_minio, move_minio_object
from app.db.base import AsyncSessionLocal
from app.db.schemas import OnboardingState
from app.db.models.document import UserDocument
from app.db.models.session import OnboardingSession
from app.db.models.user import UserInitial
from sqlalchemy.future import select
from app.db.redis_client import save_temp_extraction, get_temp_extraction, clear_temp_extraction

router = APIRouter()
security = HTTPBearer()

class IntentRequest(BaseModel):
    user_input: str
    phone_prefix: str = "+91" # Mock default extracted via middleware prior to hitting this route
    ip_address: str = "127.0.0.1" # Mock default extracted via Request in production

class UploadResponse(BaseModel):
    document_id: int
    session_id: str
    file_url: str
    file_type: str

@router.post("/intent", response_model=IntentClassificationResult)
async def analyze_intent(request: IntentRequest, req: Request, token: str = Depends(security)):
    """
    Phase 2 Endpoint: AI Services & Intent Classification
    Receives natural language input from the user and classifying what onboarding
    tier they belong to (Retail, SME, Digital-Only, Re-KYC).
    Returns the classification, confidence, and required document manifest.
    """
    
    # 1. GeoIP Validation (Placeholder)
    # Replaces request.ip_address with actual req.client.host in production
    if not verify_ip_prefix(request.ip_address, request.phone_prefix):
         raise HTTPException(status_code=403, detail="IP Address does not match phone prefix region.")
         
     
    # 2. Agentic Intent Classification via Gemini
    classification_result = await classify_intent(request.user_input)
    
    return classification_result


@router.post("/upload-documents")
async def upload_multi_documents(
    request: Request, 
    files: list[UploadFile], 
    token: str = Depends(security)
):
    """
    Step 1 of Human-in-the-Loop: Extracts data via Gemini natively, checks rules, caches to Redis.
    """
    user_data = getattr(request.state, "user", None)
    if not user_data:
        raise HTTPException(status_code=401, detail="Unauthorized active session.")
        
    session_id = user_data.get("uid") or user_data.get("id")
    if not session_id:
        raise HTTPException(status_code=400, detail="Malformed session identity mapping.")
        
    extracted_collection = []
    minio_temp_paths = []
    
    for file in files:
        raw_bytes = await file.read()
        
        # 1. Preprocess & magika standardization
        clean_bytes, mime_type = process_and_standardize_file(raw_bytes)
        
        # 2. Save strictly to temp/ bucket in MinIO
        object_name = f"{session_id}/{file.filename}"
        temp_url = save_to_minio("temp", object_name, clean_bytes, mime_type)
        minio_temp_paths.append({"filename": file.filename, "url": temp_url, "mime_type": mime_type})
        
        # 3. DB Persistence: Populate user_documents table for audit/tracking
        try:
            async with AsyncSessionLocal() as db:
                new_doc = UserDocument(
                    session_id=session_id,
                    file_type="document", # Default as requested, OCR will update it later
                    file_url=temp_url,
                    status="UPLOADED"
                )
                db.add(new_doc)
                await db.commit()
        except Exception as db_err:
            logging.error(f"[OnboardAI][UPLOAD] Non-fatal DB error for {file.filename}: {db_err}")
        
    # 4. Save temporary state to Redis (Placeholder for tracking paths)
    save_temp_extraction(session_id, {
        "files": minio_temp_paths,
        "validation": {"status": "processing"}
    })
    
    # 5. Dispatch async OCR task
    from app.workers.tasks.extraction import process_documents_async
    process_documents_async.delay(session_id, [p["url"] for p in minio_temp_paths])
    
    return {
        "status": "Accepted",
        "message": "Documents uploaded successfully. Extraction process started in background.",
        "session_id": session_id
    }

@router.post("/confirm-documents")
async def confirm_multi_documents(request: Request, payload: dict, token: str = Depends(security)):
    """
    Step 2 of Human-in-the-Loop: Accepts User verified edits, pivots MinIO temp to verified permanently, updates Postgres.
    """
    user_data = getattr(request.state, "user", None)
    if not user_data:
        raise HTTPException(status_code=401, detail="Unauthorized active session.")
        
    session_id = user_data["uid"]
    
    # 1. Pull Temp state from Redis securely
    temp_state = get_temp_extraction(session_id)
    if not temp_state:
        raise HTTPException(status_code=400, detail="No active extraction pending confirmation for this session.")
        
    verified_files = []
    
    # 2. Pivot storage domains in MinIO organically seamlessly
    for file_meta in temp_state.get("files", []):
        old_url = file_meta["url"]
        object_name = f"{session_id}/{file_meta['filename']}"
        
        # Move across MinIO buckets securely
        new_url = move_minio_object("temp", object_name, "verified", object_name)
        verified_files.append({"url": new_url, "type": file_meta["mime_type"]})
        
    # 3. Securely hit downstream generic PostgreSQL dependencies
    async with AsyncSessionLocal() as db:
        session_result = await db.execute(select(OnboardingSession).where(OnboardingSession.session_id == session_id))
        db_session = session_result.scalars().first()
        
        if not db_session:
            raise HTTPException(status_code=404, detail="Active Session unmapped cleanly")
            
        # Insert permanently mapped to overarching Identity
        user_result = await db.execute(select(UserInitial).where(UserInitial.id == db_session.user_id))
        db_user = user_result.scalars().first()
        
        db_user.verified_data = payload
        db_user.status = "VERIFIED"
        
        # Inject standard document mapping rows
        for doc in verified_files:
            new_doc = UserDocument(
                session_id=session_id,
                file_type=doc["type"],
                file_url=doc["url"],
                status="VERIFIED",
                extracted_data=payload
            )
            db.add(new_doc)
            
        await db.commit()
    
    # 4. Purge volatile memory mappings safely 
    clear_temp_extraction(session_id)
    
    return {"message": "Documents verified permanently successfully. Data safely routed to PostgreSQL and Verified MinIO buckets.", "identity_status": db_user.status}

@router.post("/finalize-documents")
async def finalize_documents(request: Request, token: str = Depends(security)):
    """
    Phase 2 Finalization:
    Freezes the volatile JSON working memory into explicit Relational database columns
    and archives the raw payload into a ReadOnly ledger seamlessly.
    """
    user_data = getattr(request.state, "user", None)
    if not user_data:
        raise HTTPException(status_code=401, detail="Unauthorized active session.")
        
    session_id = user_data["uid"]
    
    async with AsyncSessionLocal() as db:
        user_result = await db.execute(select(UserInitial).where(UserInitial.id == session_id))
        db_user = user_result.scalars().first()
        
        if not db_user:
            raise HTTPException(status_code=404, detail="Active user identity not found.")
            
        if db_user.status == "FINALIZED":
            return {"message": "User is already natively finalized.", "status": db_user.status}
            
        # Trigger Semantic Pipeline Freeze
        execute_hybrid_freeze(db_user)
        
        await db.commit()
        await db.refresh(db_user)
        
    return {
        "status": "success",
        "message": "Hybrid Freeze successful. JSON Workspace archived successfully into immutable storage, relational fields mapped.",
        "user_id": db_user.id,
        "name": db_user.name,
        "dob": db_user.dob,
        "pan": db_user.pan_id,
        "aadhaar": db_user.aadhar_id
    }

