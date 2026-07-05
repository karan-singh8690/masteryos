"""Scheduler infrastructure package.

Modules:
- processor: SchedulerProcessor (runs recurring jobs) + default handlers
"""

from app.infrastructure.scheduler.processor import (
    SchedulerProcessor,
    DEFAULT_SCHEDULED_JOBS,
    DEFAULT_HANDLERS,
    ensure_default_jobs_scheduled,
)

__all__ = [
    "SchedulerProcessor",
    "DEFAULT_SCHEDULED_JOBS",
    "DEFAULT_HANDLERS",
    "ensure_default_jobs_scheduled",
]
