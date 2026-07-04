/**
 * Learner API client — all learning-related API calls.
 */

import { apiClient } from '@/lib/api-client'
import type {
  Subject,
  Concept,
  Enrollment,
  EnrollmentRequest,
  LearningGoal,
  SetGoalRequest,
  StudySession,
  StartSessionRequest,
  AdaptiveQueue,
  Question,
  SubmitAnswerRequest,
  SubmitAnswerResponse,
  DashboardData,
  SessionSummary,
  Achievement,
  LearnerNotification,
  RecommendationWithDetails,
  ReviewWithDetails,
  ReviewStats,
  MasteryScore,
} from '@/types/learning'
import type { UUID } from '@/types/common'
import type { PaginationParams, PaginatedResponse } from '@/types/common'

// ============================================================
// Subjects API
// ============================================================

export const subjectApi = {
  list: () => apiClient.get<Subject[]>('/admin/subjects'),

  getById: (id: UUID) => apiClient.get<Subject>(`/admin/subjects/${id}`),

  getConcepts: (subjectId: UUID) =>
    apiClient.get<Concept[]>(`/admin/subjects/${subjectId}/concepts`),
}

// ============================================================
// Enrollment API
// ============================================================

export const enrollmentApi = {
  enroll: (data: EnrollmentRequest) =>
    apiClient.post<Enrollment>('/enrollments', data),

  list: () => apiClient.get<Enrollment[]>('/enrollments'),

  getById: (id: UUID) => apiClient.get<Enrollment>(`/enrollments/${id}`),

  setLearningGoal: (enrollmentId: UUID, data: SetGoalRequest) =>
    apiClient.post<LearningGoal>(`/enrollments/${enrollmentId}/learning-goals`, data),
}

// ============================================================
// Study Session API
// ============================================================

export const studySessionApi = {
  start: (data: StartSessionRequest) =>
    apiClient.post<StudySession>('/study-sessions', data),

  getById: (id: UUID) => apiClient.get<StudySession>(`/study-sessions/${id}`),

  getAdaptiveQueue: (sessionId: UUID) =>
    apiClient.get<AdaptiveQueue>(`/study-sessions/${sessionId}/adaptive-queue`),

  end: (id: UUID) =>
    apiClient.post<{ message: string }>(`/study-sessions/${id}/end`),

  abandon: (id: UUID) =>
    apiClient.post<{ message: string }>(`/study-sessions/${id}/abandon`),

  pause: (id: UUID) =>
    apiClient.post<{ message: string }>(`/study-sessions/${id}/pause`),

  resume: (id: UUID) =>
    apiClient.post<{ message: string }>(`/study-sessions/${id}/resume`),

  getSummary: (id: UUID) =>
    apiClient.get<SessionSummary>(`/study-sessions/${id}/summary`),
}

// ============================================================
// Question API
// ============================================================

export const questionApi = {
  getById: (questionInstanceId: UUID) =>
    apiClient.get<Question>(`/questions/${questionInstanceId}`),

  submit: (questionInstanceId: UUID, data: SubmitAnswerRequest) =>
    apiClient.post<SubmitAnswerResponse>(
      `/questions/${questionInstanceId}/submit`,
      data,
    ),
}

// ============================================================
// Dashboard API
// ============================================================

export const dashboardApi = {
  get: () => apiClient.get<DashboardData>('/questions/dashboard'),
}

// ============================================================
// Mastery API
// ============================================================

export const masteryApi = {
  getByEnrollment: (enrollmentId: UUID) =>
    apiClient.get<MasteryScore[]>(`/mastery/scores/${enrollmentId}`),

  getByConcept: (enrollmentId: UUID, conceptId: UUID) =>
    apiClient.get<MasteryScore>(`/mastery/scores/${enrollmentId}/${conceptId}`),

  getWeakConcepts: (enrollmentId: UUID) =>
    apiClient.get<MasteryScore[]>(`/mastery/scores/${enrollmentId}/weak`),

  getTimeline: (enrollmentId: UUID, conceptId?: UUID) =>
    apiClient.get<{ date: string; value: number }[]>(
      `/mastery/timeline/${enrollmentId}${conceptId ? `/${conceptId}` : ''}`,
    ),
}

// ============================================================
// Review API
// ============================================================

export const reviewApi = {
  getDue: (enrollmentId: UUID) =>
    apiClient.get<ReviewWithDetails[]>(`/reviews/due/${enrollmentId}`),

  getUpcoming: (enrollmentId: UUID, days = 7) =>
    apiClient.get<ReviewWithDetails[]>(`/reviews/upcoming/${enrollmentId}?days=${days}`),

  getCompleted: (enrollmentId: UUID, params?: PaginationParams) =>
    apiClient.get<PaginatedResponse<ReviewWithDetails>>(
      `/reviews/completed/${enrollmentId}`,
      { params },
    ),

  getStats: (enrollmentId: UUID) =>
    apiClient.get<ReviewStats>(`/reviews/stats/${enrollmentId}`),
}

// ============================================================
// Recommendation API
// ============================================================

export const recommendationApi = {
  list: (enrollmentId?: UUID) =>
    apiClient.get<RecommendationWithDetails[]>(
      `/recommendations${enrollmentId ? `?enrollment_id=${enrollmentId}` : ''}`,
    ),

  dismiss: (id: UUID) =>
    apiClient.post<{ message: string }>(`/recommendations/${id}/dismiss`),

  accept: (id: UUID) =>
    apiClient.post<{ message: string }>(`/recommendations/${id}/accept`),

  getHistory: (params?: PaginationParams) =>
    apiClient.get<PaginatedResponse<RecommendationWithDetails>>(
      `/recommendations/history`,
      { params },
    ),
}

// ============================================================
// Achievement API
// ============================================================

export const achievementApi = {
  list: () => apiClient.get<Achievement[]>('/achievements'),

  getById: (id: UUID) => apiClient.get<Achievement>(`/achievements/${id}`),
}

// ============================================================
// Notification API
// ============================================================

export const notificationApi = {
  list: (params?: PaginationParams & { status?: string }) =>
    apiClient.get<PaginatedResponse<LearnerNotification>>('/notifications', { params }),

  markOpened: (id: UUID) =>
    apiClient.post<{ message: string }>(`/notifications/${id}/open`),

  markDismissed: (id: UUID) =>
    apiClient.post<{ message: string }>(`/notifications/${id}/dismiss`),

  markAllOpened: () =>
    apiClient.post<{ message: string }>('/notifications/mark-all-open'),

  getUnreadCount: () =>
    apiClient.get<{ count: number }>('/notifications/unread-count'),
}
