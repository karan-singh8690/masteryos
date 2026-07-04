/**
 * Learning types — subjects, enrollments, study sessions, adaptive queue.
 */

import type { ISO8601, UUID } from './common'

// ============================================================
// Subjects
// ============================================================

export interface Subject {
  id: UUID
  name: string
  slug: string
  description: string
  status: 'draft' | 'in_review' | 'published' | 'rejected'
  difficulty_level: 'beginner' | 'intermediate' | 'advanced'
  estimated_hours: number
  concept_count: number
  question_count: number
  published_at: ISO8601 | null
  created_at: ISO8601
}

export interface Concept {
  id: UUID
  subject_id: UUID
  name: string
  slug: string
  description: string
  difficulty: 'beginner' | 'intermediate' | 'advanced'
  importance: 'low' | 'medium' | 'high' | 'critical'
  prerequisites: UUID[]
  created_at: ISO8601
}

// ============================================================
// Enrollments
// ============================================================

export interface Enrollment {
  id: UUID
  user_id: UUID
  subject_id: UUID
  subject_name: string
  status: 'pending_onboarding' | 'active' | 'dormant' | 'unenrolled' | 'anonymized'
  enrolled_at: ISO8601
  onboarded_at: ISO8601 | null
  last_active_at: ISO8601 | null
  unenrolled_at: ISO8601 | null
  progress: number
  mastery_score: number
}

export interface EnrollmentRequest {
  subject_id: UUID
}

// ============================================================
// Learning Goals
// ============================================================

export interface LearningGoal {
  id: UUID
  enrollment_id: UUID
  goal_type: 'daily_questions' | 'daily_minutes' | 'weekly_sessions' | 'mastery_target'
  target_value: number
  current_value: number
  status: 'active' | 'completed' | 'abandoned'
  created_at: ISO8601
  completed_at: ISO8601 | null
}

export interface SetGoalRequest {
  goal_type: string
  target_value: number
}

// ============================================================
// Study Sessions
// ============================================================

export interface StudySession {
  id: UUID
  learner_enrollment_id: UUID
  intent: 'practice' | 'review' | 'learn_new' | 'mixed'
  status: 'active' | 'paused' | 'ended' | 'abandoned'
  started_at: ISO8601
  ended_at: ISO8601 | null
  question_count: number
  questions_answered: number
  questions_correct: number
  time_spent_seconds: number
}

export interface StartSessionRequest {
  enrollment_id: UUID
  intent: 'practice' | 'review' | 'learn_new' | 'mixed'
  target_question_count?: number
}

// ============================================================
// Adaptive Queue
// ============================================================

export interface QueueItem {
  question_instance_id: UUID
  concept_id: UUID
  difficulty: 'beginner' | 'intermediate' | 'advanced'
  estimated_duration_seconds: number
  recommendation_score: number
  reason: string
}

export interface AdaptiveQueue {
  study_session_id: UUID
  current_position: number
  questions: QueueItem[]
}

// ============================================================
// Questions
// ============================================================

export interface QuestionChoice {
  id: string
  text: string
  code?: string
  is_correct?: boolean // Only present after submission
  explanation?: string
}

export interface QuestionPrompt {
  text: string
  code?: string
  language?: string
  image_url?: string
  context?: string
}

export interface Question {
  question_instance_id: UUID
  concept_ids: UUID[]
  difficulty: 'beginner' | 'intermediate' | 'advanced'
  estimated_duration_seconds: number
  question_type:
    | 'multiple_choice'
    | 'multiple_select'
    | 'true_false'
    | 'ordering'
    | 'fill_blank'
    | 'matching'
    | 'code_output'
    | 'short_answer'
    | 'numerical'
  prompt: QuestionPrompt
  choices: QuestionChoice[] | null
  metadata: {
    hint_tiers?: string[]
    max_points?: number
    tags?: string[]
    [key: string]: unknown
  }
}

// ============================================================
// Answer Submission
// ============================================================

export interface SubmitAnswerRequest {
  answer: Record<string, unknown>
  answer_type: 'multiple_choice' | 'code' | 'free_response'
  confidence: number
  time_spent_seconds: number
  hint_used: boolean
  hint_tiers_used: number[]
}

export interface AttemptResult {
  attempt_id: UUID
  scoring_outcome: 'correct' | 'partially_correct' | 'incorrect'
  partial_credit: number | null
  time_to_answer_ms: number
  hint_used: boolean
  created_at: ISO8601
}

export interface MasteryScore {
  concept_id: UUID
  memory_score: number
  durable_mastery_score: number
  mastery_score_combined: number
  concept_state: 'unseen' | 'novice' | 'developing' | 'proficient' | 'mastered' | 'decayed'
  weakness_severity: 'none' | 'low' | 'medium' | 'high' | 'critical'
  evidence_count: number
  last_attempt_at: ISO8601 | null
}

export interface ReviewSchedule {
  concept_id: UUID
  due_at: ISO8601
  priority: 'low' | 'medium' | 'high' | 'urgent'
  interval_days: number
}

export interface Explanation {
  content: string
  outcome_key: string
}

export interface Recommendation {
  id: UUID
  recommendation_type: 'review_concept' | 'practice_weakness' | 'learn_new' | 'take_break' | 'advance_topic'
  score: number
  reason: string
}

export interface SubmitAnswerResponse {
  attempt: AttemptResult
  mastery: MasteryScore | null
  review: ReviewSchedule | null
  explanation: Explanation
  recommendation: Recommendation | null
}

// ============================================================
// Dashboard
// ============================================================

export interface DashboardData {
  enrollment_id: UUID | null
  recommended_action: string
  current_streak: number
  longest_streak: number
  weak_concepts: MasteryScore[]
  strong_concepts: MasteryScore[]
  today_reviews: number
  today_queue_remaining: number
  daily_progress: number
  interview_readiness: number
  memory_trend: TrendPoint[]
  mastery_trend: TrendPoint[]
}

export interface TrendPoint {
  date: string
  value: number
  label?: string
}

// ============================================================
// Session Summary
// ============================================================

export interface SessionSummary {
  session_id: UUID
  questions_answered: number
  questions_correct: number
  accuracy: number
  time_spent_seconds: number
  mastery_gained: number
  weak_concepts: MasteryScore[]
  strong_concepts: MasteryScore[]
  recommendations: Recommendation[]
  review_schedule: ReviewSchedule[]
  achievements_unlocked: Achievement[]
}

// ============================================================
// Achievements
// ============================================================

export interface Achievement {
  id: UUID
  name: string
  description: string
  category: 'learning' | 'streak' | 'mastery' | 'social' | 'special'
  icon: string
  unlocked_at: ISO8601 | null
  progress: number
  target: number
  is_unlocked: boolean
}

// ============================================================
// Notifications (learner-specific)
// ============================================================

export interface LearnerNotification {
  id: UUID
  user_id: UUID
  notification_type: string
  channel: 'in_app' | 'email' | 'push' | 'sms'
  priority: 'low' | 'normal' | 'high' | 'urgent'
  status: 'queued' | 'sent' | 'delivered' | 'opened' | 'dismissed' | 'failed'
  title: string
  body: string
  payload: Record<string, unknown>
  scheduled_at: ISO8601
  sent_at: ISO8601 | null
  delivered_at: ISO8601 | null
  opened_at: ISO8601 | null
  dismissed_at: ISO8601 | null
  created_at: ISO8601
}

// ============================================================
// Recommendations
// ============================================================

export interface RecommendationWithDetails extends Recommendation {
  concept_id?: UUID
  concept_name?: string
  subject_id?: UUID
  subject_name?: string
  created_at: ISO8601
  dismissed_at: ISO8601 | null
  accepted_at: ISO8601 | null
}

// ============================================================
// Review
// ============================================================

export interface ReviewWithDetails extends ReviewSchedule {
  concept_name: string
  subject_name: string
  question_count: number
}

export interface ReviewStats {
  total_due: number
  total_today: number
  total_this_week: number
  total_this_month: number
  completion_rate: number
  avg_accuracy: number
}
