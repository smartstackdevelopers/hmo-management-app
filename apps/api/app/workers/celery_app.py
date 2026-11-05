from celery import Celery

from app.core.config import get_settings

settings = get_settings()

celery_app = Celery(
    "hmore",
    broker=settings.redis_url,
    backend=settings.redis_url,
)

celery_app.conf.update(task_ignore_result=True, task_serializer="json")
