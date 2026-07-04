'use client'

import * as React from 'react'
import { Filter, TrendingDown, ArrowRight, Layers } from 'lucide-react'

import {
  useRegistrationFunnel,
  useRetentionCohorts,
} from '@/hooks/use-beta-ops'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Skeleton } from '@/components/ui/skeleton'
import { ErrorState } from '@/components/ui/error-state'
import { EmptyState } from '@/components/ui/empty-state'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { cn } from '@/lib/cn'
import { formatNumber } from '@/lib/format'
import type { FunnelStep, RetentionCohort } from '@/lib/beta-ops-api'

const DAYS_OPTIONS: Array<{ label: string; value: number }> = [
  { label: '7 days', value: 7 },
  { label: '30 days', value: 30 },
  { label: '90 days', value: 90 },
]

const PRETTY_STEP: Record<string, string> = {
  invite_sent: 'Invite Sent',
  invite_opened: 'Invite Opened',
  invite_accepted: 'Invite Accepted',
  registration_started: 'Registration Started',
  registration_completed: 'Registration Completed',
  email_verified: 'Email Verified',
  onboarding_started: 'Onboarding Started',
  onboarding_completed: 'Onboarding Completed',
  first_study_session: 'First Study Session',
  first_question_answered: 'First Question Answered',
  day_1_retention: 'Day 1 Retention',
}

function prettyStep(step: string): string {
  return PRETTY_STEP[step] ?? step.replace(/_/g, ' ').replace(/\b\w/g, (c) => c.toUpperCase())
}

function formatMinutes(minutes: number | null): string {
  if (minutes === null || minutes === undefined) return '—'
  if (minutes < 60) return `${minutes.toFixed(0)}m`
  const h = Math.floor(minutes / 60)
  const m = Math.round(minutes % 60)
  if (h < 24) return `${h}h ${m}m`
  const d = Math.floor(h / 24)
  return `${d}d ${h % 24}h`
}

function FunnelStepRow({
  step,
  maxCount,
  isBiggestDrop,
}: {
  step: FunnelStep
  maxCount: number
  isBiggestDrop: boolean
}) {
  const widthPct = maxCount > 0 ? Math.max((step.count / maxCount) * 100, 6) : 0

  return (
    <article
      className={cn(
        'rounded-lg border p-4 transition-colors',
        isBiggestDrop
          ? 'border-destructive/50 bg-destructive/5'
          : 'border-border',
      )}
      aria-label={`Funnel step ${prettyStep(step.step)}`}
    >
      <div className="flex items-start justify-between gap-4">
        <div className="min-w-0 flex-1">
          <div className="flex items-center gap-2">
            <h3 className="truncate text-sm font-semibold">{prettyStep(step.step)}</h3>
            {isBiggestDrop && (
              <Badge variant="destructive" className="shrink-0">
                <TrendingDown className="mr-1 h-3 w-3" aria-hidden="true" />
                Biggest drop
              </Badge>
            )}
          </div>
          <p className="mt-0.5 text-xs text-muted-foreground">
            {formatNumber(step.count)} users
          </p>
        </div>
        <div className="text-right">
          <p className="text-sm font-bold">{step.cumulative_pct.toFixed(1)}%</p>
          <p className="text-xs text-muted-foreground">cumulative</p>
        </div>
      </div>

      <div className="mt-3" aria-hidden="true">
        <div className="h-3 w-full overflow-hidden rounded-full bg-muted">
          <div
            className={cn(
              'h-full rounded-full transition-all',
              isBiggestDrop ? 'bg-destructive' : 'bg-primary',
            )}
            style={{ width: `${widthPct}%` }}
          />
        </div>
      </div>

      <dl className="mt-3 grid grid-cols-2 gap-2 text-xs sm:grid-cols-3">
        <div>
          <dt className="text-muted-foreground">Step conv.</dt>
          <dd className="font-medium">{step.step_pct.toFixed(1)}%</dd>
        </div>
        <div>
          <dt className="text-muted-foreground">Cumulative</dt>
          <dd className="font-medium">{step.cumulative_pct.toFixed(1)}%</dd>
        </div>
        <div>
          <dt className="text-muted-foreground">Median time</dt>
          <dd className="font-medium">{formatMinutes(step.median_time_from_previous_minutes)}</dd>
        </div>
      </dl>
    </article>
  )
}

function FunnelSkeleton() {
  return (
    <div className="space-y-4" role="status" aria-label="Loading funnel">
      <Skeleton className="h-24 w-full" />
      <div className="space-y-3">
        {Array.from({ length: 5 }).map((_, i) => (
          <Skeleton key={i} className="h-28 w-full" />
        ))}
      </div>
    </div>
  )
}

function RetentionHeatmapCell({ value, max }: { value: number; max: number }) {
  // Heatmap gradient: red (low) → amber → green (high)
  const ratio = max > 0 ? value / max : 0
  let bg = 'bg-muted/40'
  let text = 'text-muted-foreground'
  if (ratio > 0.66) {
    bg = 'bg-success/20'
    text = 'text-success-foreground'
  } else if (ratio > 0.33) {
    bg = 'bg-warning/20'
  } else if (ratio > 0) {
    bg = 'bg-destructive/15 text-destructive'
  }
  return (
    <td
      className={cn('px-3 py-2 text-center text-sm font-medium tabular-nums', bg, text)}
      title={`${value} users`}
    >
      {value === 0 ? '—' : value}
    </td>
  )
}

function RetentionTable({ cohorts }: { cohorts: RetentionCohort[] }) {
  if (cohorts.length === 0) {
    return (
      <EmptyState
        icon={Layers}
        title="No retention cohorts"
        description="Retention cohort data is not yet available for the selected period."
      />
    )
  }
  const maxRetention = Math.max(
    ...cohorts.flatMap((c) => [c.week_0, c.week_1, c.week_2, c.week_3, c.week_4]),
    1,
  )

  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-base">Weekly Retention Cohorts</CardTitle>
        <CardDescription>
          Each row is a registration cohort; columns show users retained at week N.
        </CardDescription>
      </CardHeader>
      <CardContent>
        <div className="overflow-x-auto">
          <table className="w-full border-separate border-spacing-0 text-left text-sm">
            <thead>
              <tr className="text-xs uppercase tracking-wider text-muted-foreground">
                <th scope="col" className="px-3 py-2 font-semibold">Cohort week</th>
                <th scope="col" className="px-3 py-2 text-center font-semibold">Size</th>
                <th scope="col" className="px-3 py-2 text-center font-semibold">Week 0</th>
                <th scope="col" className="px-3 py-2 text-center font-semibold">Week 1</th>
                <th scope="col" className="px-3 py-2 text-center font-semibold">Week 2</th>
                <th scope="col" className="px-3 py-2 text-center font-semibold">Week 3</th>
                <th scope="col" className="px-3 py-2 text-center font-semibold">Week 4</th>
              </tr>
            </thead>
            <tbody>
              {cohorts.map((c) => (
                <tr key={c.cohort_week} className="border-t border-border">
                  <td className="whitespace-nowrap px-3 py-2 font-mono text-xs">
                    {c.cohort_week}
                  </td>
                  <td className="px-3 py-2 text-center font-medium tabular-nums">
                    {formatNumber(c.cohort_size)}
                  </td>
                  <RetentionHeatmapCell value={c.week_0} max={maxRetention} />
                  <RetentionHeatmapCell value={c.week_1} max={maxRetention} />
                  <RetentionHeatmapCell value={c.week_2} max={maxRetention} />
                  <RetentionHeatmapCell value={c.week_3} max={maxRetention} />
                  <RetentionHeatmapCell value={c.week_4} max={maxRetention} />
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        <p className="mt-3 text-xs text-muted-foreground">
          Heatmap colors: green = strong retention, amber = moderate, red = low.
        </p>
      </CardContent>
    </Card>
  )
}

export default function FunnelPage() {
  const [days, setDays] = React.useState(30)
  const funnelQuery = useRegistrationFunnel(days)
  const retentionQuery = useRetentionCohorts(8)

  return (
    <div className="space-y-6">
      <header>
        <h1 className="text-2xl font-bold tracking-tight">Funnel &amp; Retention</h1>
        <p className="text-sm text-muted-foreground">
          Registration funnel performance and weekly cohort retention.
        </p>
      </header>

      <Tabs defaultValue="funnel">
        <TabsList>
          <TabsTrigger value="funnel">Registration Funnel</TabsTrigger>
          <TabsTrigger value="retention">Retention Cohorts</TabsTrigger>
        </TabsList>

        <TabsContent value="funnel" className="space-y-4">
          <Card>
            <CardHeader className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
              <div>
                <CardTitle className="flex items-center gap-2 text-base">
                  <Filter className="h-4 w-4" aria-hidden="true" />
                  Time window
                </CardTitle>
                <CardDescription>
                  Filter funnel data for the last N days.
                </CardDescription>
              </div>
              <div className="flex gap-2" role="group" aria-label="Days filter">
                {DAYS_OPTIONS.map((opt) => (
                  <Button
                    key={opt.value}
                    size="sm"
                    variant={days === opt.value ? 'default' : 'outline'}
                    onClick={() => setDays(opt.value)}
                    aria-pressed={days === opt.value}
                  >
                    {opt.label}
                  </Button>
                ))}
              </div>
            </CardHeader>
          </Card>

          {funnelQuery.isLoading ? (
            <FunnelSkeleton />
          ) : funnelQuery.isError || !funnelQuery.data ? (
            <ErrorState
              title="Failed to load funnel"
              description="We couldn't fetch the registration funnel data."
              error={funnelQuery.error as Error | undefined}
              onRetry={() => funnelQuery.refetch()}
            />
          ) : (
            <>
              <section className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
                <Card>
                  <CardHeader className="pb-2">
                    <CardDescription>Overall conversion</CardDescription>
                    <p className="text-3xl font-bold text-success">
                      {funnelQuery.data.overall_conversion.toFixed(1)}%
                    </p>
                  </CardHeader>
                  <CardContent>
                    <p className="text-xs text-muted-foreground">
                      From invite sent to last step.
                    </p>
                  </CardContent>
                </Card>
                <Card>
                  <CardHeader className="pb-2">
                    <CardDescription>Avg time to first question</CardDescription>
                    <p className="text-3xl font-bold">
                      {formatMinutes(funnelQuery.data.avg_time_to_first_question_minutes)}
                    </p>
                  </CardHeader>
                  <CardContent>
                    <p className="text-xs text-muted-foreground">
                      Median minutes across all users.
                    </p>
                  </CardContent>
                </Card>
                <Card>
                  <CardHeader className="pb-2">
                    <CardDescription>Biggest drop step</CardDescription>
                    <p className="text-lg font-bold text-destructive">
                      {funnelQuery.data.biggest_drop_step
                        ? prettyStep(funnelQuery.data.biggest_drop_step)
                        : '—'}
                    </p>
                  </CardHeader>
                  <CardContent>
                    <p className="flex items-center gap-1 text-xs text-muted-foreground">
                      <ArrowRight className="h-3 w-3" aria-hidden="true" />
                      Focus your re-engagement efforts here.
                    </p>
                  </CardContent>
                </Card>
              </section>

              <section aria-label="Funnel steps" className="space-y-3">
                <h2 className="text-lg font-semibold">Steps</h2>
                {funnelQuery.data.steps.length === 0 ? (
                  <EmptyState
                    icon={Layers}
                    title="No funnel data"
                    description="No registration events recorded in the selected window."
                  />
                ) : (
                  (() => {
                    const maxCount = Math.max(
                      ...funnelQuery.data.steps.map((s) => s.count),
                      1,
                    )
                    return funnelQuery.data.steps.map((step) => (
                      <FunnelStepRow
                        key={step.step}
                        step={step}
                        maxCount={maxCount}
                        isBiggestDrop={step.step === funnelQuery.data?.biggest_drop_step}
                      />
                    ))
                  })()
                )}
              </section>
            </>
          )}
        </TabsContent>

        <TabsContent value="retention" className="space-y-4">
          {retentionQuery.isLoading ? (
            <div className="space-y-2" role="status" aria-label="Loading retention">
              <Skeleton className="h-64 w-full" />
            </div>
          ) : retentionQuery.isError || !retentionQuery.data ? (
            <ErrorState
              title="Failed to load retention"
              description="We couldn't fetch the retention cohort data."
              error={retentionQuery.error as Error | undefined}
              onRetry={() => retentionQuery.refetch()}
            />
          ) : (
            <RetentionTable cohorts={retentionQuery.data} />
          )}
        </TabsContent>
      </Tabs>
    </div>
  )
}
