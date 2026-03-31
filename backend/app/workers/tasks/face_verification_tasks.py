import logging
import os
import shutil
import tempfile
from app.workers.celery_app import celery_app
from app.services.face_verification.face_service import verify_faces
from app.services.face_verification.liveness_service import detect_blinks_in_video
from app.services.face_verification.video_utils import extract_frames_from_video, get_minio_object_bytes, save_bytes_to_local
from app.db.redis_client import redis_client
import json
from app.db.redis_client import redis_client
import json

logger = logging.getLogger(__name__)

@celery_app.task(name="verify_face_liveness_async")
def verify_face_liveness_async(session_ulid: str, live_photo_path: str, live_video_path: str):
    """
    Background task to perform face matching and liveness detection.
    
    Args:
        session_ulid: The unique session ID.
        live_photo_path: MinIO path to the live-captured selfie (e.g., "temp/ulid/live_photo.jpg").
        live_video_path: MinIO path to the live-captured video (e.g., "temp/ulid/live_video.webm").
    """
    temp_dir = tempfile.mkdtemp(prefix=f"face_verify_{session_ulid}_")
    logger.info(f"[FaceVerify][{session_ulid}] Starting background task in {temp_dir}")
    
    try:
        # 1. Download files from MinIO to local temp storage
        photo_bytes = get_minio_object_bytes("temp", live_photo_path.replace("temp/", ""))
        video_bytes = get_minio_object_bytes("temp", live_video_path.replace("temp/", ""))
        
        local_photo_path = save_bytes_to_local(photo_bytes, os.path.join(temp_dir, "ref_photo.jpg"))
        local_video_path = save_bytes_to_local(video_bytes, os.path.join(temp_dir, "liveness_video.webm"))
        
        # 2. Extract frames for face matching
        frames_dir = os.path.join(temp_dir, "frames")
        frame_paths = extract_frames_from_video(local_video_path, frames_dir, max_frames=10)
        
        if not frame_paths:
            error_res = {"status": "error", "message": "Failed to extract frames from video."}
            redis_client.setex(f"face_verification:{session_ulid}", 3600, json.dumps(error_res))
            return error_res

        # 3. Perform Face Verification
        logger.info(f"[FaceVerify][{session_ulid}] Running face matching...")
        face_result = verify_faces(local_photo_path, frame_paths)
        
        # 4. Perform Liveness Detection
        logger.info(f"[FaceVerify][{session_ulid}] Running liveness detection...")
        liveness_result = detect_blinks_in_video(local_video_path)
        
        # 5. Compile Result
        final_result = {
            "status": "success",
            "face_verification": {
                "is_verified": face_result["is_verified"],
                "average_similarity": face_result["average_similarity"],
                "matched_frames": face_result["matched_frames"],
                "total_frames": face_result["total_frames"],
            },
            "liveness": {
                "is_live": liveness_result.is_live,
                "blink_count": liveness_result.blink_count,
                "confidence": liveness_result.confidence,
                "message": liveness_result.message,
            },
            "overall_verdict": face_result["is_verified"] and liveness_result.is_live
        }
        
        # 5.1 Persistence Note: Orchestrator handles DB sync during status polling.
        
        logger.info(f"[FaceVerify][{session_ulid}] Completed. Verdict: {final_result['overall_verdict']}")
        
        # 6. Save to Redis for polling
        redis_client.setex(f"face_verification:{session_ulid}", 3600, json.dumps(final_result))
        return final_result

    except Exception as e:
        logger.error(f"[FaceVerify][{session_ulid}] Task failed: {e}", exc_info=True)
        error_res = {"status": "error", "message": str(e)}
        redis_client.setex(f"face_verification:{session_ulid}", 3600, json.dumps(error_res))
        return error_res
        
    finally:
        # Cleanup local temp files
        shutil.rmtree(temp_dir, ignore_errors=True)
        logger.info(f"[FaceVerify][{session_ulid}] Cleaned up temp directory.")
