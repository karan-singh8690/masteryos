/**
 * Beta Ops API client — Closed Beta Operations Platform (Task 026).
 *
 * All endpoints are under /api/v1/admin/beta-ops/* and require
 * ROLE_ADMINISTRATOR or ROLE_SYSTEM_ADMIN.
 */

import { apiClient } from '@/lib/api-client'

// ============================================================
// Response types
// ============================================================

export interface BetaOpsDashboard {
  total_invited: number
  active_beta_users: number
  daily_active_users: number
  weekly_active_users: number
  monthly_active_users: number
  invite_conversion_rate: number
  avg_session_duration_minutes: number
  study_sessions_completed: number
  feedback_received: number
  bugs_reported: number
  crash_reports: number
  nps_score: number
  user_satisfaction: number
  learning_progress_avg: number
  retention_day_1: number
  retention_day_7: number
  retention_day_30: number
  generated_at: string
}

export interface FunnelStep {
  step: string
  count: number
  cumulative_pct: number
  step_pct: number
  median_time_from_previous_minutes: number | null
}

export interface RegistrationFunnel {
  steps: FunnelStep[]
  overall_conversion: number
  biggest_drop_step: string | null
  avg_time_to_first_question_minutes: number | null
}

export interface RetentionCohort {
  cohort_week: string
  cohort_size: number
  week_0: number
  week_1: number
  week_2: number
  week_3: number
  week_4: number
}

export interface LearningEffectiveness {
  mastery_growth_avg: number
  time_to_mastery_hours: number | null
  weak_concepts: Array<{ concept_id: string; avg_mastery: number; avg_confidence: number; enrollment_count: number }>
  strong_concepts: Array<{ concept_id: string; avg_mastery: number; avg_confidence: number; enrollment_count: number }>
  review_effectiveness: number
  question_accuracy: number
  average_confidence: number
  hint_usage_rate: number
  recommendation_acceptance: number
  adaptive_queue_quality: number
  interview_readiness_trend: Array<{ week: string; avg_readiness: number }>
}

export interface FeedbackItem {
  id: string
  user_id: string
  rating: number
  category: string
  comment: string
  status: string
  priority: string
  roadmap_status: string
  vote_score: number
  vote_count: number
  duplicate_of: string | null
  tags: string[]
  created_at: string
}

export interface FeedbackPlatform {
  items: FeedbackItem[]
  total: number
  by_category: Record<string, number>
  by_priority: Record<string, number>
  by_status: Record<string, number>
  avg_vote_score: number
  top_voted: FeedbackItem[]
  potential_duplicates: Array<Record<string, unknown>>
}

export interface UserSuccessSignal {
  user_id: string
  email: string
  signal_type: string
  severity: string
  description: string
  last_activity: string | null
  recommendation: string
}

export interface UserSuccessReport {
  inactive_users: UserSuccessSignal[]
  at_risk_users: UserSuccessSignal[]
  incomplete_onboarding: UserSuccessSignal[]
  stuck_in_learning: UserSuccessSignal[]
  no_study_7_days: UserSuccessSignal[]
  failed_registration: UserSuccessSignal[]
  email_verification_pending: UserSuccessSignal[]
  recommendation_ignored: UserSuccessSignal[]
  summary: Record<string, number>
}

export interface InstructorAnalytics {
  content_quality: Record<string, unknown>
  concept_coverage: Record<string, unknown>
  question_quality: Record<string, unknown>
  template_usage: Array<Record<string, unknown>>
  difficulty_balance: Record<string, number>
  poor_performing_concepts: Array<Record<string, unknown>>
  frequently_missed_questions: Array<Record<string, unknown>>
  misconceptions: Array<Record<string, unknown>>
  explanation_usefulness: Record<string, unknown>
}

export interface OperationalHealth {
  platform_health: Record<string, unknown>
  worker_health: Record<string, unknown>
  background_jobs: Record<string, unknown>
  queue_status: Record<string, number>
  email_delivery: Record<string, number>
  notification_delivery: Record<string, number>
  database_health: Record<string, unknown>
  redis_health: Record<string, unknown>
  storage_usage: Record<string, unknown>
  api_latency: Record<string, unknown>
  ai_usage: Record<string, unknown>
  cost_metrics: Record<string, unknown>
}

export interface ReleaseNote {
  id: string
  version: string
  release_type: string
  title: string
  summary: string | null
  body: string
  features: Array<Record<string, unknown>>
  bug_fixes: Array<Record<string, unknown>>
  breaking_changes: Array<Record<string, unknown>>
  known_issues: Array<Record<string, unknown>>
  feature_freeze: boolean
  published_at: string | null
  current_stage: string | null
  rollout_percentage: number
}

export interface ReleaseManagement {
  releases: ReleaseNote[]
  current_version: string | null
  feature_freeze_active: boolean
  version_timeline: Array<Record<string, unknown>>
  rollback_history: Array<Record<string, unknown>>
}

export interface BetaReport {
  period: string
  period_start: string
  period_end: string
  growth: Record<string, unknown>
  retention: Record<string, number>
  learning_outcomes: Record<string, unknown>
  feedback_summary: Record<string, unknown>
  top_bugs: Array<Record<string, unknown>>
  top_requests: Array<Record<string, unknown>>
  system_health: Record<string, unknown>
  generated_at: string
}

export interface Experiment {
  id: string
  name: string
  description: string | null
  experiment_type: string
  variant_a: string
  variant_b: string
  rollout_percentage: number
  status: string
  target_metric: string | null
  min_sample_size: number
  started_at: string | null
  ended_at: string | null
  winner: string | null
  sample_size_a: number
  sample_size_b: number
  is_statistically_significant: boolean
  metadata: Record<string, unknown>
}

export interface ExperimentResults {
  experiment: Experiment
  variant_a_results: Record<string, unknown>
  variant_b_results: Record<string, unknown>
  statistical_significance: Record<string, unknown>
  recommendation: string
}

// ============================================================
// API client
// ============================================================

const BASE = '/admin/beta-ops'

export const betaOpsApi = {
  // Part 1
  getDashboard: () => apiClient.get<BetaOpsDashboard>(`${BASE}/dashboard`),

  // Part 2
  getFunnel: (days = 30) =>
    apiClient.get<RegistrationFunnel>(`${BASE}/analytics/funnel?days=${days}`),
  getRetention: (weeks = 8) =>
    apiClient.get<RetentionCohort[]>(`${BASE}/analytics/retention?weeks=${weeks}`),

  // Part 3
  getLearning: () => apiClient.get<LearningEffectiveness>(`${BASE}/learning`),

  // Part 4
  getFeedback: (limit = 100) =>
    apiClient.get<FeedbackPlatform>(`${BASE}/feedback?limit=${limit}`),
  voteFeedback: (feedbackId: string, vote: number) =>
    apiClient.post<{ message: string }>(`${BASE}/feedback/${feedbackId}/vote`, { vote }),
  updateFeedbackMeta: (
    feedbackId: string,
    payload: {
      priority?: string
      roadmap_status?: string
      roadmap_link?: string
      tags?: string[]
      assigned_to?: string
    }
  ) => apiClient.patch<{ message: string }>(`${BASE}/feedback/${feedbackId}/meta`, payload),
  markDuplicate: (feedbackId: string, duplicateOf: string) =>
    apiClient.post<{ message: string }>(`${BASE}/feedback/${feedbackId}/mark-duplicate`, {
      duplicate_of: duplicateOf,
    }),

  // Part 5
  getUserSuccess: () => apiClient.get<UserSuccessReport>(`${BASE}/success`),

  // Part 6
  getInstructor: () => apiClient.get<InstructorAnalytics>(`${BASE}/instructor`),

  // Part 7
  getOperations: () => apiClient.get<OperationalHealth>(`${BASE}/operations`),

  // Part 8
  getReleases: () => apiClient.get<ReleaseManagement>(`${BASE}/releases`),
  createRelease: (payload: Record<string, unknown>) =>
    apiClient.post<ReleaseNote>(`${BASE}/releases`, payload),
  updateRelease: (releaseId: string, payload: Record<string, unknown>) =>
    apiClient.patch<{ message: string }>(`${BASE}/releases/${releaseId}`, payload),
  addReleaseStage: (releaseId: string, payload: { stage: string; rollout_percentage: number; notes?: string }) =>
    apiClient.post<{ message: string }>(`${BASE}/releases/${releaseId}/stage`, payload),

  // Part 9
  getReport: (period: 'daily' | 'weekly' | 'monthly') =>
    apiClient.get<BetaReport>(`${BASE}/reports/${period}`),
  generateReport: (period: 'daily' | 'weekly' | 'monthly') =>
    apiClient.post<BetaReport>(`${BASE}/reports/generate`, { period }),

  // Part 10
  listExperiments: () => apiClient.get<Experiment[]>(`${BASE}/experiments`),
  getExperiment: (experimentId: string) =>
    apiClient.get<ExperimentResults>(`${BASE}/experiments/${experimentId}`),
  createExperiment: (payload: Record<string, unknown>) =>
    apiClient.post<Experiment>(`${BASE}/experiments`, payload),
  updateExperiment: (experimentId: string, payload: Record<string, unknown>) =>
    apiClient.patch<{ message: string }>(`${BASE}/experiments/${experimentId}`, payload),
  assignVariant: (experimentId: string, userId: string) =>
    apiClient.post<{ message: string }>(`${BASE}/experiments/${experimentId}/assign`, {
      user_id: userId,
    }),
  recordExperimentResult: (
    experimentId: string,
    payload: {
      variant: string
      sample_size: number
      metric_value?: number
      metric_std_error?: number
      conversion_count: number
      metadata?: Record<string, unknown>
    }
  ) => apiClient.post<{ message: string }>(`${BASE}/experiments/${experimentId}/results`, payload),
}
