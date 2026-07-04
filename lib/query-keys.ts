/**
 * Query key factory for React Query.
 *
 * Provides a centralized, type-safe way to manage query keys.
 * This ensures consistent cache keys and easy invalidation.
 *
 * Usage:
 *   queryKey.users.me() → ['users', 'me']
 *   queryKey.notifications.list({ status: 'unread' }) → ['notifications', 'list', { status: 'unread' }]
 *
 *   // Invalidate all user queries
 *   queryClient.invalidateQueries({ queryKey: queryKey.users.all })
 */

import type { UUID } from '@/types/common'

export const queryKey = {
  // Auth
  auth: {
    all: ['auth'] as const,
    me: () => ['auth', 'me'] as const,
    session: () => ['auth', 'session'] as const,
  },

  // Users
  users: {
    all: ['users'] as const,
    me: () => ['users', 'me'] as const,
    security: () => ['users', 'me', 'security'] as const,
    detail: (id: UUID) => ['users', id] as const,
  },

  // Notifications
  notifications: {
    all: ['notifications'] as const,
    list: (filters?: Record<string, unknown>) =>
      ['notifications', 'list', filters] as const,
    detail: (id: UUID) => ['notifications', id] as const,
    unreadCount: () => ['notifications', 'unread-count'] as const,
  },

  // Learning
  learning: {
    all: ['learning'] as const,
    enrollments: () => ['learning', 'enrollments'] as const,
    sessions: () => ['learning', 'sessions'] as const,
    session: (id: UUID) => ['learning', 'sessions', id] as const,
    adaptiveQueue: (sessionId: UUID) =>
      ['learning', 'sessions', sessionId, 'adaptive-queue'] as const,
  },

  // Mastery
  mastery: {
    all: ['mastery'] as const,
    scores: (enrollmentId: UUID) => ['mastery', 'scores', enrollmentId] as const,
    reviews: (enrollmentId: UUID) => ['mastery', 'reviews', enrollmentId] as const,
  },

  // Content
  content: {
    all: ['content'] as const,
    subjects: () => ['content', 'subjects'] as const,
    concepts: (subjectId: UUID) => ['content', 'subjects', subjectId, 'concepts'] as const,
  },

  // Learner (Task 019)
  learner: {
    all: ['learner'] as const,
    dashboard: () => ['learner', 'dashboard'] as const,
    subjects: () => ['learner', 'subjects'] as const,
    subject: (id: UUID) => ['learner', 'subjects', id] as const,
    concepts: (subjectId: UUID) => ['learner', 'subjects', subjectId, 'concepts'] as const,
    enrollments: () => ['learner', 'enrollments'] as const,
    enrollment: (id: UUID) => ['learner', 'enrollments', id] as const,
    sessions: () => ['learner', 'sessions'] as const,
    session: (id: UUID) => ['learner', 'sessions', id] as const,
    sessionSummary: (id: UUID) => ['learner', 'sessions', id, 'summary'] as const,
    adaptiveQueue: (sessionId: UUID) => ['learner', 'sessions', sessionId, 'adaptive-queue'] as const,
    question: (id: UUID) => ['learner', 'questions', id] as const,
    mastery: (enrollmentId: UUID) => ['learner', 'mastery', enrollmentId] as const,
    weakConcepts: (enrollmentId: UUID) => ['learner', 'mastery', enrollmentId, 'weak'] as const,
    masteryTimeline: (enrollmentId: UUID, conceptId?: UUID) =>
      ['learner', 'mastery', enrollmentId, 'timeline', conceptId ?? 'all'] as const,
    dueReviews: (enrollmentId: UUID) => ['learner', 'reviews', enrollmentId, 'due'] as const,
    upcomingReviews: (enrollmentId: UUID, days: number) =>
      ['learner', 'reviews', enrollmentId, 'upcoming', days] as const,
    reviewStats: (enrollmentId: UUID) => ['learner', 'reviews', enrollmentId, 'stats'] as const,
    recommendations: (enrollmentId?: UUID) =>
      ['learner', 'recommendations', enrollmentId ?? 'all'] as const,
    achievements: () => ['learner', 'achievements'] as const,
    notifications: (filters?: Record<string, unknown>) =>
      ['learner', 'notifications', filters] as const,
    unreadNotificationCount: () => ['learner', 'notifications', 'unread-count'] as const,
  },

  // Content authoring (Task 020)
  content: {
    all: ['content-authoring'] as const,
    dashboard: () => ['content-authoring', 'dashboard'] as const,
    analytics: (subjectId?: UUID) =>
      ['content-authoring', 'analytics', subjectId ?? 'all'] as const,
    subjects: () => ['content-authoring', 'subjects'] as const,
    subject: (id: UUID) => ['content-authoring', 'subjects', id] as const,
    concepts: (subjectId: UUID) =>
      ['content-authoring', 'subjects', subjectId, 'concepts'] as const,
    concept: (id: UUID) => ['content-authoring', 'concepts', id] as const,
    objectives: (conceptId: UUID) =>
      ['content-authoring', 'concepts', conceptId, 'objectives'] as const,
    misconceptions: (conceptId: UUID) =>
      ['content-authoring', 'concepts', conceptId, 'misconceptions'] as const,
    templates: (subjectId: UUID) =>
      ['content-authoring', 'subjects', subjectId, 'templates'] as const,
    template: (id: UUID) => ['content-authoring', 'templates', id] as const,
    templatePreview: (templateId: UUID, seed?: number) =>
      ['content-authoring', 'templates', templateId, 'preview', seed ?? 'default'] as const,
    search: (query: string) => ['content-authoring', 'search', query] as const,
  },

  // Admin
  admin: {
    all: ['admin'] as const,
    opsDashboard: () => ['admin', 'ops-dashboard'] as const,
    workers: () => ['admin', 'workers'] as const,
    workerMetrics: () => ['admin', 'workers', 'metrics'] as const,
    outbox: (filters?: Record<string, unknown>) => ['admin', 'outbox', filters] as const,
    outboxStats: () => ['admin', 'outbox', 'stats'] as const,
    deadLetters: (filters?: Record<string, unknown>) =>
      ['admin', 'dead-letters', filters] as const,
    notifications: (filters?: Record<string, unknown>) =>
      ['admin', 'notifications', filters] as const,
    jobs: () => ['admin', 'jobs'] as const,
    // Task 021 additions
    users: (filters?: Record<string, unknown>) => ['admin', 'users', filters] as const,
    user: (id: UUID) => ['admin', 'users', id] as const,
    organizations: () => ['admin', 'organizations'] as const,
    organization: (id: UUID) => ['admin', 'organizations', id] as const,
    roles: () => ['admin', 'rbac', 'roles'] as const,
    permissions: () => ['admin', 'rbac', 'permissions'] as const,
    featureFlags: () => ['admin', 'feature-flags'] as const,
    featureFlag: (id: UUID) => ['admin', 'feature-flags', id] as const,
    auditLogs: (filters?: Record<string, unknown>) => ['admin', 'audit-logs', filters] as const,
    securityDashboard: () => ['admin', 'security', 'dashboard'] as const,
    securityIncidents: (filters?: Record<string, unknown>) =>
      ['admin', 'security', 'incidents', filters] as const,
    emailDelivery: (filters?: Record<string, unknown>) =>
      ['admin', 'email-delivery', filters] as const,
    billingPlans: () => ['admin', 'billing', 'plans'] as const,
    billingSubscriptions: () => ['admin', 'billing', 'subscriptions'] as const,
    billingInvoices: () => ['admin', 'billing', 'invoices'] as const,
    billingRevenue: () => ['admin', 'billing', 'revenue'] as const,
    analytics: () => ['admin', 'analytics'] as const,
    systemConfig: () => ['admin', 'system-config'] as const,
    search: (query: string) => ['admin', 'search', query] as const,
  },
} as const

export type QueryKey = typeof queryKey
