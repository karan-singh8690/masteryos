'use client'

import * as React from 'react'
import { useParams, useRouter } from 'next/navigation'
import Link from 'next/link'
import {
  CheckCircle2,
  Clock,
  TrendingUp,
  Target,
  Award,
  ArrowRight,
  Home,
} from 'lucide-react'

import { useSessionSummary } from '@/hooks/use-learner'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { Skeleton } from '@/components/ui/skeleton'
import { CenteredSpinner } from '@/components/ui/spinner'
import { EmptyState } from '@/components/ui/empty-state'
import { formatDuration } from '@/lib/format'
import { MasteryDonut } from '@/components/charts'

export default function SessionSummaryPage() {
  const params = useParams()
  const router = useRouter()
  const sessionId = params.sessionId as string

  const { data: summary, isLoading } = useSessionSummary(sessionId)

  if (isLoading) {
    return <CenteredSpinner label="Loading session summary..." />
  }

  if (!summary) {
    return (
      <div className="max-w-2xl">
        <EmptyState
          title="Summary not available"
          description="We couldn't load the session summary."
          action={{ label: 'Back to dashboard', onClick: () => router.push('/dashboard') }}
        />
      </div>
    )
  }

  const accuracy = Math.round(summary.accuracy * 100)

  return (
    <div className="mx-auto max-w-3xl space-y-6">
      {/* Header */}
      <div className="text-center">
        <div className="mx-auto flex h-16 w-16 items-center justify-center rounded-full bg-success/10">
          <CheckCircle2 className="h-8 w-8 text-success" aria-hidden="true" />
        </div>
        <h1 className="mt-4 text-3xl font-bold">Session complete!</h1>
        <p className="mt-1 text-muted-foreground">Great work! Here&apos;s your session summary.</p>
      </div>

      {/* Stats grid */}
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <Card>
          <CardHeader className="pb-2">
            <CardDescription>Questions answered</CardDescription>
            <CardTitle className="text-3xl">{summary.questions_answered}</CardTitle>
          </CardHeader>
        </Card>
        <Card>
          <CardHeader className="pb-2">
            <CardDescription>Accuracy</CardDescription>
            <CardTitle className="text-3xl">{accuracy}%</CardTitle>
          </CardHeader>
        </Card>
        <Card>
          <CardHeader className="pb-2">
            <CardDescription>Time spent</CardDescription>
            <CardTitle className="text-3xl">{formatDuration(summary.time_spent_seconds)}</CardTitle>
          </CardHeader>
        </Card>
        <Card>
          <CardHeader className="pb-2">
            <CardDescription>Mastery gained</CardDescription>
            <CardTitle className="text-3xl">+{Math.round(summary.mastery_gained * 100)}%</CardTitle>
          </CardHeader>
        </Card>
      </div>

      {/* Mastery overview */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2 text-base">
            <TrendingUp className="h-4 w-4" aria-hidden="true" />
            Concept mastery
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid gap-6 sm:grid-cols-2">
            <div>
              <h4 className="mb-3 text-sm font-medium text-destructive">Weak concepts</h4>
              {summary.weak_concepts.length === 0 ? (
                <p className="text-sm text-muted-foreground">None — great job!</p>
              ) : (
                <ul className="space-y-1" role="list">
                  {summary.weak_concepts.map((c) => (
                    <li key={c.concept_id} className="flex items-center justify-between text-sm">
                      <span className="truncate">{c.concept_id}</span>
                      <Badge variant="destructive" className="text-xs">
                        {Math.round(c.mastery_score_combined * 100)}%
                      </Badge>
                    </li>
                  ))}
                </ul>
              )}
            </div>
            <div>
              <h4 className="mb-3 text-sm font-medium text-success">Strong concepts</h4>
              {summary.strong_concepts.length === 0 ? (
                <p className="text-sm text-muted-foreground">Keep practicing!</p>
              ) : (
                <ul className="space-y-1" role="list">
                  {summary.strong_concepts.map((c) => (
                    <li key={c.concept_id} className="flex items-center justify-between text-sm">
                      <span className="truncate">{c.concept_id}</span>
                      <Badge variant="success" className="text-xs">
                        {Math.round(c.mastery_score_combined * 100)}%
                      </Badge>
                    </li>
                  ))}
                </ul>
              )}
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Recommendations */}
      {summary.recommendations.length > 0 && (
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-base">
              <Target className="h-4 w-4" aria-hidden="true" />
              Recommendations
            </CardTitle>
          </CardHeader>
          <CardContent>
            <ul className="space-y-2" role="list">
              {summary.recommendations.map((rec) => (
                <li key={rec.id} className="rounded-lg border p-3">
                  <p className="text-sm">{rec.reason}</p>
                  <Badge variant="outline" className="mt-1 text-xs capitalize">
                    {rec.recommendation_type.replace(/_/g, ' ')}
                  </Badge>
                </li>
              ))}
            </ul>
          </CardContent>
        </Card>
      )}

      {/* Review schedule */}
      {summary.review_schedule.length > 0 && (
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-base">
              <Clock className="h-4 w-4" aria-hidden="true" />
              Upcoming reviews
            </CardTitle>
          </CardHeader>
          <CardContent>
            <ul className="space-y-2" role="list">
              {summary.review_schedule.map((review, i) => (
                <li key={i} className="flex items-center justify-between text-sm">
                  <span>{review.concept_id}</span>
                  <span className="text-muted-foreground">
                    In {review.interval_days} days
                  </span>
                </li>
              ))}
            </ul>
          </CardContent>
        </Card>
      )}

      {/* Achievements */}
      {summary.achievements_unlocked.length > 0 && (
        <Card className="border-success/50">
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-base">
              <Award className="h-4 w-4 text-success" aria-hidden="true" />
              Achievements unlocked!
            </CardTitle>
          </CardHeader>
          <CardContent>
            <ul className="space-y-2" role="list">
              {summary.achievements_unlocked.map((achievement) => (
                <li key={achievement.id} className="flex items-center gap-3 rounded-lg border bg-success/5 p-3">
                  <span className="text-2xl">{achievement.icon}</span>
                  <div>
                    <p className="text-sm font-medium">{achievement.name}</p>
                    <p className="text-xs text-muted-foreground">{achievement.description}</p>
                  </div>
                </li>
              ))}
            </ul>
          </CardContent>
        </Card>
      )}

      {/* Actions */}
      <div className="flex flex-col gap-2 sm:flex-row">
        <Button className="flex-1" size="lg" asChild>
          <Link href="/study/start">
            Start another session
            <ArrowRight className="ml-2 h-4 w-4" />
          </Link>
        </Button>
        <Button variant="outline" size="lg" asChild>
          <Link href="/dashboard">
            <Home className="mr-2 h-4 w-4" />
            Back to dashboard
          </Link>
        </Button>
      </div>
    </div>
  )
}
