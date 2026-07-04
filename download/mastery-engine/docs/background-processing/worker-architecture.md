# Worker Architecture

> **Component:** WorkerHost + WorkerProcessor + HeartbeatService

## Overview

The WorkerHost is the top-level coordinator that runs multiple background processors as asyncio tasks. It manages graceful shutdown, heartbeats, and worker identity.

## WorkerHost

### Responsibilities

1. **Start processors**: Each registered processor runs as an asyncio task.
2. **Heartbeat**: Writes to `worker_heartbeats` every 10 seconds.
3. **Graceful shutdown**: On SIGTERM/SIGINT, drains in-progress work (up to 30s), then stops.
4. **Worker identity**: Each worker has a unique `worker_id` (e.g., `worker-a1b2c3d4`).
5. **Multi-worker coordination**: Multiple workers can run concurrently; they coordinate via DB leases.

### Lifecycle

```
1. start()
   ├── Write initial heartbeat (status="starting")
   ├── Start heartbeat task (every 10s)
   ├── Start processor tasks (outbox, scheduler, notifications, etc.)
   ├── Update status to "running"
   └── Wait for all tasks (they run forever until stopped)

2. stop() (graceful)
   ├── Set _running = False
   ├── Write heartbeat (status="draining", shutdown_requested=True)
   ├── Call processor.stop() for each processor
   ├── Wait for tasks to complete (up to 30s)
   ├── Cancel remaining tasks
   └── Write final heartbeat (status="stopped")
```

### Processors

Each processor extends `WorkerProcessor` and implements `run_once()`:

```python
class MyProcessor(WorkerProcessor):
    name = "my_processor"

    async def run_once(self) -> int:
        # Process one batch; return count processed
        items = await fetch_items()
        for item in items:
            await process(item)
            self._processed_count += 1
        return len(items)
```

The host calls `run_once()` in a loop. If it returns 0, the host sleeps (1s default) before trying again.

## HeartbeatService

### Stale Worker Detection

A worker is considered "dead" if its heartbeat is older than 60 seconds:

```python
service = HeartbeatService(session_factory)
dead_workers = await service.detect_dead_workers()
for worker_id in dead_workers:
    await service.mark_worker_dead(worker_id)
```

### Admin Operations

- `list_workers()` — List all workers (active + recently dead)
- `get_worker(worker_id)` — Get a single worker's status
- `request_shutdown(worker_id)` — Request graceful shutdown
- `mark_worker_dead(worker_id)` — Mark a worker as crashed

## Horizontal Scaling

Multiple worker processes can run concurrently:

1. Each worker has a unique `worker_id`.
2. The outbox dispatcher uses `SELECT FOR UPDATE SKIP LOCKED` to claim events (PostgreSQL).
3. The scheduler uses optimistic locking to claim jobs.
4. Heartbeats ensure crashed workers are detected + their leases reclaimed.

### Deployment

```bash
# Run 3 worker processes (e.g., on different machines)
python -m app.workers.worker_main  # worker-1
python -m app.workers.worker_main  # worker-2
python -m app.workers.worker_main  # worker-3
```

The `heartbeat_check` scheduled job (runs every minute) detects dead workers and marks them as crashed. The outbox dispatcher reclaims expired leases.

## Monitoring

- **Worker status**: `GET /api/v1/admin/bg/workers`
- **Metrics**: `GET /api/v1/admin/bg/workers/metrics`
- **Worker stats**: Each processor exposes `processed_count`, `failed_count`, `current_job`
