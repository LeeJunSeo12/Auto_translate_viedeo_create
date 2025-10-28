from celery import Celery

from app.config import settings


celery_app = Celery(
    "auto_shorts",
    broker=settings.redis_url,
    backend=settings.redis_url,
    include=["app.tasks"],
)

celery_app.conf.update(task_track_started=True, result_expires=3600)
