/**
 * Beta Ops hooks — React Query hooks for the Closed Beta Operations Platform.
 */

'use client'

import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { betaOpsApi } from '@/lib/beta-ops-api'
import type {
  BetaOpsDashboard,
  RegistrationFunnel,
  RetentionCohort,
  LearningEffectiveness,
  FeedbackPlatform,
  UserSuccessReport,
  InstructorAnalytics,
  OperationalHealth,
  ReleaseManagement,
  BetaReport,
  Experiment,
  ExperimentResults,
} from '@/lib/beta-ops-api'

const QK = ['beta-ops'] as const

// ============================================================
// Part 1: Dashboard
// ============================================================

export function useBetaOpsDashboard() {
  return useQuery<BetaOpsDashboard>({
    queryKey: [...QK, 'dashboard'],
    queryFn: () => betaOpsApi.getDashboard(),
    staleTime: 30_000,
    refetchInterval: 60_000,
  })
}

// ============================================================
// Part 2: Funnel + Retention
// ============================================================

export function useRegistrationFunnel(days = 30) {
  return useQuery<RegistrationFunnel>({
    queryKey: [...QK, 'funnel', days],
    queryFn: () => betaOpsApi.getFunnel(days),
  })
}

export function useRetentionCohorts(weeks = 8) {
  return useQuery<RetentionCohort[]>({
    queryKey: [...QK, 'retention', weeks],
    queryFn: () => betaOpsApi.getRetention(weeks),
  })
}

// ============================================================
// Part 3: Learning
// ============================================================

export function useLearningEffectiveness() {
  return useQuery<LearningEffectiveness>({
    queryKey: [...QK, 'learning'],
    queryFn: () => betaOpsApi.getLearning(),
  })
}

// ============================================================
// Part 4: Feedback
// ============================================================

export function useFeedbackPlatform(limit = 100) {
  return useQuery<FeedbackPlatform>({
    queryKey: [...QK, 'feedback', limit],
    queryFn: () => betaOpsApi.getFeedback(limit),
  })
}

export function useVoteOnFeedback() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({ feedbackId, vote }: { feedbackId: string; vote: number }) =>
      betaOpsApi.voteFeedback(feedbackId, vote),
    onSuccess: () => qc.invalidateQueries({ queryKey: [...QK, 'feedback'] }),
  })
}

export function useUpdateFeedbackMeta() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({
      feedbackId,
      payload,
    }: {
      feedbackId: string
      payload: {
        priority?: string
        roadmap_status?: string
        roadmap_link?: string
        tags?: string[]
        assigned_to?: string
      }
    }) => betaOpsApi.updateFeedbackMeta(feedbackId, payload),
    onSuccess: () => qc.invalidateQueries({ queryKey: [...QK, 'feedback'] }),
  })
}

export function useMarkDuplicate() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({ feedbackId, duplicateOf }: { feedbackId: string; duplicateOf: string }) =>
      betaOpsApi.markDuplicate(feedbackId, duplicateOf),
    onSuccess: () => qc.invalidateQueries({ queryKey: [...QK, 'feedback'] }),
  })
}

// ============================================================
// Part 5: User Success
// ============================================================

export function useUserSuccess() {
  return useQuery<UserSuccessReport>({
    queryKey: [...QK, 'success'],
    queryFn: () => betaOpsApi.getUserSuccess(),
  })
}

// ============================================================
// Part 6: Instructor
// ============================================================

export function useInstructorAnalytics() {
  return useQuery<InstructorAnalytics>({
    queryKey: [...QK, 'instructor'],
    queryFn: () => betaOpsApi.getInstructor(),
  })
}

// ============================================================
// Part 7: Operations
// ============================================================

export function useOperationalHealth() {
  return useQuery<OperationalHealth>({
    queryKey: [...QK, 'operations'],
    queryFn: () => betaOpsApi.getOperations(),
    staleTime: 15_000,
    refetchInterval: 30_000,
  })
}

// ============================================================
// Part 8: Releases
// ============================================================

export function useReleases() {
  return useQuery<ReleaseManagement>({
    queryKey: [...QK, 'releases'],
    queryFn: () => betaOpsApi.getReleases(),
  })
}

export function useCreateRelease() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (payload: Record<string, unknown>) => betaOpsApi.createRelease(payload),
    onSuccess: () => qc.invalidateQueries({ queryKey: [...QK, 'releases'] }),
  })
}

export function useUpdateRelease() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({
      releaseId,
      payload,
    }: {
      releaseId: string
      payload: Record<string, unknown>
    }) => betaOpsApi.updateRelease(releaseId, payload),
    onSuccess: () => qc.invalidateQueries({ queryKey: [...QK, 'releases'] }),
  })
}

export function useAddReleaseStage() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({
      releaseId,
      payload,
    }: {
      releaseId: string
      payload: { stage: string; rollout_percentage: number; notes?: string }
    }) => betaOpsApi.addReleaseStage(releaseId, payload),
    onSuccess: () => qc.invalidateQueries({ queryKey: [...QK, 'releases'] }),
  })
}

// ============================================================
// Part 9: Reports
// ============================================================

export function useBetaReport(period: 'daily' | 'weekly' | 'monthly' = 'weekly') {
  return useQuery<BetaReport>({
    queryKey: [...QK, 'reports', period],
    queryFn: () => betaOpsApi.getReport(period),
  })
}

export function useGenerateReport() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (period: 'daily' | 'weekly' | 'monthly') =>
      betaOpsApi.generateReport(period),
    onSuccess: (_, period) =>
      qc.invalidateQueries({ queryKey: [...QK, 'reports', period] }),
  })
}

// ============================================================
// Part 10: Experiments
// ============================================================

export function useExperiments() {
  return useQuery<Experiment[]>({
    queryKey: [...QK, 'experiments'],
    queryFn: () => betaOpsApi.listExperiments(),
  })
}

export function useExperiment(experimentId: string | null) {
  return useQuery<ExperimentResults>({
    queryKey: [...QK, 'experiments', experimentId],
    queryFn: () => betaOpsApi.getExperiment(experimentId!),
    enabled: !!experimentId,
  })
}

export function useCreateExperiment() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (payload: Record<string, unknown>) =>
      betaOpsApi.createExperiment(payload),
    onSuccess: () => qc.invalidateQueries({ queryKey: [...QK, 'experiments'] }),
  })
}

export function useUpdateExperiment() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({
      experimentId,
      payload,
    }: {
      experimentId: string
      payload: Record<string, unknown>
    }) => betaOpsApi.updateExperiment(experimentId, payload),
    onSuccess: () => qc.invalidateQueries({ queryKey: [...QK, 'experiments'] }),
  })
}

export function useAssignVariant() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({ experimentId, userId }: { experimentId: string; userId: string }) =>
      betaOpsApi.assignVariant(experimentId, userId),
    onSuccess: () => qc.invalidateQueries({ queryKey: [...QK, 'experiments'] }),
  })
}

export function useRecordExperimentResult() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({
      experimentId,
      payload,
    }: {
      experimentId: string
      payload: {
        variant: string
        sample_size: number
        metric_value?: number
        metric_std_error?: number
        conversion_count: number
        metadata?: Record<string, unknown>
      }
    }) => betaOpsApi.recordExperimentResult(experimentId, payload),
    onSuccess: () => qc.invalidateQueries({ queryKey: [...QK, 'experiments'] }),
  })
}
