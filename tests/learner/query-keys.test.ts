import { describe, it, expect } from 'vitest'

import { queryKey } from '@/lib/query-keys'

describe('Learner query keys', () => {
  describe('dashboard', () => {
    it('generates dashboard key', () => {
      expect(queryKey.learner.dashboard()).toEqual(['learner', 'dashboard'])
    })
  })

  describe('subjects', () => {
    it('generates subjects list key', () => {
      expect(queryKey.learner.subjects()).toEqual(['learner', 'subjects'])
    })

    it('generates subject detail key', () => {
      expect(queryKey.learner.subject('sub-1')).toEqual(['learner', 'subjects', 'sub-1'])
    })

    it('generates concepts key', () => {
      expect(queryKey.learner.concepts('sub-1')).toEqual([
        'learner', 'subjects', 'sub-1', 'concepts',
      ])
    })
  })

  describe('enrollments', () => {
    it('generates enrollments list key', () => {
      expect(queryKey.learner.enrollments()).toEqual(['learner', 'enrollments'])
    })

    it('generates enrollment detail key', () => {
      expect(queryKey.learner.enrollment('enr-1')).toEqual(['learner', 'enrollments', 'enr-1'])
    })
  })

  describe('sessions', () => {
    it('generates sessions list key', () => {
      expect(queryKey.learner.sessions()).toEqual(['learner', 'sessions'])
    })

    it('generates session detail key', () => {
      expect(queryKey.learner.session('sess-1')).toEqual(['learner', 'sessions', 'sess-1'])
    })

    it('generates session summary key', () => {
      expect(queryKey.learner.sessionSummary('sess-1')).toEqual([
        'learner', 'sessions', 'sess-1', 'summary',
      ])
    })

    it('generates adaptive queue key', () => {
      expect(queryKey.learner.adaptiveQueue('sess-1')).toEqual([
        'learner', 'sessions', 'sess-1', 'adaptive-queue',
      ])
    })
  })

  describe('questions', () => {
    it('generates question key', () => {
      expect(queryKey.learner.question('q-1')).toEqual(['learner', 'questions', 'q-1'])
    })
  })

  describe('mastery', () => {
    it('generates mastery key', () => {
      expect(queryKey.learner.mastery('enr-1')).toEqual(['learner', 'mastery', 'enr-1'])
    })

    it('generates weak concepts key', () => {
      expect(queryKey.learner.weakConcepts('enr-1')).toEqual([
        'learner', 'mastery', 'enr-1', 'weak',
      ])
    })

    it('generates mastery timeline key without concept', () => {
      expect(queryKey.learner.masteryTimeline('enr-1')).toEqual([
        'learner', 'mastery', 'enr-1', 'timeline', 'all',
      ])
    })

    it('generates mastery timeline key with concept', () => {
      expect(queryKey.learner.masteryTimeline('enr-1', 'concept-1')).toEqual([
        'learner', 'mastery', 'enr-1', 'timeline', 'concept-1',
      ])
    })
  })

  describe('reviews', () => {
    it('generates due reviews key', () => {
      expect(queryKey.learner.dueReviews('enr-1')).toEqual([
        'learner', 'reviews', 'enr-1', 'due',
      ])
    })

    it('generates upcoming reviews key', () => {
      expect(queryKey.learner.upcomingReviews('enr-1', 7)).toEqual([
        'learner', 'reviews', 'enr-1', 'upcoming', 7,
      ])
    })

    it('generates review stats key', () => {
      expect(queryKey.learner.reviewStats('enr-1')).toEqual([
        'learner', 'reviews', 'enr-1', 'stats',
      ])
    })
  })

  describe('recommendations', () => {
    it('generates recommendations key without enrollment', () => {
      expect(queryKey.learner.recommendations()).toEqual([
        'learner', 'recommendations', 'all',
      ])
    })

    it('generates recommendations key with enrollment', () => {
      expect(queryKey.learner.recommendations('enr-1')).toEqual([
        'learner', 'recommendations', 'enr-1',
      ])
    })
  })

  describe('achievements', () => {
    it('generates achievements key', () => {
      expect(queryKey.learner.achievements()).toEqual(['learner', 'achievements'])
    })
  })

  describe('notifications', () => {
    it('generates notifications key without filters', () => {
      expect(queryKey.learner.notifications()).toEqual([
        'learner', 'notifications', undefined,
      ])
    })

    it('generates notifications key with filters', () => {
      expect(queryKey.learner.notifications({ status: 'unread' })).toEqual([
        'learner', 'notifications', { status: 'unread' },
      ])
    })

    it('generates unread count key', () => {
      expect(queryKey.learner.unreadNotificationCount()).toEqual([
        'learner', 'notifications', 'unread-count',
      ])
    })
  })
})
