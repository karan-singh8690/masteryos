import { describe, it, expect } from 'vitest'

import type {
  ContentSubject,
  ContentConcept,
  LearningObjective,
  Misconception,
  QuestionTemplate,
  TemplateVersion,
  QuestionPreview,
  QuestionPreviewChoice,
  ContentDashboardData,
  ContentAnalytics,
  ContentSearchResult,
  BulkAction,
  ContentPack,
  ContentVersion,
  ConceptDependency,
  Explanation,
  ExplanationInput,
  CreateSubjectRequest,
  CreateConceptRequest,
  CreateQuestionTemplateRequest,
} from '@/types/content'

describe('Content types', () => {
  it('ContentSubject has all fields', () => {
    const subject: ContentSubject = {
      id: 'sub-1',
      code: 'PY-INT',
      name: 'Python Interview Prep',
      slug: 'python-interview-prep',
      description: 'Master Python interviews',
      status: 'published',
      published_at: '2024-01-01T00:00:00Z',
    }
    expect(subject.code).toBe('PY-INT')
    expect(subject.status).toBe('published')
  })

  it('ContentConcept has all fields', () => {
    const concept: ContentConcept = {
      id: 'concept-1',
      subject_id: 'sub-1',
      slug: 'decorators',
      name: 'Decorators',
      description: 'Python decorators',
      difficulty: 'intermediate',
      importance: 'high',
      status: 'published',
    }
    expect(concept.slug).toBe('decorators')
    expect(concept.difficulty).toBe('intermediate')
  })

  it('LearningObjective has all fields', () => {
    const obj: LearningObjective = {
      id: 'obj-1',
      concept_id: 'concept-1',
      statement: 'Understand how decorators work',
      status: 'draft',
    }
    expect(obj.statement).toBe('Understand how decorators work')
  })

  it('Misconception has all fields', () => {
    const mis: Misconception = {
      id: 'mis-1',
      concept_id: 'concept-1',
      name: 'Decorators modify the original function',
      description: 'Common misconception',
      remediation: 'Decorators return a new function',
      status: 'draft',
    }
    expect(mis.remediation).toBe('Decorators return a new function')
  })

  it('QuestionTemplate has all fields', () => {
    const template: QuestionTemplate = {
      id: 'tpl-1',
      subject_id: 'sub-1',
      code: 'DEC-001',
      question_type: 'multiple_choice',
      status: 'draft',
      current_version_id: 'ver-1',
      published_at: null,
    }
    expect(template.code).toBe('DEC-001')
    expect(template.question_type).toBe('multiple_choice')
  })

  it('TemplateVersion has all fields', () => {
    const version: TemplateVersion = {
      id: 'ver-1',
      template_id: 'tpl-1',
      version_number: 1,
      prompt_template: { text: 'What is {x}?' },
      parameter_schema: { variables: { x: { type: 'int' } } },
      correct_answer_generator: { type: 'value', value: 42 },
      distractor_generator: { type: 'wrong', count: 3 },
      explanation_template: { correct: 'The answer is 42' },
      hint_tiers: ['Hint 1', 'Hint 2'],
      difficulty_estimate: 'medium',
      discrimination_estimate: 0.6,
      concept_ids: ['concept-1'],
    }
    expect(version.version_number).toBe(1)
    expect(version.hint_tiers).toHaveLength(2)
  })

  it('QuestionPreview has all fields', () => {
    const preview: QuestionPreview = {
      question_instance_id: 'qi-1',
      concept_ids: ['concept-1'],
      difficulty: 'medium',
      estimated_duration_seconds: 60,
      question_type: 'multiple_choice',
      prompt: { text: 'What is 2+2?' },
      choices: [{ id: 'a', text: '4', is_correct: true }],
      metadata: {},
      render_hash: 'abc123',
      seed: 42,
    }
    expect(preview.seed).toBe(42)
    expect(preview.render_hash).toBe('abc123')
  })

  it('QuestionPreviewChoice has optional fields', () => {
    const choice: QuestionPreviewChoice = {
      id: 'a',
      text: 'Answer A',
    }
    expect(choice.is_correct).toBeUndefined()
  })

  it('ContentDashboardData has all fields', () => {
    const dashboard: ContentDashboardData = {
      subjects: [],
      draft_templates: 5,
      published_templates: 10,
      pending_reviews: 2,
      content_packs: 3,
      coverage_stats: {
        total_concepts: 20,
        concepts_with_templates: 15,
        concepts_with_explanations: 12,
        concepts_with_misconceptions: 8,
      },
      recently_edited: [],
      publishing_queue: [],
      template_quality_metrics: {
        avg_discrimination: 0.5,
        avg_difficulty: 'medium',
        total_hints: 25,
      },
    }
    expect(dashboard.draft_templates).toBe(5)
    expect(dashboard.coverage_stats.total_concepts).toBe(20)
  })

  it('ContentAnalytics has all fields', () => {
    const analytics: ContentAnalytics = {
      template_usage: [],
      coverage: {
        concept_coverage: 0.75,
        explanation_coverage: 0.6,
        misconception_coverage: 0.4,
      },
      difficulty_distribution: [{ difficulty: 'easy', count: 10 }],
      question_distribution: [{ question_type: 'multiple_choice', count: 15 }],
      publishing_velocity: [{ date: '2024-01-01', published: 3 }],
      content_quality: {
        avg_discrimination: 0.5,
        avg_difficulty: 'medium',
        missing_explanations: 5,
        missing_hints: 3,
      },
    }
    expect(analytics.coverage.concept_coverage).toBe(0.75)
  })

  it('ContentSearchResult has all fields', () => {
    const result: ContentSearchResult = {
      subjects: [],
      concepts: [],
      templates: [],
      objectives: [],
      misconceptions: [],
      content_packs: [],
    }
    expect(result.subjects).toEqual([])
  })

  it('BulkAction has all valid values', () => {
    const actions: BulkAction[] = ['publish', 'archive', 'delete', 'export', 'tag', 'move']
    expect(actions).toHaveLength(6)
  })

  it('ContentPack has all fields', () => {
    const pack: ContentPack = {
      id: 'pack-1',
      content_version_id: 'cv-1',
      author_user_id: 'user-1',
      name: 'Python Basics Pack',
      description: 'Basic Python questions',
      artifact_summary: {},
      status: 'published',
      published_at: '2024-01-01T00:00:00Z',
      created_at: '2024-01-01T00:00:00Z',
      updated_at: '2024-01-01T00:00:00Z',
      deleted_at: null,
    }
    expect(pack.name).toBe('Python Basics Pack')
  })

  it('ContentVersion has all fields', () => {
    const version: ContentVersion = {
      id: 'cv-1',
      subject_id: 'sub-1',
      version_number: 1,
      status: 'published',
      published_at: '2024-01-01T00:00:00Z',
      created_at: '2024-01-01T00:00:00Z',
      artifact_summary: {},
    }
    expect(version.version_number).toBe(1)
  })

  it('ConceptDependency has all fields', () => {
    const dep: ConceptDependency = {
      id: 'dep-1',
      prerequisite_concept_id: 'concept-1',
      dependent_concept_id: 'concept-2',
      dependency_type: 'required',
      weight: 1.0,
    }
    expect(dep.dependency_type).toBe('required')
  })

  it('Explanation has all fields', () => {
    const exp: Explanation = {
      id: 'exp-1',
      template_version_id: 'ver-1',
      variant_type: 'correct',
      content: 'The answer is correct because...',
      created_at: '2024-01-01T00:00:00Z',
    }
    expect(exp.variant_type).toBe('correct')
  })

  it('ExplanationInput has all fields', () => {
    const input: ExplanationInput = {
      variant_type: 'incorrect',
      content: 'The answer is wrong because...',
    }
    expect(input.variant_type).toBe('incorrect')
  })

  it('CreateSubjectRequest has required fields', () => {
    const req: CreateSubjectRequest = {
      code: 'PY-INT',
      name: 'Python Interview Prep',
      slug: 'python-interview-prep',
    }
    expect(req.code).toBe('PY-INT')
  })

  it('CreateConceptRequest has required fields', () => {
    const req: CreateConceptRequest = {
      slug: 'decorators',
      name: 'Decorators',
      description: 'Python decorators',
    }
    expect(req.slug).toBe('decorators')
  })

  it('CreateQuestionTemplateRequest has all fields', () => {
    const req: CreateQuestionTemplateRequest = {
      code: 'DEC-001',
      question_type: 'multiple_choice',
      prompt_template: { text: 'What is {x}?' },
      parameter_schema: {},
      correct_answer_generator: { type: 'value', value: 42 },
      distractor_generator: null,
      explanation_template: {},
      hint_tiers: [],
      difficulty_estimate: 'medium',
      discrimination_estimate: 0.5,
      concept_ids: [],
      explanations: [],
    }
    expect(req.code).toBe('DEC-001')
  })
})
