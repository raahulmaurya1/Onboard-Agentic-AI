from pydantic_settings import BaseSettings
from dotenv import load_dotenv
import os

# Intercept and force overwrite the Uvicorn environment cache
load_dotenv(override=True)

class Settings(BaseSettings):
    DATABASE_URL: str = "postgresql+asyncpg://postgres:abc123@127.0.0.1:5433/bank_db"
    REDIS_URL: str = "redis://localhost:6379/0"
    MINIO_URL: str = "http://localhost:9000"
    GEMINI_API_KEY: str = ""
    TWO_FACTOR_API_KEY: str = ""
    SMTP_HOST: str = "smtp.gmail.com"
    SMTP_PORT: int = 465
    SMTP_USER: str = ""
    SMTP_PASS: str = ""
    
    # Risk Agent Log Paths (read-only, for telemetry extraction)
    GUNICORN_LOG_PATH: str = "/var/log/gunicorn/access.log"
    CELERY_LOG_PATH: str = "/var/log/celery/worker.log"

    # Face Verification & Liveness Settings
    FACE_MODEL_NAME: str = "OpenFace"
    FACE_SIMILARITY_THRESHOLD: float = 0.6
    BLINK_EAR_THRESHOLD: float = 0.2
    BLINK_CONSEC_FRAMES: int = 3
    MIN_BLINKS_FOR_LIVENESS: int = 1
    DEEPFACE_HOME: str = os.path.expanduser("~/.deepface")

    class Config:
        env_file = ".env"

settings = Settings()
