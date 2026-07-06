export const metadata = {
  title: 'Scaling — MasteryOS',
  description: 'Horizontal and vertical scaling strategies for MasteryOS.',
}

export default function ScalingPage() {
  return (
    <div className="prose prose-neutral max-w-none dark:prose-invert">
      <h1>Scaling Guide</h1>
      <p className="text-lg text-muted-foreground">
        MasteryOS is designed as a modular monolith that can scale horizontally.
      </p>

      <h2>Vertical Scaling</h2>
      <p>For small deployments (Closed Beta, &lt;100 users):</p>
      <ul>
        <li><strong>Backend:</strong> 1 instance, 1 vCPU, 512MB RAM</li>
        <li><strong>Worker:</strong> 1 instance, 1 vCPU, 512MB RAM</li>
        <li><strong>PostgreSQL:</strong> 1 vCPU, 1GB RAM, 10GB disk</li>
        <li><strong>Redis:</strong> 256MB</li>
      </ul>

      <h2>Horizontal Scaling</h2>
      <p>For larger deployments, scale each component independently:</p>

      <h3>Backend</h3>
      <ul>
        <li>Stateless — safe to run multiple replicas</li>
        <li>JWT validation works across replicas (shared public key)</li>
        <li>Rate limiting requires Redis (distributed token bucket)</li>
        <li>Recommended: 2+ replicas for high availability</li>
      </ul>

      <h3>Worker</h3>
      <ul>
        <li>Multiple workers share outbox processing via <code>FOR UPDATE SKIP LOCKED</code></li>
        <li>Scale workers based on outbox depth metric</li>
        <li>Recommended: 1 worker per 50 concurrent users</li>
      </ul>

      <h3>Database</h3>
      <ul>
        <li>Read replicas for analytics queries</li>
        <li>Connection pooling via PgBouncer (recommended at scale)</li>
        <li>Partition large tables (attempts, events) by date</li>
      </ul>

      <h3>Redis</h3>
      <ul>
        <li>Redis Cluster for high availability</li>
        <li>Cache eviction policy: <code>allkeys-lru</code></li>
      </ul>

      <h2>Performance Targets</h2>
      <table className="w-full text-sm">
        <thead>
          <tr className="border-b">
            <th className="text-left py-2">Metric</th>
            <th className="text-left py-2">Target</th>
          </tr>
        </thead>
        <tbody>
          <tr className="border-b"><td>API latency (p50)</td><td>&lt;100ms</td></tr>
          <tr className="border-b"><td>API latency (p99)</td><td>&lt;500ms</td></tr>
          <tr className="border-b"><td>Outbox dispatch latency</td><td>&lt;5s</td></tr>
          <tr className="border-b"><td>Cache hit rate</td><td>&gt;80%</td></tr>
          <tr><td>Uptime</td><td>99.9%</td></tr>
        </tbody>
      </table>
    </div>
  )
}
