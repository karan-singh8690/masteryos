'use client'

import * as React from 'react'
import {
  FileText,
  Sparkles,
  Users,
  Repeat,
  GraduationCap,
  MessageSquare,
  Bug,
  Lightbulb,
  HeartPulse,
  CalendarDays,
  CalendarRange,
  CalendarClock,
} from 'lucide-react'
import { toast } from 'sonner'

import { useBetaReport, useGenerateReport } from '@/hooks/use-beta-ops'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Skeleton } from '@/components/ui/skeleton'
import { Progress } from '@/components/ui/progress'
import { ErrorState } from '@/components/ui/error-state'
import { EmptyState } from '@/components/ui/empty-state'
import { Tabs, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { cn } from '@/lib/cn'
import { formatDateTime, formatNumber } from '@/lib/format'
import type { BetaReport } from '@/lib/beta-ops-api'

type Period = 'daily' | 'weekly' | 'monthly'

interface GenericRow {
  [key: string]: unknown
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

function pct(v: unknown, decimals = 1): string {
  const n = num(v)
  const ratio = n > 1 ? n / 100 : n
  return `${(ratio * 100).toFixed(decimals)}%`
}

function MetricCard({
  label,
  value,
  hint,
  icon: Icon,
}: {
  label: string
  value: string
  hint?: string
  icon: React.ComponentType<{ className?: string }>
}) {
  return (
    <Card>
      <CardHeader className="pb-2">
        <div className="flex items-center justify-between">
          <CardDescription>{label}</CardDescription>
          <Icon className="h-4 w-4 text-muted-foreground" aria-hidden="true" />
        </div>
        <CardTitle className="text-2xl">{value}</CardTitle>
      </CardHeader>
      {hint && (
        <CardContent>
          <p className="text-xs text-muted-foreground">{hint}</p>
        </CardContent>
      )}
    </Card>
  )
}

function GrowthCard({ growth }: { growth: GenericRow }) {
  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2 text-base">
          <Users className="h-4 w-4" aria-hidden="true" />
          Growth
        </CardTitle>
        <CardDescription>New users and invite funnel for this period.</CardDescription>
      </CardHeader>
      <CardContent className="grid grid-cols-2 gap-4 sm:grid-cols-3">
        <div>
          <p className="text-xs text-muted-foreground">New users</p>
          <p className="text-xl font-bold">{formatNumber(num(growth.new_users))}</p>
        </div>
        <div>
          <p className="text-xs text-muted-foreground">Total users</p>
          <p className="text-xl font-bold">{formatNumber(num(growth.total_users))}</p>
        </div>
        <div>
          <p className="text-xs text-muted-foreground">New invites</p>
          <p className="text-xl font-bold">{formatNumber(num(growth.new_invites))}</p>
        </div>
        <div>
          <p className="text-xs text-muted-foreground">Used invites</p>
          <p className="text-xl font-bold">{formatNumber(num(growth.used_invites))}</p>
        </div>
        <div>
          <p className="text-xs text-muted-foreground">Invite conversion</p>
          <p className="text-xl font-bold text-success">{pct(growth.invite_conversion)}</p>
        </div>
      </CardContent>
    </Card>
  )
}

function RetentionCard({ retention }: { retention: Record<string, number> }) {
  const days = [
    { key: 'day_1', label: 'Day 1' },
    { key: 'day_7', label: 'Day 7' },
    { key: 'day_30', label: 'Day 30' },
  ]
  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2 text-base">
          <Repeat className="h-4 w-4" aria-hidden="true" />
          Retention
        </CardTitle>
        <CardDescription>Cohort retention rates for this period.</CardDescription>
      </CardHeader>
      <CardContent className="space-y-4">
        {days.map((d) => {
          const value = num(retention[d.key])
          const ratio = value > 1 ? value / 100 : value
          return (
            <div key={d.key} className="space-y-1">
              <div className="flex justify-between text-sm">
                <span className="text-muted-foreground">{d.label}</span>
                <span className="font-medium">{(ratio * 100).toFixed(1)}%</span>
              </div>
              <Progress
                value={ratio * 100}
                indicatorClassName={
                  ratio >= 0.5
                    ? 'bg-success'
                    : ratio >= 0.25
                      ? 'bg-warning'
                      : 'bg-destructive'
                }
              />
            </div>
          )
        })}
      </CardContent>
    </Card>
  )
}

function LearningOutcomesCard({ learning }: { learning: GenericRow }) {
  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2 text-base">
          <GraduationCap className="h-4 w-4" aria-hidden="true" />
          Learning Outcomes
        </CardTitle>
        <CardDescription>Study sessions and question performance.</CardDescription>
      </CardHeader>
      <CardContent className="grid grid-cols-2 gap-4">
        <div>
          <p className="text-xs text-muted-foreground">Sessions completed</p>
          <p className="text-xl font-bold">{formatNumber(num(learning.sessions_completed))}</p>
        </div>
        <div>
          <p className="text-xs text-muted-foreground">Questions answered</p>
          <p className="text-xl font-bold">{formatNumber(num(learning.questions_answered))}</p>
        </div>
        <div>
          <p className="text-xs text-muted-foreground">Correct answers</p>
          <p className="text-xl font-bold text-success">
            {formatNumber(num(learning.questions_correct))}
          </p>
        </div>
        <div>
          <p className="text-xs text-muted-foreground">Accuracy</p>
          <p className="text-xl font-bold">{pct(learning.accuracy)}</p>
        </div>
      </CardContent>
    </Card>
  )
}

function FeedbackSummaryCard({ feedback }: { feedback: GenericRow }) {
  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2 text-base">
          <MessageSquare className="h-4 w-4" aria-hidden="true" />
          Feedback Summary
        </CardTitle>
        <CardDescription>Beta feedback received this period.</CardDescription>
      </CardHeader>
      <CardContent className="grid grid-cols-3 gap-4">
        <div>
          <p className="text-xs text-muted-foreground">Total</p>
          <p className="text-xl font-bold">{formatNumber(num(feedback.total))}</p>
        </div>
        <div>
          <p className="text-xs text-muted-foreground">Open</p>
          <p className="text-xl font-bold text-warning">{formatNumber(num(feedback.open))}</p>
        </div>
        <div>
          <p className="text-xs text-muted-foreground">Avg rating</p>
          <p className="text-xl font-bold">{num(feedback.avg_rating).toFixed(2)}</p>
        </div>
      </CardContent>
    </Card>
  )
}

function TopListCard({
  title,
  icon: Icon,
  items,
  emptyMessage,
}: {
  title: string
  icon: React.ComponentType<{ className?: string }>
  items: GenericRow[]
  emptyMessage: string
}) {
  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2 text-base">
          <Icon className="h-4 w-4" aria-hidden="true" />
          {title}
        </CardTitle>
        <CardDescription>Top 10 most recent items.</CardDescription>
      </CardHeader>
      <CardContent>
        {items.length === 0 ? (
          <p className="py-6 text-center text-sm text-muted-foreground">{emptyMessage}</p>
        ) : (
          <ol className="space-y-2">
            {items.slice(0, 10).map((item, i) => (
              <li
                key={i}
                className="flex items-start justify-between gap-3 border-b pb-2 last:border-0"
              >
                <div className="min-w-0 flex-1">
                  <p className="line-clamp-2 text-sm">
                    <span className="font-medium text-muted-foreground">#{i + 1}</span>{' '}
                    {str(item.title ?? item.summary ?? item.description ?? item.comment)}
                  </p>
                  {typeof item.created_at === 'string' && (
                    <p className="text-xs text-muted-foreground">
                      {formatDateTime(String(item.created_at))}
                    </p>
                  )}
                </div>
                {typeof item.severity === 'string' && item.severity && (
                  <Badge
                    variant={
                      String(item.severity) === 'critical'
                        ? 'destructive'
                        : String(item.severity) === 'high'
                          ? 'warning'
                          : 'secondary'
                    }
                    className="shrink-0 capitalize"
                  >
                    {String(item.severity)}
                  </Badge>
                )}
              </li>
            ))}
          </ol>
        )}
      </CardContent>
    </Card>
  )
}

function SystemHealthCard({ health }: { health: GenericRow }) {
  const status = String(health.status ?? 'healthy')
  const variant =
    status === 'healthy'
      ? 'success'
      : status === 'degraded'
        ? 'warning'
        : 'destructive'
  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2 text-base">
          <HeartPulse className="h-4 w-4" aria-hidden="true" />
          System Health
        </CardTitle>
        <CardDescription>Platform health at the end of the period.</CardDescription>
      </CardHeader>
      <CardContent className="grid grid-cols-2 gap-4">
        <div>
          <p className="text-xs text-muted-foreground">Status</p>
          <Badge variant={variant as 'success' | 'warning' | 'destructive'} className="mt-1 capitalize">
            {status}
          </Badge>
        </div>
        <div>
          <p className="text-xs text-muted-foreground">Outbox pending</p>
          <p className="text-xl font-bold">{formatNumber(num(health.outbox_pending))}</p>
        </div>
        <div>
          <p className="text-xs text-muted-foreground">Dead letters</p>
          <p className="text-xl font-bold text-destructive">
            {formatNumber(num(health.dead_letters))}
          </p>
        </div>
        <div>
          <p className="text-xs text-muted-foreground">Active workers</p>
          <p className="text-xl font-bold">{formatNumber(num(health.active_workers))}</p>
        </div>
      </CardContent>
    </Card>
  )
}

function ReportSkeleton() {
  return (
    <div className="space-y-6" role="status" aria-label="Loading report">
      <Skeleton className="h-10 w-72" />
      <Skeleton className="h-20 w-full" />
      <div className="grid gap-4 md:grid-cols-2">
        {Array.from({ length: 4 }).map((_, i) => (
          <Skeleton key={i} className="h-40 w-full" />
        ))}
      </div>
    </div>
  )
}

export default function ReportsPage() {
  const [period, setPeriod] = React.useState<Period>('weekly')
  const { data, isLoading, isError, error, refetch } = useBetaReport(period)
  const generateMutation = useGenerateReport()

  const handleGenerate = async () => {
    try {
      toast.info(`Generating ${period} report…`)
      await generateMutation.mutateAsync(period)
      toast.success(`${period.charAt(0).toUpperCase() + period.slice(1)} report generated`)
    } catch {
      toast.error('Failed to generate report')
    }
  }

  const periodIcon =
    period === 'daily' ? CalendarDays : period === 'weekly' ? CalendarRange : CalendarClock

  return (
    <div className="space-y-6">
      <header className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h1 className="flex items-center gap-2 text-2xl font-bold tracking-tight">
            <FileText className="h-6 w-6 text-primary" aria-hidden="true" />
            Reports
          </h1>
          <p className="text-sm text-muted-foreground">
            Periodic beta reports — growth, retention, learning, and system health.
          </p>
        </div>
        <div className="flex items-center gap-3">
          <Tabs value={period} onValueChange={(v) => setPeriod(v as Period)}>
            <TabsList>
              <TabsTrigger value="daily">Daily</TabsTrigger>
              <TabsTrigger value="weekly">Weekly</TabsTrigger>
              <TabsTrigger value="monthly">Monthly</TabsTrigger>
            </TabsList>
          </Tabs>
          <Button
            onClick={handleGenerate}
            loading={generateMutation.isPending}
            leftIcon={<Sparkles className="h-4 w-4" aria-hidden="true" />}
          >
            Generate Report
          </Button>
        </div>
      </header>

      {isLoading ? (
        <ReportSkeleton />
      ) : isError || !data ? (
        <ErrorState
          title="Failed to load report"
          description={`We couldn't fetch the ${period} report.`}
          error={error as Error | undefined}
          onRetry={() => refetch()}
        />
      ) : (
        <ReportContent data={data} periodIcon={periodIcon} />
      )}
    </div>
  )
}

function ReportContent({
  data,
  periodIcon: PeriodIcon,
}: {
  data: BetaReport
  periodIcon: React.ComponentType<{ className?: string }>
}) {
  const growth = (data.growth ?? {}) as GenericRow
  const retention = (data.retention ?? {}) as Record<string, number>
  const learning = (data.learning_outcomes ?? {}) as GenericRow
  const feedback = (data.feedback_summary ?? {}) as GenericRow
  const topBugs = (data.top_bugs ?? []) as GenericRow[]
  const topRequests = (data.top_requests ?? []) as GenericRow[]
  const systemHealth = (data.system_health ?? {}) as GenericRow

  return (
    <>
      <Card>
        <CardContent className="flex flex-col gap-3 p-4 sm:flex-row sm:items-center sm:justify-between">
          <div className="flex items-center gap-3">
            <PeriodIcon className="h-5 w-5 text-muted-foreground" aria-hidden="true" />
            <div>
              <p className="text-sm font-semibold capitalize">{data.period} report</p>
              <p className="text-xs text-muted-foreground">
                {formatDateTime(data.period_start)} → {formatDateTime(data.period_end)}
              </p>
            </div>
          </div>
          <p className="text-xs text-muted-foreground">
            Generated at{' '}
            <time dateTime={data.generated_at} className="font-medium text-foreground">
              {formatDateTime(data.generated_at)}
            </time>
          </p>
        </CardContent>
      </Card>

      <section className="grid gap-4 md:grid-cols-2">
        <GrowthCard growth={growth} />
        <RetentionCard retention={retention} />
        <LearningOutcomesCard learning={learning} />
        <FeedbackSummaryCard feedback={feedback} />
      </section>

      <section className="grid gap-4 md:grid-cols-2">
        <TopListCard
          title="Top Bugs"
          icon={Bug}
          items={topBugs}
          emptyMessage="No bugs reported in this period."
        />
        <TopListCard
          title="Top Requests"
          icon={Lightbulb}
          items={topRequests}
          emptyMessage="No feature requests in this period."
        />
      </section>

      <section
        aria-label="System health"
        className={cn('grid gap-4 md:grid-cols-2')}
      >
        <SystemHealthCard health={systemHealth} />
        {(!growth || Object.keys(growth).length === 0) &&
          (!retention || Object.keys(retention).length === 0) &&
          (!learning || Object.keys(learning).length === 0) &&
          (!feedback || Object.keys(feedback).length === 0) &&
          topBugs.length === 0 &&
          topRequests.length === 0 && (
            <EmptyState
              icon={FileText}
              title="No report data yet"
              description="Generate the report to populate this view."
            />
          )}
      </section>
    </>
  )
}
