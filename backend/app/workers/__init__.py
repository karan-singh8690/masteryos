"""Workers package — production background processing infrastructure.

Modules:
- host: WorkerHost + WorkerProcessor base class + HeartbeatService
- outbox_dispatcher: Production outbox dispatcher with visibility timeout + DLQ
- subscriber_registry: Event type → subscriber handler registry
- retry_engine: Exponential backoff retry scheduler
- scheduler: Recurring job scheduler
- notification_processor: Delivers queued notifications
- email_processor: Sends queued emails via SMTP
- cleanup_processor: Removes expired tokens/sessions
- metrics_collector: Background metrics aggregation
- worker_main: Entry point for the worker process (python -m app.workers.worker_main)
"""

from app.workers.host import WorkerHost, WorkerProcessor, HeartbeatService

__all__ = ["WorkerHost", "WorkerProcessor", "HeartbeatService"]
