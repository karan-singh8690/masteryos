/**
 * Tests for the Beta Ops React Query hooks (Task 026).
 *
 * Verifies that each hook calls the correct API method and handles
 * loading/error/success states.
 */

import { describe, it, expect, vi, beforeEach } from 'vitest'
import { renderHook, waitFor } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import React from 'react'

vi.mock('@/lib/beta-ops-api', () => ({
  betaOpsApi: {
    getDashboard: vi.fn(),
    getFunnel: vi.fn(),
    getRetention: vi.fn(),
    getLearning: vi.fn(),
    getFeedback: vi.fn(),
    voteFeedback: vi.fn(),
    updateFeedbackMeta: vi.fn(),
    markDuplicate: vi.fn(),
    getUserSuccess: vi.fn(),
    getInstructor: vi.fn(),
    getOperations: vi.fn(),
    getReleases: vi.fn(),
    createRelease: vi.fn(),
    updateRelease: vi.fn(),
    addReleaseStage: vi.fn(),
    getReport: vi.fn(),
    generateReport: vi.fn(),
    listExperiments: vi.fn(),
    getExperiment: vi.fn(),
    createExperiment: vi.fn(),
    updateExperiment: vi.fn(),
    assignVariant: vi.fn(),
    recordExperimentResult: vi.fn(),
  },
}))

import { betaOpsApi } from '@/lib/beta-ops-api'
import {
  useBetaOpsDashboard,
  useRegistrationFunnel,
  useRetentionCohorts,
  useLearningEffectiveness,
  useFeedbackPlatform,
  useVoteOnFeedback,
  useUpdateFeedbackMeta,
  useMarkDuplicate,
  useUserSuccess,
  useInstructorAnalytics,
  useOperationalHealth,
  useReleases,
  useCreateRelease,
  useUpdateRelease,
  useAddReleaseStage,
  useBetaReport,
  useGenerateReport,
  useExperiments,
  useExperiment,
  useCreateExperiment,
  useUpdateExperiment,
  useAssignVariant,
  useRecordExperimentResult,
} from '@/hooks/use-beta-ops'

function createWrapper() {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  })
  return ({ children }: { children: React.ReactNode }) =>
    React.createElement(QueryClientProvider, { value: queryClient }, children)
}

describe('Beta Ops Hooks', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  // ============================================================
  // Part 1: Dashboard
  // ============================================================

  describe('useBetaOpsDashboard', () => {
    it('calls getDashboard and returns data', async () => {
      const mockData = { total_invited: 10, active_beta_users: 5, daily_active_users: 3 }
      vi.mocked(betaOpsApi.getDashboard).mockResolvedValueOnce(mockData as any)

      const { result } = renderHook(() => useBetaOpsDashboard(), { wrapper: createWrapper() })

      await waitFor(() => expect(result.current.isSuccess).toBe(true))
      expect(result.current.data).toEqual(mockData)
      expect(betaOpsApi.getDashboard).toHaveBeenCalled()
    })

    it('handles error state', async () => {
      vi.mocked(betaOpsApi.getDashboard).mockRejectedValueOnce(new Error('Failed'))

      const { result } = renderHook(() => useBetaOpsDashboard(), { wrapper: createWrapper() })

      await waitFor(() => expect(result.current.isError).toBe(true))
    })
  })

  // ============================================================
  // Part 2: Funnel + Retention
  // ============================================================

  describe('useRegistrationFunnel', () => {
    it('calls getFunnel with default days=30', async () => {
      vi.mocked(betaOpsApi.getFunnel).mockResolvedValueOnce({ steps: [] } as any)
      const { result } = renderHook(() => useRegistrationFunnel(), { wrapper: createWrapper() })
      await waitFor(() => expect(result.current.isSuccess).toBe(true))
      expect(betaOpsApi.getFunnel).toHaveBeenCalledWith(30)
    })

    it('calls getFunnel with custom days', async () => {
      vi.mocked(betaOpsApi.getFunnel).mockResolvedValueOnce({ steps: [] } as any)
      const { result } = renderHook(() => useRegistrationFunnel(7), { wrapper: createWrapper() })
      await waitFor(() => expect(result.current.isSuccess).toBe(true))
      expect(betaOpsApi.getFunnel).toHaveBeenCalledWith(7)
    })
  })

  describe('useRetentionCohorts', () => {
    it('calls getRetention with default weeks=8', async () => {
      vi.mocked(betaOpsApi.getRetention).mockResolvedValueOnce([] as any)
      const { result } = renderHook(() => useRetentionCohorts(), { wrapper: createWrapper() })
      await waitFor(() => expect(result.current.isSuccess).toBe(true))
      expect(betaOpsApi.getRetention).toHaveBeenCalledWith(8)
    })
  })

  // ============================================================
  // Part 3: Learning
  // ============================================================

  describe('useLearningEffectiveness', () => {
    it('calls getLearning', async () => {
      vi.mocked(betaOpsApi.getLearning).mockResolvedValueOnce({ mastery_growth_avg: 0 } as any)
      const { result } = renderHook(() => useLearningEffectiveness(), { wrapper: createWrapper() })
      await waitFor(() => expect(result.current.isSuccess).toBe(true))
      expect(betaOpsApi.getLearning).toHaveBeenCalled()
    })
  })

  // ============================================================
  // Part 4: Feedback
  // ============================================================

  describe('useFeedbackPlatform', () => {
    it('calls getFeedback with default limit=100', async () => {
      vi.mocked(betaOpsApi.getFeedback).mockResolvedValueOnce({ items: [] } as any)
      const { result } = renderHook(() => useFeedbackPlatform(), { wrapper: createWrapper() })
      await waitFor(() => expect(result.current.isSuccess).toBe(true))
      expect(betaOpsApi.getFeedback).toHaveBeenCalledWith(100)
    })

    it('calls getFeedback with custom limit', async () => {
      vi.mocked(betaOpsApi.getFeedback).mockResolvedValueOnce({ items: [] } as any)
      const { result } = renderHook(() => useFeedbackPlatform(50), { wrapper: createWrapper() })
      await waitFor(() => expect(result.current.isSuccess).toBe(true))
      expect(betaOpsApi.getFeedback).toHaveBeenCalledWith(50)
    })
  })

  describe('useVoteOnFeedback', () => {
    it('calls voteFeedback on mutate', async () => {
      vi.mocked(betaOpsApi.voteFeedback).mockResolvedValueOnce({ message: 'OK' } as any)
      const { result } = renderHook(() => useVoteOnFeedback(), { wrapper: createWrapper() })
      result.current.mutate({ feedbackId: 'fb-1', vote: 1 })
      await waitFor(() => expect(betaOpsApi.voteFeedback).toHaveBeenCalledWith('fb-1', 1))
    })
  })

  describe('useUpdateFeedbackMeta', () => {
    it('calls updateFeedbackMeta on mutate', async () => {
      vi.mocked(betaOpsApi.updateFeedbackMeta).mockResolvedValueOnce({ message: 'OK' } as any)
      const { result } = renderHook(() => useUpdateFeedbackMeta(), { wrapper: createWrapper() })
      result.current.mutate({ feedbackId: 'fb-1', payload: { priority: 'high' } })
      await waitFor(() => expect(betaOpsApi.updateFeedbackMeta).toHaveBeenCalledWith('fb-1', { priority: 'high' }))
    })
  })

  describe('useMarkDuplicate', () => {
    it('calls markDuplicate on mutate', async () => {
      vi.mocked(betaOpsApi.markDuplicate).mockResolvedValueOnce({ message: 'OK' } as any)
      const { result } = renderHook(() => useMarkDuplicate(), { wrapper: createWrapper() })
      result.current.mutate({ feedbackId: 'fb-1', duplicateOf: 'fb-2' })
      await waitFor(() => expect(betaOpsApi.markDuplicate).toHaveBeenCalledWith('fb-1', 'fb-2'))
    })
  })

  // ============================================================
  // Part 5: User Success
  // ============================================================

  describe('useUserSuccess', () => {
    it('calls getUserSuccess', async () => {
      vi.mocked(betaOpsApi.getUserSuccess).mockResolvedValueOnce({ summary: {} } as any)
      const { result } = renderHook(() => useUserSuccess(), { wrapper: createWrapper() })
      await waitFor(() => expect(result.current.isSuccess).toBe(true))
      expect(betaOpsApi.getUserSuccess).toHaveBeenCalled()
    })
  })

  // ============================================================
  // Part 6: Instructor
  // ============================================================

  describe('useInstructorAnalytics', () => {
    it('calls getInstructor', async () => {
      vi.mocked(betaOpsApi.getInstructor).mockResolvedValueOnce({} as any)
      const { result } = renderHook(() => useInstructorAnalytics(), { wrapper: createWrapper() })
      await waitFor(() => expect(result.current.isSuccess).toBe(true))
      expect(betaOpsApi.getInstructor).toHaveBeenCalled()
    })
  })

  // ============================================================
  // Part 7: Operations
  // ============================================================

  describe('useOperationalHealth', () => {
    it('calls getOperations', async () => {
      vi.mocked(betaOpsApi.getOperations).mockResolvedValueOnce({} as any)
      const { result } = renderHook(() => useOperationalHealth(), { wrapper: createWrapper() })
      await waitFor(() => expect(result.current.isSuccess).toBe(true))
      expect(betaOpsApi.getOperations).toHaveBeenCalled()
    })
  })

  // ============================================================
  // Part 8: Releases
  // ============================================================

  describe('useReleases', () => {
    it('calls getReleases', async () => {
      vi.mocked(betaOpsApi.getReleases).mockResolvedValueOnce({ releases: [] } as any)
      const { result } = renderHook(() => useReleases(), { wrapper: createWrapper() })
      await waitFor(() => expect(result.current.isSuccess).toBe(true))
      expect(betaOpsApi.getReleases).toHaveBeenCalled()
    })
  })

  describe('useCreateRelease', () => {
    it('calls createRelease on mutate', async () => {
      vi.mocked(betaOpsApi.createRelease).mockResolvedValueOnce({} as any)
      const { result } = renderHook(() => useCreateRelease(), { wrapper: createWrapper() })
      result.current.mutate({ version: 'v1.0.0' })
      await waitFor(() => expect(betaOpsApi.createRelease).toHaveBeenCalledWith({ version: 'v1.0.0' }))
    })
  })

  describe('useUpdateRelease', () => {
    it('calls updateRelease on mutate', async () => {
      vi.mocked(betaOpsApi.updateRelease).mockResolvedValueOnce({ message: 'OK' } as any)
      const { result } = renderHook(() => useUpdateRelease(), { wrapper: createWrapper() })
      result.current.mutate({ releaseId: 'rel-1', payload: { title: 'Updated' } })
      await waitFor(() => expect(betaOpsApi.updateRelease).toHaveBeenCalledWith('rel-1', { title: 'Updated' }))
    })
  })

  describe('useAddReleaseStage', () => {
    it('calls addReleaseStage on mutate', async () => {
      vi.mocked(betaOpsApi.addReleaseStage).mockResolvedValueOnce({ message: 'OK' } as any)
      const { result } = renderHook(() => useAddReleaseStage(), { wrapper: createWrapper() })
      result.current.mutate({
        releaseId: 'rel-1',
        payload: { stage: 'canary', rollout_percentage: 10 },
      })
      await waitFor(() =>
        expect(betaOpsApi.addReleaseStage).toHaveBeenCalledWith('rel-1', {
          stage: 'canary',
          rollout_percentage: 10,
        })
      )
    })
  })

  // ============================================================
  // Part 9: Reports
  // ============================================================

  describe('useBetaReport', () => {
    it('calls getReport with default period=weekly', async () => {
      vi.mocked(betaOpsApi.getReport).mockResolvedValueOnce({} as any)
      const { result } = renderHook(() => useBetaReport(), { wrapper: createWrapper() })
      await waitFor(() => expect(result.current.isSuccess).toBe(true))
      expect(betaOpsApi.getReport).toHaveBeenCalledWith('weekly')
    })

    it('calls getReport with custom period', async () => {
      vi.mocked(betaOpsApi.getReport).mockResolvedValueOnce({} as any)
      const { result } = renderHook(() => useBetaReport('daily'), { wrapper: createWrapper() })
      await waitFor(() => expect(result.current.isSuccess).toBe(true))
      expect(betaOpsApi.getReport).toHaveBeenCalledWith('daily')
    })
  })

  describe('useGenerateReport', () => {
    it('calls generateReport on mutate', async () => {
      vi.mocked(betaOpsApi.generateReport).mockResolvedValueOnce({} as any)
      const { result } = renderHook(() => useGenerateReport(), { wrapper: createWrapper() })
      result.current.mutate('weekly')
      await waitFor(() => expect(betaOpsApi.generateReport).toHaveBeenCalledWith('weekly'))
    })
  })

  // ============================================================
  // Part 10: Experiments
  // ============================================================

  describe('useExperiments', () => {
    it('calls listExperiments', async () => {
      vi.mocked(betaOpsApi.listExperiments).mockResolvedValueOnce([] as any)
      const { result } = renderHook(() => useExperiments(), { wrapper: createWrapper() })
      await waitFor(() => expect(result.current.isSuccess).toBe(true))
      expect(betaOpsApi.listExperiments).toHaveBeenCalled()
    })
  })

  describe('useExperiment', () => {
    it('calls getExperiment when id is provided', async () => {
      vi.mocked(betaOpsApi.getExperiment).mockResolvedValueOnce({} as any)
      const { result } = renderHook(() => useExperiment('exp-1'), { wrapper: createWrapper() })
      await waitFor(() => expect(result.current.isSuccess).toBe(true))
      expect(betaOpsApi.getExperiment).toHaveBeenCalledWith('exp-1')
    })

    it('does not call getExperiment when id is null', async () => {
      const { result } = renderHook(() => useExperiment(null), { wrapper: createWrapper() })
      expect(result.current.isLoading).toBe(false)
      expect(betaOpsApi.getExperiment).not.toHaveBeenCalled()
    })
  })

  describe('useCreateExperiment', () => {
    it('calls createExperiment on mutate', async () => {
      vi.mocked(betaOpsApi.createExperiment).mockResolvedValueOnce({} as any)
      const { result } = renderHook(() => useCreateExperiment(), { wrapper: createWrapper() })
      result.current.mutate({ id: 'exp-1', name: 'Test' })
      await waitFor(() => expect(betaOpsApi.createExperiment).toHaveBeenCalledWith({ id: 'exp-1', name: 'Test' }))
    })
  })

  describe('useUpdateExperiment', () => {
    it('calls updateExperiment on mutate', async () => {
      vi.mocked(betaOpsApi.updateExperiment).mockResolvedValueOnce({ message: 'OK' } as any)
      const { result } = renderHook(() => useUpdateExperiment(), { wrapper: createWrapper() })
      result.current.mutate({ experimentId: 'exp-1', payload: { status: 'running' } })
      await waitFor(() =>
        expect(betaOpsApi.updateExperiment).toHaveBeenCalledWith('exp-1', { status: 'running' })
      )
    })
  })

  describe('useAssignVariant', () => {
    it('calls assignVariant on mutate', async () => {
      vi.mocked(betaOpsApi.assignVariant).mockResolvedValueOnce({ message: 'OK' } as any)
      const { result } = renderHook(() => useAssignVariant(), { wrapper: createWrapper() })
      result.current.mutate({ experimentId: 'exp-1', userId: 'user-1' })
      await waitFor(() => expect(betaOpsApi.assignVariant).toHaveBeenCalledWith('exp-1', 'user-1'))
    })
  })

  describe('useRecordExperimentResult', () => {
    it('calls recordExperimentResult on mutate', async () => {
      vi.mocked(betaOpsApi.recordExperimentResult).mockResolvedValueOnce({ message: 'OK' } as any)
      const { result } = renderHook(() => useRecordExperimentResult(), { wrapper: createWrapper() })
      result.current.mutate({
        experimentId: 'exp-1',
        payload: { variant: 'a', sample_size: 100, conversion_count: 30 },
      })
      await waitFor(() =>
        expect(betaOpsApi.recordExperimentResult).toHaveBeenCalledWith('exp-1', {
          variant: 'a',
          sample_size: 100,
          conversion_count: 30,
        })
      )
    })
  })
})
