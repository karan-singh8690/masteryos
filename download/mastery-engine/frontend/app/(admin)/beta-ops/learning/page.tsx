'use client'

import * as React from 'react'
import {
  LineChart as RechartsLineChart,
  Line,
  CartesianGrid,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
} from 'recharts'
import {
  GraduationCap,
  Clock,
  HelpCircle,
  Lightbulb,
  ThumbsUp,
  Brain,
  TrendingUp,
  ArrowUpCircle,
  ArrowDownCircle,
} from 'lucide-react'

import { useLearningEffectiveness } from '@/hooks/use-beta-ops'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Skeleton } from '@/components/ui/skeleton'
import { ErrorState } from '@/components/ui/error-state'
import { EmptyState } from '@/components/ui/empty-state'
import { Progress } from '@/components/ui/progress'
import { cn } from '@/lib/cn'
import { formatNumber } from '@/lib/format'
import type { LearningEffectiveness } from '@/lib/beta-ops-api'

interface MetricCardProps {
  label: string
  value: string
  hint?: string
  icon: React.ComponentType<{ className?: string }>
}

function MetricCard({ label, value, hint, icon: Icon }: MetricCardProps) {
  return (
    <Card hover>
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

interface ConceptRow {
  concept_id: string
  avg_mastery: number
  avg_confidence: number
  enrollment_count: number
}

function ConceptTable({
  title,
  rows,
  variant,
}: {
  title: string
  rows: ConceptRow[]
  variant: 'weak' | 'strong'
}) {
  const Icon = variant === 'weak' ? ArrowDownCircle : ArrowUpCircle
  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2 text-base">
          <Icon
            className={cn(
              'h-4 w-4',
              variant === 'weak' ? 'text-destructive' : 'text-success',
            )}
            aria-hidden="true"
          />
          {title}
        </CardTitle>
        <CardDescription>
          {variant === 'weak'
            ? 'Concepts with the lowest average mastery.'
            : 'Concepts with the highest average mastery.'}
        </CardDescription>
      </CardHeader>
      <CardContent>
        {rows.length === 0 ? (
          <p className="py-6 text-center text-sm text-muted-foreground">No data available</p>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-sm">
              <thead>
                <tr className="border-b text-xs uppercase tracking-wider text-muted-foreground">
                  <th scope="col" className="px-3 py-2 font-semibold">Concept ID</th>
                  <th scope="col" className="px-3 py-2 text-right font-semibold">Avg mastery</th>
                  <th scope="col" className="px-3 py-2 text-right font-semibold">Avg confidence</th>
                  <th scope="col" className="px-3 py-2 text-right font-semibold">Enrollments</th>
                </tr>
              </thead>
              <tbody>
                {rows.map((r) => (
                  <tr key={r.concept_id} className="border-b last:border-0">
                    <td className="px-3 py-2 font-mono text-xs">{r.concept_id}</td>
                    <td className="px-3 py-2 text-right tabular-nums">
                      <Badge
                        variant={
                          r.avg_mastery >= 0.7
                            ? 'success'
                            : r.avg_mastery >= 0.4
                              ? 'warning'
                              : 'destructive'
                        }
                      >
                        {(r.avg_mastery * 100).toFixed(0)}%
                      </Badge>
                    </td>
                    <td className="px-3 py-2 text-right tabular-nums text-muted-foreground">
                      {(r.avg_confidence * 100).toFixed(0)}%
                    </td>
                    <td className="px-3 py-2 text-right tabular-nums">
                      {formatNumber(r.enrollment_count)}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </CardContent>
    </Card>
  )
}

function LearningSkeleton() {
  return (
    <div className="space-y-6" role="status" aria-label="Loading learning insights">
      <Skeleton className="h-10 w-72" />
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
        {Array.from({ length: 6 }).map((_, i) => (
          <Skeleton key={i} className="h-28 w-full" />
        ))}
      </div>
      <Skeleton className="h-72 w-full" />
      <div className="grid gap-4 md:grid-cols-2">
        <Skeleton className="h-64 w-full" />
        <Skeleton className="h-64 w-full" />
      </div>
    </div>
  )
}

export default function LearningPage() {
  const { data, isLoading, isError, error, refetch } = useLearningEffectiveness()

  if (isLoading) return <LearningSkeleton />
  if (isError || !data) {
    return (
      <ErrorState
        title="Failed to load learning insights"
        description="We couldn't fetch the learning effectiveness data."
        error={error as Error | undefined}
        onRetry={() => refetch()}
      />
    )
  }

  const trendData = (data.interview_readiness_trend ?? []).map((p) => ({
    week: p.week,
    avg_readiness: Math.round(p.avg_readiness * 1000) / 10,
  }))

  return (
    <div className="space-y-6">
      <header>
        <h1 className="text-2xl font-bold tracking-tight">Learning Insights</h1>
        <p className="text-sm text-muted-foreground">
          Mastery growth, concept performance, and adaptive learning effectiveness.
        </p>
      </header>

      <section
        aria-label="Learning metrics"
        className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3"
      >
        <MetricCard
          label="Mastery Growth Avg"
          value={`${(data.mastery_growth_avg * 100).toFixed(1)}%`}
          icon={GraduationCap}
          hint="Average mastery improvement per learner"
        />
        <MetricCard
          label="Time to Mastery"
          value={data.time_to_mastery_hours !== null ? `${data.time_to_mastery_hours.toFixed(1)} hrs` : '—'}
          icon={Clock}
          hint="Median hours from enrolment to mastery"
        />
        <MetricCard
          label="Question Accuracy"
          value={`${(data.question_accuracy * 100).toFixed(1)}%`}
          icon={HelpCircle}
        />
        <MetricCard
          label="Hint Usage Rate"
          value={`${(data.hint_usage_rate * 100).toFixed(1)}%`}
          icon={Lightbulb}
          hint="Questions where learners used hints"
        />
        <MetricCard
          label="Recommendation Acceptance"
          value={`${(data.recommendation_acceptance * 100).toFixed(1)}%`}
          icon={ThumbsUp}
          hint="Adaptive suggestions accepted by learners"
        />
        <MetricCard
          label="Adaptive Queue Quality"
          value={`${(data.adaptive_queue_quality * 100).toFixed(1)}%`}
          icon={Brain}
          hint="Quality score of the adaptive queue"
        />
      </section>

      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2 text-base">
            <TrendingUp className="h-4 w-4" aria-hidden="true" />
            Interview Readiness Trend
          </CardTitle>
          <CardDescription>
            Weekly average interview readiness score across active beta learners.
          </CardDescription>
        </CardHeader>
        <CardContent>
          {trendData.length === 0 ? (
            <EmptyState
              icon={TrendingUp}
              title="No trend data"
              description="Interview readiness trend data is not yet available."
            />
          ) : (
            <div className="h-72 w-full">
              <ResponsiveContainer width="100%" height="100%">
                <RechartsLineChart data={trendData} aria-label="Interview readiness trend">
                  <CartesianGrid strokeDasharray="3 3" stroke="hsl(var(--border))" />
                  <XAxis
                    dataKey="week"
                    tick={{ fontSize: 11, fill: 'hsl(var(--muted-foreground))' }}
                    tickLine={false}
                    axisLine={false}
                  />
                  <YAxis
                    domain={[0, 100]}
                    tick={{ fontSize: 11, fill: 'hsl(var(--muted-foreground))' }}
                    tickLine={false}
                    axisLine={false}
                    tickFormatter={(v) => `${v}%`}
                  />
                  <Tooltip
                    contentStyle={{
                      backgroundColor: 'hsl(var(--popover))',
                      border: '1px solid hsl(var(--border))',
                      borderRadius: '0.5rem',
                      fontSize: '12px',
                    }}
                    formatter={(v: number) => [`${v}%`, 'Avg readiness']}
                  />
                  <Line
                    type="monotone"
                    dataKey="avg_readiness"
                    stroke="#3b82f6"
                    strokeWidth={2}
                    dot={{ r: 3 }}
                    activeDot={{ r: 5 }}
                  />
                </RechartsLineChart>
              </ResponsiveContainer>
            </div>
          )}
        </CardContent>
      </Card>

      <section className="grid gap-4 md:grid-cols-2">
        <ConceptTable title="Weak Concepts" rows={data.weak_concepts} variant="weak" />
        <ConceptTable title="Strong Concepts" rows={data.strong_concepts} variant="strong" />
      </section>

      <section className="grid gap-4 md:grid-cols-2">
        <Card>
          <CardHeader>
            <CardTitle className="text-base">Review Effectiveness</CardTitle>
            <CardDescription>
              How well spaced reviews reinforce previously mastered content.
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-3">
            <div className="flex items-center justify-between text-sm">
              <span className="text-muted-foreground">Score</span>
              <span className="text-2xl font-bold">
                {(data.review_effectiveness * 100).toFixed(1)}%
              </span>
            </div>
            <Progress
              value={data.review_effectiveness * 100}
              indicatorClassName="bg-success"
            />
          </CardContent>
        </Card>
        <Card>
          <CardHeader>
            <CardTitle className="text-base">Average Confidence</CardTitle>
            <CardDescription>
              Self-reported learner confidence across all concepts.
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-3">
            <div className="flex items-center justify-between text-sm">
              <span className="text-muted-foreground">Score</span>
              <span className="text-2xl font-bold">
                {(data.average_confidence * 100).toFixed(1)}%
              </span>
            </div>
            <Progress value={data.average_confidence * 100} />
          </CardContent>
        </Card>
      </section>
    </div>
  )
}
