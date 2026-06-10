from celery import Celery
from app.core.config import settings

# Initialize Celery and point it to Upstash Redis
celery_app = Celery(
    "blueprint_worker",
    broker=settings.REDIS_URL,
    backend=settings.REDIS_URL,
    include=["app.workers.tasks"]  # We will create this file next
)

# Optional: configure Celery to be a bit more robust
celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="Asia/Kolkata",
    enable_utc=True,
)