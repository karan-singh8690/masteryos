'use client'

import * as React from 'react'
import { useParams, useRouter } from 'next/navigation'
import Link from 'next/link'
import { ArrowLeft, TrendingUp } from 'lucide-react'

import { useEnrollments, useMasteryScores, useMasteryTimeline } from '@/hooks/use-learner'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Skeleton } from '@/components/ui/skeleton'
import { EmptyState } from '@/components/ui/empty-state'
import { MasteryDonut, TrendChart, Sparkline } from '@/components/charts'
import { formatRelativeTime } from '@/lib/format'

export default function ConceptMasteryPage() {
  const params = useParams()
  const router = useRouter()
  const conceptId = params.conceptId as string

  const { data: enrollments } = useEnrollments()
  const [enrollmentId, setEnrollmentId] = React.useState<string | null>(null)

  React.useEffect(() => {
    if (enrollments && enrollments.length > 0) {
      const active = enrollments.find((e) => e.status === 'active')
      if (active) setEnrollmentId(active.id)
    }
  }, [enrollments])

  const { data: scores, isLoading } = useMasteryScores(enrollmentId)
  const { data: timeline } = useMasteryTimeline(enrollmentId, conceptId)

  const score = scores?.find((s) => s.concept_id === conceptId)

  if (isLoading) {
    return (
      <div className="max-w-3xl space-y-6">
        <Skeleton className="h-8 w-32" />
        <Skeleton className="h-64 w-full" />
        <Skeleton className="h-48 w-full" />
      </div>
    )
  }

  if (!score) {
    return (
      <div className="max-w-2xl">
        <EmptyState
          title="Concept not found"
          description="We couldn't find mastery data for this concept."
          action={{ label: 'Back to mastery', onClick: () => router.push('/mastery') }}
        />
      </div>
    )
  }

  return (
    <div className="max-w-3xl space-y-6">
      <div>
        <Link href="/mastery" className="inline-flex items-center gap-1 text-sm text-muted-foreground hover:text-foreground">
          <ArrowLeft className="h-3 w-3" /> Back to mastery
        </Link>
      </div>

      {/* Overview */}
      <Card>
        <CardHeader>
          <CardTitle className="text-xl">{score.concept_id}</CardTitle>
          <CardDescription>Concept mastery details</CardDescription>
        </CardHeader>
        <CardContent className="flex items-center justify-center">
          <MasteryDonut value={score.mastery_score_combined * 100} label="Mastery" size={180} />
        </CardContent>
      </Card>

      {/* Stats */}
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <Card>
          <CardHeader className="pb-2">
            <CardDescription>Memory score</CardDescription>
            <CardTitle className="text-2xl">{Math.round(score.memory_score * 100)}%</CardTitle>
          </CardHeader>
        </Card>
        <Card>
          <CardHeader className="pb-2">
            <CardDescription>Durable mastery</CardDescription>
            <CardTitle className="text-2xl">{Math.round(score.durable_mastery_score * 100)}%</CardTitle>
          </CardHeader>
        </Card>
        <Card>
          <CardHeader className="pb-2">
            <CardDescription>Evidence count</CardDescription>
            <CardTitle className="text-2xl">{score.evidence_count}</CardTitle>
          </CardHeader>
        </Card>
        <Card>
          <CardHeader className="pb-2">
            <CardDescription>Last attempt</CardDescription>
            <CardTitle className="text-lg">
              {score.last_attempt_at ? formatRelativeTime(score.last_attempt_at) : '—'}
            </CardTitle>
          </CardHeader>
        </Card>
      </div>

      {/* State + Severity */}
      <div className="flex gap-4">
        <Card className="flex-1">
          <CardContent className="pt-6">
            <p className="text-xs text-muted-foreground">Concept state</p>
            <Badge variant="secondary" className="mt-1 capitalize">
              {score.concept_state.replace(/_/g, ' ')}
            </Badge>
          </CardContent>
        </Card>
        <Card className="flex-1">
          <CardContent className="pt-6">
            <p className="text-xs text-muted-foreground">Weakness severity</p>
            <Badge
              variant={
                score.weakness_severity === 'critical' || score.weakness_severity === 'high' ? 'destructive' :
                score.weakness_severity === 'medium' || score.weakness_severity === 'low' ? 'warning' : 'success'
              }
              className="mt-1 capitalize"
            >
              {score.weakness_severity}
            </Badge>
          </CardContent>
        </Card>
      </div>

      {/* Timeline */}
      {timeline && timeline.length > 0 && (
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-base">
              <TrendingUp className="h-4 w-4" aria-hidden="true" />
              Mastery history
            </CardTitle>
          </CardHeader>
          <CardContent>
            <TrendChart data={timeline} title="Mastery" height={250} />
          </CardContent>
        </Card>
      )}
    </div>
  )
}
