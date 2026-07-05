'use client'

import * as React from 'react'
import Link from 'next/link'
import { Users, Activity, Server, Mail, AlertTriangle, Database, Cpu, HardDrive, Zap, Flag, Building2 } from 'lucide-react'

import { useOpsDashboard, useWorkerMetrics } from '@/hooks/use-admin'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Skeleton } from '@/components/ui/skeleton'
import { Progress } from '@/components/ui/progress'
import { ErrorState } from '@/components/ui/error-state'
import { cn } from '@/lib/cn'

export default function AdminDashboardPage() {
  const { data: dashboard, isLoading, isError, refetch } = useOpsDashboard()
  const { data: metrics } = useWorkerMetrics()

  if (isLoading) return <DashboardSkeleton />
  if (isError) return <ErrorState onRetry={() => refetch()} />
  if (!dashboard) return null

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold tracking-tight">Operations Dashboard</h1>
        <p className="text-sm text-muted-foreground">Live platform Health — auto-refreshing every 30s</p>
      </div>

      {/* Primary stats */}
      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
        <StatCard icon={Users} label="Active Users" value={safeDashboard.active_users ?? 0} sublabel={`${safeDashboard.daily_active_users ?? 0} DAU`} />
        <StatCard icon={Activity} label="Study Sessions" value={safeDashboard.active_study_sessions ?? 0} sublabel={`${safeDashboard.queue_throughput ?? 0}/min throughput`} />
        <StatCard icon={Server} label="Workers" value={`${safeDashboard.worker_status?.active ?? 0}/${safeDashboard.worker_status?.total ?? 0}`} sublabel={`${safeDashboard.worker_status?.dead ?? 0} dead`} />
        <StatCard icon={AlertTriangle} label="Dead Letters" value={safeDashboard.dead_letter_count ?? 0} sublabel={`${safeDashboard.outbox_backlog ?? 0} outbox backlog`} />
      </div>

      {/* Health + Performance */}
      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
        <StatCard icon={Mail} label="Notification Rate" value={`${Math.round((safeDashboard.notification_delivery_rate ?? 0) * 100)}%`} sublabel="delivery success" />
        <StatCard icon={Mail} label="Email Rate" value={`${Math.round((safeDashboard.email_delivery_rate ?? 0) * 100)}%`} sublabel="delivery success" />
        <StatCard icon={Zap} label="API Latency" value={`${safeDashboard.api_latency_ms ?? 0}ms`} sublabel={`${((safeDashboard.error_rate ?? 0) * 100).toFixed(1)}% error rate`} />
        <StatCard icon={Flag} label="Feature Flags" value={safeDashboard.feature_flags_enabled ?? 0} sublabel="enabled" />
      </div>

      {/* System Health */}
      <Card>
        <CardHeader><CardTitle className="text-base">System Health</CardTitle></CardHeader>
        <CardContent className="grid gap-4 sm:grid-cols-3">
          <HealthIndicator label="Database" status={safeDashboard.database_health ?? 'healthy'} />
          <HealthIndicator label="Redis" status={safeDashboard.redis_health ?? 'healthy'} />
          <HealthIndicator label="Background Jobs" value={safeDashboard.background_jobs ?? 0} />
        </CardContent>
      </Card>

      {/* Storage + Version */}
      <div className="grid gap-4 md:grid-cols-2">
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-base"><HardDrive className="h-4 w-4" aria-hidden="true" /> Storage Usage</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-2">
              <div className="flex justify-between text-sm">
                <span className="text-muted-foreground">{((safeDashboard.storage_usage?.used ?? 0) / 1e9).toFixed(1)} GB used</span>
                <span className="text-muted-foreground">{((safeDashboard.storage_usage?.total ?? 1) / 1e9).toFixed(1)} GB total</span>
              </div>
              <Progress value={((safeDashboard.storage_usage?.used ?? 0) / (safeDashboard.storage_usage?.total ?? 1)) * 100} />
            </div>
          </CardContent>
        </Card>
        <Card>
          <CardHeader><CardTitle className="text-base">System Information</CardTitle></CardHeader>
          <CardContent className="space-y-2 text-sm">
            <div className="flex justify-between"><span className="text-muted-foreground">Version</span><span className="font-medium">{safeDashboard.system_version ?? '1.0.0'}</span></div>
            <div className="flex justify-between"><span className="text-muted-foreground">Active Organizations</span><span className="font-medium">{safeDashboard.active_organizations ?? 0}</span></div>
          </CardContent>
        </Card>
      </div>

      {/* Worker metrics */}
      {metrics && (
        <Card>
          <CardHeader><CardTitle className="text-base">Background Processing Metrics</CardTitle></CardHeader>
          <CardContent>
            <div className="grid gap-4 sm:grid-cols-3 lg:grid-cols-6">
              <Metric label="Pending" value={metrics.outbox.pending} />
              <Metric label="Dispatched" value={metrics.outbox.dispatched} />
              <Metric label="In Progress" value={metrics.outbox.in_progress} />
              <Metric label="Dead Lettered" value={metrics.outbox.dead_lettered} />
              <Metric label="Emails Sent" value={metrics.email.sent} />
              <Metric label="Throughput/min" value={metrics.throughput_per_minute?.toFixed(1) || '0'} />
            </div>
          </CardContent>
        </Card>
      )}

      {/* Quick links */}
      <div className="flex flex-wrap gap-2">
        <Link href="/admin/users" className="text-sm text-primary hover:underline">Manage Users →</Link>
        <Link href="/admin/workers" className="text-sm text-primary hover:underline">Worker Console →</Link>
        <Link href="/admin/security" className="text-sm text-primary hover:underline">Security Center →</Link>
        <Link href="/admin/audit" className="text-sm text-primary hover:underline">Audit Logs →</Link>
      </div>
    </div>
  )
}

function StatCard({ icon: Icon, label, value, sublabel }: { icon: React.ComponentType<{ className?: string }>; label: string; value: string | number; sublabel?: string }) {
  return (
    <Card>
      <CardHeader className="pb-2">
        <div className="flex items-center justify-between">
          <CardDescription>{label}</CardDescription>
          <Icon className="h-4 w-4 text-muted-foreground" aria-hidden="true" />
        </div>
        <CardTitle className="text-3xl">{value}</CardTitle>
      </CardHeader>
      {sublabel && <CardContent><p className="text-xs text-muted-foreground">{sublabel}</p></CardContent>}
    </Card>
  )
}

function HealthIndicator({ label, status, value }: { label: string; status?: 'healthy' | 'degraded' | 'down'; value?: number }) {
  return (
    <div>
      <p className="text-xs text-muted-foreground">{label}</p>
      {status ? (
        <Badge variant={status === 'healthy' ? 'success' : status === 'degraded' ? 'warning' : 'destructive'} className="mt-1 capitalize">
          {status}
        </Badge>
      ) : value !== undefined ? (
        <p className="text-lg font-bold">{value}</p>
      ) : null}
    </div>
  )
}

function Metric({ label, value }: { label: string; value: number | string }) {
  return (
    <div>
      <p className="text-xs text-muted-foreground">{label}</p>
      <p className="text-lg font-bold">{value}</p>
    </div>
  )
}

function DashboardSkeleton() {
  return (
    <div className="space-y-6">
      <Skeleton className="h-8 w-48" />
      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
        {Array.from({ length: 8 }).map((_, i) => <Skeleton key={i} className="h-32 w-full" />)}
      </div>
      <Skeleton className="h-48 w-full" />
    </div>
  )
}
