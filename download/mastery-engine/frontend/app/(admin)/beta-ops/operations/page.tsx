'use client'

import * as React from 'react'
import {
  Activity,
  Server,
  ListChecks,
  ListTree,
  Mail,
  Bell,
  Database,
  HardDrive,
  Zap,
  Gauge,
  Cpu,
  DollarSign,
  RefreshCw,
  CircleAlert,
  Wrench,
} from 'lucide-react'

import { useOperationalHealth } from '@/hooks/use-beta-ops'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Skeleton } from '@/components/ui/skeleton'
import { Progress } from '@/components/ui/progress'
import { ErrorState } from '@/components/ui/error-state'
import { cn } from '@/lib/cn'
import { formatNumber, formatRelativeTime } from '@/lib/format'

interface HealthCardProps {
  title: string
  icon: React.ComponentType<{ className?: string }>
  status?: 'healthy' | 'degraded' | 'down' | string
  children: React.ReactNode
  description?: string
}

function statusFromValue(v: unknown): 'healthy' | 'degraded' | 'down' | undefined {
  if (typeof v !== 'string') return undefined
  const s = v.toLowerCase()
  if (s === 'healthy' || s === 'ok' || s === 'green' || s === 'up') return 'healthy'
  if (s === 'degraded' || s === 'warning' || s === 'amber' || s === 'slow') return 'degraded'
  if (s === 'down' || s === 'critical' || s === 'red' || s === 'error') return 'down'
  return undefined
}

function HealthDot({ status }: { status?: 'healthy' | 'degraded' | 'down' }) {
  const color =
    status === 'healthy'
      ? 'bg-success'
      : status === 'degraded'
        ? 'bg-warning'
        : status === 'down'
          ? 'bg-destructive'
          : 'bg-muted-foreground'
  return (
    <span
      className={cn('inline-block h-2.5 w-2.5 rounded-full', color)}
      aria-label={status ?? 'unknown'}
      role="img"
    />
  )
}

function HealthCard({ title, icon: Icon, status, children, description }: HealthCardProps) {
  return (
    <Card>
      <CardHeader className="pb-2">
        <div className="flex items-center justify-between">
          <CardTitle className="flex items-center gap-2 text-sm">
            <Icon className="h-4 w-4 text-muted-foreground" aria-hidden="true" />
            {title}
          </CardTitle>
          <HealthDot status={status as 'healthy' | 'degraded' | 'down' | undefined} />
        </div>
        {description && <CardDescription className="text-xs">{description}</CardDescription>}
      </CardHeader>
      <CardContent className="text-sm">{children}</CardContent>
    </Card>
  )
}

function num(v: unknown, fallback = 0): number {
  if (typeof v === 'number') return v
  if (typeof v === 'string') {
    const n = Number(v)
    return Number.isFinite(n) ? n : fallback
  }
  return fallback
}

function str(v: unknown, fallback = '—'): string {
  if (typeof v === 'string') return v
  if (typeof v === 'number') return String(v)
  return fallback
}

interface GenericRow {
  [key: string]: unknown
}

function OperationsSkeleton() {
  return (
    <div className="space-y-6" role="status" aria-label="Loading operations health">
      <Skeleton className="h-16 w-full" />
      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
        {Array.from({ length: 6 }).map((_, i) => (
          <Skeleton key={i} className="h-32 w-full" />
        ))}
      </div>
    </div>
  )
}

export default function OperationsPage() {
  const { data, isLoading, isError, error, refetch, isFetching } =
    useOperationalHealth()

  if (isLoading) return <OperationsSkeleton />
  if (isError || !data) {
    return (
      <ErrorState
        title="Failed to load operational health"
        description="We couldn't fetch the operations health data."
        error={error as Error | undefined}
        onRetry={() => refetch()}
      />
    )
  }

  const platform = (data.platform_health ?? {}) as GenericRow
  const workers = (data.worker_health ?? {}) as GenericRow
  const backgroundJobs = (data.background_jobs ?? {}) as GenericRow
  const queue = (data.queue_status ?? {}) as Record<string, number>
  const emailDelivery = (data.email_delivery ?? {}) as Record<string, number>
  const notificationDelivery = (data.notification_delivery ?? {}) as Record<string, number>
  const database = (data.database_health ?? {}) as GenericRow
  const redis = (data.redis_health ?? {}) as GenericRow
  const storage = (data.storage_usage ?? {}) as GenericRow
  const apiLatency = (data.api_latency ?? {}) as GenericRow
  const aiUsage = (data.ai_usage ?? {}) as GenericRow
  const costMetrics = (data.cost_metrics ?? {}) as GenericRow

  const platformStatus = statusFromValue(platform.status) ?? statusFromValue(platform.health)
  const workersStatus = statusFromValue(workers.status) ?? statusFromValue(workers.health)
  const jobsStatus = statusFromValue(backgroundJobs.status)
  const databaseStatus = statusFromValue(database.status) ?? statusFromValue(database.health)
  const redisStatus = statusFromValue(redis.status) ?? statusFromValue(redis.health)
  const storageStatus = statusFromValue(storage.status)
  const apiStatus = statusFromValue(apiLatency.status)

  // Email & notification delivery are healthy if delivery_rate is high
  const emailRate = num(emailDelivery.delivery_rate ?? emailDelivery.success_rate)
  const notifRate = num(notificationDelivery.delivery_rate ?? notificationDelivery.success_rate)
  const emailStatus =
    emailRate === 0 ? undefined : emailRate >= 0.95 ? 'healthy' : emailRate >= 0.8 ? 'degraded' : 'down'
  const notifStatus =
    notifRate === 0 ? undefined : notifRate >= 0.95 ? 'healthy' : notifRate >= 0.8 ? 'degraded' : 'down'

  // Worker list
  const workerList = (workers.workers ?? workers.list ?? []) as GenericRow[]

  // Storage percentage
  const storageUsed = num(storage.used ?? storage.used_bytes)
  const storageTotal = num(storage.total ?? storage.total_bytes)
  const storagePct = storageTotal > 0 ? (storageUsed / storageTotal) * 100 : num(storage.percentage ?? storage.usage_pct)
  const storageDisplayStatus =
    storagePct >= 90 ? 'down' : storagePct >= 75 ? 'degraded' : 'healthy'

  // AI usage / cost — typically informational, assume healthy
  const aiStatus: 'healthy' | 'degraded' | 'down' | undefined = 'healthy'
  const costStatus: 'healthy' | 'degraded' | 'down' | undefined = 'healthy'

  const bannerStatus = platformStatus ?? 'healthy'
  const bannerVariant =
    bannerStatus === 'healthy'
      ? 'success'
      : bannerStatus === 'degraded'
        ? 'warning'
        : 'destructive'

  return (
    <div className="space-y-6">
      <header className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h1 className="flex items-center gap-2 text-2xl font-bold tracking-tight">
            <Wrench className="h-6 w-6" aria-hidden="true" />
            Operations
          </h1>
          <p className="text-sm text-muted-foreground">
            Live platform health — auto-refreshing every 30 seconds.
          </p>
        </div>
        <div className="flex items-center gap-3">
          <div
            className="flex items-center gap-2 text-xs text-muted-foreground"
            role="status"
            aria-live="polite"
          >
            <span
              className={cn(
                'inline-block h-2 w-2 rounded-full',
                isFetching ? 'animate-pulse bg-warning' : 'bg-success',
              )}
              aria-hidden="true"
            />
            {isFetching ? 'Refreshing…' : 'Auto-refresh active'}
          </div>
          <Button
            variant="outline"
            size="sm"
            onClick={() => refetch()}
            aria-label="Refresh operations"
          >
            <RefreshCw className="h-4 w-4" aria-hidden="true" />
          </Button>
        </div>
      </header>

      <Card
        role="status"
        className={cn(
          'border-l-4',
          bannerStatus === 'healthy' && 'border-l-success',
          bannerStatus === 'degraded' && 'border-l-warning',
          bannerStatus === 'down' && 'border-l-destructive',
        )}
      >
        <CardContent className="flex items-center gap-3 p-4">
          {bannerStatus === 'healthy' ? (
            <Activity className="h-5 w-5 text-success" aria-hidden="true" />
          ) : (
            <CircleAlert
              className={cn(
                'h-5 w-5',
                bannerStatus === 'degraded' ? 'text-warning' : 'text-destructive',
              )}
              aria-hidden="true"
            />
          )}
          <div className="flex-1">
            <p className="text-sm font-semibold">
              Platform Status:{' '}
              <span className="capitalize">{bannerStatus}</span>
            </p>
            <p className="text-xs text-muted-foreground">
              {bannerStatus === 'healthy'
                ? 'All systems operating normally.'
                : bannerStatus === 'degraded'
                  ? 'Some systems are degraded — investigate below.'
                  : 'Critical issue detected — immediate action required.'}
            </p>
          </div>
          <Badge variant={bannerVariant as 'success' | 'warning' | 'destructive'} className="capitalize">
            {bannerStatus}
          </Badge>
        </CardContent>
      </Card>

      <section
        aria-label="Operational health cards"
        className="grid gap-4 md:grid-cols-2 lg:grid-cols-3"
      >
        <HealthCard
          title="Platform Health"
          icon={Activity}
          status={platformStatus}
          description={str(platform.message ?? platform.description)}
        >
          <div className="space-y-1">
            <div className="flex justify-between">
              <span className="text-muted-foreground">Uptime</span>
              <span className="font-medium">
                {num(platform.uptime_pct ?? platform.uptime, 0).toFixed(2)}%
              </span>
            </div>
            <div className="flex justify-between">
              <span className="text-muted-foreground">Version</span>
              <span className="font-medium">{str(platform.version, '—')}</span>
            </div>
          </div>
        </HealthCard>

        <HealthCard
          title="Worker Health"
          icon={Server}
          status={workersStatus}
          description={`${num(workers.active, 0)} active · ${num(workers.dead, 0)} dead`}
        >
          {workerList.length === 0 ? (
            <p className="text-xs text-muted-foreground">No worker details available.</p>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-left text-xs">
                <thead>
                  <tr className="text-muted-foreground">
                    <th scope="col" className="px-1 py-1 font-semibold">Worker</th>
                    <th scope="col" className="px-1 py-1 font-semibold">Status</th>
                    <th scope="col" className="px-1 py-1 text-right font-semibold">Jobs</th>
                  </tr>
                </thead>
                <tbody>
                  {workerList.slice(0, 5).map((w, i) => (
                    <tr key={i} className="border-t">
                      <td className="px-1 py-1 font-mono">{str(w.worker_id).slice(0, 12)}</td>
                      <td className="px-1 py-1 capitalize">{str(w.status)}</td>
                      <td className="px-1 py-1 text-right tabular-nums">
                        {formatNumber(num(w.jobs_processed))}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
              {workerList.length > 5 && (
                <p className="mt-2 text-xs text-muted-foreground">
                  +{workerList.length - 5} more workers…
                </p>
              )}
            </div>
          )}
        </HealthCard>

        <HealthCard
          title="Background Jobs"
          icon={ListChecks}
          status={jobsStatus}
          description="Active, paused, and failing job counts"
        >
          <div className="grid grid-cols-3 gap-2 text-center">
            <div>
              <p className="text-xs text-muted-foreground">Active</p>
              <p className="text-lg font-bold text-success">
                {formatNumber(num(backgroundJobs.active))}
              </p>
            </div>
            <div>
              <p className="text-xs text-muted-foreground">Paused</p>
              <p className="text-lg font-bold text-warning">
                {formatNumber(num(backgroundJobs.paused))}
              </p>
            </div>
            <div>
              <p className="text-xs text-muted-foreground">Failing</p>
              <p className="text-lg font-bold text-destructive">
                {formatNumber(num(backgroundJobs.failing ?? backgroundJobs.failed))}
              </p>
            </div>
          </div>
        </HealthCard>

        <HealthCard
          title="Queue Status"
          icon={ListTree}
          description="Pending items per queue"
        >
          {Object.keys(queue).length === 0 ? (
            <p className="text-xs text-muted-foreground">No queue data.</p>
          ) : (
            <ul className="space-y-1">
              {Object.entries(queue).slice(0, 6).map(([k, v]) => (
                <li key={k} className="flex justify-between">
                  <span className="text-muted-foreground capitalize">{k.replace(/_/g, ' ')}</span>
                  <span className="font-medium tabular-nums">{formatNumber(num(v))}</span>
                </li>
              ))}
            </ul>
          )}
        </HealthCard>

        <HealthCard
          title="Email Delivery"
          icon={Mail}
          status={emailStatus}
          description="Delivery success rate"
        >
          <div className="space-y-1">
            <div className="flex justify-between">
              <span className="text-muted-foreground">Sent</span>
              <span className="font-medium tabular-nums">
                {formatNumber(num(emailDelivery.sent))}
              </span>
            </div>
            <div className="flex justify-between">
              <span className="text-muted-foreground">Failed</span>
              <span className="font-medium tabular-nums text-destructive">
                {formatNumber(num(emailDelivery.failed))}
              </span>
            </div>
            <div className="flex justify-between">
              <span className="text-muted-foreground">Bounced</span>
              <span className="font-medium tabular-nums text-warning">
                {formatNumber(num(emailDelivery.bounced))}
              </span>
            </div>
          </div>
        </HealthCard>

        <HealthCard
          title="Notification Delivery"
          icon={Bell}
          status={notifStatus}
          description="In-app notification delivery"
        >
          <div className="space-y-1">
            <div className="flex justify-between">
              <span className="text-muted-foreground">Queued</span>
              <span className="font-medium tabular-nums">
                {formatNumber(num(notificationDelivery.queued))}
              </span>
            </div>
            <div className="flex justify-between">
              <span className="text-muted-foreground">Delivered</span>
              <span className="font-medium tabular-nums text-success">
                {formatNumber(num(notificationDelivery.delivered))}
              </span>
            </div>
            <div className="flex justify-between">
              <span className="text-muted-foreground">Failed</span>
              <span className="font-medium tabular-nums text-destructive">
                {formatNumber(num(notificationDelivery.failed))}
              </span>
            </div>
          </div>
        </HealthCard>

        <HealthCard
          title="Database Health"
          icon={Database}
          status={databaseStatus}
          description={str(database.message)}
        >
          <div className="space-y-1">
            <div className="flex justify-between">
              <span className="text-muted-foreground">Connections</span>
              <span className="font-medium tabular-nums">
                {formatNumber(num(database.connections ?? database.active_connections))}
              </span>
            </div>
            <div className="flex justify-between">
              <span className="text-muted-foreground">Query latency</span>
              <span className="font-medium">
                {num(database.avg_query_ms).toFixed(0)} ms
              </span>
            </div>
          </div>
        </HealthCard>

        <HealthCard
          title="Redis Health"
          icon={Cpu}
          status={redisStatus}
          description={str(redis.message)}
        >
          <div className="space-y-1">
            <div className="flex justify-between">
              <span className="text-muted-foreground">Connections</span>
              <span className="font-medium tabular-nums">
                {formatNumber(num(redis.connections ?? redis.connected_clients))}
              </span>
            </div>
            <div className="flex justify-between">
              <span className="text-muted-foreground">Memory</span>
              <span className="font-medium">
                {num(redis.memory_pct ?? redis.used_memory_mb).toFixed(0)}
                {redis.memory_pct ? '%' : ' MB'}
              </span>
            </div>
          </div>
        </HealthCard>

        <HealthCard
          title="Storage Usage"
          icon={HardDrive}
          status={storageDisplayStatus}
          description={`${storagePct.toFixed(1)}% used`}
        >
          <div className="space-y-2">
            <Progress
              value={storagePct}
              indicatorClassName={
                storagePct >= 90
                  ? 'bg-destructive'
                  : storagePct >= 75
                    ? 'bg-warning'
                    : 'bg-success'
              }
            />
            <div className="flex justify-between text-xs text-muted-foreground">
              <span>{(storageUsed / 1e9).toFixed(1)} GB used</span>
              <span>{(storageTotal / 1e9).toFixed(1)} GB total</span>
            </div>
          </div>
        </HealthCard>

        <HealthCard
          title="API Latency"
          icon={Zap}
          status={apiStatus}
          description="P95 latency across endpoints"
        >
          <div className="space-y-1">
            <div className="flex justify-between">
              <span className="text-muted-foreground">P50</span>
              <span className="font-medium">
                {num(apiLatency.p50 ?? apiLatency.median_ms).toFixed(0)} ms
              </span>
            </div>
            <div className="flex justify-between">
              <span className="text-muted-foreground">P95</span>
              <span className="font-medium">
                {num(apiLatency.p95).toFixed(0)} ms
              </span>
            </div>
            <div className="flex justify-between">
              <span className="text-muted-foreground">P99</span>
              <span className="font-medium">
                {num(apiLatency.p99).toFixed(0)} ms
              </span>
            </div>
          </div>
        </HealthCard>

        <HealthCard
          title="AI Usage"
          icon={Gauge}
          status={aiStatus}
          description="Model invocations and tokens"
        >
          <div className="space-y-1">
            <div className="flex justify-between">
              <span className="text-muted-foreground">Requests</span>
              <span className="font-medium tabular-nums">
                {formatNumber(num(aiUsage.requests ?? aiUsage.total_requests))}
              </span>
            </div>
            <div className="flex justify-between">
              <span className="text-muted-foreground">Tokens</span>
              <span className="font-medium tabular-nums">
                {formatNumber(num(aiUsage.tokens ?? aiUsage.total_tokens))}
              </span>
            </div>
            <div className="flex justify-between">
              <span className="text-muted-foreground">Errors</span>
              <span className="font-medium tabular-nums text-destructive">
                {formatNumber(num(aiUsage.errors ?? aiUsage.error_count))}
              </span>
            </div>
          </div>
        </HealthCard>

        <HealthCard
          title="Cost Metrics"
          icon={DollarSign}
          status={costStatus}
          description="Estimated spend this period"
        >
          <div className="space-y-1">
            <div className="flex justify-between">
              <span className="text-muted-foreground">Total</span>
              <span className="font-medium">
                ${num(costMetrics.total_cost ?? costMetrics.total).toFixed(2)}
              </span>
            </div>
            <div className="flex justify-between">
              <span className="text-muted-foreground">AI</span>
              <span className="font-medium">
                ${num(costMetrics.ai_cost ?? costMetrics.ai).toFixed(2)}
              </span>
            </div>
            <div className="flex justify-between">
              <span className="text-muted-foreground">Infra</span>
              <span className="font-medium">
                ${num(costMetrics.infra_cost ?? costMetrics.infra).toFixed(2)}
              </span>
            </div>
          </div>
        </HealthCard>
      </section>

      {workerList.length > 0 && (
        <Card>
          <CardHeader>
            <CardTitle className="text-base">Workers Detail</CardTitle>
            <CardDescription>
              All registered workers with their current status and throughput.
            </CardDescription>
          </CardHeader>
          <CardContent>
            <div className="overflow-x-auto">
              <table className="w-full text-left text-sm">
                <thead>
                  <tr className="border-b text-xs uppercase tracking-wider text-muted-foreground">
                    <th scope="col" className="px-3 py-2 font-semibold">Worker ID</th>
                    <th scope="col" className="px-3 py-2 font-semibold">Status</th>
                    <th scope="col" className="px-3 py-2 font-semibold">Last seen</th>
                    <th scope="col" className="px-3 py-2 text-right font-semibold">Processed</th>
                    <th scope="col" className="px-3 py-2 text-right font-semibold">Failed</th>
                    <th scope="col" className="px-3 py-2 font-semibold">Current job</th>
                  </tr>
                </thead>
                <tbody>
                  {workerList.map((w, i) => (
                    <tr key={i} className="border-b last:border-0">
                      <td className="px-3 py-2 font-mono text-xs">{str(w.worker_id)}</td>
                      <td className="px-3 py-2">
                        <Badge
                          variant={
                            str(w.status) === 'running'
                              ? 'success'
                              : str(w.status) === 'crashed'
                                ? 'destructive'
                                : 'secondary'
                          }
                          className="capitalize"
                        >
                          {str(w.status)}
                        </Badge>
                      </td>
                      <td className="px-3 py-2 text-xs text-muted-foreground">
                        {w.last_seen ? formatRelativeTime(str(w.last_seen)) : '—'}
                      </td>
                      <td className="px-3 py-2 text-right tabular-nums">
                        {formatNumber(num(w.jobs_processed))}
                      </td>
                      <td className="px-3 py-2 text-right tabular-nums text-destructive">
                        {formatNumber(num(w.jobs_failed))}
                      </td>
                      <td className="px-3 py-2 text-xs">{str(w.current_job)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  )
}
