import cv2
import os
import logging
import io
from typing import List
from app.storage.minio import minio_client

logger = logging.getLogger(__name__)

def extract_frames_from_video(video_path: str, output_dir: str, max_frames: int = 60) -> List[str]:
    """
    Extracts frames from a video file and saves them to the output directory.
    Returns a list of absolute paths to the extracted frames.
    """
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        logger.error(f"Could not open video: {video_path}")
        return []

    frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    fps = cap.get(cv2.CAP_PROP_FPS) or 30
    logger.info(f"[VideoUtil] Video: {video_path} | Frames: {frame_count} | FPS: {fps}")
    
    # We want a sample of max_frames distributed throughout the video
    # If frame_count is <= 0 (common for some webm), we'll just read until max_frames or EOF.
    if frame_count <= 0:
        step = 1
    else:
        step = max(1, frame_count // max_frames)
    
    frame_paths = []
    idx = 0
    saved_count = 0
    
    while True:
        ret, frame = cap.read()
        if not ret or saved_count >= max_frames:
            break
            
        if idx % step == 0:
            frame_filename = f"frame_{saved_count:04d}.jpg"
            frame_path = os.path.join(output_dir, frame_filename)
            cv2.imwrite(frame_path, frame)
            frame_paths.append(frame_path)
            saved_count += 1
            
        idx += 1
        
    cap.release()
    logger.info(f"Extracted {len(frame_paths)} frames from {video_path}")
    return frame_paths

def get_minio_object_bytes(bucket: str, object_name: str) -> bytes:
    """Fetch raw bytes from MinIO."""
    try:
        response = minio_client.get_object(bucket, object_name)
        return response.read()
    except Exception as e:
        logger.error(f"Failed to fetch {object_name} from MinIO: {e}")
        raise

def save_bytes_to_local(data: bytes, local_path: str):
    """Save bytes to a local file."""
    os.makedirs(os.path.dirname(local_path), exist_ok=True)
    with open(local_path, "wb") as f:
        f.write(data)
    return local_path
