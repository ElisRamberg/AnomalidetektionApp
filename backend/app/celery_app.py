"""Celery application configuration."""

from celery import Celery

from .config import get_settings

settings = get_settings()

# Create Celery instance
celery_app = Celery(
    "anomaly_detection",
    broker=getattr(settings, "redis_url", "redis://localhost:6379/0"),
    backend=getattr(settings, "redis_url", "redis://localhost:6379/0"),
    include=["backend.app.tasks.file_processing", "backend.app.tasks.analysis_tasks"],
)

# Celery configuration
celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_time_limit=30 * 60,  # 30 minutes
    task_soft_time_limit=25 * 60,  # 25 minutes
    worker_prefetch_multiplier=1,
    worker_max_tasks_per_child=1000,
)

# Task routing - disabled for now, using default queue
# celery_app.conf.task_routes = {
#     "backend.app.tasks.file_processing.*": {"queue": "file_processing"},
#     "backend.app.tasks.analysis_tasks.*": {"queue": "analysis"},
# }

# Beat schedule for periodic tasks
celery_app.conf.beat_schedule = {
    "cleanup-old-uploads": {
        "task": "backend.app.tasks.file_processing.cleanup_old_uploads",
        "schedule": 3600.0,  # Every hour
    },
    "cleanup-old-analyses": {
        "task": "backend.app.tasks.analysis_tasks.cleanup_old_analyses",
        "schedule": 86400.0,  # Every day
    },
}
