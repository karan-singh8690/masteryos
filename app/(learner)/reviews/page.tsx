'use client'

import * as React from 'react'
import { Calendar, Clock, AlertCircle, CheckCircle2 } from 'lucide-react'

import { useEnrollments, useDueReviews, useUpcomingReviews, useReviewStats } from '@/hooks/use-learner'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Skeleton } from '@/components/ui/skeleton'
import { EmptyState } from '@/components/ui/empty-state'
import { Tabs, TabsList, TabsTrigger, TabsContent } from '@/components/ui/tabs'
import { formatRelativeTime, formatDate } from '@/lib/format'
import { cn } from '@/lib/cn'

export default function ReviewsPage() {
  const { data: enrollments } = useEnrollments()
  const [enrollmentId, setEnrollmentId] = React.useState<string | null>(null)

  React.useEffect(() => {
    if (enrollments && enrollments.length > 0) {
      const active = enrollments.find((e) => e.status === 'active')
      if (active) setEnrollmentId(active.id)
    }
  }, [enrollments])

  const { data: dueReviews, isLoading: dueLoading } = useDueReviews(enrollmentId)
  const { data: upcomingReviews } = useUpcomingReviews(enrollmentId, 7)
  const { data: stats } = useReviewStats(enrollmentId)

  if (!enrollments || enrollments.length === 0) {
    return (
      <div className="max-w-2xl">
        <EmptyState
          icon={Calendar}
          title="No enrollments"
          description="Enroll in a subject to see reviews."
          action={{ label: 'Browse subjects', onClick: () => window.location.href = '/subjects' }}
        />
      </div>
    )
  }

  return (
    <div className="max-w-4xl space-y-6">
      <div>
        <h1 className="text-2xl font-bold tracking-tight">Review Center</h1>
        <p className="text-sm text-muted-foreground">Manage your spaced repetition reviews</p>
      </div>

      {/* Stats */}
      {stats && (
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
          <Card>
            <CardHeader className="pb-2">
              <CardDescription>Due now</CardDescription>
              <CardTitle className="text-3xl text-destructive">{stats.total_due}</CardTitle>
            </CardHeader>
          </Card>
          <Card>
            <CardHeader className="pb-2">
              <CardDescription>Today</CardDescription>
              <CardTitle className="text-3xl">{stats.total_today}</CardTitle>
            </CardHeader>
          </Card>
          <Card>
            <CardHeader className="pb-2">
              <CardDescription>This week</CardDescription>
              <CardTitle className="text-3xl">{stats.total_this_week}</CardTitle>
            </CardHeader>
          </Card>
          <Card>
            <CardHeader className="pb-2">
              <CardDescription>Completion rate</CardDescription>
              <CardTitle className="text-3xl">{Math.round(stats.completion_rate * 100)}%</CardTitle>
            </CardHeader>
          </Card>
        </div>
      )}

      <Tabs defaultValue="due">
        <TabsList>
          <TabsTrigger value="due">Due now ({dueReviews?.length || 0})</TabsTrigger>
          <TabsTrigger value="upcoming">Upcoming</TabsTrigger>
        </TabsList>

        {/* Due reviews */}
        <TabsContent value="due" className="space-y-3">
          {dueLoading ? (
            <Skeleton className="h-48 w-full" />
          ) : !dueReviews || dueReviews.length === 0 ? (
            <EmptyState
              icon={CheckCircle2}
              title="All caught up!"
              description="No reviews are due right now. Come back later."
            />
          ) : (
            <ul className="space-y-2" role="list">
              {dueReviews.map((review) => (
                <li key={review.concept_id}>
                  <Card hover>
                    <CardContent className="flex items-center justify-between p-4">
                      <div className="flex-1">
                        <p className="text-sm font-medium">{review.concept_name}</p>
                        <p className="text-xs text-muted-foreground">
                          {review.subject_name} • {review.question_count} questions
                        </p>
                      </div>
                      <div className="flex items-center gap-2">
                        <Badge
                          variant={review.priority === 'urgent' || review.priority === 'high' ? 'destructive' : 'warning'}
                          className="text-xs capitalize"
                        >
                          {review.priority}
                        </Badge>
                        <Button size="sm" asChild>
                          <a href="/study/start">Review</a>
                        </Button>
                      </div>
                    </CardContent>
                  </Card>
                </li>
              ))}
            </ul>
          )}
        </TabsContent>

        {/* Upcoming reviews */}
        <TabsContent value="upcoming" className="space-y-3">
          {!upcomingReviews || upcomingReviews.length === 0 ? (
            <EmptyState
              icon={Clock}
              title="No upcoming reviews"
              description="No reviews scheduled in the next 7 days."
            />
          ) : (
            <ul className="space-y-2" role="list">
              {upcomingReviews.map((review) => (
                <li key={`${review.concept_id}-${review.due_at}`}>
                  <Card>
                    <CardContent className="flex items-center justify-between p-4">
                      <div className="flex-1">
                        <p className="text-sm font-medium">{review.concept_name}</p>
                        <p className="text-xs text-muted-foreground">{review.subject_name}</p>
                      </div>
                      <Badge variant="outline" className="text-xs">
                        Due {formatRelativeTime(review.due_at)}
                      </Badge>
                    </CardContent>
                  </Card>
                </li>
              ))}
            </ul>
          )}
        </TabsContent>
      </Tabs>
    </div>
  )
}
