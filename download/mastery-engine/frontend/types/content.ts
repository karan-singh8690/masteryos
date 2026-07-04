/**
 * Content authoring types — subjects, concepts, objectives, misconceptions,
 * question templates, template versions, content packs, explanations.
 */

import type { ISO8601, UUID } from './common'

// ============================================================
// Subjects
// ============================================================

export interface ContentSubject {
  id: UUID
  code: string
  name: string
  slug: string
  description: string | null
  status: 'draft' | 'in_review' | 'published' | 'rejected' | 'archived'
  published_at: ISO8601 | null
}

export interface CreateSubjectRequest {
  code: string
  name: string
  slug: string
  description?: string
}

export interface UpdateSubjectRequest {
  code?: string
  name?: string
  slug?: string
  description?: string
}

// ============================================================
// Concepts
// ============================================================

export interface ContentConcept {
  id: UUID
  subject_id: UUID
  slug: string
  name: string
  description: string
  difficulty: 'beginner' | 'intermediate' | 'advanced' | 'easy' | 'medium' | 'hard'
  importance: 'low' | 'medium' | 'high' | 'critical'
  status: 'draft' | 'in_review' | 'published' | 'rejected' | 'archived'
}

export interface CreateConceptRequest {
  slug: string
  name: string
  description: string
  difficulty?: string
  importance?: string
}

export interface UpdateConceptRequest {
  slug?: string
  name?: string
  description?: string
  difficulty?: string
  importance?: string
}

// ============================================================
// Learning Objectives
// ============================================================

export interface LearningObjective {
  id: UUID
  concept_id: UUID
  statement: string
  status: 'draft' | 'in_review' | 'published' | 'rejected' | 'archived'
}

export interface CreateObjectiveRequest {
  statement: string
}

// ============================================================
// Misconceptions
// ============================================================

export interface Misconception {
  id: UUID
  concept_id: UUID
  name: string
  description: string
  remediation: string | null
  status: 'draft' | 'in_review' | 'published' | 'rejected' | 'archived'
}

export interface CreateMisconceptionRequest {
  name: string
  description: string
  remediation?: string
}

// ============================================================
// Question Templates
// ============================================================

export interface QuestionTemplate {
  id: UUID
  subject_id: UUID
  code: string
  question_type: string
  status: 'draft' | 'in_review' | 'published' | 'rejected' | 'archived'
  current_version_id: UUID | null
  published_at: ISO8601 | null
}

export interface TemplateVersion {
  id: UUID
  template_id: UUID
  version_number: number
  prompt_template: Record<string, unknown>
  parameter_schema: Record<string, unknown>
  correct_answer_generator: Record<string, unknown>
  distractor_generator: Record<string, unknown> | null
  explanation_template: Record<string, unknown>
  hint_tiers: string[]
  difficulty_estimate: string
  discrimination_estimate: number
  concept_ids: UUID[]
}

export interface CreateQuestionTemplateRequest {
  code: string
  question_type?: string
  prompt_template: Record<string, unknown>
  parameter_schema?: Record<string, unknown>
  correct_answer_generator: Record<string, unknown>
  distractor_generator?: Record<string, unknown> | null
  explanation_template?: Record<string, unknown>
  hint_tiers?: string[]
  difficulty_estimate?: string
  discrimination_estimate?: number
  concept_ids?: UUID[]
  explanations?: ExplanationInput[]
}

export interface ExplanationInput {
  variant_type: string
  content: string
}

export interface PublishTemplateRequest {
  // No body needed
}

// ============================================================
// Explanations
// ============================================================

export interface Explanation {
  id: UUID
  template_version_id: UUID
  variant_type: 'correct' | 'incorrect' | 'hint' | 'interview' | 'beginner'
  content: string
  created_at: ISO8601
}

// ============================================================
// Content Packs
// ============================================================

export interface ContentPack {
  id: UUID
  content_version_id: UUID
  author_user_id: UUID
  name: string
  description: string | null
  artifact_summary: Record<string, unknown>
  status: 'draft' | 'in_review' | 'published' | 'rejected' | 'archived'
  published_at: ISO8601 | null
  created_at: ISO8601
  updated_at: ISO8601
  deleted_at: ISO8601 | null
}

// ============================================================
// Content Version
// ============================================================

export interface ContentVersion {
  id: UUID
  subject_id: UUID
  version_number: number
  status: 'draft' | 'in_review' | 'published' | 'rejected' | 'archived'
  published_at: ISO8601 | null
  created_at: ISO8601
  artifact_summary: Record<string, unknown>
}

// ============================================================
// Concept Dependencies
// ============================================================

export interface ConceptDependency {
  id: UUID
  prerequisite_concept_id: UUID
  dependent_concept_id: UUID
  dependency_type: 'required' | 'recommended' | 'optional'
  weight: number
}

// ============================================================
// Content Preview (from backend QuestionFactory)
// ============================================================

export interface QuestionPreview {
  question_instance_id: UUID
  concept_ids: UUID[]
  difficulty: string
  estimated_duration_seconds: number
  question_type: string
  prompt: {
    text: string
    code?: string
    language?: string
  }
  choices: QuestionPreviewChoice[] | null
  metadata: Record<string, unknown>
  render_hash: string
  seed: number
}

export interface QuestionPreviewChoice {
  id: string
  text: string
  is_correct?: boolean
  explanation?: string
}

export interface GeneratePreviewRequest {
  template_id: UUID
  seed?: number
  variables?: Record<string, unknown>
}

// ============================================================
// Content Dashboard
// ============================================================

export interface ContentDashboardData {
  subjects: ContentSubject[]
  draft_templates: number
  published_templates: number
  pending_reviews: number
  content_packs: number
  coverage_stats: {
    total_concepts: number
    concepts_with_templates: number
    concepts_with_explanations: number
    concepts_with_misconceptions: number
  }
  recently_edited: RecentlyEditedItem[]
  publishing_queue: PublishingQueueItem[]
  template_quality_metrics: {
    avg_discrimination: number
    avg_difficulty: string
    total_hints: number
  }
}

export interface RecentlyEditedItem {
  id: UUID
  type: 'subject' | 'concept' | 'template' | 'objective' | 'misconception'
  name: string
  status: string
  updated_at: ISO8601
  editor: string
}

export interface PublishingQueueItem {
  id: UUID
  type: 'subject' | 'template' | 'content_pack'
  name: string
  status: string
  ready_to_publish: boolean
  validation_issues: string[]
}

// ============================================================
// Bulk Operations
// ============================================================

export type BulkAction = 'publish' | 'archive' | 'delete' | 'export' | 'tag' | 'move'

export interface BulkOperationResult {
  success: boolean
  affected_count: number
  errors: { id: UUID; error: string }[]
}

// ============================================================
// Import / Export
// ============================================================

export type ImportFormat = 'json' | 'markdown' | 'csv' | 'zip'
export type ExportFormat = 'json' | 'markdown' | 'csv' | 'zip'

export interface ImportPreview {
  format: ImportFormat
  items: ImportPreviewItem[]
  warnings: string[]
  errors: string[]
}

export interface ImportPreviewItem {
  type: string
  name: string
  action: 'create' | 'update' | 'skip'
  data: Record<string, unknown>
}

// ============================================================
// Search
// ============================================================

export interface ContentSearchResult {
  subjects: ContentSubject[]
  concepts: ContentConcept[]
  templates: QuestionTemplate[]
  objectives: LearningObjective[]
  misconceptions: Misconception[]
  content_packs: ContentPack[]
}

// ============================================================
// Analytics
// ============================================================

export interface ContentAnalytics {
  template_usage: { template_id: UUID; template_code: string; usage_count: number }[]
  coverage: {
    concept_coverage: number
    explanation_coverage: number
    misconception_coverage: number
  }
  difficulty_distribution: { difficulty: string; count: number }[]
  question_distribution: { question_type: string; count: number }[]
  publishing_velocity: { date: string; published: number }[]
  content_quality: {
    avg_discrimination: number
    avg_difficulty: string
    missing_explanations: number
    missing_hints: number
  }
}
