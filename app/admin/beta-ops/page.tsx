'use client'

import * as React from 'react'
import {
  Activity,
  Users,
  UserCheck,
  CalendarDays,
  CalendarRange,
  Clock,
  BookOpen,
  MessageSquare,
  Bug,
  AlertOctagon,
  Smile,
  TrendingUp,
  GraduationCap,
  RefreshCw,
  Repeat,
} from 'lucide-react'
import { toast } from 'sonner'

import { useBetaOpsDashboard } from '@/hooks/use-beta-ops'
import { Card, CardContent, CardHeader } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Skeleton } from '@/components/ui/skeleton'
import { ErrorState } from '@/components/ui/error-state'
import { cn } from '@/lib/cn'
import { formatDateTime, formatNumber } from '@/lib/format'

interface KpiCardProps {
  label: string
  value: string
  hint?: string
  icon: React.ComponentType<{ className?: string }>
  trend?: 'up' | 'down' | 'neutral'
}

function KpiCard({ label, value, hint, icon: Icon, trend }: KpiCardProps) {
  return (
    <Card hover>
      <CardHeader className="pb-2">
        <div className="flex items-center justify-between">
          <p className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">
            {label}
          </p>
          <Icon className="h-4 w-4 text-muted-foreground" aria-hidden="true" />
        </div>
        <p className="mt-2 text-3xl font-bold tracking-tight">{value}</p>
      </CardHeader>
      {hint && (
        <CardContent className="pt-0">
          <p
            className={cn(
              'text-xs',
              trend === 'up' && 'text-success',
              trend === 'down' && 'text-destructive',
              (!trend || trend === 'neutral') && 'text-muted-foreground',
            )}
          >
            {trend === 'up' && '▲ '}
            {trend === 'down' && '▼ '}
            {hint}
          </p>
        </CardContent>
      )}
    </Card>
  )
}

function DashboardSkeleton() {
  return (
    <div className="space-y-6" role="status" aria-label="Loading dashboard">
      <div className="flex items-center justify-between">
        <Skeleton className="h-10 w-72" />
        <Skeleton className="h-8 w-48" />
      </div>
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
        {Array.from({ length: 17 }).map((_, i) => (
          <Skeleton key={i} className="h-28 w-full" />
        ))}
      </div>
    </div>
  )
}

export default function BetaOpsDashboardPage() {
  const { data, isLoading, isError, error, refetch, isFetching } =
    useBetaOpsDashboard()

  if (isLoading) return <DashboardSkeleton />
  if (isError || !data) {
    return (
      <ErrorState
        title="Failed to load dashboard"
        description="We couldn't fetch the beta operations dashboard."
        error={error as Error | undefined}
        onRetry={() => refetch()}
      />
    )
  }

  const pct = (n: number) => `${(n * 100).toFixed(1)}%`

  return (
    <div className="space-y-6">
      <header className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h1 className="text-2xl font-bold tracking-tight">
            Beta Operations Dashboard
          </h1>
          <p className="text-sm text-muted-foreground">
            Live beta metrics — auto-refreshing every 60 seconds.
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
          <div className="text-xs text-muted-foreground">
            Generated at{' '}
            <time dateTime={data.generated_at} className="font-medium text-foreground">
              {formatDateTime(data.generated_at)}
            </time>
          </div>
          <Button
            variant="outline"
            size="sm"
            onClick={() => {
              refetch()
              toast.success('Dashboard refreshed')
            }}
            aria-label="Refresh dashboard"
          >
            <RefreshCw className="h-4 w-4" aria-hidden="true" />
            <span className="sr-only sm:not-sr-only">Refresh</span>
          </Button>
        </div>
      </header>

      <section
        aria-label="Key performance indicators"
        className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4"
      >
        <KpiCard
          label="Total Invited"
          value={formatNumber(data.total_invited)}
          icon={Users}
          hint={`${formatNumber(data.active_beta_users)} active`}
        />
        <KpiCard
          label="Active Beta Users"
          value={formatNumber(data.active_beta_users)}
          icon={UserCheck}
        />
        <KpiCard
          label="Daily Active Users"
          value={formatNumber(data.daily_active_users)}
          icon={Activity}
          trend="up"
          hint={`${data.weekly_active_users} WAU`}
        />
        <KpiCard
          label="Weekly Active Users"
          value={formatNumber(data.weekly_active_users)}
          icon={CalendarRange}
        />
        <KpiCard
          label="Monthly Active Users"
          value={formatNumber(data.monthly_active_users)}
          icon={CalendarDays}
        />
        <KpiCard
          label="Invite Conversion"
          value={pct(data.invite_conversion_rate)}
          icon={TrendingUp}
          trend={data.invite_conversion_rate >= 0.5 ? 'up' : 'down'}
          hint="Invites accepted"
        />
        <KpiCard
          label="Avg Session"
          value={`${data.avg_session_duration_minutes.toFixed(1)} min`}
          icon={Clock}
        />
        <KpiCard
          label="Sessions Completed"
          value={formatNumber(data.study_sessions_completed)}
          icon={BookOpen}
        />
        <KpiCard
          label="Feedback Received"
          value={formatNumber(data.feedback_received)}
          icon={MessageSquare}
        />
        <KpiCard
          label="Bugs Reported"
          value={formatNumber(data.bugs_reported)}
          icon={Bug}
        />
        <KpiCard
          label="Crash Reports"
          value={formatNumber(data.crash_reports)}
          icon={AlertOctagon}
          trend={data.crash_reports > 0 ? 'down' : 'neutral'}
          hint={data.crash_reports > 0 ? 'Investigate' : 'No crashes'}
        />
        <KpiCard
          label="NPS Score"
          value={data.nps_score.toFixed(0)}
          icon={Smile}
          trend={data.nps_score >= 30 ? 'up' : data.nps_score < 0 ? 'down' : 'neutral'}
          hint={data.nps_score >= 30 ? 'Healthy' : data.nps_score < 0 ? 'At risk' : 'Stable'}
        />
        <KpiCard
          label="User Satisfaction"
          value={pct(data.user_satisfaction)}
          icon={Smile}
        />
        <KpiCard
          label="Learning Progress Avg"
          value={pct(data.learning_progress_avg)}
          icon={GraduationCap}
        />
        <KpiCard
          label="Retention Day 1"
          value={pct(data.retention_day_1)}
          icon={Repeat}
        />
        <KpiCard
          label="Retention Day 7"
          value={pct(data.retention_day_7)}
          icon={Repeat}
        />
        <KpiCard
          label="Retention Day 30"
          value={pct(data.retention_day_30)}
          icon={Repeat}
        />
      </section>
    </div>
  )
}
