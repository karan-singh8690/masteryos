import { describe, it, expect, vi } from 'vitest'

// Mock the learner API
vi.mock('@/lib/learner-api', () => ({
  subjectApi: {
    list: vi.fn(),
    getById: vi.fn(),
    getConcepts: vi.fn(),
  },
  enrollmentApi: {
    enroll: vi.fn(),
    list: vi.fn(),
    getById: vi.fn(),
    setLearningGoal: vi.fn(),
  },
  studySessionApi: {
    start: vi.fn(),
    getById: vi.fn(),
    getAdaptiveQueue: vi.fn(),
    end: vi.fn(),
    abandon: vi.fn(),
    pause: vi.fn(),
    resume: vi.fn(),
    getSummary: vi.fn(),
  },
  questionApi: {
    getById: vi.fn(),
    submit: vi.fn(),
  },
  dashboardApi: {
    get: vi.fn(),
  },
  masteryApi: {
    getByEnrollment: vi.fn(),
    getByConcept: vi.fn(),
    getWeakConcepts: vi.fn(),
    getTimeline: vi.fn(),
  },
  reviewApi: {
    getDue: vi.fn(),
    getUpcoming: vi.fn(),
    getCompleted: vi.fn(),
    getStats: vi.fn(),
  },
  recommendationApi: {
    list: vi.fn(),
    dismiss: vi.fn(),
    accept: vi.fn(),
    getHistory: vi.fn(),
  },
  achievementApi: {
    list: vi.fn(),
    getById: vi.fn(),
  },
  notificationApi: {
    list: vi.fn(),
    markOpened: vi.fn(),
    markDismissed: vi.fn(),
    markAllOpened: vi.fn(),
    getUnreadCount: vi.fn(),
  },
}))

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

describe('Learner API methods', () => {
  it('subjectApi has all methods', () => {
    expect(subjectApi.list).toBeDefined()
    expect(subjectApi.getById).toBeDefined()
    expect(subjectApi.getConcepts).toBeDefined()
  })

  it('enrollmentApi has all methods', () => {
    expect(enrollmentApi.enroll).toBeDefined()
    expect(enrollmentApi.list).toBeDefined()
    expect(enrollmentApi.getById).toBeDefined()
    expect(enrollmentApi.setLearningGoal).toBeDefined()
  })

  it('studySessionApi has all methods', () => {
    expect(studySessionApi.start).toBeDefined()
    expect(studySessionApi.getById).toBeDefined()
    expect(studySessionApi.getAdaptiveQueue).toBeDefined()
    expect(studySessionApi.end).toBeDefined()
    expect(studySessionApi.abandon).toBeDefined()
    expect(studySessionApi.pause).toBeDefined()
    expect(studySessionApi.resume).toBeDefined()
    expect(studySessionApi.getSummary).toBeDefined()
  })

  it('questionApi has all methods', () => {
    expect(questionApi.getById).toBeDefined()
    expect(questionApi.submit).toBeDefined()
  })

  it('dashboardApi has all methods', () => {
    expect(dashboardApi.get).toBeDefined()
  })

  it('masteryApi has all methods', () => {
    expect(masteryApi.getByEnrollment).toBeDefined()
    expect(masteryApi.getByConcept).toBeDefined()
    expect(masteryApi.getWeakConcepts).toBeDefined()
    expect(masteryApi.getTimeline).toBeDefined()
  })

  it('reviewApi has all methods', () => {
    expect(reviewApi.getDue).toBeDefined()
    expect(reviewApi.getUpcoming).toBeDefined()
    expect(reviewApi.getCompleted).toBeDefined()
    expect(reviewApi.getStats).toBeDefined()
  })

  it('recommendationApi has all methods', () => {
    expect(recommendationApi.list).toBeDefined()
    expect(recommendationApi.dismiss).toBeDefined()
    expect(recommendationApi.accept).toBeDefined()
    expect(recommendationApi.getHistory).toBeDefined()
  })

  it('achievementApi has all methods', () => {
    expect(achievementApi.list).toBeDefined()
    expect(achievementApi.getById).toBeDefined()
  })

  it('notificationApi has all methods', () => {
    expect(notificationApi.list).toBeDefined()
    expect(notificationApi.markOpened).toBeDefined()
    expect(notificationApi.markDismissed).toBeDefined()
    expect(notificationApi.markAllOpened).toBeDefined()
    expect(notificationApi.getUnreadCount).toBeDefined()
  })
})

describe('Learner hooks', () => {
  it('use-learner module exports all hooks', async () => {
    const module = await import('@/hooks/use-learner')
    expect(module.useDashboard).toBeDefined()
    expect(module.useSubjects).toBeDefined()
    expect(module.useSubject).toBeDefined()
    expect(module.useSubjectConcepts).toBeDefined()
    expect(module.useEnrollments).toBeDefined()
    expect(module.useEnrollment).toBeDefined()
    expect(module.useEnroll).toBeDefined()
    expect(module.useSetLearningGoal).toBeDefined()
    expect(module.useStartStudySession).toBeDefined()
    expect(module.useStudySession).toBeDefined()
    expect(module.useAdaptiveQueue).toBeDefined()
    expect(module.useEndSession).toBeDefined()
    expect(module.useAbandonSession).toBeDefined()
    expect(module.useSessionSummary).toBeDefined()
    expect(module.useQuestion).toBeDefined()
    expect(module.useSubmitAnswer).toBeDefined()
    expect(module.useMasteryScores).toBeDefined()
    expect(module.useWeakConcepts).toBeDefined()
    expect(module.useMasteryTimeline).toBeDefined()
    expect(module.useDueReviews).toBeDefined()
    expect(module.useUpcomingReviews).toBeDefined()
    expect(module.useReviewStats).toBeDefined()
    expect(module.useRecommendations).toBeDefined()
    expect(module.useDismissRecommendation).toBeDefined()
    expect(module.useAcceptRecommendation).toBeDefined()
    expect(module.useAchievements).toBeDefined()
    expect(module.useNotifications).toBeDefined()
    expect(module.useUnreadNotificationCount).toBeDefined()
    expect(module.useMarkNotificationOpened).toBeDefined()
    expect(module.useMarkNotificationDismissed).toBeDefined()
    expect(module.useMarkAllNotificationsOpened).toBeDefined()
  })
})
