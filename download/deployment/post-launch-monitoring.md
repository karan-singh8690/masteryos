# Post-Launch Monitoring — Mastery Engine Closed Beta

> **Audience:** SRE, on-call engineers, engineering leads.
> **Scope:** Long-term monitoring strategy, alert rules, dashboard usage, and operational health KPIs for the Closed Beta.
> **Last updated:** 2026-07-03

---

## 0. Monitoring Philosophy

The Mastery Engine uses a **three-pillar observability** strategy:

1. **Metrics** (Prometheus + Grafana) — for trend analysis, alerting, capacity planning
2. **Logs** (Docker json-file driver + structured JSON logs) — for debugging, audit trails
3. **Traces** (Sentry performance + correlation IDs) — for request-level diagnosis

For the Closed Beta with 20 users, the monitoring goals are:
- Detect user-facing issues within 5 minutes
- Diagnose root cause within 30 minutes
- Track engagement trends to inform product decisions
- Validate capacity for expansion to 50+ users

---

## 1. Monitoring Stack Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                    MONITORING STACK                                  │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  ┌──────────────────────┐                                          │
│  │  Application         │  Backend & worker expose:                │
│  │  (FastAPI + worker)  │   • /metrics (Prometheus exposition)     │
│  │                      │   • /api/v1/admin/bg/workers/metrics     │
│  │                      │   • /api/v1/health (liveness)            │
│  │                      │   • /api/v1/health/ready (readiness)     │
│  │                      │   • Structured JSON logs (stdout)        │
│  │                      │   • Sentry SDK for exceptions            │
│  └──────────┬───────────┘                                          │
│             │                                                       │
│             │ scrape (10-30s intervals)                            │
│             ▼                                                       │
│  ┌──────────────────────┐                                          │
│  │  Prometheus          │  Stores 30 days of metrics               │
│  │  (15s scrape int.)   │  Evaluates alert rules every 15s         │
│  │                      │  External labels:                        │
│  │                      │    monitor: mastery-engine               │
│  │                      │    environment: production               │
│  └──────────┬───────────┘                                          │
│             │                                                       │
│             │ query (PromQL)                                       │
│             ▼                                                       │
│  ┌──────────────────────┐    ┌──────────────────────┐             │
│  │  Grafana             │    │  Alertmanager        │             │
│  │  (dashboards UI)     │    │  (alert routing)     │             │
│  │                      │    │   • Slack webhook    │             │
│  │  Datasource:         │    │   • PagerDuty (SEV-1)│             │
│  │   Prometheus         │    │   • Email            │             │
│  │                      │    │                      │             │
│  │  Dashboard:          │    │  ⚠️ NOT YET DEPLOYED │             │
│  │   Production         │    │  See §4 to deploy    │             │
│  │   Overview           │    │                      │             │
│  └──────────────────────┘    └──────────────────────┘             │
│                                                                     │
│  ┌──────────────────────────────────────────────────────┐         │
│  │  Sentry (SaaS)                                       │         │
│  │  • Error tracking (unhandled exceptions)             │         │
│  │  • Performance monitoring (span traces)              │         │
│  │  • Release tracking (git SHA)                        │         │
│  │  • User feedback collection                          │         │
│  └──────────────────────────────────────────────────────┘         │
│                                                                     │
│  ┌──────────────────────────────────────────────────────┐         │
│  │  Logs (Docker json-file driver)                      │         │
│  │  • Backend: max-size 100m, max-file 10 (1GB total)   │         │
│  │  • Worker:  same                                     │         │
│  │  • Frontend: max-size 50m, max-file 5 (250MB)        │         │
│  │  • Nginx:   access + error logs to nginx_logs vol.   │         │
│  │  • Postgres: logging_collector writes to PG data dir │         │
│  │  • Structured JSON with correlation_id field         │         │
│  └──────────────────────────────────────────────────────┘         │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
```

---

## 2. Prometheus Configuration

### 2.1 Current config (`infrastructure/monitoring/prometheus/prometheus.yml`)

```yaml
global:
  scrape_interval: 15s
  evaluation_interval: 15s
  external_labels:
    monitor: 'mastery-engine'
    environment: 'production'

rule_files:
  - alerts.yml   # ⚠️ MUST BE CREATED — see §3

alerting:
  alertmanagers:
    - static_configs:
        - targets: ['alertmanager:9093']   # ⚠️ MUST BE DEPLOYED — see §4

scrape_configs:
  - job_name: 'mastery-backend'
    metrics_path: /metrics
    scrape_interval: 10s
    static_configs:
      - targets: ['backend:8000']
        labels:
          service: backend

  - job_name: 'mastery-workers'
    metrics_path: /api/v1/admin/bg/workers/metrics
    scrape_interval: 15s
    static_configs:
      - targets: ['backend:8000']
        labels:
          service: workers

  - job_name: 'mastery-frontend'
    metrics_path: /api/v1/health
    scrape_interval: 30s
    static_configs:
      - targets: ['frontend:3000']
        labels:
          service: frontend

  # ⚠️ The 3 jobs below require exporters that are NOT yet deployed.
  # Either deploy the exporters (recommended) or remove these jobs.

  - job_name: 'postgres'
    scrape_interval: 30s
    static_configs:
      - targets: ['postgres-exporter:9187']

  - job_name: 'redis'
    scrape_interval: 15s
    static_configs:
      - targets: ['redis-exporter:9121']

  - job_name: 'nginx'
    scrape_interval: 15s
    static_configs:
      - targets: ['nginx-exporter:9113']
```

### 2.2 Deploy the missing exporters

Add to `docker-compose.prod.yml`:

```yaml
  postgres-exporter:
    image: prometheuscommunity/postgres-exporter:v0.15.0
    environment:
      DATA_SOURCE_NAME: "postgresql://mastery:${DATABASE_PASSWORD}@postgres:5432/mastery_engine?sslmode=disable"
    restart: always
    networks: [default]

  redis-exporter:
    image: oliver006/redis_exporter:v1.59.0
    command:
      - --redis.addr=redis:6379
      - --redis.password=${REDIS_PASSWORD}
    restart: always
    networks: [default]

  nginx-exporter:
    image: nginx/nginx-prometheus-exporter:v1.1.0
    command:
      - -nginx.scrape-uri=http://nginx:80/stub_status
    restart: always
    networks: [default]
    depends_on: [nginx]
```

And add to `infrastructure/nginx/nginx.conf` (inside the `server` block on port 80):

```nginx
location /stub_status {
    stub_status on;
    access_log off;
    allow 172.16.0.0/12;  # Docker network
    deny all;
}
```

Then:
```bash
docker compose --env-file .env.production -f docker-compose.prod.yml up -d \
  postgres-exporter redis-exporter nginx-exporter
docker compose -f docker-compose.prod.yml restart prometheus
```

### 2.3 Verify scrape targets

```bash
curl -sf http://localhost:9090/api/v1/targets | \
  jq '.data.activeTargets[] | {job: .labels.job, health: .health, last_error: .lastError}'
```

Expected: all jobs `health: "up"`. If any are `down`, see `troubleshooting.md` §10.

---

## 3. Alert Rules (`alerts.yml`)

Create `infrastructure/monitoring/prometheus/alerts.yml`:

```yaml
groups:
  - name: mastery-engine-infrastructure
    interval: 30s
    rules:
      # ====== SERVICE DOWN ======
      - alert: ServiceDown
        expr: up == 0
        for: 2m
        labels:
          severity: critical
          team: sre
        annotations:
          summary: "Service {{ $labels.job }} is down"
          description: "{{ $labels.job }} has been down for more than 2 minutes."

      - alert: BackendHealthCheckFailing
        expr: up{job="mastery-backend"} == 0
        for: 1m
        labels:
          severity: critical
          team: sre
        annotations:
          summary: "Backend is down or unhealthy"
          description: "Backend healthcheck failing. Users cannot access the platform."

      - alert: WorkerDown
        expr: up{job="mastery-workers"} == 0
        for: 5m
        labels:
          severity: warning
          team: sre
        annotations:
          summary: "Worker is down"
          description: "Worker metrics endpoint unreachable. Background jobs not processing."

      - alert: FrontendDown
        expr: up{job="mastery-frontend"} == 0
        for: 2m
        labels:
          severity: critical
          team: sre
        annotations:
          summary: "Frontend is down"
          description: "Frontend healthcheck failing."

      # ====== HIGH ERROR RATE ======
      - alert: HighErrorRate
        expr: |
          sum(rate(http_requests_total{status=~"5.."}[5m])) by (service)
          / sum(rate(http_requests_total[5m])) by (service)
          > 0.01
        for: 5m
        labels:
          severity: warning
          team: sre
        annotations:
          summary: "High 5xx error rate on {{ $labels.service }}"
          description: "Error rate is {{ $value | humanizePercentage }} (threshold 1%) for 5 minutes."

      - alert: CriticalErrorRate
        expr: |
          sum(rate(http_requests_total{status=~"5.."}[5m])) by (service)
          / sum(rate(http_requests_total[5m])) by (service)
          > 0.05
        for: 2m
        labels:
          severity: critical
          team: sre
        annotations:
          summary: "CRITICAL: 5xx error rate > 5%"
          description: "Error rate is {{ $value | humanizePercentage }}. Investigate immediately."

      # ====== HIGH LATENCY ======
      - alert: HighP95Latency
        expr: |
          histogram_quantile(0.95,
            sum(rate(http_request_duration_ms_bucket[5m])) by (le, service)
          ) > 500
        for: 10m
        labels:
          severity: warning
          team: sre
        annotations:
          summary: "p95 latency > 500ms on {{ $labels.service }}"
          description: "Current p95: {{ $value }}ms"

      - alert: CriticalP95Latency
        expr: |
          histogram_quantile(0.95,
            sum(rate(http_request_duration_ms_bucket[5m])) by (le, service)
          ) > 2000
        for: 5m
        labels:
          severity: critical
          team: sre
        annotations:
          summary: "CRITICAL: p95 latency > 2s"
          description: "Users experiencing extreme latency. Current p95: {{ $value }}ms"

      # ====== DATABASE ======
      - alert: PostgresDown
        expr: pg_up == 0
        for: 1m
        labels:
          severity: critical
          team: sre
        annotations:
          summary: "PostgreSQL is down"
          description: "PostgreSQL instance unreachable."

      - alert: PostgresHighConnections
        expr: pg_stat_activity_count{datname="mastery_engine"} > 150
        for: 5m
        labels:
          severity: warning
          team: sre
        annotations:
          summary: "PostgreSQL connections > 150 (75% of max)"
          description: "Current connections: {{ $value }}"

      - alert: PostgresConnectionExhaustion
        expr: pg_stat_activity_count{datname="mastery_engine"} > 180
        for: 2m
        labels:
          severity: critical
          team: sre
        annotations:
          summary: "CRITICAL: PostgreSQL connections near exhaustion"
          description: "Current connections: {{ $value }} / 200"

      - alert: PostgresSlowQueries
        expr: pg_stat_statements_mean_time_seconds > 1
        for: 10m
        labels:
          severity: warning
          team: sre
        annotations:
          summary: "Slow PostgreSQL queries detected"
          description: "Average query time > 1 second."

      # ====== REDIS ======
      - alert: RedisDown
        expr: redis_up == 0
        for: 1m
        labels:
          severity: critical
          team: sre
        annotations:
          summary: "Redis is down"
          description: "Redis instance unreachable. Cache, sessions, rate limiting impacted."

      - alert: RedisHighMemory
        expr: redis_memory_used_bytes / redis_memory_max_bytes > 0.85
        for: 5m
        labels:
          severity: warning
          team: sre
        annotations:
          summary: "Redis memory > 85% of max"
          description: "Current usage: {{ $value | humanizePercentage }}"

      - alert: RedisEvictionStorm
        expr: rate(redis_evicted_keys_total[5m]) > 100
        for: 5m
        labels:
          severity: warning
          team: sre
        annotations:
          summary: "Redis evicting keys rapidly"
          description: "{{ $value }} keys/sec being evicted. Cache may be too small."

      - alert: RedisLowHitRate
        expr: |
          (rate(redis_keyspace_hits_total[5m]))
          / (rate(redis_keyspace_hits_total[5m]) + rate(redis_keyspace_misses_total[5m]))
          < 0.7
        for: 15m
        labels:
          severity: warning
          team: sre
        annotations:
          summary: "Redis cache hit rate < 70%"
          description: "Current hit rate: {{ $value | humanizePercentage }}"

      # ====== WORKERS & OUTBOX ======
      - alert: OutboxBacklog
        expr: outbox_pending > 100
        for: 5m
        labels:
          severity: warning
          team: sre
        annotations:
          summary: "Outbox backlog > 100 events"
          description: "Worker may be down or unable to keep up. Current: {{ $value }}"

      - alert: OutboxBacklogCritical
        expr: outbox_pending > 1000
        for: 5m
        labels:
          severity: critical
          team: sre
        annotations:
          summary: "CRITICAL: Outbox backlog > 1000 events"
          description: "Background processing severely degraded. Current: {{ $value }}"

      - alert: DeadLetterAccumulating
        expr: increase(dead_letter_events_total[1h]) > 10
        for: 5m
        labels:
          severity: warning
          team: sre
        annotations:
          summary: "Dead letter events accumulating"
          description: "{{ $value }} new dead letter events in the last hour."

      - alert: WorkerNoHeartbeat
        expr: workers_active < 1
        for: 2m
        labels:
          severity: critical
          team: sre
        annotations:
          summary: "No active worker heartbeats"
          description: "No workers have checked in for 2 minutes. Background processing halted."

      - alert: WorkerHighFailureRate
        expr: |
          rate(workers_jobs_failed_total[5m])
          / (rate(workers_jobs_processed_total[5m]) + rate(workers_jobs_failed_total[5m]))
          > 0.1
        for: 10m
        labels:
          severity: warning
          team: sre
        annotations:
          summary: "Worker job failure rate > 10%"
          description: "Current failure rate: {{ $value | humanizePercentage }}"

      # ====== CACHE ======
      - alert: CacheHitRateLow
        expr: |
          sum(rate(cache_operations_total{result="hit"}[5m]))
          / sum(rate(cache_operations_total[5m]))
          < 0.8
        for: 15m
        labels:
          severity: warning
          team: sre
        annotations:
          summary: "Cache hit rate < 80%"
          description: "Backend will hit DB more often. Current: {{ $value | humanizePercentage }}"

      # ====== WEBSOCKET ======
      - alert: WebSocketConnectionsDropped
        expr: |
          websocket_connections < 1
          and on()
          sum(rate(http_requests_total{path="/api/v1/learning/dashboard"}[5m])) > 0
        for: 10m
        labels:
          severity: warning
          team: sre
        annotations:
          summary: "No active WebSocket connections despite active users"
          description: "Real-time updates may be broken."

  - name: mastery-engine-business
    interval: 60s
    rules:
      # ====== CLOSED BETA ======
      - alert: BetaAlmostFull
        expr: 20 - mastery_beta_user_count > 0 and 20 - mastery_beta_user_count < 3
        for: 1m
        labels:
          severity: info
          team: product
        annotations:
          summary: "Closed Beta almost full ({{ $value }} slots remaining)"
          description: "Consider raising MAX_BETA_USERS or preparing the waitlist."

      - alert: BetaFull
        expr: mastery_beta_user_count >= 20
        for: 1m
        labels:
          severity: warning
          team: product
        annotations:
          summary: "Closed Beta is full"
          description: "No new users can register until MAX_BETA_USERS is raised."

      - alert: FeedbackBacklog
        expr: mastery_beta_open_feedback > 10
        for: 1h
        labels:
          severity: info
          team: product
        annotations:
          summary: "Beta feedback backlog > 10 open items"
          description: "{{ $value }} open feedback items need triage."

      # ====== ENGAGEMENT ======
      - alert: DAUDrop
        expr: |
          mastery_beta_dau < 3
          and on()
          day() != 0 and day() != 6  # Not weekend
        for: 2h
        labels:
          severity: info
          team: product
        annotations:
          summary: "DAU < 3 on a weekday"
          description: "Engagement drop. Investigate if there's a UX issue."

      - alert: SessionCompletionRateDrop
        expr: |
          sum(rate(questions_submitted_total[1h]))
          / sum(rate(study_sessions_started_total[1h]))
          < 3
        for: 2h
        labels:
          severity: info
          team: product
        annotations:
          summary: "Session completion rate dropping"
          description: "Average < 3 questions per session. Content may be too hard or sessions too long."

  - name: mastery-engine-system
    interval: 60s
    rules:
      # ====== DISK ======
      - alert: DiskSpaceLow
        expr: |
          (node_filesystem_avail_bytes{mountpoint="/",fstype!~"tmpfs|overlay"})
          / node_filesystem_size_bytes{mountpoint="/"}
          < 0.2
        for: 5m
        labels:
          severity: warning
          team: sre
        annotations:
          summary: "Disk space < 20% on /"
          description: "Available: {{ $value | humanizePercentage }}"

      - alert: DiskSpaceCritical
        expr: |
          (node_filesystem_avail_bytes{mountpoint="/",fstype!~"tmpfs|overlay"})
          / node_filesystem_size_bytes{mountpoint="/"}
          < 0.1
        for: 5m
        labels:
          severity: critical
          team: sre
        annotations:
          summary: "CRITICAL: Disk space < 10%"
          description: "Available: {{ $value | humanizePercentage }}. Service disruption imminent."

      # ====== CONTAINER ======
      - alert: ContainerOomKilled
        expr: increase(container_memory_failcnt[5m]) > 0
        for: 1m
        labels:
          severity: warning
          team: sre
        annotations:
          summary: "Container OOM-killed: {{ $labels.name }}"
          description: "Memory limit exceeded. Consider raising the limit or investigating leak."

      - alert: ContainerHighCpu
        expr: |
          sum(rate(container_cpu_usage_seconds_total{name!=""}[5m])) by (name)
          > 0.9
        for: 10m
        labels:
          severity: warning
          team: sre
        annotations:
          summary: "Container CPU > 90%: {{ $labels.name }}"
          description: "Sustained high CPU for 10 minutes."

      - alert: ContainerHighMemory
        expr: |
          container_memory_usage_bytes / container_spec_memory_limit_bytes > 0.85
        for: 10m
        labels:
          severity: warning
          team: sre
        annotations:
          summary: "Container memory > 85%: {{ $labels.name }}"
          description: "Sustained high memory for 10 minutes."

      # ====== SSL ======
      - alert: SslCertExpiringSoon
        expr: |
          probe_ssl_earliest_cert_expiry - time() < 86400 * 14
        for: 1h
        labels:
          severity: warning
          team: sre
        annotations:
          summary: "SSL cert expiring in < 14 days"
          description: "Days remaining: {{ $value }}"

      # ====== BACKUP ======
      - alert: BackupStale
        expr: time() - mastery_backup_last_success_timestamp > 86400 * 1.5
        for: 1h
        labels:
          severity: warning
          team: sre
        annotations:
          summary: "No successful backup in > 36 hours"
          description: "Backup may be failing. Check cron and Slack notifications."
```

### 3.1 Custom metrics required

The alert rules above reference several custom metrics that the backend must expose at `/metrics`. Verify they're present:

```bash
curl -sf https://app.masteryengine.com/metrics | grep -E 'mastery_beta|outbox_pending|workers_active|dead_letter_events_total'
```

If any are missing, add them to the Prometheus instrumentation in `backend/app/main.py` (or wherever the metrics middleware is defined). Required custom metrics:

| Metric | Type | Description |
|---|---|---|
| `mastery_beta_user_count` | gauge | Current registered user count |
| `mastery_beta_dau` | gauge | Daily active users (reset at midnight UTC) |
| `mastery_beta_open_feedback` | gauge | Count of feedback with status='open' |
| `outbox_pending` | gauge | Count of outbox events with consumed_at IS NULL |
| `workers_active` | gauge | Count of workers with last_seen_at in last 60s |
| `workers_dead` | gauge | Count of workers with last_seen_at older than 60s |
| `workers_jobs_processed_total` | counter | Total jobs processed (with worker_id label) |
| `workers_jobs_failed_total` | counter | Total jobs failed |
| `dead_letter_events_total` | counter | Total dead letter events created |
| `mastery_backup_last_success_timestamp` | gauge | Unix timestamp of last successful backup |

### 3.2 Apply the alert rules

```bash
# 1. Save the YAML above to infrastructure/monitoring/prometheus/alerts.yml
# 2. Restart Prometheus
docker compose -f docker-compose.prod.yml restart prometheus

# 3. Verify rules loaded
curl -sf http://localhost:9090/api/v1/rules | jq '.data.groups[] | {name: .name, rule_count: (.rules | length)}'
```

---

## 4. Alertmanager Deployment

### 4.1 Add Alertmanager to docker-compose.prod.yml

```yaml
  alertmanager:
    image: prom/alertmanager:v0.26.0
    restart: always
    ports:
      - "9093:9093"
    volumes:
      - ./infrastructure/monitoring/alertmanager/alertmanager.yml:/etc/alertmanager/alertmanager.yml:ro
      - alertmanager_data:/alertmanager
    networks: [default]
```

Add to volumes:
```yaml
volumes:
  ...
  alertmanager_data:
```

### 4.2 Create `infrastructure/monitoring/alertmanager/alertmanager.yml`

```yaml
global:
  resolve_timeout: 5m
  slack_api_url: '${SLACK_WEBHOOK}'

route:
  group_by: ['alertname', 'service']
  group_wait: 30s
  group_interval: 5m
  repeat_interval: 4h
  receiver: 'slack-default'
  routes:
    - matchers:
        - severity="critical"
      receiver: 'slack-critical'
      group_wait: 10s
      repeat_interval: 1h
    - matchers:
        - severity="info"
      receiver: 'slack-info'
      group_wait: 5m
      repeat_interval: 12h

receivers:
  - name: 'slack-default'
    slack_configs:
      - channel: '#beta-alerts'
        send_resolved: true
        title: '[{{ .Status | toUpper }}] {{ .CommonLabels.alertname }}'
        text: '{{ .CommonAnnotations.summary }}\n{{ .CommonAnnotations.description }}'

  - name: 'slack-critical'
    slack_configs:
      - channel: '#beta-alerts'
        send_resolved: true
        title: ':rotating_light: [CRITICAL] {{ .CommonLabels.alertname }}'
        text: '{{ .CommonAnnotations.summary }}\n{{ .CommonAnnotations.description }}\nRunbook: https://github.com/<org>/mastery-engine/blob/main/docs/runbooks/{{ .CommonLabels.alertname }}.md'

  - name: 'slack-info'
    slack_configs:
      - channel: '#beta-info'
        send_resolved: true
        title: '[INFO] {{ .CommonLabels.alertname }}'
        text: '{{ .CommonAnnotations.summary }}'

inhibit_rules:
  - source_matchers:
      - severity="critical"
    target_matchers:
      - severity="warning"
    equal: ['alertname', 'service']
```

### 4.3 Deploy and verify

```bash
docker compose --env-file .env.production -f docker-compose.prod.yml up -d alertmanager
sleep 10
curl -sf http://localhost:9093/-/healthy
# Expected: Alertmanager is Healthy.
```

---

## 5. Grafana Dashboard Usage

### 5.1 The "Production Overview" dashboard

The dashboard at `infrastructure/monitoring/grafana/dashboards/production-overview.json` contains 11 panels:

| Panel | What it shows | What to look for |
|---|---|---|
| Request Rate | HTTP requests per second | Daily pattern; sudden drop = frontend issue |
| Response Time p95 | 95th percentile latency | Should be < 200ms; > 500ms = investigate |
| Error Rate | % of 5xx responses | Should be < 0.1%; > 1% = bug |
| Active Sessions | Users currently studying | Matches DAU; sudden drop = backend issue |
| WebSocket Connections | Live WS connections | > 0 during active hours |
| Outbox Pending | Events awaiting processing | Should be 0 (or trending to 0) |
| Workers Active/Dead | Worker health | 1+ active, 0 dead |
| Cache Hit Rate | Redis cache effectiveness | > 80% |
| Questions/min | Engagement metric | > 0 during active hours |
| AI Latency | AI request p50 | Only relevant if AI enabled |

### 5.2 Additional dashboards to create (recommended)

Beyond the production overview, create these dashboards in Grafana:

#### 5.2.1 Database Health Dashboard
- Connection count over time
- Query rate
- Slow queries (top 10)
- Cache hit ratio (Postgres)
- Table sizes
- WAL generation rate
- Autovacuum activity

#### 5.2.2 Worker & Outbox Dashboard
- Outbox pending over time
- Outbox throughput (events/sec)
- Worker heartbeat timeline
- Jobs processed/failed rate
- Dead letter events over time
- Email delivery status breakdown

#### 5.2.3 Beta Engagement Dashboard
- DAU/WAU/MAU
- New registrations per day
- Sessions per user per day
- Average session duration
- Completion rate
- Questions per session
- Feedback submission rate
- Rating distribution

#### 5.2.4 Security Dashboard
- Failed login attempts over time
- Top IPs by failed logins
- Refresh token reuse detections
- MFA setup rate
- Active sessions
- Audit log event rate

### 5.3 Importing dashboards

If the production-overview dashboard doesn't auto-provision (it's wrapped under a top-level `"dashboard"` key):

1. Open Grafana → Dashboards → New → Import
2. Upload `infrastructure/monitoring/grafana/dashboards/production-overview.json`
3. Select Prometheus as the data source
4. Save

For new dashboards, build them in the Grafana UI, then export as JSON and commit to `infrastructure/monitoring/grafana/dashboards/`.

---

## 6. Log Strategy

### 6.1 Log levels and what they capture

| Level | When to use | Captured by |
|---|---|---|
| DEBUG | Verbose diagnostic info (SQL queries, cache hits) | Only when `APP_LOG_LEVEL=DEBUG` |
| INFO | Routine operations (login, session start, job processed) | Always |
| WARNING | Degraded behavior (rate limit hit, cache miss, retry scheduled) | Always |
| ERROR | Operation failed but request completed (5xx response) | Always + Sentry |
| CRITICAL | Service-level failure (cannot start, DB unreachable) | Always + Sentry + Alert |

### 6.2 Structured log format

All logs are JSON with these fields:

```json
{
  "timestamp": "2026-07-03T08:15:23.456Z",
  "level": "info",
  "logger": "app.presentation.api.v1.auth",
  "message": "User logged in",
  "correlation_id": "abc-123-def",
  "user_id": "uuid",
  "request_id": "uuid",
  "http_method": "POST",
  "http_path": "/api/v1/auth/login",
  "http_status": 200,
  "duration_ms": 145,
  "ip_address": "1.2.3.4",
  "user_agent": "Mozilla/5.0..."
}
```

### 6.3 Querying logs

Logs are in Docker json-file format. To query:

```bash
# All backend errors in the last hour
docker compose -f docker-compose.prod.yml logs backend --since 1h | \
  jq 'select(.level == "error" or .level == "critical")'

# Logs for a specific correlation ID
docker compose -f docker-compose.prod.yml logs backend --since 24h | \
  jq 'select(.correlation_id == "abc-123-def")'

# Slow requests (>500ms)
docker compose -f docker-compose.prod.yml logs backend --since 1h | \
  jq 'select(.duration_ms > 500) | {path: .http_path, duration: .duration_ms, correlation_id}'

# Failed login attempts
docker compose -f docker-compose.prod.yml logs backend --since 24h | \
  jq 'select(.message == "Login failed" or .http_path == "/api/v1/auth/login" and .http_status == 401)'
```

### 6.4 Log retention

| Service | Container limit | Total cap |
|---|---|---|
| Backend | 100 MB × 10 files | 1 GB |
| Worker | 100 MB × 10 files | 1 GB |
| Frontend | 50 MB × 5 files | 250 MB |
| Postgres | 100 MB × 10 (in PG data dir) | 1 GB |
| Nginx | 50 MB × 5 | 250 MB |
| Prometheus/Grafana | (managed internally) | — |

Total log storage: ~3.5 GB. Comfortably fits on a 40 GB disk.

### 6.5 Recommended: ship logs to a central service

For the Closed Beta, Docker-local logs are sufficient. For production scale, consider:
- **Loki** (Grafana stack) — lightweight, integrates with Grafana
- **Elasticsearch + Kibana** — heavyweight, full-text search
- **Datadog / New Relic** — SaaS, all-in-one

---

## 7. Sentry Configuration

### 7.1 Verify Sentry is receiving events

```bash
# Send a test event
docker compose -f docker-compose.prod.yml exec backend python -c "
import sentry_sdk
sentry_sdk.init(dsn='$SENTRY_DSN', environment='production')
sentry_sdk.capture_message('Post-launch monitoring verification')
print('captured — check Sentry UI within 30 seconds')
"
```

### 7.2 Recommended Sentry settings

In the Sentry project settings:

- **Release tracking**: set `release` to the git SHA in the SDK init:
  ```python
  sentry_sdk.init(dsn=..., release=os.environ.get('GIT_SHA', 'unknown'))
  ```
- **Environment**: `production` (set in init)
- **Sample rate**: `traces_sample_rate=0.1` (10% of transactions traced — enough for beta)
- **Before-send hook**: scrub PII (emails, passwords) from events:
  ```python
  def before_send(event, hint):
      for field in ['password', 'email', 'token', 'Authorization']:
          if field in event.get('request', {}).get('data', {}):
              event['request']['data'][field] = '[REDACTED]'
      return event
  sentry_sdk.init(dsn=..., before_send=before_send)
  ```
- **Inbound filters**: ignore `KeyboardInterrupt`, `SystemExit`
- **Alerts**: notify on new `fatal` events; weekly digest for `warning`

### 7.3 Sentry dashboards to monitor

- **Issues** — group by event fingerprint; sort by `Last Seen`
- **Releases** — track error rate per release; compare to previous release
- **Performance** — p50/p95/p99 transaction traces; identify slow endpoints
- **Crons** — if using Sentry Crons, monitor scheduled job execution

---

## 8. Operational KPIs (Weekly Review)

Every Monday, review these KPIs:

### 8.1 Availability
- **Uptime**: target 99.5% (beta) — 1.68 hours downtime/week allowed
- **MTTR** (Mean Time To Recovery): target < 30 minutes
- **MTBF** (Mean Time Between Failures): target > 7 days

### 8.2 Performance
- **p50 response time**: < 100ms
- **p95 response time**: < 200ms
- **p99 response time**: < 500ms
- **WebSocket connection setup time**: < 500ms

### 8.3 Reliability
- **Error rate (5xx)**: < 0.1%
- **Error rate (4xx)**: < 5% (mostly 401/403/404 expected)
- **Outbox backlog**: 0 sustained, < 100 transient
- **Dead letter events**: < 5/week
- **Email delivery rate**: > 95%

### 8.4 Engagement
- **DAU/MAU ratio**: > 30% (sticky)
- **Session completion rate**: > 60%
- **Average session duration**: 10–30 minutes
- **Feedback submissions per user per week**: > 0.5

### 8.5 Resource utilization
- **CPU average**: < 50%
- **Memory average**: < 60%
- **Disk usage**: < 70%
- **DB connections average**: < 50
- **Redis memory**: < 60% of maxmemory

### 8.6 Security
- **Failed login attempts**: < 100/day (per IP)
- **Security incidents**: 0 critical
- **Refresh token reuse detections**: 0
- **Audit log entries**: trending with DAU

---

## 9. On-Call Alert Triage Workflow

When an alert fires:

```
ALERT FIRES (Slack #beta-alerts)
       │
       ▼
┌─────────────────────────────────────────┐
│ 1. ACKNOWLEDGE in Slack (react 👀)      │
│    - This tells others you've seen it   │
└────────────────┬────────────────────────┘
                 │
                 ▼
┌─────────────────────────────────────────┐
│ 2. TRIAGE within 5 minutes              │
│    - Read the alert description         │
│    - Open the corresponding runbook     │
│    - Check Grafana for context          │
│    - Check Sentry for related errors    │
└────────────────┬────────────────────────┘
                 │
                 ▼
┌─────────────────────────────────────────┐
│ 3. CLASSIFY severity                    │
│    - If higher than labeled: upgrade    │
│    - If lower than labeled: note why    │
└────────────────┬────────────────────────┘
                 │
                 ▼
┌─────────────────────────────────────────┐
│ 4. MITIGATE                             │
│    - Apply the runbook fix              │
│    - Or rollback if faster              │
│    - Communicate in #beta-status        │
└────────────────┬────────────────────────┘
                 │
                 ▼
┌─────────────────────────────────────────┐
│ 5. RESOLVE                              │
│    - Verify alert clears in Prometheus  │
│    - Verify platform health (smoke test)│
│    - Post resolution in #beta-status    │
└────────────────┬────────────────────────┘
                 │
                 ▼
┌─────────────────────────────────────────┐
│ 6. POSTMORTEM (for SEV-1/2)             │
│    - Within 48 hours                    │
│    - Root cause, timeline, action items │
│    - File in runbooks/                  │
└─────────────────────────────────────────┘
```

---

## 10. Runbook Index (Per Alert)

Each alert should have a corresponding runbook. Create them in `docs/runbooks/`:

| Alert | Runbook | Quick action |
|---|---|---|
| `ServiceDown` | `runbooks/service-down.md` | `docker compose ps`, restart failing service |
| `BackendHealthCheckFailing` | `runbooks/backend-down.md` | Check backend logs, restart |
| `WorkerDown` | `runbooks/worker-down.md` | Restart worker, check heartbeat table |
| `FrontendDown` | `runbooks/frontend-down.md` | Rebuild frontend image |
| `HighErrorRate` | `runbooks/high-error-rate.md` | Check Sentry, identify endpoint, rollback if needed |
| `CriticalErrorRate` | `runbooks/critical-error-rate.md` | Same as above + page on-call |
| `HighP95Latency` | `runbooks/high-latency.md` | Check slow queries, cache hit rate |
| `PostgresDown` | `runbooks/postgres-down.md` | Check PG logs, restart, restore from backup if needed |
| `PostgresHighConnections` | `runbooks/pg-connections.md` | Find idle-in-transaction, terminate |
| `RedisDown` | `runbooks/redis-down.md` | Restart Redis, verify volume persisted |
| `RedisHighMemory` | `runbooks/redis-memory.md` | Raise maxmemory or investigate cache usage |
| `OutboxBacklog` | `runbooks/outbox-backlog.md` | Release stuck leases, restart worker |
| `DeadLetterAccumulating` | `runbooks/dead-letters.md` | Identify failing subscriber, fix, replay |
| `WorkerNoHeartbeat` | `runbooks/worker-heartbeat.md` | Restart worker, check logs |
| `CacheHitRateLow` | `runbooks/cache-hit-rate.md` | Check Redis memory, cache key patterns |
| `BetaFull` | `runbooks/beta-full.md` | Raise MAX_BETA_USERS or notify product |
| `DiskSpaceLow` | `runbooks/disk-space.md` | Clear logs, old backups; expand disk |
| `SslCertExpiringSoon` | `runbooks/ssl-renew.md` | `sudo certbot renew` |
| `BackupStale` | `runbooks/backup-stale.md` | Run backup manually, check cron |

Each runbook should follow the template:

```markdown
# Runbook: [Alert Name]

## Summary
[1-2 sentence description of what this alert means]

## Impact
[What users experience]

## Diagnosis
[Commands to investigate]

## Mitigation
[Steps to resolve]

## Verification
[How to confirm resolution]

## Prevention
[How to prevent recurrence]

## Escalation
[Who to contact if unresolved]
```

---

## 11. Monthly Operations Review

On the first Monday of each month, conduct a formal review:

### 11.1 Agenda (60 minutes)

1. **Availability review** (10 min)
   - Uptime percentage vs target
   - All incidents from the previous month
   - MTTR analysis

2. **Performance review** (10 min)
   - p50/p95/p99 trends
   - Slowest endpoints
   - Resource utilization trends

3. **Engagement review** (15 min)
   - DAU/WAU/MAU trends
   - Feedback themes
   - Feature flag impact analysis

4. **Capacity review** (10 min)
   - Are we ready to expand?
   - Resource headroom
   - Cost trends

5. **Action items** (15 min)
   - What to fix this month
   - What to monitor more closely
   - What to alert on (new rules)

### 11.2 Output

A short report (1–2 pages) committed to `docs/operations/monthly-reviews/YYYY-MM.md` covering:
- Month-over-month metric comparison
- Incidents with postmortem links
- Action items with owners and due dates
- Capacity recommendation (expand / hold / contract)

---

## 12. Long-Term Monitoring Roadmap (Post-Beta)

When transitioning from Closed Beta to General Availability:

### 12.1 Add
- **Distributed tracing** (OpenTelemetry + Jaeger or Tempo) — for cross-service request tracing
- **Real User Monitoring (RUM)** — Sentry RUM or Datadog RUM for frontend performance
- **Synthetic monitoring** — scheduled checks from multiple regions
- **Log aggregation** — Loki or ELK stack
- **Uptime monitoring** — external service (Pingdom, UptimeRobot) for independent verification
- **Crash reporting for mobile** (if mobile apps are built)

### 12.2 Improve
- **SLO tracking** — formal Service Level Objectives with error budgets
- **Capacity planning** — predictive alerts based on trends, not just thresholds
- **Anomaly detection** — ML-based alerting (Prometheus + ML adapter, or a SaaS)
- **Chaos engineering** — periodic fault injection to test resilience
- **Multi-region monitoring** — if deploying to multiple regions

### 12.3 Replace (when outgrowing beta)
- Docker Compose → Kubernetes (with Helm charts)
- Single-host Postgres → managed Postgres (RDS, Cloud SQL) or Patroni cluster
- Single-host Redis → Redis Cluster or managed Redis
- Local volume backups → cloud-managed backups (RDS automated backups, etc.)
- UFW firewall → cloud security groups + WAF

---

## Appendix A: Quick Health Check Command

Save as `/opt/mastery-engine/scripts/health-check.sh` (replacing the existing minimal version):

```bash
#!/usr/bin/env bash
set -u

cd /opt/mastery-engine
PASS=0; FAIL=0

check() {
  local name="$1" cmd="$2" pattern="$3"
  local result
  result=$(eval "$cmd" 2>&1)
  if echo "$result" | grep -qE "$pattern"; then
    echo "✅ $name"
    PASS=$((PASS+1))
  else
    echo "❌ $name"
    echo "   Expected pattern: $pattern"
    echo "   Got: $(echo "$result" | head -3)"
    FAIL=$((FAIL+1))
  fi
}

check "Backend liveness" \
  "curl -sf https://app.masteryengine.com/api/v1/health | jq -r .status" \
  "^healthy$"

check "Backend readiness" \
  "curl -sf https://app.masteryengine.com/api/v1/health/ready | jq -r .status" \
  "^ready$"

check "Postgres" \
  "docker compose -f docker-compose.prod.yml exec -T postgres pg_isready -U mastery" \
  "accepting connections"

check "Redis" \
  "docker compose -f docker-compose.prod.yml exec -T redis redis-cli -a \${REDIS_PASSWORD} ping" \
  "^PONG$"

check "Worker heartbeat" \
  "docker compose -f docker-compose.prod.yml exec -T postgres psql -U mastery -d mastery_engine -t -c \"SELECT count(*) FROM infrastructure.worker_heartbeats WHERE last_seen_at > now() - interval '1 minute'\"" \
  "^[1-9]"

check "Outbox pending" \
  "docker compose -f docker-compose.prod.yml exec -T postgres psql -U mastery -d mastery_engine -t -c \"SELECT count(*) FROM infrastructure.outbox_events WHERE consumed_at IS NULL AND created_at > now() - interval '5 minutes'\"" \
  "^0$"

check "Dead letters (unresolved)" \
  "docker compose -f docker-compose.prod.yml exec -T postgres psql -U mastery -d mastery_engine -t -c \"SELECT count(*) FROM infrastructure.dead_letter_events WHERE resolved_at IS NULL\"" \
  "^0$"

check "Beta status" \
  "curl -sf https://app.masteryengine.com/api/v1/beta/status | jq -r .closed_beta_enabled" \
  "^true$"

check "Disk space (/)" \
  "df --output=pcent / | tail -1 | tr -d ' '" \
  "^[0-7][0-9]%$"

check "SSL cert expiry (days)" \
  "echo \| openssl s_client -connect app.masteryengine.com:443 -servername app.masteryengine.com 2>/dev/null \| openssl x509 -noout -enddate \| cut -d= -f2 \| xargs -I{} date -d {} +%s \| xargs -I{} expr \( {} - \$(date +%s) \) / 86400" \
  "^[3-9][0-9]$|^[1-9][0-9]{2,}$"

echo ""
echo "================================"
echo "  PASS: $PASS    FAIL: $FAIL"
echo "================================"

[ "$FAIL" -eq 0 ]
```

Make executable and run via cron every 5 minutes:

```bash
chmod +x /opt/mastery-engine/scripts/health-check.sh

# Cron: every 5 min, post to Slack if any check fails
*/5 * * * * /opt/mastery-engine/scripts/health-check.sh > /tmp/health-check.log 2>&1 || \
  curl -s -X POST -H 'Content-Type: application/json' \
    --data "{\"text\":\"⚠️ Health check failed. See /tmp/health-check.log on the server.\"}" \
    $SLACK_WEBHOOK
```

---

## Appendix B: Glossary

| Term | Definition |
|---|---|
| **DAU** | Daily Active Users — unique users who performed at least one action in 24h |
| **WAU** | Weekly Active Users |
| **MAU** | Monthly Active Users |
| **MTTR** | Mean Time To Recovery — average time from incident detection to resolution |
| **MTBF** | Mean Time Between Failures |
| **RPO** | Recovery Point Objective — maximum acceptable data loss (current: 24h) |
| **RTO** | Recovery Time Objective — maximum acceptable downtime (target: 2h) |
| **SLI** | Service Level Indicator — a metric (e.g. p95 latency) |
| **SLO** | Service Level Objective — a target for an SLI (e.g. p95 < 200ms) |
| **SLA** | Service Level Agreement — a contract with users (not applicable for beta) |
| **SEV-1** | Severity 1 — platform down, all users affected |
| **SEV-2** | Severity 2 — major feature broken for > 50% of users |
| **SEV-3** | Severity 3 — minor feature broken or single-user issue |
| **SEV-4** | Severity 4 — cosmetic or low-impact |
| **Outbox** | Pattern for reliable event publishing via a DB-backed queue |
| **Dead letter** | An event that exhausted retries and was moved aside for investigation |
| **Heartbeat** | Periodic "I'm alive" signal from a worker |
| **Lease** | A lock on a resource (e.g. outbox event) with an expiry time |
| **Correlation ID** | A UUID propagated through logs for a single request flow |

---

**End of post-launch monitoring.** This completes the 8-document deployment guide set. Refer back to the other documents as needed:

- `deployment-checklist.md` — Master checklist
- `environment-reference.md` — Env var reference
- `production-launch.md` — Step-by-step launch
- `beta-launch-guide.md` — Admin operations
- `operations-checklist.md` — Daily/weekly ops
- `troubleshooting.md` — Issue resolution
- `deployment-diagrams.md` — Visual architecture
- `post-launch-monitoring.md` — This document
