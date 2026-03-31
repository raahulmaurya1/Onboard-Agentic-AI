"""
Liveness detection using Eye Aspect Ratio (EAR) blink detection.
"""
import cv2
import numpy as np
import logging
import os
import urllib.request
from typing import List, Optional
from dataclasses import dataclass

from app.config import settings

logger = logging.getLogger(__name__)

# ── Landmark indices (468-point Face Mesh topology) ──────────────────────────
LEFT_EYE_INDICES  = [33, 160, 158, 133, 153, 144]
RIGHT_EYE_INDICES = [263, 387, 385, 362, 380, 373]

# ── Model auto-download ───────────────────────────────────────────────────────
_MODEL_URL = (
    "https://storage.googleapis.com/mediapipe-models/"
    "face_landmarker/face_landmarker/float16/latest/face_landmarker.task"
)
_MODEL_FILENAME = "face_landmarker.task"


def _get_model_path() -> str:
    """Return local path to face_landmarker.task, downloading once if needed."""
    deepface_home = getattr(settings, "DEEPFACE_HOME", os.path.expanduser("~/.deepface"))
    model_dir = os.path.join(deepface_home, "mediapipe_models")
    os.makedirs(model_dir, exist_ok=True)
    model_path = os.path.join(model_dir, _MODEL_FILENAME)
    if not os.path.exists(model_path):
        logger.info(f"Downloading MediaPipe face landmarker model → {model_path}")
        urllib.request.urlretrieve(_MODEL_URL, model_path)
        logger.info("Model download complete.")
    return model_path


@dataclass
class LivenessResult:
    is_live: bool
    blink_count: int
    blink_frames: List[int]
    ear_values: List[float]
    total_frames_analyzed: int
    faces_detected: int
    confidence: float
    message: str


def compute_ear(eye: np.ndarray) -> float:
    """Eye Aspect Ratio: (|p2-p6| + |p3-p5|) / (2 * |p1-p4|)"""
    A = np.linalg.norm(eye[1] - eye[5])
    B = np.linalg.norm(eye[2] - eye[4])
    C = np.linalg.norm(eye[0] - eye[3])
    return float((A + B) / (2.0 * C)) if C > 1e-6 else 0.0


def _landmarks_to_eye(landmark_list, indices: List[int], w: int, h: int) -> np.ndarray:
    """NormalizedLandmark list → pixel-coord numpy array for given indices."""
    return np.array([[landmark_list[i].x * w, landmark_list[i].y * h] for i in indices])


def _build_landmarker():
    """Build FaceLandmarker via mediapipe.tasks (0.10.x API)."""
    from mediapipe.tasks import python as mp_python
    from mediapipe.tasks.python import vision as mp_vision

    model_path = _get_model_path()
    base_options = mp_python.BaseOptions(model_asset_path=model_path)
    options = mp_vision.FaceLandmarkerOptions(
        base_options=base_options,
        output_face_blendshapes=False,
        output_facial_transformation_matrixes=False,
        num_faces=1,
        min_face_detection_confidence=0.5,
        min_face_presence_confidence=0.5,
        min_tracking_confidence=0.5,
        running_mode=mp_vision.RunningMode.IMAGE,
    )
    return mp_vision.FaceLandmarker.create_from_options(options)


def _process_frame_tasks(landmarker, frame_bgr: np.ndarray) -> Optional[float]:
    """Run landmarker on one BGR frame. Returns avg EAR or None if no face."""
    import mediapipe as mp
    h, w = frame_bgr.shape[:2]
    rgb = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2RGB)
    mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb)
    result = landmarker.detect(mp_image)
    if not result.face_landmarks:
        return None
    lms = result.face_landmarks[0]
    left_eye  = _landmarks_to_eye(lms, LEFT_EYE_INDICES,  w, h)
    right_eye = _landmarks_to_eye(lms, RIGHT_EYE_INDICES, w, h)
    return (compute_ear(left_eye) + compute_ear(right_eye)) / 2.0


def _run_ear_on_frames(frames_iter) -> Optional[LivenessResult]:
    """Core blink-counting loop."""
    try:
        landmarker = _build_landmarker()
    except Exception as e:
        logger.warning(f"MediaPipe landmarker build failed: {e}")
        return None

    ear_threshold = getattr(settings, "BLINK_EAR_THRESHOLD", 0.2)
    consec_frames = getattr(settings, "BLINK_CONSEC_FRAMES", 2)
    min_blinks = getattr(settings, "MIN_BLINKS_FOR_LIVENESS", 1)

    ear_values: List[float] = []
    blink_frames: List[int] = []
    faces_detected = 0
    blink_count = 0
    consec_below = 0
    total_frames = 0

    for frame_idx, frame in frames_iter:
        total_frames += 1
        if frame is None:
            consec_below = 0
            continue

        avg_ear = _process_frame_tasks(landmarker, frame)

        if avg_ear is not None:
            faces_detected += 1
            ear_values.append(round(avg_ear, 4))
            # Log all EAR values at INFO level for debugging baseline issues
            logger.info(f"[Liveness] Frame {frame_idx}: EAR={avg_ear:.4f}")
            if avg_ear < ear_threshold:
                consec_below += 1
                logger.info(f"[Liveness] Frame {frame_idx}: EAR {avg_ear:.3f} < {ear_threshold} (consec={consec_below})")
            else:
                if consec_below >= consec_frames:
                    blink_count += 1
                    blink_frames.append(frame_idx - consec_below)
                    logger.info(f"Blink detected at frame {frame_idx - consec_below}, EAR dropped then recovered.")
                consec_below = 0
            
            # ── Optimization: Early Exit ──
            if blink_count >= min_blinks:
                logger.info(f"[Liveness] Early exit: target blinks ({min_blinks}) reached at frame {frame_idx}")
                break
        else:
            if total_frames % 10 == 0:
                logger.warning(f"[Liveness] Frame {frame_idx}: No face detected.")
            consec_below = 0

    landmarker.close()

    if consec_below >= consec_frames:
        blink_count += 1

    is_live    = blink_count >= min_blinks and faces_detected > 0
    face_rate  = faces_detected / max(total_frames, 1)
    confidence = round(
        min(1.0, blink_count / max(min_blinks, 1)) * face_rate * 100, 2
    )
    return LivenessResult(
        is_live=is_live,
        blink_count=blink_count,
        blink_frames=blink_frames,
        ear_values=ear_values,
        total_frames_analyzed=total_frames,
        faces_detected=faces_detected,
        confidence=confidence,
        message=(
            f"Liveness confirmed: {blink_count} blink(s) detected"
            if is_live
            else f"Liveness failed: {blink_count} blink(s) detected (need {min_blinks})"
        ),
    )


def _opencv_fallback_video(video_path: str) -> LivenessResult:
    """OpenCV fallback for blink detection."""
    face_casc = cv2.CascadeClassifier(cv2.data.haarcascades + "haarcascade_frontalface_default.xml")
    eye_casc  = cv2.CascadeClassifier(cv2.data.haarcascades + "haarcascade_eye.xml")

    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        return LivenessResult(False, 0, [], [], 0, 0, 0.0, "Could not open video file")

    min_blinks = getattr(settings, "MIN_BLINKS_FOR_LIVENESS", 1)
    prev_eyes = 2; blink_count = 0; blink_frames: List[int] = []
    faces_detected = 0; frame_idx = 0; open_streak = 0

    while True:
        ret, frame = cap.read()
        if not ret:
            break
        gray  = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        faces = face_casc.detectMultiScale(gray, 1.1, 4)
        if len(faces):
            faces_detected += 1
            x, y, w, h = faces[0]
            eye_count = len(eye_casc.detectMultiScale(gray[y:y+h, x:x+w], 1.1, 3))
            if eye_count == 2:
                if prev_eyes < 2 and open_streak > 0:
                    blink_count += 1; blink_frames.append(frame_idx)
                open_streak += 1
            else:
                open_streak = 0
            prev_eyes = eye_count
        frame_idx += 1

    cap.release()
    is_live    = blink_count >= min_blinks and faces_detected > 0
    confidence = round(min(1.0, blink_count / max(min_blinks, 1))
                       * (faces_detected / max(frame_idx, 1)) * 100, 2)
    return LivenessResult(
        is_live=is_live, blink_count=blink_count, blink_frames=blink_frames,
        ear_values=[], total_frames_analyzed=frame_idx, faces_detected=faces_detected,
        confidence=confidence,
        message=(f"Liveness confirmed: {blink_count} blink(s) (OpenCV fallback)"
                 if is_live else f"Liveness failed: {blink_count} blink(s) (OpenCV fallback)"),
    )


def detect_blinks_in_video(video_path: str) -> LivenessResult:
    """Analyze a video file."""
    try:
        import mediapipe
    except ImportError:
        logger.warning("MediaPipe not installed — using OpenCV fallback")
        return _opencv_fallback_video(video_path)

    def _video_iter(path):
        cap = cv2.VideoCapture(path)
        idx = 0
        while True:
            ret, frame = cap.read()
            if not ret:
                break
            yield idx, frame
            idx += 1
        cap.release()

    result = _run_ear_on_frames(_video_iter(video_path))
    if result is None:
        return _opencv_fallback_video(video_path)
    return result


def detect_blinks_from_frames(frame_paths: List[str]) -> LivenessResult:
    """Detect blinks from saved frame image paths."""
    try:
        import mediapipe
    except ImportError:
        return LivenessResult(False, 0, [], [], len(frame_paths), 0, 0.0,
                              "MediaPipe not installed — liveness check skipped")

    def _image_iter(paths):
        for idx, p in enumerate(paths):
            yield idx, cv2.imread(p)

    result = _run_ear_on_frames(_image_iter(frame_paths))
    if result is None:
        return LivenessResult(False, 0, [], [], len(frame_paths), 0, 0.0,
                              "MediaPipe landmarker init failed — liveness check skipped")
    return result
