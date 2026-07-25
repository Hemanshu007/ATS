from celery import Celery
from celery.schedules import crontab

from app.core.config import settings

celery_app = Celery(
    "ats",
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND,
    include=["app.tasks.email_tasks", "app.tasks.scheduled_tasks", "app.tasks.resume_processing_tasks"],
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
)

celery_app.conf.beat_schedule = {
    "flag-stale-applications-daily": {
        "task": "app.tasks.scheduled_tasks.flag_stale_applications",
        "schedule": crontab(hour=2, minute=0),
    },
}
