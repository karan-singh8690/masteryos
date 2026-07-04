/**
 * Content authoring hooks — React Query hooks for all content management.
 */

'use client'

import {
  useQuery,
  useMutation,
  useQueryClient,
} from '@tanstack/react-query'

import { queryKey } from '@/lib/query-keys'
import {
  contentSubjectApi,
  contentConceptApi,
  objectiveApi,
  misconceptionApi,
  questionTemplateApi,
  contentDashboardApi,
  contentAnalyticsApi,
  contentSearchApi,
  bulkOperationApi,
  importExportApi,
} from '@/lib/content-api'
import type { UUID } from '@/types/common'
import type {
  CreateSubjectRequest,
  UpdateSubjectRequest,
  CreateConceptRequest,
  UpdateConceptRequest,
  CreateObjectiveRequest,
  CreateMisconceptionRequest,
  CreateQuestionTemplateRequest,
  GeneratePreviewRequest,
  BulkAction,
} from '@/types/content'

// ============================================================
// Content Dashboard
// ============================================================

export function useContentDashboard() {
  return useQuery({
    queryKey: queryKey.content.dashboard(),
    queryFn: () => contentDashboardApi.get(),
    staleTime: 30_000,
  })
}

// ============================================================
// Subjects
// ============================================================

export function useContentSubjects() {
  return useQuery({
    queryKey: queryKey.content.subjects(),
    queryFn: () => contentSubjectApi.list(),
  })
}

export function useContentSubject(id: UUID | null) {
  return useQuery({
    queryKey: queryKey.content.subject(id!),
    queryFn: () => contentSubjectApi.getById(id!),
    enabled: !!id,
  })
}

export function useCreateSubject() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (data: CreateSubjectRequest) => contentSubjectApi.create(data),
    onSuccess: () => qc.invalidateQueries({ queryKey: queryKey.content.subjects() }),
  })
}

export function useUpdateSubject() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({ id, data }: { id: UUID; data: UpdateSubjectRequest }) =>
      contentSubjectApi.update(id, data),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: queryKey.content.subjects() })
    },
  })
}

export function usePublishSubject() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (id: UUID) => contentSubjectApi.publish(id),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: queryKey.content.subjects() })
      qc.invalidateQueries({ queryKey: queryKey.content.dashboard() })
    },
  })
}

export function useArchiveSubject() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (id: UUID) => contentSubjectApi.archive(id),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: queryKey.content.subjects() })
      qc.invalidateQueries({ queryKey: queryKey.content.dashboard() })
    },
  })
}

// ============================================================
// Concepts
// ============================================================

export function useContentConcepts(subjectId: UUID | null) {
  return useQuery({
    queryKey: queryKey.content.concepts(subjectId!),
    queryFn: () => contentConceptApi.listBySubject(subjectId!),
    enabled: !!subjectId,
  })
}

export function useContentConcept(id: UUID | null) {
  return useQuery({
    queryKey: queryKey.content.concept(id!),
    queryFn: () => contentConceptApi.getById(id!),
    enabled: !!id,
  })
}

export function useCreateConcept() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({ subjectId, data }: { subjectId: UUID; data: CreateConceptRequest }) =>
      contentConceptApi.create(subjectId, data),
    onSuccess: (_data, { subjectId }) => {
      qc.invalidateQueries({ queryKey: queryKey.content.concepts(subjectId) })
      qc.invalidateQueries({ queryKey: queryKey.content.dashboard() })
    },
  })
}

export function useUpdateConcept() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({ id, data }: { id: UUID; data: UpdateConceptRequest }) =>
      contentConceptApi.update(id, data),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['content-authoring', 'concepts'] })
      qc.invalidateQueries({ queryKey: ['content-authoring', 'subjects'] })
    },
  })
}

export function useDeleteConcept() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (id: UUID) => contentConceptApi.delete(id),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['content-authoring', 'concepts'] })
      qc.invalidateQueries({ queryKey: ['content-authoring', 'subjects'] })
      qc.invalidateQueries({ queryKey: queryKey.content.dashboard() })
    },
  })
}

// ============================================================
// Learning Objectives
// ============================================================

export function useObjectives(conceptId: UUID | null) {
  return useQuery({
    queryKey: queryKey.content.objectives(conceptId!),
    queryFn: () => objectiveApi.listByConcept(conceptId!),
    enabled: !!conceptId,
  })
}

export function useCreateObjective() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({ conceptId, data }: { conceptId: UUID; data: CreateObjectiveRequest }) =>
      objectiveApi.create(conceptId, data),
    onSuccess: (_data, { conceptId }) => {
      qc.invalidateQueries({ queryKey: queryKey.content.objectives(conceptId) })
    },
  })
}

export function useDeleteObjective() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (id: UUID) => objectiveApi.delete(id),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['content-authoring', 'concepts'] })
    },
  })
}

// ============================================================
// Misconceptions
// ============================================================

export function useMisconceptions(conceptId: UUID | null) {
  return useQuery({
    queryKey: queryKey.content.misconceptions(conceptId!),
    queryFn: () => misconceptionApi.listByConcept(conceptId!),
    enabled: !!conceptId,
  })
}

export function useCreateMisconception() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({ conceptId, data }: { conceptId: UUID; data: CreateMisconceptionRequest }) =>
      misconceptionApi.create(conceptId, data),
    onSuccess: (_data, { conceptId }) => {
      qc.invalidateQueries({ queryKey: queryKey.content.misconceptions(conceptId) })
    },
  })
}

export function useDeleteMisconception() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (id: UUID) => misconceptionApi.delete(id),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['content-authoring', 'concepts'] })
    },
  })
}

// ============================================================
// Question Templates
// ============================================================

export function useQuestionTemplates(subjectId: UUID | null) {
  return useQuery({
    queryKey: queryKey.content.templates(subjectId!),
    queryFn: () => questionTemplateApi.listBySubject(subjectId!),
    enabled: !!subjectId,
  })
}

export function useQuestionTemplate(id: UUID | null) {
  return useQuery({
    queryKey: queryKey.content.template(id!),
    queryFn: () => questionTemplateApi.getById(id!),
    enabled: !!id,
  })
}

export function useCreateQuestionTemplate() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({
      subjectId,
      data,
    }: {
      subjectId: UUID
      data: CreateQuestionTemplateRequest
    }) => questionTemplateApi.create(subjectId, data),
    onSuccess: (_data, { subjectId }) => {
      qc.invalidateQueries({ queryKey: queryKey.content.templates(subjectId) })
      qc.invalidateQueries({ queryKey: queryKey.content.dashboard() })
    },
  })
}

export function usePublishTemplate() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (id: UUID) => questionTemplateApi.publish(id),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['content-authoring', 'templates'] })
      qc.invalidateQueries({ queryKey: queryKey.content.dashboard() })
    },
  })
}

export function useArchiveTemplate() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (id: UUID) => questionTemplateApi.archive(id),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['content-authoring', 'templates'] })
      qc.invalidateQueries({ queryKey: queryKey.content.dashboard() })
    },
  })
}

export function useDuplicateTemplate() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (id: UUID) => questionTemplateApi.duplicate(id),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['content-authoring', 'templates'] })
    },
  })
}

// ============================================================
// Live Question Preview (via backend QuestionFactory)
// ============================================================

export function useQuestionPreview() {
  return useMutation({
    mutationFn: (data: GeneratePreviewRequest) =>
      questionTemplateApi.generatePreview(data),
  })
}

// ============================================================
// Content Analytics
// ============================================================

export function useContentAnalytics(subjectId?: UUID) {
  return useQuery({
    queryKey: queryKey.content.analytics(subjectId),
    queryFn: () => contentAnalyticsApi.get(subjectId),
  })
}

// ============================================================
// Content Search
// ============================================================

export function useContentSearch(query: string, enabled = true) {
  return useQuery({
    queryKey: queryKey.content.search(query),
    queryFn: () => contentSearchApi.search(query),
    enabled: enabled && query.length > 0,
    staleTime: 10_000,
  })
}

// ============================================================
// Bulk Operations
// ============================================================

export function useBulkOperation() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({
      action,
      items,
      options,
    }: {
      action: BulkAction
      items: { type: string; id: UUID }[]
      options?: Record<string, unknown>
    }) => bulkOperationApi.execute(action, items, options),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['content-authoring'] })
    },
  })
}

// ============================================================
// Import / Export
// ============================================================

export function useImportContent() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({ format, data }: { format: string; data: unknown }) =>
      importExportApi.import(format, data),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['content-authoring'] })
    },
  })
}

export function useExportContent() {
  return useMutation({
    mutationFn: ({ format, subjectId }: { format: string; subjectId?: UUID }) =>
      importExportApi.export(format, subjectId),
  })
}
