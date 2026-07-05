export const metadata = {
  title: 'Monitoring — MasteryOS',
  description: 'Prometheus metrics, Grafana dashboards, and Alertmanager configuration for MasteryOS.',
}

export default function MonitoringPage() {
  return (
    <div className="prose prose-neutral max-w-none dark:prose-invert">
      <h1>Monitoring</h1>
      <p className="text-lg text-muted-foreground">
        MasteryOS includes comprehensive observability via Prometheus, Grafana, and Alertmanager.
      </p>

      <h2>Prometheus</h2>
      <p>Prometheus scrapes metrics from the backend at <code>/metrics</code>.</p>
      <pre className="bg-muted p-4 rounded-lg text-sm">{`# prometheus.yml
scrape_configs:
  - job_name: 'masteryos-backend'
    metrics_path: /metrics
    static_configs:
      - targets: ['backend:8000']`}</pre>

      <h2>Key Metrics</h2>
      <ul>
        <li><code>http_requests_total</code> — Request count by method/path/status</li>
        <li><code>http_request_duration_seconds</code> — Latency histogram</li>
        <li><code>db_connection_pool_size</code> — Active DB connections</li>
        <li><code>redis_operations_total</code> — Redis cache hits/misses</li>
        <li><code>outbox_events_pending</code> — Outbox queue depth</li>
        <li><code>worker_heartbeats_active</code> — Worker count</li>
        <li><code>ai_requests_total</code> — AI provider usage</li>
      </ul>

      <h2>Grafana Dashboards</h2>
      <p>Pre-provisioned dashboard at <code>infrastructure/monitoring/grafana/dashboards/</code>:</p>
      <ul>
        <li>Production Overview — Request rate, error rate, latency, DB/Redis health</li>
        <li>Worker Health — Outbox depth, dispatch latency, dead letters</li>
        <li>AI Platform — Provider usage, cost, latency, safety rejections</li>
      </ul>

      <h2>Alertmanager</h2>
      <p>Alerts are routed to Slack:</p>
      <ul>
        <li><strong>Critical:</strong> High error rate, DB down, worker crash</li>
        <li><strong>Warning:</strong> High latency, queue depth, disk usage</li>
        <li><strong>Info:</strong> Deployments, scaling events</li>
      </ul>

      <h2>Sentry</h2>
      <p>Error tracking via Sentry. Configure with <code>SENTRY_DSN</code> environment variable.</p>
    </div>
  )
}
