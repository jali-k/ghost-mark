# ghost_mark/celery.py
import os
from celery import Celery
from django.conf import settings

# Set the default Django settings module for the 'celery' program.
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "ghost_mark.settings")

app = Celery("ghost_mark")

# Using a string here means the worker doesn't have to serialize
# the configuration object to child processes.
app.config_from_object("django.conf:settings", namespace="CELERY")

# Load task modules from all registered Django apps.
app.autodiscover_tasks()

# Optional: Configure additional settings
app.conf.update(
    # Task routing
    task_routes={
        "pdf_app.tasks.process_pdf_task": {"queue": "pdf_processing"},
        "pdf_app.tasks.cleanup_expired_jobs": {"queue": "cleanup"},
    },
    # Task execution settings
    task_always_eager=False,  # Set to True for testing without Redis
    task_eager_propagates=True,
    # Result backend settings
    result_expires=3600,  # 1 hour
    # Worker settings
    worker_prefetch_multiplier=1,  # Important for memory management with large files
    worker_max_tasks_per_child=50,  # Restart workers after 50 tasks to prevent memory leaks
    # Task time limits
    task_soft_time_limit=300,  # 5 minutes soft limit
    task_time_limit=600,  # 10 minutes hard limit
    # Timezone
    timezone="UTC",
    enable_utc=True,
)


@app.task(bind=True)
def debug_task(self):
    print(f"Request: {self.request!r}")


# Optional: Add periodic tasks
from celery.schedules import crontab

app.conf.beat_schedule = {
    "cleanup-expired-jobs": {
        "task": "pdf_app.tasks.cleanup_expired_jobs",
        "schedule": crontab(minute="*/15"),  # Run every 15 minutes
        "options": {"queue": "cleanup"},
    },
}
app.conf.timezone = "UTC"
