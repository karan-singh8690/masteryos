/**
 * Content authoring API client — all content management API calls.
 */

import { apiClient } from '@/lib/api-client'
import type { UUID } from '@/types/common'
import type {
  ContentSubject,
  CreateSubjectRequest,
  UpdateSubjectRequest,
  ContentConcept,
  CreateConceptRequest,
  UpdateConceptRequest,
  LearningObjective,
  CreateObjectiveRequest,
  Misconception,
  CreateMisconceptionRequest,
  QuestionTemplate,
  TemplateVersion,
  CreateQuestionTemplateRequest,
  QuestionPreview,
  GeneratePreviewRequest,
  ContentDashboardData,
  ContentAnalytics,
  ContentSearchResult,
  BulkAction,
  BulkOperationResult,
} from '@/types/content'

// ============================================================
// Subjects API
// ============================================================

export const contentSubjectApi = {
  list: () => apiClient.get<ContentSubject[]>('/admin/subjects'),

  getById: (id: UUID) => apiClient.get<ContentSubject>(`/admin/subjects/${id}`),

  create: (data: CreateSubjectRequest) =>
    apiClient.post<ContentSubject>('/admin/subjects', data),

  update: (id: UUID, data: UpdateSubjectRequest) =>
    apiClient.patch<ContentSubject>(`/admin/subjects/${id}`, data),

  publish: (id: UUID) =>
    apiClient.post<ContentSubject>(`/admin/subjects/${id}/publish`),

  archive: (id: UUID) =>
    apiClient.post<ContentSubject>(`/admin/subjects/${id}/archive`),
}

// ============================================================
// Concepts API
// ============================================================

export const contentConceptApi = {
  listBySubject: (subjectId: UUID) =>
    apiClient.get<ContentConcept[]>(`/admin/subjects/${subjectId}/concepts`),

  getById: (id: UUID) =>
    apiClient.get<ContentConcept>(`/admin/concepts/${id}`),

  create: (subjectId: UUID, data: CreateConceptRequest) =>
    apiClient.post<ContentConcept>(`/admin/subjects/${subjectId}/concepts`, data),

  update: (id: UUID, data: UpdateConceptRequest) =>
    apiClient.patch<ContentConcept>(`/admin/concepts/${id}`, data),

  delete: (id: UUID) =>
    apiClient.delete<void>(`/admin/concepts/${id}`),
}

// ============================================================
// Learning Objectives API
// ============================================================

export const objectiveApi = {
  listByConcept: (conceptId: UUID) =>
    apiClient.get<LearningObjective[]>(`/admin/concepts/${conceptId}/objectives`),

  create: (conceptId: UUID, data: CreateObjectiveRequest) =>
    apiClient.post<LearningObjective>(`/admin/concepts/${conceptId}/objectives`, data),

  update: (id: UUID, data: Partial<CreateObjectiveRequest>) =>
    apiClient.patch<LearningObjective>(`/admin/objectives/${id}`, data),

  delete: (id: UUID) =>
    apiClient.delete<void>(`/admin/objectives/${id}`),
}

// ============================================================
// Misconceptions API
// ============================================================

export const misconceptionApi = {
  listByConcept: (conceptId: UUID) =>
    apiClient.get<Misconception[]>(`/admin/concepts/${conceptId}/misconceptions`),

  create: (conceptId: UUID, data: CreateMisconceptionRequest) =>
    apiClient.post<Misconception>(`/admin/concepts/${conceptId}/misconceptions`, data),

  update: (id: UUID, data: Partial<CreateMisconceptionRequest>) =>
    apiClient.patch<Misconception>(`/admin/misconceptions/${id}`, data),

  delete: (id: UUID) =>
    apiClient.delete<void>(`/admin/misconceptions/${id}`),
}

// ============================================================
// Question Templates API
// ============================================================

export const questionTemplateApi = {
  listBySubject: (subjectId: UUID) =>
    apiClient.get<QuestionTemplate[]>(`/admin/subjects/${subjectId}/question-templates`),

  getById: (id: UUID) =>
    apiClient.get<TemplateVersion>(`/admin/question-templates/${id}`),

  create: (subjectId: UUID, data: CreateQuestionTemplateRequest) =>
    apiClient.post<QuestionTemplate>(
      `/admin/subjects/${subjectId}/question-templates`,
      data,
    ),

  publish: (id: UUID) =>
    apiClient.post<QuestionTemplate>(`/admin/question-templates/${id}/publish`),

  archive: (id: UUID) =>
    apiClient.post<QuestionTemplate>(`/admin/question-templates/${id}/archive`),

  duplicate: (id: UUID) =>
    apiClient.post<QuestionTemplate>(`/admin/question-templates/${id}/duplicate`),

  // Live preview via backend QuestionFactory
  generatePreview: (data: GeneratePreviewRequest) =>
    apiClient.post<QuestionPreview>('/admin/question-templates/preview', data),
}

// ============================================================
// Content Dashboard API
// ============================================================

export const contentDashboardApi = {
  get: () => apiClient.get<ContentDashboardData>('/admin/content/dashboard'),
}

// ============================================================
// Content Analytics API
// ============================================================

export const contentAnalyticsApi = {
  get: (subjectId?: UUID) =>
    apiClient.get<ContentAnalytics>(
      `/admin/content/analytics${subjectId ? `?subject_id=${subjectId}` : ''}`,
    ),
}

// ============================================================
// Content Search API
// ============================================================

export const contentSearchApi = {
  search: (query: string) =>
    apiClient.get<ContentSearchResult>(
      `/admin/content/search?q=${encodeURIComponent(query)}`,
    ),
}

// ============================================================
// Bulk Operations API
// ============================================================

export const bulkOperationApi = {
  execute: (
    action: BulkAction,
    items: { type: string; id: UUID }[],
    options?: Record<string, unknown>,
  ) =>
    apiClient.post<BulkOperationResult>('/admin/content/bulk', {
      action,
      items,
      options,
    }),
}

// ============================================================
// Import / Export API
// ============================================================

export const importExportApi = {
  import: (format: string, data: unknown) =>
    apiClient.post<{ success: boolean; imported: number; errors: string[] }>(
      `/admin/content/import?format=${format}`,
      data,
    ),

  export: (format: string, subjectId?: UUID) =>
    apiClient.post<Blob>(
      `/admin/content/export?format=${format}${subjectId ? `&subject_id=${subjectId}` : ''}`,
      {},
      { responseType: 'blob' },
    ),

  previewImport: (format: string, data: unknown) =>
    apiClient.post<{
      format: string
      items: { type: string; name: string; action: string; data: Record<string, unknown> }[]
      warnings: string[]
      errors: string[]
    }>(`/admin/content/import/preview?format=${format}`, data),
}
