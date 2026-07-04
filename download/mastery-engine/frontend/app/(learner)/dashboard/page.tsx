'use client'

import * as React from 'react'
import { useQueryClient } from '@tanstack/react-query'

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

export default function DashboardPage() {
  const { user } = useAuth()
  const queryClient = useQueryClient()
  const { data: dashboard, isLoading, isError, refetch } = useDashboard()
  const { data: recommendations } = useRecommendations()
  const acceptMutation = useAcceptRecommendation()
  const dismissMutation = useDismissRecommendation()

  const displayName = user?.profile.displayName || 'there'

  if (isLoading) return <DashboardSkeleton />

  if (isError) return <DashboardError onRetry={() => refetch()} />

  if (!dashboard || !dashboard.enrollment_id) return <DashboardEmpty />

  const topRecommendation = recommendations?.[0] || null

  return (
    <div className="space-y-6">
      <WelcomeWidget displayName={displayName} />

      {/* Stats row */}
      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
        <StreakWidget current={dashboard.current_streak} longest={dashboard.longest_streak} />
        <DailyGoalWidget progress={dashboard.daily_progress} />
        <QueueRemainingWidget remaining={dashboard.today_queue_remaining} />
        <DueReviewsWidget count={dashboard.today_reviews} />
      </div>

      {/* Interview readiness + Mastery overview */}
      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
        <InterviewReadinessWidget readiness={dashboard.interview_readiness} />
        <MasteryOverviewWidget score={dashboard.interview_readiness} />
        <ContinueStudyingWidget enrollmentId={dashboard.enrollment_id} />
      </div>

      {/* Charts */}
      <div className="grid gap-4 md:grid-cols-2">
        <WeeklyLearningWidget data={dashboard.memory_trend} />
        <MonthlyLearningWidget data={dashboard.mastery_trend} />
      </div>

      {/* Weak + Strong concepts */}
      <div className="grid gap-4 md:grid-cols-2">
        <WeakConceptsWidget concepts={dashboard.weak_concepts} />
        <StrongConceptsWidget concepts={dashboard.strong_concepts} />
      </div>

      {/* Recommendation */}
      {topRecommendation && (
        <RecommendationCard
          recommendation={topRecommendation}
          onAccept={() => {
            acceptMutation.mutate(topRecommendation.id)
          }}
          onDismiss={() => {
            dismissMutation.mutate(topRecommendation.id)
          }}
        />
      )}
    </div>
  )
}
