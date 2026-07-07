'use client'

import * as React from 'react'
import Link from 'next/link'
import { useQueryClient } from '@tanstack/react-query'
import {
  Area,
  AreaChart,
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts'
import {
  Flame,
  Target,
  ListTodo,
  Zap,
  ArrowRight,
  AlertTriangle,
  TrendingUp,
  CheckCircle2,
  Sparkles,
  BookOpen,
  FileText,
  ChevronRight,
} from 'lucide-react'

import { useDashboard } from '@/hooks/use-learner'
import { useAuth } from '@/providers/auth-provider'
import {
  WelcomeWidget,
  StreakWidget,
  DailyGoalWidget,
  QueueRemainingWidget,
  DueReviewsWidget,
  InterviewReadinessWidget,
  MasteryOverviewWidget,
  WeakConceptsWidget,
  StrongConceptsWidget,
  WeeklyLearningWidget,
  MonthlyLearningWidget,
  RecommendationCard,
  ContinueStudyingWidget,
  DashboardSkeleton,
  DashboardError,
  DashboardEmpty,
} from '@/components/learner/dashboard-widgets'
import { useAcceptRecommendation, useDismissRecommendation, useRecommendations } from '@/hooks/use-learner'
import { queryKey } from '@/lib/query-keys'
import { cn } from '@/lib/cn'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Progress } from '@/components/ui/progress'
import { EmptyState } from '@/components/ui/empty-state'
import { ROUTES } from '@/lib/constants'
import type { DashboardData, RecommendationWithDetails } from '@/types/learning'

// ============================================================
// Stat card — emerald accent variant
// ============================================================

interface StatCardProps {
  label: string
  value: string | number
  hint?: string
  icon: React.ComponentType<{ className?: string }>
  progress?: number
  accent?: 'emerald' | 'amber' | 'sky' | 'violet'
}

const ACCENT_STYLES: Record<
  NonNullable<StatCardProps['accent']>,
  { iconBg: string; iconColor: string; ring: string }
> = {
  emerald: {
    iconBg: 'bg-emerald-500/10',
    iconColor: 'text-emerald-500 dark:text-emerald-400',
    ring: 'ring-emerald-500/20',
  },
  amber: {
    iconBg: 'bg-amber-500/10',
    iconColor: 'text-amber-500 dark:text-amber-400',
    ring: 'ring-amber-500/20',
  },
  sky: {
    iconBg: 'bg-sky-500/10',
    iconColor: 'text-sky-500 dark:text-sky-400',
    ring: 'ring-sky-500/20',
  },
  violet: {
    iconBg: 'bg-violet-500/10',
    iconColor: 'text-violet-500 dark:text-violet-400',
    ring: 'ring-violet-500/20',
  },
}

function StatCard({ label, value, hint, icon: Icon, progress, accent = 'emerald' }: StatCardProps) {
  const styles = ACCENT_STYLES[accent]
  return (
    <Card className="overflow-hidden rounded-2xl border-border/60 transition-shadow hover:shadow-md">
      <CardContent className="p-5">
        <div className="flex items-start justify-between gap-3">
          <div className="space-y-1">
            <p className="text-xs font-medium uppercase tracking-wider text-muted-foreground">
              {label}
            </p>
            <p className="text-3xl font-bold tracking-tight">{value}</p>
          </div>
          <div
            className={cn(
              'flex h-10 w-10 shrink-0 items-center justify-center rounded-xl ring-1 ring-inset',
              styles.iconBg,
              styles.iconColor,
              styles.ring,
            )}
          >
            <Icon className="h-5 w-5" aria-hidden="true" />
          </div>
        </div>
        {typeof progress === 'number' && (
          <div className="mt-4">
            <Progress value={progress} className="h-1.5" />
          </div>
        )}
        {hint && <p className="mt-3 text-xs text-muted-foreground">{hint}</p>}
      </CardContent>
    </Card>
  )
}

// ============================================================
// Mastery overview — Recharts area chart
// ============================================================

interface MasteryOverviewProps {
  data: { date: string; value: number }[]
  readiness: number
}

function MasteryOverviewChart({ data, readiness }: MasteryOverviewProps) {
  const chartData = React.useMemo(
    () =>
      data.map((d) => ({
        date: new Date(d.date).toLocaleDateString('en-US', { month: 'short', day: 'numeric' }),
        value: Math.round(d.value * 100),
      })),
    [data],
  )

  const hasData = chartData.length > 0

  return (
    <Card className="rounded-2xl border-border/60">
      <CardHeader className="flex flex-row items-start justify-between gap-2 pb-2">
        <div className="space-y-1">
          <CardTitle className="text-base font-semibold">Mastery Overview</CardTitle>
          <CardDescription>Last 30 days of mastery progression</CardDescription>
        </div>
        <div className="flex items-center gap-1.5 rounded-full bg-emerald-500/10 px-2.5 py-1 text-xs font-semibold text-emerald-600 ring-1 ring-inset ring-emerald-500/20 dark:text-emerald-400">
          <TrendingUp className="h-3.5 w-3.5" aria-hidden="true" />
          {Math.round(readiness * 100)}% ready
        </div>
      </CardHeader>
      <CardContent>
        {hasData ? (
          <div className="h-[220px] w-full">
            <ResponsiveContainer width="100%" height="100%">
              <AreaChart data={chartData} margin={{ top: 10, right: 4, left: 4, bottom: 0 }}>
                <defs>
                  <linearGradient id="masteryOverviewGradient" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="#10B981" stopOpacity={0.35} />
                    <stop offset="95%" stopColor="#10B981" stopOpacity={0} />
                  </linearGradient>
                </defs>
                <CartesianGrid
                  strokeDasharray="3 3"
                  stroke="hsl(var(--border))"
                  strokeOpacity={0.5}
                  vertical={false}
                />
                <XAxis
                  dataKey="date"
                  tick={{ fontSize: 11, fill: 'hsl(var(--muted-foreground))' }}
                  tickLine={false}
                  axisLine={false}
                  minTickGap={24}
                />
                <YAxis
                  tick={{ fontSize: 11, fill: 'hsl(var(--muted-foreground))' }}
                  tickLine={false}
                  axisLine={false}
                  domain={[0, 100]}
                  tickFormatter={(v) => `${v}%`}
                  width={36}
                />
                <Tooltip
                  contentStyle={{
                    backgroundColor: 'hsl(var(--popover))',
                    border: '1px solid hsl(var(--border))',
                    borderRadius: '0.75rem',
                    fontSize: '12px',
                    boxShadow: '0 4px 12px rgba(0,0,0,0.08)',
                  }}
                  labelStyle={{ color: 'hsl(var(--muted-foreground))' }}
                  formatter={(value: number) => [`${value}%`, 'Mastery']}
                />
                <Area
                  type="monotone"
                  dataKey="value"
                  stroke="#10B981"
                  strokeWidth={2.5}
                  fill="url(#masteryOverviewGradient)"
                  dot={false}
                  activeDot={{
                    r: 4,
                    fill: '#10B981',
                    stroke: 'hsl(var(--background))',
                    strokeWidth: 2,
                  }}
                />
              </AreaChart>
            </ResponsiveContainer>
          </div>
        ) : (
          <div className="flex h-[220px] items-center justify-center">
            <EmptyState
              icon={TrendingUp}
              title="No mastery data yet"
              description="Start studying to see your mastery progression over time."
            />
          </div>
        )}
      </CardContent>
    </Card>
  )
}

// ============================================================
// Weekly learning activity — Recharts bar chart
// ============================================================

function WeeklyLearningChart({ data }: { data: { date: string; value: number }[] }) {
  const chartData = React.useMemo(
    () =>
      data.map((d) => ({
        label: new Date(d.date).toLocaleDateString('en-US', { weekday: 'short' }),
        value: d.value,
      })),
    [data],
  )

  const hasData = chartData.length > 0
  const maxValue = React.useMemo(
    () => (hasData ? Math.max(...chartData.map((d) => d.value), 1) : 1),
    [chartData, hasData],
  )

  return (
    <Card className="rounded-2xl border-border/60">
      <CardHeader className="flex flex-row items-start justify-between gap-2 pb-2">
        <div className="space-y-1">
          <CardTitle className="text-base font-semibold">Weekly Learning Activity</CardTitle>
          <CardDescription>Questions answered per day</CardDescription>
        </div>
        <div className="flex items-center gap-1.5 rounded-full bg-emerald-500/10 px-2.5 py-1 text-xs font-semibold text-emerald-600 ring-1 ring-inset ring-emerald-500/20 dark:text-emerald-400">
          <Sparkles className="h-3.5 w-3.5" aria-hidden="true" />
          {chartData.reduce((sum, d) => sum + d.value, 0)} this week
        </div>
      </CardHeader>
      <CardContent>
        {hasData ? (
          <div className="h-[220px] w-full">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={chartData} margin={{ top: 10, right: 4, left: 4, bottom: 0 }}>
                <defs>
                  <linearGradient id="weeklyBarGradient" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="0%" stopColor="#10B981" />
                    <stop offset="100%" stopColor="#14B8A6" />
                  </linearGradient>
                </defs>
                <CartesianGrid
                  strokeDasharray="3 3"
                  stroke="hsl(var(--border))"
                  strokeOpacity={0.5}
                  vertical={false}
                />
                <XAxis
                  dataKey="label"
                  tick={{ fontSize: 11, fill: 'hsl(var(--muted-foreground))' }}
                  tickLine={false}
                  axisLine={false}
                />
                <YAxis
                  tick={{ fontSize: 11, fill: 'hsl(var(--muted-foreground))' }}
                  tickLine={false}
                  axisLine={false}
                  allowDecimals={false}
                  width={28}
                />
                <Tooltip
                  contentStyle={{
                    backgroundColor: 'hsl(var(--popover))',
                    border: '1px solid hsl(var(--border))',
                    borderRadius: '0.75rem',
                    fontSize: '12px',
                    boxShadow: '0 4px 12px rgba(0,0,0,0.08)',
                  }}
                  cursor={{ fill: 'hsl(var(--muted))', opacity: 0.4 }}
                  formatter={(value: number) => [`${value} questions`, 'Answered']}
                />
                <Bar dataKey="value" radius={[6, 6, 0, 0]} maxBarSize={48}>
                  {chartData.map((entry, index) => {
                    const isPeak = entry.value === maxValue && entry.value > 0
                    return (
                      <Cell
                        key={index}
                        fill={isPeak ? '#10B981' : 'url(#weeklyBarGradient)'}
                      />
                    )
                  })}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </div>
        ) : (
          <div className="flex h-[220px] items-center justify-center">
            <EmptyState
              icon={Zap}
              title="No activity yet"
              description="Answer questions to see your weekly learning activity here."
            />
          </div>
        )}
      </CardContent>
    </Card>
  )
}

// ============================================================
// Weak concepts — emerald-accented list
// ============================================================

function WeakConceptsCard({ concepts }: { concepts: DashboardData['weak_concepts'] }) {
  return (
    <Card className="rounded-2xl border-border/60">
      <CardHeader className="flex flex-row items-start justify-between gap-2 pb-3">
        <div className="space-y-1">
          <CardTitle className="flex items-center gap-2 text-base font-semibold">
            <AlertTriangle className="h-4 w-4 text-amber-500" aria-hidden="true" />
            Weak Concepts
          </CardTitle>
          <CardDescription>Focus on these to boost your mastery</CardDescription>
        </div>
        {concepts.length > 0 && (
          <Badge variant="destructive" className="rounded-full">
            {concepts.length} to review
          </Badge>
        )}
      </CardHeader>
      <CardContent>
        {concepts.length === 0 ? (
          <EmptyState
            icon={CheckCircle2}
            title="No weak concepts"
            description="Great job! You're on top of everything."
          />
        ) : (
          <ul className="space-y-2" role="list">
            {concepts.slice(0, 5).map((concept) => {
              const pct = Math.round(concept.mastery_score_combined * 100)
              const severityColor =
                concept.weakness_severity === 'critical'
                  ? 'bg-red-500'
                  : concept.weakness_severity === 'high'
                    ? 'bg-orange-500'
                    : concept.weakness_severity === 'medium'
                      ? 'bg-amber-500'
                      : 'bg-emerald-500'
              return (
                <li
                  key={concept.concept_id}
                  className="group flex items-center gap-3 rounded-xl border border-border/50 bg-muted/30 px-3 py-2.5 transition-colors hover:bg-muted/60"
                >
                  <div className="flex-1 space-y-1">
                    <p className="truncate text-sm font-medium">{concept.concept_name || concept.concept_id}</p>
                    <div className="flex items-center gap-2">
                      <div className="h-1.5 flex-1 overflow-hidden rounded-full bg-muted">
                        <div
                          className={cn('h-full rounded-full transition-all', severityColor)}
                          style={{ width: `${pct}%` }}
                        />
                      </div>
                      <span className="text-xs font-medium text-muted-foreground">{pct}%</span>
                    </div>
                  </div>
                  <ArrowRight
                    className="h-4 w-4 text-muted-foreground opacity-0 transition-opacity group-hover:opacity-100"
                    aria-hidden="true"
                  />
                </li>
              )
            })}
          </ul>
        )}
      </CardContent>
    </Card>
  )
}

// ============================================================
// Recommendations card — emerald accent
// ============================================================

interface RecommendationsCardProps {
  recommendations: RecommendationWithDetails[]
  onAccept: (id: string) => void
  onDismiss: (id: string) => void
  isAccepting?: boolean
  isDismissing?: boolean
}

function RecommendationsCard({
  recommendations,
  onAccept,
  onDismiss,
  isAccepting,
  isDismissing,
}: RecommendationsCardProps) {
  const top = recommendations?.[0] || null

  return (
    <Card className="rounded-2xl border-border/60">
      <CardHeader className="pb-3">
        <CardTitle className="flex items-center gap-2 text-base font-semibold">
          <span className="flex h-7 w-7 items-center justify-center rounded-lg bg-emerald-500/10 text-emerald-500 ring-1 ring-inset ring-emerald-500/20 dark:text-emerald-400">
            <Sparkles className="h-4 w-4" aria-hidden="true" />
          </span>
          Recommendations
        </CardTitle>
        <CardDescription>AI-powered next steps for you</CardDescription>
      </CardHeader>
      <CardContent>
        {top ? (
          <div className="space-y-4">
            <div className="rounded-xl border border-emerald-500/20 bg-emerald-500/5 p-4">
              <div className="flex items-start gap-3">
                <TrendingUp className="mt-0.5 h-5 w-5 shrink-0 text-emerald-500 dark:text-emerald-400" aria-hidden="true" />
                <div className="flex-1 space-y-1">
                  <p className="text-sm font-medium text-foreground">{top.reason}</p>
                  <p className="text-xs uppercase tracking-wide text-muted-foreground">
                    {top.recommendation_type?.replace(/_/g, ' ')}
                  </p>
                </div>
              </div>
            </div>
            <div className="flex gap-2">
              <Button
                size="sm"
                onClick={() => onAccept(top.id)}
                loading={isAccepting}
                className="flex-1 bg-gradient-to-r from-emerald-500 to-teal-500 text-white shadow-sm hover:from-emerald-600 hover:to-teal-600"
              >
                Accept
              </Button>
              <Button
                size="sm"
                variant="outline"
                onClick={() => onDismiss(top.id)}
                disabled={isDismissing}
                className="flex-1"
              >
                Dismiss
              </Button>
            </div>
          </div>
        ) : (
          <EmptyState
            icon={Sparkles}
            title="No recommendations right now"
            description="Check back after your next study session for AI-powered next steps."
          />
        )}
      </CardContent>
    </Card>
  )
}

// ============================================================
// Quick actions card
// ============================================================

function QuickActionsCard({ enrollmentId }: { enrollmentId: string | null }) {
  return (
    <Card className="rounded-2xl border-border/60">
      <CardHeader className="pb-3">
        <CardTitle className="text-base font-semibold">Continue Studying</CardTitle>
        <CardDescription>Pick up where you left off</CardDescription>
      </CardHeader>
      <CardContent className="space-y-2">
        {enrollmentId ? (
          <>
            <Button
              asChild
              className="w-full bg-gradient-to-r from-emerald-500 to-teal-500 text-white shadow-sm hover:from-emerald-600 hover:to-teal-600"
            >
              <Link href={`/study/start?enrollment=${enrollmentId}`}>
                Start a study session
                <ArrowRight className="ml-1 h-4 w-4" aria-hidden="true" />
              </Link>
            </Button>
            <Button asChild variant="outline" className="w-full">
              <Link href="/reviews">Review due concepts</Link>
            </Button>
          </>
        ) : (
          <EmptyState
            title="No active enrollment"
            description="Browse subjects to start learning."
            action={{
              label: 'Browse subjects',
              onClick: () => {
                if (typeof window !== 'undefined') {
                  window.location.href = '/subjects'
                }
              },
            }}
          />
        )}
      </CardContent>
    </Card>
  )
}

// ============================================================
// Dashboard page
// ============================================================

export default function DashboardPage() {
  const { user } = useAuth()
  const queryClient = useQueryClient()
  const { data: dashboard, isLoading, isError, refetch } = useDashboard()
  const { data: recommendations } = useRecommendations()
  const acceptMutation = useAcceptRecommendation()
  const dismissMutation = useDismissRecommendation()

  const displayName = user?.profile.display_name || 'there'

  if (isLoading) return <DashboardSkeleton />

  if (isError) return <DashboardError onRetry={() => refetch()} />

  if (!dashboard || !dashboard.enrollment_id) return <DashboardEmpty />

  const streakPct = Math.min(100, dashboard.current_streak * 10)
  const dailyPct = Math.round(dashboard.daily_progress * 100)
  const readinessPct = Math.round(dashboard.interview_readiness * 100)

  return (
    <div className="space-y-6">
      {/* Welcome / page header */}
      <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <WelcomeWidget displayName={displayName} />
        <div className="hidden sm:block">
          <Button
            asChild
            className="bg-gradient-to-r from-emerald-500 to-teal-500 text-white shadow-sm hover:from-emerald-600 hover:to-teal-600"
          >
            <Link href={`/study/start?enrollment=${dashboard.enrollment_id}`}>
              Start studying
              <ArrowRight className="ml-1 h-4 w-4" aria-hidden="true" />
            </Link>
          </Button>
        </div>
      </div>

      {/* Top row — 4 stat cards */}
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <StatCard
          label="Current Streak"
          value={`${dashboard.current_streak}d`}
          hint={`Best: ${dashboard.longest_streak} days`}
          icon={Flame}
          accent="amber"
          progress={streakPct}
        />
        <StatCard
          label="Daily Goal"
          value={`${dailyPct}%`}
          hint={dailyPct >= 100 ? 'Goal achieved! 🎉' : `${100 - dailyPct}% to go`}
          icon={Target}
          accent="emerald"
          progress={dailyPct}
        />
        <StatCard
          label="Queue Remaining"
          value={dashboard.today_queue_remaining}
          hint={dashboard.today_queue_remaining === 0 ? 'All caught up!' : 'Questions left today'}
          icon={ListTodo}
          accent="sky"
        />
        <StatCard
          label="Interview Readiness"
          value={`${readinessPct}%`}
          hint={
            readinessPct >= 80
              ? 'Interview ready!'
              : readinessPct >= 50
                ? 'Getting there'
                : 'Keep practicing'
          }
          icon={Zap}
          accent="violet"
          progress={readinessPct}
        />
      </div>

      {/* Middle row — charts */}
      <div className="grid gap-4 lg:grid-cols-2">
        <MasteryOverviewChart data={dashboard.mastery_trend} readiness={dashboard.interview_readiness} />
        <WeeklyLearningChart data={dashboard.memory_trend} />
      </div>

      {/* Bottom row — weak concepts + recommendations */}
      <div className="grid gap-4 lg:grid-cols-3">
        <div className="lg:col-span-2">
          <WeakConceptsCard concepts={dashboard.weak_concepts} />
        </div>
        <RecommendationsCard
          recommendations={recommendations || []}
          onAccept={(id) => acceptMutation.mutate(id)}
          onDismiss={(id) => dismissMutation.mutate(id)}
          isAccepting={acceptMutation.isPending}
          isDismissing={dismissMutation.isPending}
        />
      </div>

      {/* Quick actions row */}
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
        <QuickActionsCard enrollmentId={dashboard.enrollment_id} />
        <Card className="rounded-2xl border-border/60">
          <CardHeader className="pb-3">
            <CardTitle className="text-base font-semibold">Due Reviews</CardTitle>
            <CardDescription>Spaced repetition queue</CardDescription>
          </CardHeader>
          <CardContent className="flex items-center justify-between">
            <div>
              <p className="text-3xl font-bold tracking-tight">{dashboard.today_reviews}</p>
              <p className="text-xs text-muted-foreground">
                {dashboard.today_reviews === 0 ? 'No reviews due' : 'Due today'}
              </p>
            </div>
            <Button asChild variant="outline" size="sm" disabled={dashboard.today_reviews === 0}>
              <Link href="/reviews">Review now</Link>
            </Button>
          </CardContent>
        </Card>
        <Card className="rounded-2xl border-border/60">
          <CardHeader className="pb-3">
            <CardTitle className="text-base font-semibold">Strong Concepts</CardTitle>
            <CardDescription>Mastered topics</CardDescription>
          </CardHeader>
          <CardContent className="flex items-center justify-between">
            <div>
              <p className="text-3xl font-bold tracking-tight">{dashboard.strong_concepts.length}</p>
              <p className="text-xs text-muted-foreground">concepts mastered</p>
            </div>
            <Button asChild variant="outline" size="sm">
              <Link href="/mastery">View all</Link>
            </Button>
          </CardContent>
        </Card>
      </div>

      {/* Phase B: Read First — prerequisite materials */}
      <ReadFirstCard enrollmentId={String(dashboard.enrollment_id || '')} />
    </div>
  )
}

function ReadFirstCard({ enrollmentId }: { enrollmentId: string }) {
  const [prereqs, setPrereqs] = React.useState<{ read_first_materials: any[] } | null>(null)

  React.useEffect(() => {
    if (!enrollmentId || enrollmentId === 'null') return
    const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'
    const token = localStorage.getItem('mastery.access_token')
    if (!token) return
    fetch(`${API_URL}/api/v1/materials/prerequisites/check?enrollment_id=${enrollmentId}`, {
      headers: { Authorization: `Bearer ${token}` },
    })
      .then(r => r.ok ? r.json() : null)
      .then(d => d && setPrereqs(d))
      .catch(() => {})
  }, [enrollmentId])

  if (!prereqs || !prereqs.read_first_materials || prereqs.read_first_materials.length === 0) return null

  return (
    <Card className="glass-card rounded-2xl border-amber-500/20">
      <CardHeader className="pb-3">
        <CardTitle className="flex items-center gap-2 text-base font-semibold text-amber-400">
          <BookOpen className="h-4 w-4" />
          Read These First
        </CardTitle>
        <CardDescription>Complete reading prerequisites before practicing these concepts</CardDescription>
      </CardHeader>
      <CardContent className="space-y-3">
        {prereqs.read_first_materials.map((m: any) => (
          <Link
            key={m.material_id}
            href={`/materials/${m.material_id}`}
            className="flex items-center gap-3 rounded-xl border border-white/10 bg-white/5 p-3 transition-colors hover:bg-white/10"
          >
            <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-lg bg-amber-500/10 ring-1 ring-inset ring-amber-500/20">
              <FileText className="h-5 w-5 text-amber-400" />
            </div>
            <div className="flex-1 min-w-0">
              <p className="text-sm font-medium text-white truncate">{m.title}</p>
              <p className="text-xs text-zinc-500">
                For: {m.concept_name} · Read {m.pages_read}/{m.min_pages_read} pages
              </p>
              <div className="mt-1 h-1 overflow-hidden rounded-full bg-white/10">
                <div
                  className="h-full rounded-full bg-amber-500"
                  style={{ width: `${Math.min(100, (m.pages_read / Math.max(m.min_pages_read, 1)) * 100)}%` }}
                />
              </div>
            </div>
            <ChevronRight className="h-5 w-5 shrink-0 text-zinc-600" />
          </Link>
        ))}
      </CardContent>
    </Card>
  )
}
