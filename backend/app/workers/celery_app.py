import os
from celery import Celery

REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")

celery_app = Celery(
    "bank_worker",
    broker=REDIS_URL,
    backend=REDIS_URL,
    include=[
        "app.workers.tasks.extraction",
        "app.workers.tasks.face_verification_tasks"
        # Note: process_sme_documents_async lives in app.workers.tasks.extraction
        # and is auto-registered via the @celery_app.task decorator in that module.
    ]
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True
)
