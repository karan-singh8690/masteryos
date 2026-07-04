import { describe, it, expect } from 'vitest'

import type {
  Subject,
  Concept,
  Enrollment,
  StudySession,
  AdaptiveQueue,
  QueueItem,
  Question,
  QuestionChoice,
  SubmitAnswerRequest,
  SubmitAnswerResponse,
  AttemptResult,
  MasteryScore,
  ReviewSchedule,
  Explanation,
  Recommendation,
  DashboardData,
  SessionSummary,
  Achievement,
  LearnerNotification,
} from '@/types/learning'

describe('Learning types', () => {
  it('Subject has all fields', () => {
    const subject: Subject = {
      id: 'sub-1',
      name: 'Python Interview Prep',
      slug: 'python-interview-prep',
      description: 'Master Python interviews',
      status: 'published',
      difficulty_level: 'intermediate',
      estimated_hours: 40,
      concept_count: 20,
      question_count: 100,
      published_at: '2024-01-01T00:00:00Z',
      created_at: '2024-01-01T00:00:00Z',
    }
    expect(subject.id).toBe('sub-1')
    expect(subject.name).toBe('Python Interview Prep')
    expect(subject.status).toBe('published')
  })

  it('Concept has all fields', () => {
    const concept: Concept = {
      id: 'concept-1',
      subject_id: 'sub-1',
      name: 'Decorators',
      slug: 'decorators',
      description: 'Python decorators',
      difficulty: 'intermediate',
      importance: 'high',
      prerequisites: [],
      created_at: '2024-01-01T00:00:00Z',
    }
    expect(concept.name).toBe('Decorators')
    expect(concept.difficulty).toBe('intermediate')
  })

  it('Enrollment has all fields', () => {
    const enrollment: Enrollment = {
      id: 'enr-1',
      user_id: 'user-1',
      subject_id: 'sub-1',
      subject_name: 'Python Interview Prep',
      status: 'active',
      enrolled_at: '2024-01-01T00:00:00Z',
      onboarded_at: null,
      last_active_at: null,
      unenrolled_at: null,
      progress: 0.5,
      mastery_score: 0.6,
    }
    expect(enrollment.status).toBe('active')
    expect(enrollment.progress).toBe(0.5)
  })

  it('StudySession has all fields', () => {
    const session: StudySession = {
      id: 'sess-1',
      learner_enrollment_id: 'enr-1',
      intent: 'mixed',
      status: 'active',
      started_at: '2024-01-01T00:00:00Z',
      ended_at: null,
      question_count: 10,
      questions_answered: 0,
      questions_correct: 0,
      time_spent_seconds: 0,
    }
    expect(session.status).toBe('active')
    expect(session.question_count).toBe(10)
  })

  it('QueueItem has all fields', () => {
    const item: QueueItem = {
      question_instance_id: 'q-1',
      concept_id: 'concept-1',
      difficulty: 'intermediate',
      estimated_duration_seconds: 60,
      recommendation_score: 0.8,
      reason: 'Weak concept needs practice',
    }
    expect(item.question_instance_id).toBe('q-1')
    expect(item.recommendation_score).toBe(0.8)
  })

  it('AdaptiveQueue has all fields', () => {
    const queue: AdaptiveQueue = {
      study_session_id: 'sess-1',
      current_position: 0,
      questions: [],
    }
    expect(queue.study_session_id).toBe('sess-1')
    expect(queue.questions).toEqual([])
  })

  it('Question has all fields', () => {
    const question: Question = {
      question_instance_id: 'q-1',
      concept_ids: ['concept-1'],
      difficulty: 'intermediate',
      estimated_duration_seconds: 60,
      question_type: 'multiple_choice',
      prompt: { text: 'What is a decorator?' },
      choices: [
        { id: 'a', text: 'A function modifier' },
        { id: 'b', text: 'A design pattern' },
      ],
      metadata: { hint_tiers: ['Hint 1', 'Hint 2'] },
    }
    expect(question.question_type).toBe('multiple_choice')
    expect(question.choices).toHaveLength(2)
  })

  it('QuestionChoice has optional fields', () => {
    const choice: QuestionChoice = {
      id: 'a',
      text: 'Answer A',
    }
    expect(choice.id).toBe('a')
    expect(choice.is_correct).toBeUndefined()
  })

  it('SubmitAnswerRequest has all fields', () => {
    const request: SubmitAnswerRequest = {
      answer: { choice: 'a' },
      answer_type: 'multiple_choice',
      confidence: 0.8,
      time_spent_seconds: 30,
      hint_used: false,
      hint_tiers_used: [],
    }
    expect(request.answer_type).toBe('multiple_choice')
    expect(request.confidence).toBe(0.8)
  })

  it('AttemptResult has all fields', () => {
    const result: AttemptResult = {
      attempt_id: 'att-1',
      scoring_outcome: 'correct',
      partial_credit: null,
      time_to_answer_ms: 30000,
      hint_used: false,
      created_at: '2024-01-01T00:00:00Z',
    }
    expect(result.scoring_outcome).toBe('correct')
  })

  it('MasteryScore has all fields', () => {
    const score: MasteryScore = {
      concept_id: 'concept-1',
      memory_score: 0.7,
      durable_mastery_score: 0.6,
      mastery_score_combined: 0.65,
      concept_state: 'developing',
      weakness_severity: 'low',
      evidence_count: 5,
      last_attempt_at: '2024-01-01T00:00:00Z',
    }
    expect(score.concept_state).toBe('developing')
    expect(score.evidence_count).toBe(5)
  })

  it('ReviewSchedule has all fields', () => {
    const review: ReviewSchedule = {
      concept_id: 'concept-1',
      due_at: '2024-01-02T00:00:00Z',
      priority: 'high',
      interval_days: 3,
    }
    expect(review.priority).toBe('high')
    expect(review.interval_days).toBe(3)
  })

  it('Explanation has all fields', () => {
    const explanation: Explanation = {
      content: 'Decorators are functions that modify other functions.',
      outcome_key: 'correct',
    }
    expect(explanation.outcome_key).toBe('correct')
  })

  it('Recommendation has all fields', () => {
    const rec: Recommendation = {
      id: 'rec-1',
      recommendation_type: 'review_concept',
      score: 0.9,
      reason: 'Review decorators — last seen 7 days ago',
    }
    expect(rec.recommendation_type).toBe('review_concept')
  })

  it('SubmitAnswerResponse has all fields', () => {
    const response: SubmitAnswerResponse = {
      attempt: {
        attempt_id: 'att-1',
        scoring_outcome: 'correct',
        partial_credit: null,
        time_to_answer_ms: 30000,
        hint_used: false,
        created_at: '2024-01-01T00:00:00Z',
      },
      mastery: null,
      review: null,
      explanation: { content: 'Correct!', outcome_key: 'correct' },
      recommendation: null,
    }
    expect(response.attempt.scoring_outcome).toBe('correct')
  })

  it('DashboardData has all fields', () => {
    const data: DashboardData = {
      enrollment_id: 'enr-1',
      recommended_action: 'Review decorators',
      current_streak: 5,
      longest_streak: 10,
      weak_concepts: [],
      strong_concepts: [],
      today_reviews: 3,
      today_queue_remaining: 7,
      daily_progress: 0.6,
      interview_readiness: 0.75,
      memory_trend: [],
      mastery_trend: [],
    }
    expect(data.current_streak).toBe(5)
    expect(data.interview_readiness).toBe(0.75)
  })

  it('SessionSummary has all fields', () => {
    const summary: SessionSummary = {
      session_id: 'sess-1',
      questions_answered: 10,
      questions_correct: 8,
      accuracy: 0.8,
      time_spent_seconds: 600,
      mastery_gained: 0.15,
      weak_concepts: [],
      strong_concepts: [],
      recommendations: [],
      review_schedule: [],
      achievements_unlocked: [],
    }
    expect(summary.questions_answered).toBe(10)
    expect(summary.accuracy).toBe(0.8)
  })

  it('Achievement has all fields', () => {
    const achievement: Achievement = {
      id: 'ach-1',
      name: 'First Steps',
      description: 'Complete your first question',
      category: 'learning',
      icon: '🎯',
      unlocked_at: '2024-01-01T00:00:00Z',
      progress: 1,
      target: 1,
      is_unlocked: true,
    }
    expect(achievement.is_unlocked).toBe(true)
  })

  it('LearnerNotification has all fields', () => {
    const notification: LearnerNotification = {
      id: 'notif-1',
      user_id: 'user-1',
      notification_type: 'review_due',
      channel: 'in_app',
      priority: 'normal',
      status: 'delivered',
      title: 'Review due',
      body: 'You have 3 reviews due today',
      payload: {},
      scheduled_at: '2024-01-01T00:00:00Z',
      sent_at: '2024-01-01T00:00:00Z',
      delivered_at: '2024-01-01T00:00:00Z',
      opened_at: null,
      dismissed_at: null,
      created_at: '2024-01-01T00:00:00Z',
    }
    expect(notification.notification_type).toBe('review_due')
    expect(notification.status).toBe('delivered')
  })

  it('Question supports all question types', () => {
    const types = [
      'multiple_choice', 'multiple_select', 'true_false',
      'ordering', 'fill_blank', 'matching', 'code_output',
      'short_answer', 'numerical',
    ]
    types.forEach((type) => {
      const question: Question = {
        question_instance_id: 'q-1',
        concept_ids: ['concept-1'],
        difficulty: 'beginner',
        estimated_duration_seconds: 60,
        question_type: type as Question['question_type'],
        prompt: { text: 'Test' },
        choices: null,
        metadata: {},
      }
      expect(question.question_type).toBe(type)
    })
  })
})
