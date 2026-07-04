'use client'

import * as React from 'react'
import Link from 'next/link'
import { Flame, Target, Clock, TrendingUp, Zap, BookOpen, Award, AlertCircle } from 'lucide-react'

import { cn } from '@/lib/cn'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { Progress } from '@/components/ui/progress'
import { Skeleton } from '@/components/ui/skeleton'
import { EmptyState } from '@/components/ui/empty-state'
import { ROUTES } from '@/lib/constants'
import { formatRelativeTime } from '@/lib/format'
import { MasteryDonut, TrendChart, ActivityBarChart } from '@/components/charts'
import type { DashboardData, MasteryScore } from '@/types/learning'

// ============================================================
// Welcome Section
// ============================================================

export function WelcomeWidget({ displayName }: { displayName: string }) {
  const hour = new Date().getHours()
  const greeting = hour < 12 ? 'Good morning' : hour < 18 ? 'Good afternoon' : 'Good evening'

  return (
    <Card>
      <CardContent className="pt-6">
        <h2 className="text-2xl font-bold">
          {greeting}, {displayName}! 👋
        </h2>
        <p className="mt-1 text-sm text-muted-foreground">
          Ready to continue your mastery journey?
        </p>
      </CardContent>
    </Card>
  )
}

// ============================================================
// Streak Widget
// ============================================================

export function StreakWidget({ current, longest }: { current: number; longest: number }) {
  return (
    <Card>
      <CardHeader className="pb-2">
        <div className="flex items-center justify-between">
          <CardDescription>Current streak</CardDescription>
          <Flame className="h-4 w-4 text-orange-500" aria-hidden="true" />
        </div>
        <CardTitle className="text-3xl">{current} days</CardTitle>
      </CardHeader>
      <CardContent>
        <p className="text-xs text-muted-foreground">
          Best: {longest} days 🔥
        </p>
      </CardContent>
    </Card>
  )
}

// ============================================================
// Daily Goal Progress Widget
// ============================================================

export function DailyGoalWidget({ progress }: { progress: number }) {
  const percentage = Math.round(progress * 100)
  return (
    <Card>
      <CardHeader className="pb-2">
        <div className="flex items-center justify-between">
          <CardDescription>Daily goal</CardDescription>
          <Target className="h-4 w-4 text-primary" aria-hidden="true" />
        </div>
        <CardTitle className="text-3xl">{percentage}%</CardTitle>
      </CardHeader>
      <CardContent>
        <Progress value={percentage} className="h-2" />
        <p className="mt-2 text-xs text-muted-foreground">
          {percentage >= 100 ? 'Goal achieved! 🎉' : `${100 - percentage}% to go`}
        </p>
      </CardContent>
    </Card>
  )
}

// ============================================================
// Queue Remaining Widget
// ============================================================

export function QueueRemainingWidget({ remaining }: { remaining: number }) {
  return (
    <Card>
      <CardHeader className="pb-2">
        <div className="flex items-center justify-between">
          <CardDescription>Queue remaining</CardDescription>
          <Clock className="h-4 w-4 text-primary" aria-hidden="true" />
        </div>
        <CardTitle className="text-3xl">{remaining}</CardTitle>
      </CardHeader>
      <CardContent>
        <Button size="sm" className="w-full" asChild disabled={remaining === 0}>
          <Link href={ROUTES.DASHBOARD}>Continue studying</Link>
        </Button>
      </CardContent>
    </Card>
  )
}

// ============================================================
// Due Reviews Widget
// ============================================================

export function DueReviewsWidget({ count }: { count: number }) {
  return (
    <Card>
      <CardHeader className="pb-2">
        <div className="flex items-center justify-between">
          <CardDescription>Due reviews</CardDescription>
          <AlertCircle className={cn('h-4 w-4', count > 0 ? 'text-destructive' : 'text-muted-foreground')} aria-hidden="true" />
        </div>
        <CardTitle className="text-3xl">{count}</CardTitle>
      </CardHeader>
      <CardContent>
        <Button size="sm" variant="outline" className="w-full" asChild disabled={count === 0}>
          <Link href="/reviews">Review now</Link>
        </Button>
      </CardContent>
    </Card>
  )
}

// ============================================================
// Interview Readiness Widget
// ============================================================

export function InterviewReadinessWidget({ readiness }: { readiness: number }) {
  const percentage = Math.round(readiness * 100)
  const label = percentage >= 80 ? 'Interview ready!' : percentage >= 50 ? 'Getting there' : 'Keep practicing'

  return (
    <Card>
      <CardHeader className="pb-2">
        <div className="flex items-center justify-between">
          <CardDescription>Interview readiness</CardDescription>
          <Zap className="h-4 w-4 text-yellow-500" aria-hidden="true" />
        </div>
        <CardTitle className="text-3xl">{percentage}%</CardTitle>
      </CardHeader>
      <CardContent>
        <p className="text-xs text-muted-foreground">{label}</p>
      </CardContent>
    </Card>
  )
}

// ============================================================
// Mastery Overview Widget
// ============================================================

export function MasteryOverviewWidget({ score }: { score: number }) {
  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-base">Overall mastery</CardTitle>
      </CardHeader>
      <CardContent className="flex items-center justify-center">
        <MasteryDonut value={score} label="Mastered" />
      </CardContent>
    </Card>
  )
}

// ============================================================
// Weak Concepts Widget
// ============================================================

export function WeakConceptsWidget({ concepts }: { concepts: MasteryScore[] }) {
  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-base">Weak concepts</CardTitle>
        <CardDescription>Focus on these to improve</CardDescription>
      </CardHeader>
      <CardContent>
        {concepts.length === 0 ? (
          <EmptyState title="No weak concepts" description="Great job! You're on top of everything." />
        ) : (
          <ul className="space-y-2" role="list">
            {concepts.slice(0, 5).map((concept) => (
              <li key={concept.concept_id} className="flex items-center justify-between text-sm">
                <span className="truncate">{concept.concept_id}</span>
                <Badge variant="destructive" className="text-xs">
                  {Math.round(concept.mastery_score_combined * 100)}%
                </Badge>
              </li>
            ))}
          </ul>
        )}
      </CardContent>
    </Card>
  )
}

// ============================================================
// Strong Concepts Widget
// ============================================================

export function StrongConceptsWidget({ concepts }: { concepts: MasteryScore[] }) {
  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-base">Strong concepts</CardTitle>
        <CardDescription>You've mastered these</CardDescription>
      </CardHeader>
      <CardContent>
        {concepts.length === 0 ? (
          <EmptyState title="No strong concepts yet" description="Keep studying to build mastery." />
        ) : (
          <ul className="space-y-2" role="list">
            {concepts.slice(0, 5).map((concept) => (
              <li key={concept.concept_id} className="flex items-center justify-between text-sm">
                <span className="truncate">{concept.concept_id}</span>
                <Badge variant="success" className="text-xs">
                  {Math.round(concept.mastery_score_combined * 100)}%
                </Badge>
              </li>
            ))}
          </ul>
        )}
      </CardContent>
    </Card>
  )
}

// ============================================================
// Weekly Learning Chart Widget
// ============================================================

export function WeeklyLearningWidget({ data }: { data: { date: string; value: number }[] }) {
  const chartData = data.map((d) => ({
    label: new Date(d.date).toLocaleDateString('en-US', { weekday: 'short' }),
    value: d.value,
  }))

  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-base">Weekly learning</CardTitle>
        <CardDescription>Questions answered per day</CardDescription>
      </CardHeader>
      <CardContent>
        <ActivityBarChart data={chartData} title="" height={180} />
      </CardContent>
    </Card>
  )
}

// ============================================================
// Monthly Learning Chart Widget
// ============================================================

export function MonthlyLearningWidget({ data }: { data: { date: string; value: number }[] }) {
  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-base">Mastery trend</CardTitle>
        <CardDescription>Last 30 days</CardDescription>
      </CardHeader>
      <CardContent>
        <TrendChart data={data} title="Mastery" height={180} />
      </CardContent>
    </Card>
  )
}

// ============================================================
// Recommendation Card Widget
// ============================================================

export function RecommendationCard({
  recommendation,
  onAccept,
  onDismiss,
}: {
  recommendation: { id: string; reason: string; recommendation_type: string } | null
  onAccept?: () => void
  onDismiss?: () => void
}) {
  if (!recommendation) return null

  return (
    <Card className="border-primary/50">
      <CardHeader>
        <div className="flex items-center gap-2">
          <TrendingUp className="h-4 w-4 text-primary" aria-hidden="true" />
          <CardTitle className="text-base">Recommendation</CardTitle>
        </div>
      </CardHeader>
      <CardContent className="space-y-3">
        <p className="text-sm">{recommendation.reason}</p>
        <div className="flex gap-2">
          <Button size="sm" onClick={onAccept}>Accept</Button>
          <Button size="sm" variant="outline" onClick={onDismiss}>Dismiss</Button>
        </div>
      </CardContent>
    </Card>
  )
}

// ============================================================
// Continue Studying Widget
// ============================================================

export function ContinueStudyingWidget({ enrollmentId }: { enrollmentId: string | null }) {
  if (!enrollmentId) {
    return (
      <Card>
        <CardHeader>
          <CardTitle className="text-base">Continue studying</CardTitle>
        </CardHeader>
        <CardContent>
          <EmptyState
            title="No active enrollment"
            description="Browse subjects to start learning."
            action={{ label: 'Browse subjects', onClick: () => window.location.href = '/subjects' }}
          />
        </CardContent>
      </Card>
    )
  }

  return (
    <Card>
      <CardHeader>
        <div className="flex items-center gap-2">
          <BookOpen className="h-4 w-4 text-primary" aria-hidden="true" />
          <CardTitle className="text-base">Continue studying</CardTitle>
        </div>
      </CardHeader>
      <CardContent>
        <Button className="w-full" asChild>
          <Link href={`/study/start?enrollment=${enrollmentId}`}>
            Start a study session
          </Link>
        </Button>
      </CardContent>
    </Card>
  )
}

// ============================================================
// Dashboard Loading Skeleton
// ============================================================

export function DashboardSkeleton() {
  return (
    <div className="space-y-6">
      <Skeleton className="h-24 w-full" />
      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
        {Array.from({ length: 4 }).map((_, i) => (
          <Skeleton key={i} className="h-32 w-full" />
        ))}
      </div>
      <div className="grid gap-4 md:grid-cols-2">
        <Skeleton className="h-64 w-full" />
        <Skeleton className="h-64 w-full" />
      </div>
      <div className="grid gap-4 md:grid-cols-3">
        {Array.from({ length: 3 }).map((_, i) => (
          <Skeleton key={i} className="h-48 w-full" />
        ))}
      </div>
    </div>
  )
}

// ============================================================
// Dashboard Error
// ============================================================

export function DashboardError({ onRetry }: { onRetry: () => void }) {
  return (
    <Card>
      <CardContent className="pt-6">
        <EmptyState
          icon={AlertCircle}
          title="Failed to load dashboard"
          description="We couldn't load your dashboard data. Please try again."
          action={{ label: 'Retry', onClick: onRetry }}
        />
      </CardContent>
    </Card>
  )
}

// ============================================================
// Dashboard Empty
// ============================================================

export function DashboardEmpty() {
  return (
    <Card>
      <CardContent className="pt-6">
        <EmptyState
          icon={Award}
          title="Welcome to Mastery Engine!"
          description="Enroll in a subject to start your learning journey."
          action={{ label: 'Browse subjects', onClick: () => window.location.href = '/subjects' }}
        />
      </CardContent>
    </Card>
  )
}
