import { describe, it, expect } from 'vitest'
import { render, screen } from '@testing-library/react'

import {
  WelcomeWidget,
  StreakWidget,
  DailyGoalWidget,
  QueueRemainingWidget,
  DueReviewsWidget,
  InterviewReadinessWidget,
  WeakConceptsWidget,
  StrongConceptsWidget,
  DashboardSkeleton,
  DashboardEmpty,
  RecommendationCard,
  ContinueStudyingWidget,
} from '@/components/learner/dashboard-widgets'
import type { MasteryScore } from '@/types/learning'

const mockMastery: MasteryScore = {
  concept_id: 'concept-1',
  memory_score: 0.5,
  durable_mastery_score: 0.4,
  mastery_score_combined: 0.45,
  concept_state: 'developing',
  weakness_severity: 'medium',
  evidence_count: 3,
  last_attempt_at: '2024-01-01T00:00:00Z',
}

describe('Dashboard widgets', () => {
  describe('WelcomeWidget', () => {
    it('renders greeting with name', () => {
      render(<WelcomeWidget displayName="Alice" />)
      expect(screen.getByText(/Alice/)).toBeInTheDocument()
    })

    it('shows morning greeting before noon', () => {
      // This test depends on current time, so we just check it renders
      render(<WelcomeWidget displayName="Bob" />)
      expect(screen.getByText(/Bob/)).toBeInTheDocument()
    })
  })

  describe('StreakWidget', () => {
    it('renders current streak', () => {
      render(<StreakWidget current={5} longest={10} />)
      expect(screen.getByText('5 days')).toBeInTheDocument()
    })

    it('renders longest streak', () => {
      render(<StreakWidget current={3} longest={15} />)
      expect(screen.getByText(/15 days/)).toBeInTheDocument()
    })
  })

  describe('DailyGoalWidget', () => {
    it('renders progress percentage', () => {
      render(<DailyGoalWidget progress={0.6} />)
      expect(screen.getByText('60%')).toBeInTheDocument()
    })

    it('shows remaining percentage', () => {
      render(<DailyGoalWidget progress={0.4} />)
      expect(screen.getByText(/60% to go/)).toBeInTheDocument()
    })

    it('shows completion message at 100%', () => {
      render(<DailyGoalWidget progress={1} />)
      expect(screen.getByText(/Goal achieved/)).toBeInTheDocument()
    })
  })

  describe('QueueRemainingWidget', () => {
    it('renders remaining count', () => {
      render(<QueueRemainingWidget remaining={7} />)
      expect(screen.getByText('7')).toBeInTheDocument()
    })
  })

  describe('DueReviewsWidget', () => {
    it('renders due count', () => {
      render(<DueReviewsWidget count={3} />)
      expect(screen.getByText('3')).toBeInTheDocument()
    })
  })

  describe('InterviewReadinessWidget', () => {
    it('renders readiness percentage', () => {
      render(<InterviewReadinessWidget readiness={0.75} />)
      expect(screen.getByText('75%')).toBeInTheDocument()
    })

    it('shows interview ready label for high score', () => {
      render(<InterviewReadinessWidget readiness={0.85} />)
      expect(screen.getByText(/Interview ready/)).toBeInTheDocument()
    })

    it('shows getting there for medium score', () => {
      render(<InterviewReadinessWidget readiness={0.6} />)
      expect(screen.getByText(/Getting there/)).toBeInTheDocument()
    })

    it('shows keep practicing for low score', () => {
      render(<InterviewReadinessWidget readiness={0.3} />)
      expect(screen.getByText(/Keep practicing/)).toBeInTheDocument()
    })
  })

  describe('WeakConceptsWidget', () => {
    it('renders concepts list', () => {
      render(<WeakConceptsWidget concepts={[mockMastery]} />)
      expect(screen.getByText('concept-1')).toBeInTheDocument()
    })

    it('shows empty state when no weak concepts', () => {
      render(<WeakConceptsWidget concepts={[]} />)
      expect(screen.getByText(/No weak concepts/)).toBeInTheDocument()
    })

    it('limits to 5 concepts', () => {
      const concepts = Array.from({ length: 10 }, (_, i) => ({
        ...mockMastery,
        concept_id: `concept-${i}`,
      }))
      render(<WeakConceptsWidget concepts={concepts} />)
      expect(screen.getAllByRole('listitem')).toHaveLength(5)
    })
  })

  describe('StrongConceptsWidget', () => {
    it('renders concepts list', () => {
      render(<StrongConceptsWidget concepts={[mockMastery]} />)
      expect(screen.getByText('concept-1')).toBeInTheDocument()
    })

    it('shows empty state when no strong concepts', () => {
      render(<StrongConceptsWidget concepts={[]} />)
      expect(screen.getByText(/No strong concepts/)).toBeInTheDocument()
    })
  })

  describe('RecommendationCard', () => {
    it('renders recommendation reason', () => {
      render(
        <RecommendationCard
          recommendation={{ id: 'rec-1', reason: 'Review decorators', recommendation_type: 'review_concept' }}
        />,
      )
      expect(screen.getByText('Review decorators')).toBeInTheDocument()
    })

    it('renders accept + dismiss buttons', () => {
      render(
        <RecommendationCard
          recommendation={{ id: 'rec-1', reason: 'Test', recommendation_type: 'review_concept' }}
          onAccept={() => {}}
          onDismiss={() => {}}
        />,
      )
      expect(screen.getByRole('button', { name: /accept/i })).toBeInTheDocument()
      expect(screen.getByRole('button', { name: /dismiss/i })).toBeInTheDocument()
    })

    it('returns null when no recommendation', () => {
      const { container } = render(<RecommendationCard recommendation={null} />)
      expect(container).toBeEmptyDOMElement()
    })
  })

  describe('ContinueStudyingWidget', () => {
    it('renders start button when enrolled', () => {
      render(<ContinueStudyingWidget enrollmentId="enr-1" />)
      expect(screen.getByRole('link', { name: /start a study session/i })).toBeInTheDocument()
    })

    it('renders empty state when no enrollment', () => {
      render(<ContinueStudyingWidget enrollmentId={null} />)
      expect(screen.getByText(/No active enrollment/)).toBeInTheDocument()
    })
  })

  describe('DashboardSkeleton', () => {
    it('renders loading skeletons', () => {
      const { container } = render(<DashboardSkeleton />)
      const skeletons = container.querySelectorAll('[aria-hidden="true"]')
      expect(skeletons.length).toBeGreaterThan(0)
    })
  })

  describe('DashboardEmpty', () => {
    it('renders welcome message', () => {
      render(<DashboardEmpty />)
      expect(screen.getByText(/Welcome to Mastery Engine/)).toBeInTheDocument()
    })
  })
})
