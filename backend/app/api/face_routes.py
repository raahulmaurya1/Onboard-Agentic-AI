from fastapi import APIRouter, File, UploadFile, HTTPException, Form
from typing import Optional
import logging
import json
from app.storage.minio import save_to_minio
from app.db.redis_client import redis_client
from app.workers.tasks.face_verification_tasks import verify_face_liveness_async
from app.db.base import AsyncSessionLocal
from app.db.models.user import UserInitial
from sqlalchemy.future import select

router = APIRouter()
logger = logging.getLogger(__name__)

@router.post("/verify")
async def trigger_face_verification(
    session_ulid: str = Form(...),
    live_photo: UploadFile = File(...),
    live_video: UploadFile = File(...)
):
    """
    Endpoint to upload live photo and video for face/liveness verification.
    """
    try:
        logger.info(f"[FaceAPI][{session_ulid}] Received face verification request.")
        
        # 1. Save files to MinIO
        photo_bytes = await live_photo.read()
        video_bytes = await live_video.read()
        
        photo_name = f"{session_ulid}/face_verification/live_photo.jpg"
        video_name = f"{session_ulid}/face_verification/live_video.webm"
        
        photo_path = save_to_minio("temp", photo_name, photo_bytes, content_type=live_photo.content_type)
        video_path = save_to_minio("temp", video_name, video_bytes, content_type=live_video.content_type)
        
        logger.info(f"[FaceAPI][{session_ulid}] Files saved to MinIO: {photo_path}, {video_path}")
        
        # 2. Trigger Celery Task
        verify_face_liveness_async.delay(session_ulid, photo_path, video_path)
        
        # 3. Clear any old result in Redis
        redis_client.delete(f"face_verification:{session_ulid}")
        
        return {
            "status": "processing",
            "message": "Face verification task triggered.",
            "session_ulid": session_ulid
        }
        
    except Exception as e:
        logger.error(f"[FaceAPI][{session_ulid}] Trigger failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/status/{session_ulid}")
async def get_face_verification_status(session_ulid: str):
    """
    Poll the status of face verification from Redis.
    """
    res_raw = redis_client.get(f"face_verification:{session_ulid}")
    if not res_raw:
        return {"status": "processing", "message": "Verification is still in progress."}
    
    result_data = json.loads(res_raw)
    
    # Synchronization: If successful, persist to PostgreSQL
    if result_data.get("status") == "success" and result_data.get("overall_verdict") is True:
        async with AsyncSessionLocal() as db:
            print(f"[FaceAPI][{session_ulid}] ✓ Verification Success. Synchronizing to PostgreSQL.")
            stmt = select(UserInitial).where(UserInitial.id == session_ulid)
            db_res = await db.execute(stmt)
            user = db_res.scalar_one_or_none()
            if user:
                user.face_verified = True
                user.status = "FACE_VERIFIED"
                await db.commit()
                print(f"[FaceAPI][{session_ulid}] ✓ PostgreSQL updated: status=FACE_VERIFIED, face_verified=True")
                
    return result_data
