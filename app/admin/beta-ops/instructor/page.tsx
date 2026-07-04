'use client'

import * as React from 'react'
import {
  PieChart as RechartsPieChart,
  Pie,
  Cell,
  ResponsiveContainer,
  Tooltip,
  Legend,
} from 'recharts'
import {
  GraduationCap,
  Star,
  HelpCircle,
  Gauge,
  AlertTriangle,
  Bug,
  Brain,
  BookOpen,
} from 'lucide-react'

import { useInstructorAnalytics } from '@/hooks/use-beta-ops'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Skeleton } from '@/components/ui/skeleton'
import { Progress } from '@/components/ui/progress'
import { ErrorState } from '@/components/ui/error-state'
import { EmptyState } from '@/components/ui/empty-state'
import { formatNumber } from '@/lib/format'

const PIE_COLORS = ['#3b82f6', '#22c55e', '#f59e0b', '#ef4444', '#a855f7', '#06b6d4', '#ec4899']

// ============================================================
// Helpers — pull typed values out of the loosely-typed API
// ============================================================

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

function numFormat(v: unknown, decimals = 0): string {
  const n = num(v)
  return formatNumber(Number(n.toFixed(decimals)))
}

function pctFormat(v: unknown, decimals = 1): string {
  const n = num(v)
  // The API may return 0-1 or 0-100 — detect.
  const ratio = n > 1 ? n / 100 : n
  return `${(ratio * 100).toFixed(decimals)}%`
}

interface MetricCardProps {
  label: string
  value: string
  hint?: string
  icon: React.ComponentType<{ className?: string }>
}

function MetricCard({ label, value, hint, icon: Icon }: MetricCardProps) {
  return (
    <Card>
      <CardHeader className="pb-2">
        <div className="flex items-center justify-between">
          <CardDescription>{label}</CardDescription>
          <Icon className="h-4 w-4 text-muted-foreground" aria-hidden="true" />
        </div>
        <CardTitle className="text-3xl">{value}</CardTitle>
      </CardHeader>
      {hint && (
        <CardContent>
          <p className="text-xs text-muted-foreground">{hint}</p>
        </CardContent>
      )}
    </Card>
  )
}

interface GenericRow {
  [key: string]: unknown
}

function GenericTable({
  columns,
  rows,
  emptyMessage = 'No data available',
  renderCell,
}: {
  columns: Array<{ key: string; label: string; align?: 'left' | 'right' }>
  rows: GenericRow[]
  emptyMessage?: string
  renderCell?: (row: GenericRow, col: string) => React.ReactNode
}) {
  if (rows.length === 0) {
    return <p className="py-6 text-center text-sm text-muted-foreground">{emptyMessage}</p>
  }
  return (
    <div className="overflow-x-auto">
      <table className="w-full text-left text-sm">
        <thead>
          <tr className="border-b text-xs uppercase tracking-wider text-muted-foreground">
            {columns.map((c) => (
              <th
                key={c.key}
                scope="col"
                className={`px-3 py-2 font-semibold ${c.align === 'right' ? 'text-right' : ''}`}
              >
                {c.label}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rows.map((row, i) => (
            <tr key={i} className="border-b last:border-0">
              {columns.map((c) => (
                <td
                  key={c.key}
                  className={`px-3 py-2 ${c.align === 'right' ? 'text-right tabular-nums' : ''}`}
                >
                  {renderCell ? renderCell(row, c.key) : str(row[c.key])}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}

function InstructorSkeleton() {
  return (
    <div className="space-y-6" role="status" aria-label="Loading instructor analytics">
      <Skeleton className="h-10 w-72" />
      <div className="grid gap-4 md:grid-cols-2">
        {Array.from({ length: 4 }).map((_, i) => (
          <Skeleton key={i} className="h-32 w-full" />
        ))}
      </div>
      <Skeleton className="h-64 w-full" />
      <div className="grid gap-4 md:grid-cols-2">
        <Skeleton className="h-64 w-full" />
        <Skeleton className="h-64 w-full" />
      </div>
    </div>
  )
}

export default function InstructorPage() {
  const { data, isLoading, isError, error, refetch } = useInstructorAnalytics()

  if (isLoading) return <InstructorSkeleton />
  if (isError || !data) {
    return (
      <ErrorState
        title="Failed to load instructor analytics"
        description="We couldn't fetch the instructor analytics data."
        error={error as Error | undefined}
        onRetry={() => refetch()}
      />
    )
  }

  const contentQuality = (data.content_quality ?? {}) as GenericRow
  const conceptCoverage = (data.concept_coverage ?? {}) as GenericRow
  const questionQuality = (data.question_quality ?? {}) as GenericRow
  const explanationUsefulness = (data.explanation_usefulness ?? {}) as GenericRow
  const templateUsage = (data.template_usage ?? []) as GenericRow[]
  const poorPerforming = (data.poor_performing_concepts ?? []) as GenericRow[]
  const frequentlyMissed = (data.frequently_missed_questions ?? []) as GenericRow[]
  const misconceptions = (data.misconceptions ?? []) as GenericRow[]
  const difficultyBalance = (data.difficulty_balance ?? {}) as Record<string, number>

  const pieData = Object.entries(difficultyBalance).map(([name, value]) => ({
    name,
    value: num(value),
  }))

  const coveragePct = num(conceptCoverage.coverage_pct ?? conceptCoverage.coverage_percentage)
  const coverageRatio = coveragePct > 1 ? coveragePct / 100 : coveragePct

  return (
    <div className="space-y-6">
      <header>
        <h1 className="flex items-center gap-2 text-2xl font-bold tracking-tight">
          <GraduationCap className="h-6 w-6 text-primary" aria-hidden="true" />
          Instructor Analytics
        </h1>
        <p className="text-sm text-muted-foreground">
          Content quality, concept coverage, and question analytics for instructors.
        </p>
      </header>

      <section className="grid gap-4 md:grid-cols-2">
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-base">
              <Star className="h-4 w-4" aria-hidden="true" />
              Content Quality
            </CardTitle>
            <CardDescription>
              Average learner rating and feedback volume across published content.
            </CardDescription>
          </CardHeader>
          <CardContent className="grid grid-cols-2 gap-4">
            <div>
              <p className="text-xs text-muted-foreground">Average rating</p>
              <p className="text-2xl font-bold">
                {num(contentQuality.avg_rating, 0).toFixed(2)}
              </p>
            </div>
            <div>
              <p className="text-xs text-muted-foreground">Feedback count</p>
              <p className="text-2xl font-bold">
                {numFormat(contentQuality.feedback_count)}
              </p>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-base">
              <HelpCircle className="h-4 w-4" aria-hidden="true" />
              Question Quality
            </CardTitle>
            <CardDescription>
              Aggregate performance across all question templates.
            </CardDescription>
          </CardHeader>
          <CardContent className="grid grid-cols-2 gap-4">
            <div>
              <p className="text-xs text-muted-foreground">Templates analyzed</p>
              <p className="text-2xl font-bold">
                {numFormat(questionQuality.templates_analyzed)}
              </p>
            </div>
            <div>
              <p className="text-xs text-muted-foreground">Avg accuracy</p>
              <p className="text-2xl font-bold">
                {pctFormat(questionQuality.avg_accuracy_across_templates)}
              </p>
            </div>
          </CardContent>
        </Card>
      </section>

      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2 text-base">
            <BookOpen className="h-4 w-4" aria-hidden="true" />
            Concept Coverage
          </CardTitle>
          <CardDescription>
            Per-subject published vs total concepts.
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="mb-4 grid gap-4 sm:grid-cols-3">
            <div>
              <p className="text-xs text-muted-foreground">Subject</p>
              <p className="font-medium">{str(conceptCoverage.subject_id)}</p>
            </div>
            <div>
              <p className="text-xs text-muted-foreground">Total concepts</p>
              <p className="font-medium">{numFormat(conceptCoverage.total_concepts)}</p>
            </div>
            <div>
              <p className="text-xs text-muted-foreground">Published</p>
              <p className="font-medium">{numFormat(conceptCoverage.published_concepts)}</p>
            </div>
          </div>
          <div className="space-y-2">
            <div className="flex justify-between text-sm">
              <span className="text-muted-foreground">Coverage</span>
              <span className="font-medium">{(coverageRatio * 100).toFixed(1)}%</span>
            </div>
            <Progress value={coverageRatio * 100} />
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle className="text-base">Template Usage</CardTitle>
          <CardDescription>
            Performance of question templates currently in rotation.
          </CardDescription>
        </CardHeader>
        <CardContent>
          <GenericTable
            columns={[
              { key: 'template_version_id', label: 'Template' },
              { key: 'attempts', label: 'Attempts', align: 'right' },
              { key: 'correct', label: 'Correct', align: 'right' },
              { key: 'accuracy', label: 'Accuracy', align: 'right' },
              { key: 'avg_time_ms', label: 'Avg time (ms)', align: 'right' },
            ]}
            rows={templateUsage}
            emptyMessage="No template usage recorded yet."
            renderCell={(row, col) => {
              if (col === 'accuracy') {
                const v = num(row[col])
                const ratio = v > 1 ? v / 100 : v
                return (
                  <Badge variant={ratio >= 0.7 ? 'success' : ratio >= 0.4 ? 'warning' : 'destructive'}>
                    {(ratio * 100).toFixed(1)}%
                  </Badge>
                )
              }
              if (col === 'template_version_id') {
                return <span className="font-mono text-xs">{str(row[col])}</span>
              }
              return numFormat(row[col])
            }}
          />
        </CardContent>
      </Card>

      <section className="grid gap-4 md:grid-cols-2">
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-base">
              <Gauge className="h-4 w-4" aria-hidden="true" />
              Difficulty Balance
            </CardTitle>
            <CardDescription>
              Distribution of concepts across difficulty states.
            </CardDescription>
          </CardHeader>
          <CardContent>
            {pieData.length === 0 ? (
              <EmptyState
                icon={Gauge}
                title="No difficulty data"
                description="Concept difficulty distribution is not yet available."
              />
            ) : (
              <div className="h-64 w-full">
                <ResponsiveContainer width="100%" height="100%">
                  <RechartsPieChart aria-label="Difficulty distribution">
                    <Pie
                      data={pieData}
                      dataKey="value"
                      nameKey="name"
                      cx="50%"
                      cy="50%"
                      outerRadius={80}
                      label={({ name, value }) => `${name}: ${value}`}
                    >
                      {pieData.map((_, i) => (
                        <Cell key={i} fill={PIE_COLORS[i % PIE_COLORS.length]} />
                      ))}
                    </Pie>
                    <Tooltip
                      contentStyle={{
                        backgroundColor: 'hsl(var(--popover))',
                        border: '1px solid hsl(var(--border))',
                        borderRadius: '0.5rem',
                        fontSize: '12px',
                      }}
                    />
                    <Legend wrapperStyle={{ fontSize: '12px' }} />
                  </RechartsPieChart>
                </ResponsiveContainer>
              </div>
            )}
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-base">
              <Brain className="h-4 w-4" aria-hidden="true" />
              Explanation Usefulness
            </CardTitle>
            <CardDescription>
              How learners rate the usefulness of concept explanations.
            </CardDescription>
          </CardHeader>
          <CardContent className="grid grid-cols-2 gap-4">
            <div>
              <p className="text-xs text-muted-foreground">Avg rating</p>
              <p className="text-2xl font-bold">
                {num(explanationUsefulness.avg_rating, 0).toFixed(2)}
              </p>
            </div>
            <div>
              <p className="text-xs text-muted-foreground">Total ratings</p>
              <p className="text-2xl font-bold">
                {numFormat(explanationUsefulness.total_ratings)}
              </p>
            </div>
          </CardContent>
        </Card>
      </section>

      <section className="grid gap-4 md:grid-cols-2">
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-base">
              <AlertTriangle className="h-4 w-4 text-warning" aria-hidden="true" />
              Poor Performing Concepts
            </CardTitle>
            <CardDescription>
              Concepts where learners consistently struggle.
            </CardDescription>
          </CardHeader>
          <CardContent>
            <GenericTable
              columns={[
                { key: 'concept_id', label: 'Concept' },
                { key: 'avg_mastery', label: 'Avg mastery', align: 'right' },
                { key: 'attempts', label: 'Attempts', align: 'right' },
              ]}
              rows={poorPerforming}
              emptyMessage="No poor performing concepts — looking great!"
              renderCell={(row, col) => {
                if (col === 'concept_id')
                  return <span className="font-mono text-xs">{str(row[col])}</span>
                if (col === 'avg_mastery') return pctFormat(row[col])
                return numFormat(row[col])
              }}
            />
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-base">
              <Bug className="h-4 w-4 text-destructive" aria-hidden="true" />
              Frequently Missed Questions
            </CardTitle>
            <CardDescription>
              Questions with the highest miss rates.
            </CardDescription>
          </CardHeader>
          <CardContent>
            <GenericTable
              columns={[
                { key: 'question_id', label: 'Question' },
                { key: 'miss_rate', label: 'Miss rate', align: 'right' },
                { key: 'attempts', label: 'Attempts', align: 'right' },
              ]}
              rows={frequentlyMissed}
              emptyMessage="No frequently missed questions."
              renderCell={(row, col) => {
                if (col === 'question_id')
                  return <span className="font-mono text-xs">{str(row[col])}</span>
                if (col === 'miss_rate') return pctFormat(row[col])
                return numFormat(row[col])
              }}
            />
          </CardContent>
        </Card>
      </section>

      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2 text-base">
            <Brain className="h-4 w-4" aria-hidden="true" />
            Misconceptions
          </CardTitle>
          <CardDescription>
            Recurring learner misconceptions ordered by frequency.
          </CardDescription>
        </CardHeader>
        <CardContent>
          <GenericTable
            columns={[
              { key: 'misconception_id', label: 'Misconception' },
              { key: 'occurrences', label: 'Occurrences', align: 'right' },
            ]}
            rows={misconceptions}
            emptyMessage="No misconceptions recorded."
            renderCell={(row, col) => {
              if (col === 'misconception_id')
                return <span className="font-mono text-xs">{str(row[col])}</span>
              return numFormat(row[col])
            }}
          />
        </CardContent>
      </Card>
    </div>
  )
}
