/**
 * Tests for the Beta Ops API client (Task 026).
 *
 * Verifies that the API client methods call the underlying apiClient
 * with the correct URLs and HTTP methods.
 */

import { describe, it, expect, vi, beforeEach } from 'vitest'

// Mock the apiClient BEFORE importing betaOpsApi
vi.mock('@/lib/api-client', () => ({
  apiClient: {
    get: vi.fn(),
    post: vi.fn(),
    patch: vi.fn(),
    put: vi.fn(),
    delete: vi.fn(),
  },
}))

import { apiClient } from '@/lib/api-client'
import { betaOpsApi } from '@/lib/beta-ops-api'

describe('betaOpsApi', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  // ============================================================
  // Part 1: Dashboard
  // ============================================================

  describe('getDashboard', () => {
    it('calls GET /admin/beta-ops/dashboard', async () => {
      vi.mocked(apiClient.get).mockResolvedValueOnce({ total_invited: 10 })
      const result = await betaOpsApi.getDashboard()
      expect(apiClient.get).toHaveBeenCalledWith('/admin/beta-ops/dashboard')
      expect(result).toEqual({ total_invited: 10 })
    })
  })

  // ============================================================
  // Part 2: Funnel + Retention
  // ============================================================

  describe('getFunnel', () => {
    it('calls GET with default days=30', async () => {
      vi.mocked(apiClient.get).mockResolvedValueOnce({ steps: [] })
      await betaOpsApi.getFunnel()
      expect(apiClient.get).toHaveBeenCalledWith('/admin/beta-ops/analytics/funnel?days=30')
    })

    it('calls GET with custom days', async () => {
      vi.mocked(apiClient.get).mockResolvedValueOnce({ steps: [] })
      await betaOpsApi.getFunnel(7)
      expect(apiClient.get).toHaveBeenCalledWith('/admin/beta-ops/analytics/funnel?days=7')
    })
  })

  describe('getRetention', () => {
    it('calls GET with default weeks=8', async () => {
      vi.mocked(apiClient.get).mockResolvedValueOnce([])
      await betaOpsApi.getRetention()
      expect(apiClient.get).toHaveBeenCalledWith('/admin/beta-ops/analytics/retention?weeks=8')
    })

    it('calls GET with custom weeks', async () => {
      vi.mocked(apiClient.get).mockResolvedValueOnce([])
      await betaOpsApi.getRetention(4)
      expect(apiClient.get).toHaveBeenCalledWith('/admin/beta-ops/analytics/retention?weeks=4')
    })
  })

  // ============================================================
  // Part 3: Learning
  // ============================================================

  describe('getLearning', () => {
    it('calls GET /admin/beta-ops/learning', async () => {
      vi.mocked(apiClient.get).mockResolvedValueOnce({ mastery_growth_avg: 0 })
      await betaOpsApi.getLearning()
      expect(apiClient.get).toHaveBeenCalledWith('/admin/beta-ops/learning')
    })
  })

  // ============================================================
  // Part 4: Feedback
  // ============================================================

  describe('getFeedback', () => {
    it('calls GET with default limit=100', async () => {
      vi.mocked(apiClient.get).mockResolvedValueOnce({ items: [] })
      await betaOpsApi.getFeedback()
      expect(apiClient.get).toHaveBeenCalledWith('/admin/beta-ops/feedback?limit=100')
    })

    it('calls GET with custom limit', async () => {
      vi.mocked(apiClient.get).mockResolvedValueOnce({ items: [] })
      await betaOpsApi.getFeedback(50)
      expect(apiClient.get).toHaveBeenCalledWith('/admin/beta-ops/feedback?limit=50')
    })
  })

  describe('voteFeedback', () => {
    it('calls POST with feedback_id and vote', async () => {
      vi.mocked(apiClient.post).mockResolvedValueOnce({ message: 'Vote recorded' })
      await betaOpsApi.voteFeedback('fb-123', 1)
      expect(apiClient.post).toHaveBeenCalledWith('/admin/beta-ops/feedback/fb-123/vote', { vote: 1 })
    })

    it('supports downvote', async () => {
      vi.mocked(apiClient.post).mockResolvedValueOnce({ message: 'Vote recorded' })
      await betaOpsApi.voteFeedback('fb-123', -1)
      expect(apiClient.post).toHaveBeenCalledWith('/admin/beta-ops/feedback/fb-123/vote', { vote: -1 })
    })
  })

  describe('updateFeedbackMeta', () => {
    it('calls PATCH with feedback_id and payload', async () => {
      vi.mocked(apiClient.patch).mockResolvedValueOnce({ message: 'Updated' })
      await betaOpsApi.updateFeedbackMeta('fb-123', { priority: 'high' })
      expect(apiClient.patch).toHaveBeenCalledWith('/admin/beta-ops/feedback/fb-123/meta', { priority: 'high' })
    })
  })

  describe('markDuplicate', () => {
    it('calls POST with feedback_id and duplicate_of', async () => {
      vi.mocked(apiClient.post).mockResolvedValueOnce({ message: 'Marked' })
      await betaOpsApi.markDuplicate('fb-123', 'fb-456')
      expect(apiClient.post).toHaveBeenCalledWith('/admin/beta-ops/feedback/fb-123/mark-duplicate', {
        duplicate_of: 'fb-456',
      })
    })
  })

  // ============================================================
  // Part 5: User Success
  // ============================================================

  describe('getUserSuccess', () => {
    it('calls GET /admin/beta-ops/success', async () => {
      vi.mocked(apiClient.get).mockResolvedValueOnce({ summary: {} })
      await betaOpsApi.getUserSuccess()
      expect(apiClient.get).toHaveBeenCalledWith('/admin/beta-ops/success')
    })
  })

  // ============================================================
  // Part 6: Instructor
  // ============================================================

  describe('getInstructor', () => {
    it('calls GET /admin/beta-ops/instructor', async () => {
      vi.mocked(apiClient.get).mockResolvedValueOnce({})
      await betaOpsApi.getInstructor()
      expect(apiClient.get).toHaveBeenCalledWith('/admin/beta-ops/instructor')
    })
  })

  // ============================================================
  // Part 7: Operations
  // ============================================================

  describe('getOperations', () => {
    it('calls GET /admin/beta-ops/operations', async () => {
      vi.mocked(apiClient.get).mockResolvedValueOnce({})
      await betaOpsApi.getOperations()
      expect(apiClient.get).toHaveBeenCalledWith('/admin/beta-ops/operations')
    })
  })

  // ============================================================
  // Part 8: Releases
  // ============================================================

  describe('getReleases', () => {
    it('calls GET /admin/beta-ops/releases', async () => {
      vi.mocked(apiClient.get).mockResolvedValueOnce({ releases: [] })
      await betaOpsApi.getReleases()
      expect(apiClient.get).toHaveBeenCalledWith('/admin/beta-ops/releases')
    })
  })

  describe('createRelease', () => {
    it('calls POST /admin/beta-ops/releases with payload', async () => {
      vi.mocked(apiClient.post).mockResolvedValueOnce({})
      const payload = { version: 'v1.0.0', title: 'Test', body: 'Body' }
      await betaOpsApi.createRelease(payload)
      expect(apiClient.post).toHaveBeenCalledWith('/admin/beta-ops/releases', payload)
    })
  })

  describe('updateRelease', () => {
    it('calls PATCH with release_id and payload', async () => {
      vi.mocked(apiClient.patch).mockResolvedValueOnce({ message: 'Updated' })
      await betaOpsApi.updateRelease('rel-123', { title: 'Updated' })
      expect(apiClient.patch).toHaveBeenCalledWith('/admin/beta-ops/releases/rel-123', { title: 'Updated' })
    })
  })

  describe('addReleaseStage', () => {
    it('calls POST with release_id and stage payload', async () => {
      vi.mocked(apiClient.post).mockResolvedValueOnce({ message: 'Stage added' })
      await betaOpsApi.addReleaseStage('rel-123', { stage: 'canary', rollout_percentage: 10 })
      expect(apiClient.post).toHaveBeenCalledWith('/admin/beta-ops/releases/rel-123/stage', {
        stage: 'canary',
        rollout_percentage: 10,
      })
    })
  })

  // ============================================================
  // Part 9: Reports
  // ============================================================

  describe('getReport', () => {
    it('calls GET /admin/beta-ops/reports/{period}', async () => {
      vi.mocked(apiClient.get).mockResolvedValueOnce({})
      await betaOpsApi.getReport('weekly')
      expect(apiClient.get).toHaveBeenCalledWith('/admin/beta-ops/reports/weekly')
    })

    it('supports daily period', async () => {
      vi.mocked(apiClient.get).mockResolvedValueOnce({})
      await betaOpsApi.getReport('daily')
      expect(apiClient.get).toHaveBeenCalledWith('/admin/beta-ops/reports/daily')
    })

    it('supports monthly period', async () => {
      vi.mocked(apiClient.get).mockResolvedValueOnce({})
      await betaOpsApi.getReport('monthly')
      expect(apiClient.get).toHaveBeenCalledWith('/admin/beta-ops/reports/monthly')
    })
  })

  describe('generateReport', () => {
    it('calls POST /admin/beta-ops/reports/generate with period', async () => {
      vi.mocked(apiClient.post).mockResolvedValueOnce({})
      await betaOpsApi.generateReport('weekly')
      expect(apiClient.post).toHaveBeenCalledWith('/admin/beta-ops/reports/generate', { period: 'weekly' })
    })
  })

  // ============================================================
  // Part 10: Experiments
  // ============================================================

  describe('listExperiments', () => {
    it('calls GET /admin/beta-ops/experiments', async () => {
      vi.mocked(apiClient.get).mockResolvedValueOnce([])
      await betaOpsApi.listExperiments()
      expect(apiClient.get).toHaveBeenCalledWith('/admin/beta-ops/experiments')
    })
  })

  describe('getExperiment', () => {
    it('calls GET with experiment_id', async () => {
      vi.mocked(apiClient.get).mockResolvedValueOnce({})
      await betaOpsApi.getExperiment('exp-1')
      expect(apiClient.get).toHaveBeenCalledWith('/admin/beta-ops/experiments/exp-1')
    })
  })

  describe('createExperiment', () => {
    it('calls POST with payload', async () => {
      vi.mocked(apiClient.post).mockResolvedValueOnce({})
      const payload = { id: 'exp-1', name: 'Test', variant_a: 'a', variant_b: 'b' }
      await betaOpsApi.createExperiment(payload)
      expect(apiClient.post).toHaveBeenCalledWith('/admin/beta-ops/experiments', payload)
    })
  })

  describe('updateExperiment', () => {
    it('calls PATCH with experiment_id and payload', async () => {
      vi.mocked(apiClient.patch).mockResolvedValueOnce({ message: 'Updated' })
      await betaOpsApi.updateExperiment('exp-1', { status: 'running' })
      expect(apiClient.patch).toHaveBeenCalledWith('/admin/beta-ops/experiments/exp-1', { status: 'running' })
    })
  })

  describe('assignVariant', () => {
    it('calls POST with experiment_id and user_id', async () => {
      vi.mocked(apiClient.post).mockResolvedValueOnce({ message: 'Assigned' })
      await betaOpsApi.assignVariant('exp-1', 'user-123')
      expect(apiClient.post).toHaveBeenCalledWith('/admin/beta-ops/experiments/exp-1/assign', {
        user_id: 'user-123',
      })
    })
  })

  describe('recordExperimentResult', () => {
    it('calls POST with experiment_id and result payload', async () => {
      vi.mocked(apiClient.post).mockResolvedValueOnce({ message: 'Recorded' })
      const payload = {
        variant: 'a',
        sample_size: 100,
        conversion_count: 30,
      }
      await betaOpsApi.recordExperimentResult('exp-1', payload)
      expect(apiClient.post).toHaveBeenCalledWith('/admin/beta-ops/experiments/exp-1/results', payload)
    })
  })
})
