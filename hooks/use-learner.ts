/**
 * Learner hooks — React Query hooks for all learning-related data.
 */

'use client'

import {
  useQuery,
  useMutation,
  useQueryClient,
} from '@tanstack/react-query'

import { queryKey } from '@/lib/query-keys'
import {
  subjectApi,
  enrollmentApi,
  studySessionApi,
  questionApi,
  dashboardApi,
  masteryApi,
  reviewApi,
  recommendationApi,
  achievementApi,
  notificationApi,
} from '@/lib/learner-api'
import type { UUID } from '@/types/common'
import type {
  EnrollmentRequest,
  StartSessionRequest,
  SubmitAnswerRequest,
  SetGoalRequest,
} from '@/types/learning'

// ============================================================
// Dashboard
// ============================================================

export function useDashboard() {
  return useQuery({
    queryKey: queryKey.learner.dashboard(),
    queryFn: () => dashboardApi.get(),
    staleTime: 30_000, // 30 seconds
  })
}

// ============================================================
// Subjects
// ============================================================

export function useSubjects() {
  return useQuery({
    queryKey: queryKey.learner.subjects(),
    queryFn: () => subjectApi.list(),
  })
}

export function useSubject(subjectId: UUID | null) {
  return useQuery({
    queryKey: queryKey.learner.subject(subjectId!),
    queryFn: () => subjectApi.getById(subjectId!),
    enabled: !!subjectId,
  })
}

export function useSubjectConcepts(subjectId: UUID | null) {
  return useQuery({
    queryKey: queryKey.learner.concepts(subjectId!),
    queryFn: () => subjectApi.getConcepts(subjectId!),
    enabled: !!subjectId,
  })
}

// ============================================================
// Enrollments
// ============================================================

export function useEnrollments() {
  return useQuery({
    queryKey: queryKey.learner.enrollments(),
    queryFn: () => enrollmentApi.list(),
  })
}

export function useEnrollment(enrollmentId: UUID | null) {
  return useQuery({
    queryKey: queryKey.learner.enrollment(enrollmentId!),
    queryFn: () => enrollmentApi.getById(enrollmentId!),
    enabled: !!enrollmentId,
  })
}

export function useEnroll() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (data: EnrollmentRequest) => enrollmentApi.enroll(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: queryKey.learner.enrollments() })
    },
  })
}

export function useSetLearningGoal() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: ({
      enrollmentId,
      data,
    }: {
      enrollmentId: UUID
      data: SetGoalRequest
    }) => enrollmentApi.setLearningGoal(enrollmentId, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: queryKey.learner.enrollments() })
    },
  })
}

// ============================================================
// Study Sessions
// ============================================================

export function useStartStudySession() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (data: StartSessionRequest) => studySessionApi.start(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: queryKey.learner.sessions() })
    },
  })
}

export function useStudySession(sessionId: UUID | null) {
  return useQuery({
    queryKey: queryKey.learner.session(sessionId!),
    queryFn: () => studySessionApi.getById(sessionId!),
    enabled: !!sessionId,
  })
}

export function useAdaptiveQueue(sessionId: UUID | null) {
  return useQuery({
    queryKey: queryKey.learner.adaptiveQueue(sessionId!),
    queryFn: () => studySessionApi.getAdaptiveQueue(sessionId!),
    enabled: !!sessionId,
    staleTime: 0, // Always refetch when invalidated
  })
}

export function useEndSession() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (sessionId: UUID) => studySessionApi.end(sessionId),
    onSuccess: (_data, sessionId) => {
      queryClient.invalidateQueries({ queryKey: queryKey.learner.session(sessionId) })
      queryClient.invalidateQueries({ queryKey: queryKey.learner.dashboard() })
    },
  })
}

export function useAbandonSession() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (sessionId: UUID) => studySessionApi.abandon(sessionId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: queryKey.learner.sessions() })
    },
  })
}

export function useSessionSummary(sessionId: UUID | null) {
  return useQuery({
    queryKey: queryKey.learner.sessionSummary(sessionId!),
    queryFn: () => studySessionApi.getSummary(sessionId!),
    enabled: !!sessionId,
  })
}

// ============================================================
// Questions
// ============================================================

export function useQuestion(questionInstanceId: UUID | null) {
  return useQuery({
    queryKey: queryKey.learner.question(questionInstanceId!),
    queryFn: () => questionApi.getById(questionInstanceId!),
    enabled: !!questionInstanceId,
  })
}

export function useSubmitAnswer() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: ({
      questionInstanceId,
      data,
    }: {
      questionInstanceId: UUID
      data: SubmitAnswerRequest
    }) => questionApi.submit(questionInstanceId, data),
    onSuccess: (_data, { questionInstanceId }) => {
      queryClient.invalidateQueries({
        queryKey: queryKey.learner.question(questionInstanceId),
      })
      queryClient.invalidateQueries({ queryKey: queryKey.learner.dashboard() })
      // Invalidate all adaptive-queue queries (sessionId-based)
      queryClient.invalidateQueries({ queryKey: ['learner'] })
    },
  })
}

// ============================================================
// Mastery
// ============================================================

export function useMasteryScores(enrollmentId: UUID | null) {
  return useQuery({
    queryKey: queryKey.learner.mastery(enrollmentId!),
    queryFn: () => masteryApi.getByEnrollment(enrollmentId!),
    enabled: !!enrollmentId,
  })
}

export function useWeakConcepts(enrollmentId: UUID | null) {
  return useQuery({
    queryKey: queryKey.learner.weakConcepts(enrollmentId!),
    queryFn: () => masteryApi.getWeakConcepts(enrollmentId!),
    enabled: !!enrollmentId,
  })
}

export function useMasteryTimeline(enrollmentId: UUID | null, conceptId?: UUID) {
  return useQuery({
    queryKey: queryKey.learner.masteryTimeline(enrollmentId!, conceptId),
    queryFn: () => masteryApi.getTimeline(enrollmentId!, conceptId),
    enabled: !!enrollmentId,
  })
}

// ============================================================
// Reviews
// ============================================================

export function useDueReviews(enrollmentId: UUID | null) {
  return useQuery({
    queryKey: queryKey.learner.dueReviews(enrollmentId!),
    queryFn: () => reviewApi.getDue(enrollmentId!),
    enabled: !!enrollmentId,
  })
}

export function useUpcomingReviews(enrollmentId: UUID | null, days = 7) {
  return useQuery({
    queryKey: queryKey.learner.upcomingReviews(enrollmentId!, days),
    queryFn: () => reviewApi.getUpcoming(enrollmentId!, days),
    enabled: !!enrollmentId,
  })
}

export function useReviewStats(enrollmentId: UUID | null) {
  return useQuery({
    queryKey: queryKey.learner.reviewStats(enrollmentId!),
    queryFn: () => reviewApi.getStats(enrollmentId!),
    enabled: !!enrollmentId,
  })
}

// ============================================================
// Recommendations
// ============================================================

export function useRecommendations(enrollmentId?: UUID) {
  return useQuery({
    queryKey: queryKey.learner.recommendations(enrollmentId),
    queryFn: () => recommendationApi.list(enrollmentId),
  })
}

export function useDismissRecommendation() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (id: UUID) => recommendationApi.dismiss(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: queryKey.learner.recommendations() })
    },
  })
}

export function useAcceptRecommendation() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (id: UUID) => recommendationApi.accept(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: queryKey.learner.recommendations() })
      queryClient.invalidateQueries({ queryKey: queryKey.learner.dashboard() })
    },
  })
}

// ============================================================
// Achievements
// ============================================================

export function useAchievements() {
  return useQuery({
    queryKey: queryKey.learner.achievements(),
    queryFn: () => achievementApi.list(),
  })
}

// ============================================================
// Notifications
// ============================================================

export function useNotifications(params?: { status?: string; page?: number; pageSize?: number }) {
  return useQuery({
    queryKey: queryKey.learner.notifications(params),
    queryFn: () => notificationApi.list(params),
  })
}

export function useUnreadNotificationCount() {
  return useQuery({
    queryKey: queryKey.learner.unreadNotificationCount(),
    queryFn: () => notificationApi.getUnreadCount(),
    refetchInterval: 60_000, // Refresh every minute
  })
}

export function useMarkNotificationOpened() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (id: UUID) => notificationApi.markOpened(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: queryKey.learner.notifications() })
      queryClient.invalidateQueries({ queryKey: queryKey.learner.unreadNotificationCount() })
    },
  })
}

export function useMarkNotificationDismissed() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (id: UUID) => notificationApi.markDismissed(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: queryKey.learner.notifications() })
      queryClient.invalidateQueries({ queryKey: queryKey.learner.unreadNotificationCount() })
    },
  })
}

export function useMarkAllNotificationsOpened() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: () => notificationApi.markAllOpened(),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: queryKey.learner.notifications() })
      queryClient.invalidateQueries({ queryKey: queryKey.learner.unreadNotificationCount() })
    },
  })
}
