'use client'

import * as React from 'react'
import Link from 'next/link'
import { TrendingUp, AlertCircle } from 'lucide-react'

import { useEnrollments, useMasteryScores, useMasteryTimeline } from '@/hooks/use-learner'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Skeleton } from '@/components/ui/skeleton'
import { EmptyState } from '@/components/ui/empty-state'
import { Tabs, TabsList, TabsTrigger, TabsContent } from '@/components/ui/tabs'
import { MasteryDonut, TrendChart } from '@/components/charts'

export default function MasteryPage() {
  const { data: enrollments } = useEnrollments()
  const [selectedEnrollment, setSelectedEnrollment] = React.useState<string | null>(null)

  React.useEffect(() => {
    if (enrollments && enrollments.length > 0 && !selectedEnrollment) {
      const active = enrollments.find((e) => e.status === 'active')
      if (active) setSelectedEnrollment(active.id)
    }
  }, [enrollments, selectedEnrollment])

  const { data: scores, isLoading } = useMasteryScores(selectedEnrollment)
  const { data: timeline } = useMasteryTimeline(selectedEnrollment)

  if (!enrollments || enrollments.length === 0) {
    return (
      <div className="max-w-2xl">
        <EmptyState
          title="No enrollments"
          description="Enroll in a subject to see your mastery scores."
          action={{ label: 'Browse subjects', onClick: () => window.location.href = '/subjects' }}
        />
      </div>
    )
  }

  const avgMastery = scores && scores.length > 0
    ? scores.reduce((sum, s) => sum + s.mastery_score_combined, 0) / scores.length * 100
    : 0

  const weakCount = scores?.filter((s) => s.weakness_severity !== 'none').length || 0
  const strongCount = scores?.filter((s) => s.concept_state === 'mastered').length || 0

  return (
    <div className="max-w-4xl space-y-6">
      <div>
        <h1 className="text-2xl font-bold tracking-tight">Mastery overview</h1>
        <p className="text-sm text-muted-foreground">Track your mastery across all concepts</p>
      </div>

      {/* Enrollment selector */}
      {enrollments.length > 1 && (
        <Tabs value={selectedEnrollment || ''} onValueChange={setSelectedEnrollment}>
          <TabsList className="flex-wrap">
            {enrollments.map((e) => (
              <TabsTrigger key={e.id} value={e.id}>
                {e.subject_name}
              </TabsTrigger>
            ))}
          </TabsList>
        </Tabs>
      )}

      {isLoading ? (
        <div className="grid gap-4 md:grid-cols-3">
          {Array.from({ length: 3 }).map((_, i) => (
            <Skeleton key={i} className="h-32 w-full" />
          ))}
        </div>
      ) : (
        <>
          {/* Stats */}
          <div className="grid gap-4 md:grid-cols-3">
            <Card>
              <CardContent className="flex items-center justify-center pt-6">
                <MasteryDonut value={avgMastery} label="Avg mastery" size={140} />
              </CardContent>
            </Card>
            <Card>
              <CardHeader className="pb-2">
                <CardDescription>Weak concepts</CardDescription>
                <CardTitle className="text-3xl text-destructive">{weakCount}</CardTitle>
              </CardHeader>
              <CardContent>
                <p className="text-xs text-muted-foreground">Need attention</p>
              </CardContent>
            </Card>
            <Card>
              <CardHeader className="pb-2">
                <CardDescription>Mastered</CardDescription>
                <CardTitle className="text-3xl text-success">{strongCount}</CardTitle>
              </CardHeader>
              <CardContent>
                <p className="text-xs text-muted-foreground">Fully mastered</p>
              </CardContent>
            </Card>
          </div>

          {/* Timeline chart */}
          {timeline && timeline.length > 0 && (
            <Card>
              <CardHeader>
                <CardTitle className="text-base">Mastery timeline</CardTitle>
                <CardDescription>Your mastery progress over time</CardDescription>
              </CardHeader>
              <CardContent>
                <TrendChart data={timeline} title="Mastery" height={250} />
              </CardContent>
            </Card>
          )}

          {/* Concept list */}
          <Card>
            <CardHeader>
              <CardTitle className="text-base">All concepts</CardTitle>
              <CardDescription>{scores?.length || 0} concepts tracked</CardDescription>
            </CardHeader>
            <CardContent>
              {!scores || scores.length === 0 ? (
                <EmptyState title="No mastery data yet" description="Start studying to build mastery." />
              ) : (
                <ul className="space-y-2" role="list">
                  {scores
                    .sort((a, b) => a.mastery_score_combined - b.mastery_score_combined)
                    .map((score) => (
                      <li key={score.concept_id}>
                        <Link
                          href={`/mastery/${score.concept_id}`}
                          className="flex items-center justify-between rounded-lg border p-3 hover:bg-muted/50"
                        >
                          <div className="flex-1">
                            <p className="text-sm font-medium">{score.concept_id}</p>
                            <p className="text-xs capitalize text-muted-foreground">
                              {score.concept_state.replace(/_/g, ' ')} • {score.evidence_count} attempts
                            </p>
                          </div>
                          <div className="flex items-center gap-2">
                            <span className="text-sm font-bold">
                              {Math.round(score.mastery_score_combined * 100)}%
                            </span>
                            <Badge
                              variant={
                                score.weakness_severity === 'critical' ? 'destructive' :
                                score.weakness_severity === 'high' || score.weakness_severity === 'medium' ? 'warning' :
                                score.concept_state === 'mastered' ? 'success' : 'secondary'
                              }
                              className="text-xs"
                            >
                              {score.weakness_severity !== 'none'
                                ? score.weakness_severity
                                : score.concept_state}
                            </Badge>
                          </div>
                        </Link>
                      </li>
                    ))}
                </ul>
              )}
            </CardContent>
          </Card>
        </>
      )}
    </div>
  )
}
