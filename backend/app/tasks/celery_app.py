from celery import Celery
from celery.schedules import crontab

from app.core.config import get_settings

settings = get_settings()

celery_app = Celery(
    "scholarship_autopilot",
    broker=settings.celery_broker_url,
    backend=settings.celery_result_backend,
    include=["app.tasks.jobs"],
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    worker_prefetch_multiplier=1,
)

celery_app.conf.beat_schedule = {
    "discover-scholarships-daily": {
        "task": "app.tasks.jobs.discover_all_users",
        "schedule": crontab(hour=6, minute=0),
    },
    "send-deadline-reminders-daily": {
        "task": "app.tasks.jobs.send_deadline_reminders",
        "schedule": crontab(hour=8, minute=0),
    },
    "verify-scholarships-weekly": {
        "task": "app.tasks.jobs.verify_all_scholarships",
        "schedule": crontab(hour=3, minute=0, day_of_week="sun"),
    },
    "recheck-approaching-daily": {
        "task": "app.tasks.jobs.recheck_approaching_scholarships",
        "schedule": crontab(hour=5, minute=30),
    },
    "remove-expired-daily": {
        "task": "app.tasks.jobs.remove_expired_opportunities",
        "schedule": crontab(hour=4, minute=0),
    },
}
