'use client'

import * as React from 'react'
import {
  Activity,
  Users,
  UserCheck,
  Clock,
  MessageSquare,
  Smile,
  RefreshCw,
  TrendingUp,
  TrendingDown,
  Minus,
  type LucideIcon,
} from 'lucide-react'
import { toast } from 'sonner'
import {
  ResponsiveContainer,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
  Cell,
  AreaChart,
  Area,
  CartesianGrid,
} from 'recharts'

import {
  useBetaOpsDashboard,
  useRegistrationFunnel,
  useRetentionCohorts,
  useFeedbackPlatform,
} from '@/hooks/use-beta-ops'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Skeleton } from '@/components/ui/skeleton'
import { Badge } from '@/components/ui/badge'
import { ErrorState } from '@/components/ui/error-state'
import { cn } from '@/lib/cn'
import { formatDateTime, formatNumber, formatRelativeTime } from '@/lib/format'

const EMERALD = '#10B981'
const EMERALD_SOFT = '#34d399'

interface KpiCardProps {
  label: string
  value: string
  hint?: string
  icon: LucideIcon
  trend?: 'up' | 'down' | 'neutral'
}

function KpiCard({ label, value, hint, icon: Icon, trend }: KpiCardProps) {
  const TrendIcon = trend === 'up' ? TrendingUp : trend === 'down' ? TrendingDown : Minus
  const trendColor =
    trend === 'up'
      ? 'text-emerald-500'
      : trend === 'down'
        ? 'text-red-500'
        : 'text-muted-foreground'
  return (
    <Card hover className="group overflow-hidden rounded-2xl border-border/60">
      <CardContent className="p-5">
        <div className="flex items-center justify-between">
          <span className="flex h-9 w-9 items-center justify-center rounded-xl bg-emerald-500/10 text-emerald-500">
            <Icon className="h-4 w-4" aria-hidden="true" />
          </span>
          {trend && (
            <span className={cn('flex items-center text-xs font-medium', trendColor)}>
              <TrendIcon className="mr-0.5 h-3 w-3" aria-hidden="true" />
              {trend === 'up' ? 'Up' : trend === 'down' ? 'Down' : 'Flat'}
            </span>
          )}
        </div>
        <p className="mt-4 text-[11px] font-semibold uppercase tracking-wider text-muted-foreground">
          {label}
        </p>
        <p className="mt-1 text-3xl font-bold tracking-tight text-foreground">{value}</p>
        {hint && <p className={cn('mt-1 text-xs', trendColor)}>{hint}</p>}
      </CardContent>
    </Card>
  )
}

function ChartCard({
  title,
  subtitle,
  children,
  className,
}: {
  title: string
  subtitle?: string
  children: React.ReactNode
  className?: string
}) {
  return (
    <Card className={cn('rounded-2xl border-border/60', className)}>
      <CardHeader className="border-b border-border/60 bg-muted/30 px-5 py-4">
        <CardTitle className="text-base">{title}</CardTitle>
        {subtitle && <p className="text-xs text-muted-foreground">{subtitle}</p>}
      </CardHeader>
      <CardContent className="p-5">{children}</CardContent>
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
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-6">
        {Array.from({ length: 6 }).map((_, i) => (
          <Skeleton key={i} className="h-36 w-full rounded-2xl" />
        ))}
      </div>
      <div className="grid gap-4 lg:grid-cols-2">
        <Skeleton className="h-80 w-full rounded-2xl" />
        <Skeleton className="h-80 w-full rounded-2xl" />
      </div>
      <Skeleton className="h-64 w-full rounded-2xl" />
    </div>
  )
}

export default function BetaOpsDashboardPage() {
  const { data, isLoading, isError, error, refetch, isFetching } = useBetaOpsDashboard()
  const { data: funnel, isLoading: funnelLoading } = useRegistrationFunnel(30)
  const { data: cohorts, isLoading: retentionLoading } = useRetentionCohorts(8)
  const { data: feedback, isLoading: feedbackLoading } = useFeedbackPlatform(50)

  // Retention curve — average each week across cohorts
  const retentionData = React.useMemo(() => {
    if (!cohorts || cohorts.length === 0) return []
    const weeks = [0, 1, 2, 3, 4] as const
    return weeks.map((w) => {
      const valid = cohorts.filter((c) => c.cohort_size > 0)
      const avg =
        valid.length === 0
          ? 0
          : valid.reduce((sum, c) => {
              const val = c[`week_${w}` as 'week_0' | 'week_1' | 'week_2' | 'week_3' | 'week_4']
              return sum + val / c.cohort_size
            }, 0) / valid.length
      return {
        week: `Week ${w}`,
        retention: Math.round(avg * 1000) / 10, // one decimal as %
      }
    })
  }, [cohorts])

  // Recent feedback items (most recent first)
  const recentFeedback = React.useMemo(() => {
    if (!feedback?.items) return []
    return [...feedback.items]
      .sort((a, b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime())
      .slice(0, 6)
  }, [feedback])

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

  // Funnel chart data
  const funnelData = (funnel?.steps ?? []).map((s) => ({
    name: s.step,
    count: s.count,
    pct: s.cumulative_pct,
  }))

  return (
    <div className="space-y-6">
      {/* Header */}
      <header className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-foreground">
            Beta Operations Dashboard
          </h1>
          <p className="mt-1 text-sm text-muted-foreground">
            Live beta metrics · auto-refreshing every 60 seconds
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
                isFetching ? 'animate-pulse bg-amber-500' : 'bg-emerald-500',
              )}
              aria-hidden="true"
            />
            {isFetching ? 'Refreshing…' : 'Auto-refresh active'}
          </div>
          <div className="hidden text-xs text-muted-foreground sm:block">
            Generated at{' '}
            <time
              dateTime={data.generated_at}
              className="font-medium text-foreground"
            >
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

      {/* KPI grid (6 cards) */}
      <section
        aria-label="Key performance indicators"
        className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-6"
      >
        <KpiCard
          label="DAU"
          value={formatNumber(data.daily_active_users)}
          icon={Activity}
          trend="up"
          hint={`${formatNumber(data.weekly_active_users)} WAU`}
        />
        <KpiCard
          label="Registrations"
          value={formatNumber(data.active_beta_users)}
          icon={UserCheck}
          hint={`${formatNumber(data.total_invited)} invited`}
        />
        <KpiCard
          label="Feedback Count"
          value={formatNumber(data.feedback_received)}
          icon={MessageSquare}
          hint={`${formatNumber(data.bugs_reported)} bugs`}
        />
        <KpiCard
          label="Avg Session"
          value={`${data.avg_session_duration_minutes.toFixed(1)}m`}
          icon={Clock}
        />
        <KpiCard
          label="Completion Rate"
          value={pct(data.learning_progress_avg)}
          icon={TrendingUp}
          trend={data.learning_progress_avg >= 0.5 ? 'up' : 'down'}
          hint="Learning progress"
        />
        <KpiCard
          label="NPS Score"
          value={data.nps_score.toFixed(0)}
          icon={Smile}
          trend={data.nps_score >= 30 ? 'up' : data.nps_score < 0 ? 'down' : 'neutral'}
          hint={
            data.nps_score >= 30 ? 'Healthy' : data.nps_score < 0 ? 'At risk' : 'Stable'
          }
        />
      </section>

      {/* Charts */}
      <div className="grid gap-4 lg:grid-cols-2">
        <ChartCard
          title="Registration Funnel"
          subtitle="Last 30 days · cumulative conversion"
        >
          {funnelLoading ? (
            <Skeleton className="h-64 w-full" />
          ) : funnelData.length === 0 ? (
            <ChartEmpty label="No funnel data yet" />
          ) : (
            <div className="h-64 w-full">
              <ResponsiveContainer width="100%" height="100%">
                <BarChart
                  data={funnelData}
                  layout="vertical"
                  margin={{ top: 4, right: 16, bottom: 4, left: 8 }}
                >
                  <CartesianGrid
                    horizontal={false}
                    stroke="hsl(var(--border) / 0.4)"
                    strokeDasharray="3 3"
                  />
                  <XAxis
                    type="number"
                    tick={{ fontSize: 11, fill: 'hsl(var(--muted-foreground))' }}
                    axisLine={false}
                    tickLine={false}
                  />
                  <YAxis
                    type="category"
                    dataKey="name"
                    width={110}
                    tick={{ fontSize: 11, fill: 'hsl(var(--muted-foreground))' }}
                    axisLine={false}
                    tickLine={false}
                  />
                  <Tooltip
                    cursor={{ fill: 'hsl(var(--muted) / 0.3)' }}
                    contentStyle={{
                      borderRadius: 12,
                      border: '1px solid hsl(var(--border))',
                      background: 'hsl(var(--popover))',
                      color: 'hsl(var(--popover-foreground))',
                      fontSize: 12,
                    }}
                    formatter={(value: number, _name, item) => {
                      const cumulativePct = ((item.payload as { pct?: number })?.pct ?? 0) * 100
                      return [`${formatNumber(value)} users (${cumulativePct.toFixed(1)}%)`, 'Count']
                    }}
                  />
                  <Bar dataKey="count" radius={[0, 6, 6, 0]} maxBarSize={28}>
                    {funnelData.map((_, i) => (
                      <Cell
                        key={i}
                        fill={EMERALD}
                        fillOpacity={Math.max(0.4, 1 - i * 0.12)}
                      />
                    ))}
                  </Bar>
                </BarChart>
              </ResponsiveContainer>
            </div>
          )}
        </ChartCard>

        <ChartCard
          title="Retention Curve"
          subtitle="Average % returning · weeks 0–4"
        >
          {retentionLoading ? (
            <Skeleton className="h-64 w-full" />
          ) : retentionData.length === 0 ? (
            <ChartEmpty label="No retention cohorts yet" />
          ) : (
            <div className="h-64 w-full">
              <ResponsiveContainer width="100%" height="100%">
                <AreaChart
                  data={retentionData}
                  margin={{ top: 8, right: 16, bottom: 4, left: 0 }}
                >
                  <defs>
                    <linearGradient id="retentionGrad" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="0%" stopColor={EMERALD} stopOpacity={0.4} />
                      <stop offset="100%" stopColor={EMERALD} stopOpacity={0} />
                    </linearGradient>
                  </defs>
                  <CartesianGrid
                    vertical={false}
                    stroke="hsl(var(--border) / 0.4)"
                    strokeDasharray="3 3"
                  />
                  <XAxis
                    dataKey="week"
                    tick={{ fontSize: 11, fill: 'hsl(var(--muted-foreground))' }}
                    axisLine={false}
                    tickLine={false}
                  />
                  <YAxis
                    domain={[0, 100]}
                    tick={{ fontSize: 11, fill: 'hsl(var(--muted-foreground))' }}
                    axisLine={false}
                    tickLine={false}
                    tickFormatter={(v: number) => `${v}%`}
                  />
                  <Tooltip
                    contentStyle={{
                      borderRadius: 12,
                      border: '1px solid hsl(var(--border))',
                      background: 'hsl(var(--popover))',
                      color: 'hsl(var(--popover-foreground))',
                      fontSize: 12,
                    }}
                    formatter={(value: number) => [`${value}%`, 'Retention']}
                  />
                  <Area
                    type="monotone"
                    dataKey="retention"
                    stroke={EMERALD}
                    strokeWidth={2.5}
                    fill="url(#retentionGrad)"
                    dot={{ r: 4, fill: EMERALD, strokeWidth: 0 }}
                    activeDot={{ r: 6, fill: EMERALD_SOFT }}
                  />
                </AreaChart>
              </ResponsiveContainer>
            </div>
          )}
        </ChartCard>
      </div>

      {/* Recent feedback */}
      <Card className="overflow-hidden rounded-2xl border-border/60">
        <CardHeader className="flex flex-row items-center justify-between border-b border-border/60 bg-muted/30 px-5 py-4">
          <div>
            <CardTitle className="text-base">Recent Feedback</CardTitle>
            <p className="text-xs text-muted-foreground">
              Latest responses from beta participants
            </p>
          </div>
          <Badge variant="secondary" className="font-mono">
            {formatNumber(feedback?.total ?? data.feedback_received)} total
          </Badge>
        </CardHeader>
        <CardContent className="p-0">
          {feedbackLoading ? (
            <div className="space-y-2 p-5">
              {Array.from({ length: 5 }).map((_, i) => (
                <Skeleton key={i} className="h-16 w-full rounded-xl" />
              ))}
            </div>
          ) : recentFeedback.length === 0 ? (
            <div className="flex flex-col items-center justify-center px-6 py-16 text-center">
              <div className="mb-3 flex h-12 w-12 items-center justify-center rounded-2xl bg-muted">
                <MessageSquare className="h-6 w-6 text-muted-foreground" aria-hidden="true" />
              </div>
              <p className="text-sm font-medium text-foreground">No feedback yet</p>
              <p className="mt-1 max-w-xs text-xs text-muted-foreground">
                Feedback from beta users will appear here.
              </p>
            </div>
          ) : (
            <ul className="divide-y divide-border/40">
              {recentFeedback.map((item) => (
                <li
                  key={item.id}
                  className="flex items-start gap-4 px-5 py-4 transition-colors hover:bg-muted/20"
                >
                  <RatingPill rating={item.rating} />
                  <div className="min-w-0 flex-1">
                    <div className="flex flex-wrap items-center gap-2">
                      <Badge
                        variant="secondary"
                        className="bg-emerald-500/10 text-emerald-600 dark:text-emerald-400"
                      >
                        {item.category}
                      </Badge>
                      <span className="text-xs text-muted-foreground">
                        {formatRelativeTime(item.created_at)}
                      </span>
                      {item.priority && item.priority !== 'normal' && (
                        <Badge
                          variant={
                            item.priority === 'critical' || item.priority === 'high'
                              ? 'destructive'
                              : 'warning'
                          }
                          className="capitalize"
                        >
                          {item.priority}
                        </Badge>
                      )}
                    </div>
                    <p className="mt-1.5 line-clamp-2 text-sm text-foreground">
                      {item.comment || 'No comment provided.'}
                    </p>
                  </div>
                  {item.vote_count > 0 && (
                    <span className="hidden shrink-0 items-center gap-1 rounded-full bg-muted px-2 py-0.5 text-xs font-medium text-muted-foreground sm:flex">
                      <Users className="h-3 w-3" aria-hidden="true" />
                      {item.vote_count}
                    </span>
                  )}
                </li>
              ))}
            </ul>
          )}
        </CardContent>
      </Card>
    </div>
  )
}

function RatingPill({ rating }: { rating: number }) {
  const tone =
    rating >= 4
      ? 'bg-emerald-500/10 text-emerald-600 dark:text-emerald-400'
      : rating === 3
        ? 'bg-amber-500/10 text-amber-600 dark:text-amber-400'
        : 'bg-red-500/10 text-red-600 dark:text-red-400'
  return (
    <span
      className={cn(
        'flex h-9 w-9 shrink-0 items-center justify-center rounded-lg text-xs font-bold',
        tone,
      )}
      aria-label={`Rating ${rating} out of 5`}
    >
      {rating}★
    </span>
  )
}

function ChartEmpty({ label }: { label: string }) {
  return (
    <div className="flex h-64 w-full flex-col items-center justify-center text-center">
      <Activity className="h-8 w-8 text-muted-foreground/40" aria-hidden="true" />
      <p className="mt-2 text-sm text-muted-foreground">{label}</p>
    </div>
  )
}
