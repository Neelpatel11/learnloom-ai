"""Celery application."""

from celery import Celery
from learnloom_agents.tracing import lock_down_global_tracing
from learnloom_core.settings import get_settings

lock_down_global_tracing()  # only the masked per-run tracer may send traces
settings = get_settings()

celery_app = Celery(
    "learnloom",
    broker=settings.redis_url,
    backend=settings.redis_url,
    include=["learnloom_worker.tasks"],
)

celery_app.conf.update(
    task_default_queue="default",
    task_acks_late=True,  # a crashed worker leaves the job for another worker
    worker_prefetch_multiplier=1,  # long OCR and embedding jobs should not queue behind each other
    task_track_started=True,
    timezone="UTC",
    enable_utc=True,
)
