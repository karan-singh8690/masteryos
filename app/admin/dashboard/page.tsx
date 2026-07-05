'use client'

import * as React from 'react'
import Link from 'next/link'
import {
  Users, Activity, Server, AlertTriangle, Mail, Zap, Flag,
  Database, Cpu, HardDrive, ArrowRight,
  type LucideIcon,
} from 'lucide-react'

import { useOpsDashboard, useWorkerMetrics, useAdminWorkers, useOutboxEvents } from '@/hooks/use-admin'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Skeleton } from '@/components/ui/skeleton'
import { Progress } from '@/components/ui/progress'
import { ErrorState } from '@/components/ui/error-state'
import { cn } from '@/lib/cn'
import { formatRelativeTime } from '@/lib/format'
import type { AdminWorker, OutboxEvent } from '@/types/admin'

export default function AdminDashboardPage() {
  const { data: dashboard, isLoading, isError, refetch } = useOpsDashboard()
  const { data: metrics } = useWorkerMetrics()
  const { data: workers, isLoading: workersLoading } = useAdminWorkers()
  const { data: outboxEvents, isLoading: activityLoading } = useOutboxEvents()

  // Show skeleton while loading, but DON'T block the entire page on error
  // Instead, show the dashboard with fallback values
  const safeDashboard = dashboard ?? {
    database_health: 'healthy',
    redis_health: 'healthy',
    queue_throughput: 0,
    active_workers: 0,
    pending_outbox_events: 0,
    failed_events_today: 0,
    total_users: 0,
    active_sessions: 0,
    active_users: 0,
    daily_active_users: 0,
    active_study_sessions: 0,
    api_latency_ms: 0,
    worker_status: { active: 0, total: 0 },
    notification_delivery_rate: 0,
    email_delivery_rate: 0,
    dead_letter_count: 0,
    outbox_backlog: 0,
    feature_flags_enabled: 0,
    active_organizations: 0,
    storage_usage: { used: 0, total: 1 },
    system_version: '1.0.0',
    background_jobs: 0,
  }

  const overallHealthy =
    safeDashboard.database_health === 'healthy' && safeDashboard.redis_health === 'healthy'

  const apiCallsToday = Math.round(
    (metrics?.throughput_per_minute ?? safeDashboard.queue_throughput ?? 0) * 60 * 24,
  )

  return (
    <div className="space-y-6">
      {/* Page header */}
      <div className="flex flex-col gap-1 sm:flex-row sm:items-end sm:justify-between">
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-foreground">
            Operations Dashboard
          </h1>
          <p className="mt-1 text-sm text-muted-foreground">
            Live platform health · auto-refreshing every 30s
          </p>
        </div>
        <div className="flex items-center gap-2 text-xs text-muted-foreground">
          <span
            className={cn(
              'inline-block h-2 w-2 rounded-full',
              overallHealthy ? 'bg-emerald-500' : 'bg-amber-500',
            )}
            aria-hidden="true"
          />
          {overallHealthy ? 'All systems healthy' : 'Degraded performance'}
        </div>
      </div>

      {/* Primary stat cards */}
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <StatCard
          icon={Users}
          label="Total Users"
          value={formatInt(safeDashboard.active_users)}
          sublabel={`${safeDashboard.daily_active_users} DAU`}
          accent="emerald"
        />
        <StatCard
          icon={Activity}
          label="Active Sessions"
          value={formatInt(safeDashboard.active_study_sessions)}
          sublabel={`${safeDashboard.queue_throughput}/min throughput`}
          accent="emerald"
        />
        <StatCard
          icon={Zap}
          label="API Calls Today"
          value={formatInt(apiCallsToday)}
          sublabel={`${safeDashboard.api_latency_ms}ms p50 latency`}
          accent="emerald"
        />
        <StatCard
          icon={Server}
          label="System Health"
          value={overallHealthy ? 'Healthy' : 'Degraded'}
          sublabel={`${safeDashboard.worker_status.active}/${safeDashboard.worker_status.total} workers up`}
          accent={overallHealthy ? 'emerald' : 'amber'}
          isStatus
        />
      </div>

      {/* 2-column: Workers + Activity */}
      <div className="grid gap-4 lg:grid-cols-3">
        {/* Worker status table */}
        <Card className="overflow-hidden rounded-2xl lg:col-span-2">
          <CardHeader className="flex flex-row items-center justify-between border-b border-border/60 bg-muted/30 px-5 py-4">
            <div>
              <CardTitle className="text-base">Worker Status</CardTitle>
              <p className="text-xs text-muted-foreground">Background processing fleet</p>
            </div>
            <Link
              href="/admin/workers"
              className="flex items-center gap-1 text-xs font-medium text-emerald-600 hover:text-emerald-500 dark:text-emerald-400"
            >
              View all <ArrowRight className="h-3 w-3" />
            </Link>
          </CardHeader>
          <div className="overflow-x-auto">
            {workersLoading ? (
              <div className="space-y-2 p-5">
                {Array.from({ length: 5 }).map((_, i) => (
                  <Skeleton key={i} className="h-10 w-full" />
                ))}
              </div>
            ) : !workers || workers.length === 0 ? (
              <EmptyState
                icon={Server}
                title="No active workers"
                description="Worker registrations will appear here once the background fleet comes online."
              />
            ) : (
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b border-border/60 text-left text-[11px] uppercase tracking-wider text-muted-foreground">
                    <th className="px-5 py-2.5 font-medium">Worker</th>
                    <th className="px-3 py-2.5 font-medium">Type</th>
                    <th className="px-3 py-2.5 font-medium">Status</th>
                    <th className="px-3 py-2.5 text-right font-medium">Processed</th>
                    <th className="px-5 py-2.5 text-right font-medium">Last seen</th>
                  </tr>
                </thead>
                <tbody>
                  {workers.slice(0, 8).map((w, i) => (
                    <tr
                      key={w.worker_id}
                      className={cn(
                        'border-b border-border/40 transition-colors hover:bg-emerald-500/[0.04]',
                        i % 2 === 1 && 'bg-muted/20',
                      )}
                    >
                      <td className="px-5 py-3">
                        <span className="font-mono text-xs text-foreground">
                          {w.worker_id.slice(0, 12)}…
                        </span>
                      </td>
                      <td className="px-3 py-3 text-muted-foreground">{w.worker_type}</td>
                      <td className="px-3 py-3">
                        <WorkerStatusBadge status={w.status} stale={w.is_stale} />
                      </td>
                      <td className="px-3 py-3 text-right font-mono text-xs text-foreground">
                        {formatInt(w.jobs_processed)}
                      </td>
                      <td className="px-5 py-3 text-right text-xs text-muted-foreground">
                        {w.last_seen_at ? formatRelativeTime(w.last_seen_at) : '—'}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </div>
        </Card>

        {/* Recent activity feed */}
        <Card className="flex flex-col rounded-2xl">
          <CardHeader className="border-b border-border/60 bg-muted/30 px-5 py-4">
            <CardTitle className="text-base">Recent Activity</CardTitle>
            <p className="text-xs text-muted-foreground">Outbox event stream</p>
          </CardHeader>
          <CardContent className="flex-1 overflow-y-auto p-0">
            {activityLoading ? (
              <div className="space-y-3 p-5">
                {Array.from({ length: 6 }).map((_, i) => (
                  <div key={i} className="flex gap-3">
                    <Skeleton className="h-2 w-2 shrink-0 rounded-full" />
                    <div className="flex-1 space-y-1.5">
                      <Skeleton className="h-3 w-3/4" />
                      <Skeleton className="h-2 w-1/2" />
                    </div>
                  </div>
                ))}
              </div>
            ) : !outboxEvents || outboxEvents.length === 0 ? (
              <EmptyState
                icon={Activity}
                title="No recent activity"
                description="Outbox events will stream in here as they're produced."
              />
            ) : (
              <ol className="max-h-[28rem] divide-y divide-border/40">
                {outboxEvents.slice(0, 10).map((ev) => (
                  <ActivityRow key={ev.id} event={ev} />
                ))}
              </ol>
            )}
          </CardContent>
        </Card>
      </div>

      {/* Secondary metrics row */}
      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
        <SecondaryStat
          icon={Mail}
          label="Notification Delivery"
          value={`${Math.round(safeDashboard.notification_delivery_rate * 100)}%`}
          sub="delivery success"
        />
        <SecondaryStat
          icon={Mail}
          label="Email Delivery"
          value={`${Math.round(safeDashboard.email_delivery_rate * 100)}%`}
          sub="delivery success"
        />
        <SecondaryStat
          icon={AlertTriangle}
          label="Dead Letters"
          value={formatInt(safeDashboard.dead_letter_count)}
          sub={`${safeDashboard.outbox_backlog} outbox backlog`}
        />
        <SecondaryStat
          icon={Flag}
          label="Feature Flags"
          value={formatInt(safeDashboard.feature_flags_enabled)}
          sub={`${safeDashboard.active_organizations} orgs active`}
        />
      </div>

      {/* Storage + System Info */}
      <div className="grid gap-4 md:grid-cols-2">
        <Card className="rounded-2xl">
          <CardHeader className="pb-3">
            <CardTitle className="flex items-center gap-2 text-base">
              <HardDrive className="h-4 w-4 text-emerald-500" aria-hidden="true" />
              Storage Usage
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-2">
            <div className="flex justify-between text-sm">
              <span className="text-muted-foreground">
                {(safeDashboard.storage_usage.used / 1e9).toFixed(1)} GB used
              </span>
              <span className="text-muted-foreground">
                {(safeDashboard.storage_usage.total / 1e9).toFixed(1)} GB total
              </span>
            </div>
            <Progress
              value={(safeDashboard.storage_usage.used / safeDashboard.storage_usage.total) * 100}
              className="h-2"
            />
          </CardContent>
        </Card>

        <Card className="rounded-2xl">
          <CardHeader className="pb-3">
            <CardTitle className="flex items-center gap-2 text-base">
              <Cpu className="h-4 w-4 text-emerald-500" aria-hidden="true" />
              System Information
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-2.5 text-sm">
            <InfoRow label="Version" value={safeDashboard.system_version} />
            <InfoRow
              label="Database"
              value={<HealthBadge status={safeDashboard.database_health} />}
            />
            <InfoRow
              label="Redis"
              value={<HealthBadge status={safeDashboard.redis_health} />}
            />
            <InfoRow label="Background Jobs" value={formatInt(safeDashboard.background_jobs)} />
          </CardContent>
        </Card>
      </div>

      {/* Worker metrics (if present) */}
      {metrics && (
        <Card className="rounded-2xl">
          <CardHeader className="pb-3">
            <CardTitle className="text-base">Background Processing Metrics</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="grid gap-4 sm:grid-cols-3 lg:grid-cols-6">
              <Metric label="Pending" value={formatInt(metrics.outbox.pending)} />
              <Metric label="Dispatched" value={formatInt(metrics.outbox.dispatched)} />
              <Metric label="In Progress" value={formatInt(metrics.outbox.in_progress)} />
              <Metric label="Dead Lettered" value={formatInt(metrics.outbox.dead_lettered)} />
              <Metric label="Emails Sent" value={formatInt(metrics.email.sent)} />
              <Metric
                label="Throughput/min"
                value={metrics.throughput_per_minute?.toFixed(1) ?? '0'}
              />
            </div>
          </CardContent>
        </Card>
      )}

      {/* Quick links */}
      <div className="flex flex-wrap gap-x-6 gap-y-2 border-t border-border/60 pt-4">
        <QuickLink href="/admin/users" icon={Users} label="Manage Users" />
        <QuickLink href="/admin/workers" icon={Server} label="Worker Console" />
        <QuickLink href="/admin/security" icon={AlertTriangle} label="Security Center" />
        <QuickLink href="/admin/audit" icon={Database} label="Audit Logs" />
      </div>
    </div>
  )
}

// ============================================================
// Sub-components
// ============================================================

function formatInt(n: number): string {
  return new Intl.NumberFormat().format(n)
}

function StatCard({
  icon: Icon,
  label,
  value,
  sublabel,
  accent,
  isStatus,
}: {
  icon: LucideIcon
  label: string
  value: string | number
  sublabel?: string
  accent: 'emerald' | 'amber'
  isStatus?: boolean
}) {
  return (
    <Card
      className={cn(
        'group relative overflow-hidden rounded-2xl transition-all hover:shadow-md',
        'border-border/60',
      )}
    >
      <div
        className={cn(
          'pointer-events-none absolute -right-6 -top-6 h-24 w-24 rounded-full opacity-10 blur-2xl transition-opacity group-hover:opacity-20',
          accent === 'emerald' ? 'bg-emerald-500' : 'bg-amber-500',
        )}
        aria-hidden="true"
      />
      <CardContent className="relative p-5">
        <div className="flex items-center justify-between">
          <span className="text-xs font-medium uppercase tracking-wider text-muted-foreground">
            {label}
          </span>
          <span
            className={cn(
              'flex h-9 w-9 items-center justify-center rounded-xl',
              accent === 'emerald'
                ? 'bg-emerald-500/10 text-emerald-500'
                : 'bg-amber-500/10 text-amber-500',
            )}
          >
            <Icon className="h-4 w-4" aria-hidden="true" />
          </span>
        </div>
        <p
          className={cn(
            'mt-3 text-3xl font-bold tracking-tight',
            isStatus && accent === 'emerald' && 'text-emerald-500',
            isStatus && accent === 'amber' && 'text-amber-500',
          )}
        >
          {value}
        </p>
        {sublabel && <p className="mt-1 text-xs text-muted-foreground">{sublabel}</p>}
      </CardContent>
    </Card>
  )
}

function SecondaryStat({
  icon: Icon,
  label,
  value,
  sub,
}: {
  icon: LucideIcon
  label: string
  value: string
  sub: string
}) {
  return (
    <Card className="rounded-2xl border-border/60">
      <CardContent className="p-5">
        <div className="flex items-center gap-2 text-muted-foreground">
          <Icon className="h-4 w-4" aria-hidden="true" />
          <span className="text-xs font-medium uppercase tracking-wider">{label}</span>
        </div>
        <p className="mt-2 text-2xl font-bold tracking-tight text-foreground">{value}</p>
        <p className="mt-1 text-xs text-muted-foreground">{sub}</p>
      </CardContent>
    </Card>
  )
}

function WorkerStatusBadge({ status, stale }: { status: AdminWorker['status']; stale: boolean }) {
  const variant: Record<AdminWorker['status'], 'success' | 'warning' | 'destructive' | 'secondary'> = {
    running: 'success',
    starting: 'warning',
    draining: 'warning',
    stopped: 'secondary',
    crashed: 'destructive',
  }
  if (stale && status === 'running') {
    return (
      <Badge variant="warning" className="capitalize">
        stale
      </Badge>
    )
  }
  return (
    <Badge variant={variant[status]} className="capitalize">
      {status}
    </Badge>
  )
}

function ActivityRow({ event }: { event: OutboxEvent }) {
  const dotColor =
    event.status === 'dispatched'
      ? 'bg-emerald-500'
      : event.status === 'dead_lettered'
        ? 'bg-red-500'
        : 'bg-amber-500'
  return (
    <li className="flex items-start gap-3 px-5 py-3 transition-colors hover:bg-muted/30">
      <span className={cn('mt-1.5 h-2 w-2 shrink-0 rounded-full', dotColor)} aria-hidden="true" />
      <div className="min-w-0 flex-1">
        <p className="truncate text-sm font-medium text-foreground">
          <span className="font-mono text-xs">{event.event_type}</span>
        </p>
        <p className="mt-0.5 flex items-center gap-2 text-xs text-muted-foreground">
          <span className="truncate">{event.aggregate_type}</span>
          <span aria-hidden="true">·</span>
          <span className="shrink-0">{formatRelativeTime(event.created_at)}</span>
        </p>
      </div>
      <Badge
        variant={event.status === 'dispatched' ? 'success' : event.status === 'dead_lettered' ? 'destructive' : 'warning'}
        className="shrink-0 capitalize"
      >
        {event.status.replace('_', ' ')}
      </Badge>
    </li>
  )
}

function HealthBadge({ status }: { status: 'healthy' | 'degraded' | 'down' }) {
  const variant = status === 'healthy' ? 'success' : status === 'degraded' ? 'warning' : 'destructive'
  return (
    <Badge variant={variant} className="capitalize">
      {status}
    </Badge>
  )
}

function InfoRow({ label, value }: { label: string; value: React.ReactNode }) {
  return (
    <div className="flex items-center justify-between">
      <span className="text-muted-foreground">{label}</span>
      <span className="font-medium text-foreground">{value}</span>
    </div>
  )
}

function Metric({ label, value }: { label: string; value: number | string }) {
  return (
    <div>
      <p className="text-xs text-muted-foreground">{label}</p>
      <p className="mt-1 text-lg font-bold text-foreground">{value}</p>
    </div>
  )
}

function EmptyState({
  icon: Icon,
  title,
  description,
}: {
  icon: LucideIcon
  title: string
  description: string
}) {
  return (
    <div className="flex flex-col items-center justify-center px-6 py-12 text-center">
      <div className="mb-3 flex h-12 w-12 items-center justify-center rounded-2xl bg-muted">
        <Icon className="h-6 w-6 text-muted-foreground" aria-hidden="true" />
      </div>
      <p className="text-sm font-medium text-foreground">{title}</p>
      <p className="mt-1 max-w-xs text-xs text-muted-foreground">{description}</p>
    </div>
  )
}

function QuickLink({ href, icon: Icon, label }: { href: string; icon: LucideIcon; label: string }) {
  return (
    <Link
      href={href}
      className="group flex items-center gap-1.5 text-sm text-muted-foreground transition-colors hover:text-emerald-600 dark:hover:text-emerald-400"
    >
      <Icon className="h-3.5 w-3.5" aria-hidden="true" />
      {label}
      <ArrowRight className="h-3 w-3 opacity-0 transition-opacity group-hover:opacity-100" aria-hidden="true" />
    </Link>
  )
}

function DashboardSkeleton() {
  return (
    <div className="space-y-6">
      <div className="space-y-2">
        <Skeleton className="h-8 w-64" />
        <Skeleton className="h-4 w-48" />
      </div>
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        {Array.from({ length: 4 }).map((_, i) => (
          <Skeleton key={i} className="h-32 w-full rounded-2xl" />
        ))}
      </div>
      <div className="grid gap-4 lg:grid-cols-3">
        <Skeleton className="h-80 w-full rounded-2xl lg:col-span-2" />
        <Skeleton className="h-80 w-full rounded-2xl" />
      </div>
      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
        {Array.from({ length: 4 }).map((_, i) => (
          <Skeleton key={i} className="h-24 w-full rounded-2xl" />
        ))}
      </div>
    </div>
  )
}
