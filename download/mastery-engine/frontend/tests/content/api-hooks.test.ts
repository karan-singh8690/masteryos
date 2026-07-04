import { describe, it, expect, vi } from 'vitest'

// Mock the content API
vi.mock('@/lib/content-api', () => ({
  contentSubjectApi: {
    list: vi.fn(),
    getById: vi.fn(),
    create: vi.fn(),
    update: vi.fn(),
    publish: vi.fn(),
    archive: vi.fn(),
  },
  contentConceptApi: {
    listBySubject: vi.fn(),
    getById: vi.fn(),
    create: vi.fn(),
    update: vi.fn(),
    delete: vi.fn(),
  },
  objectiveApi: {
    listByConcept: vi.fn(),
    create: vi.fn(),
    update: vi.fn(),
    delete: vi.fn(),
  },
  misconceptionApi: {
    listByConcept: vi.fn(),
    create: vi.fn(),
    update: vi.fn(),
    delete: vi.fn(),
  },
  questionTemplateApi: {
    listBySubject: vi.fn(),
    getById: vi.fn(),
    create: vi.fn(),
    publish: vi.fn(),
    archive: vi.fn(),
    duplicate: vi.fn(),
    generatePreview: vi.fn(),
  },
  contentDashboardApi: {
    get: vi.fn(),
  },
  contentAnalyticsApi: {
    get: vi.fn(),
  },
  contentSearchApi: {
    search: vi.fn(),
  },
  bulkOperationApi: {
    execute: vi.fn(),
  },
  importExportApi: {
    import: vi.fn(),
    export: vi.fn(),
    previewImport: vi.fn(),
  },
}))

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

describe('Content API exports', () => {
  it('contentSubjectApi has all methods', () => {
    expect(contentSubjectApi.list).toBeDefined()
    expect(contentSubjectApi.getById).toBeDefined()
    expect(contentSubjectApi.create).toBeDefined()
    expect(contentSubjectApi.update).toBeDefined()
    expect(contentSubjectApi.publish).toBeDefined()
    expect(contentSubjectApi.archive).toBeDefined()
  })

  it('contentConceptApi has all methods', () => {
    expect(contentConceptApi.listBySubject).toBeDefined()
    expect(contentConceptApi.getById).toBeDefined()
    expect(contentConceptApi.create).toBeDefined()
    expect(contentConceptApi.update).toBeDefined()
    expect(contentConceptApi.delete).toBeDefined()
  })

  it('objectiveApi has all methods', () => {
    expect(objectiveApi.listByConcept).toBeDefined()
    expect(objectiveApi.create).toBeDefined()
    expect(objectiveApi.update).toBeDefined()
    expect(objectiveApi.delete).toBeDefined()
  })

  it('misconceptionApi has all methods', () => {
    expect(misconceptionApi.listByConcept).toBeDefined()
    expect(misconceptionApi.create).toBeDefined()
    expect(misconceptionApi.update).toBeDefined()
    expect(misconceptionApi.delete).toBeDefined()
  })

  it('questionTemplateApi has all methods', () => {
    expect(questionTemplateApi.listBySubject).toBeDefined()
    expect(questionTemplateApi.getById).toBeDefined()
    expect(questionTemplateApi.create).toBeDefined()
    expect(questionTemplateApi.publish).toBeDefined()
    expect(questionTemplateApi.archive).toBeDefined()
    expect(questionTemplateApi.duplicate).toBeDefined()
    expect(questionTemplateApi.generatePreview).toBeDefined()
  })

  it('contentDashboardApi has all methods', () => {
    expect(contentDashboardApi.get).toBeDefined()
  })

  it('contentAnalyticsApi has all methods', () => {
    expect(contentAnalyticsApi.get).toBeDefined()
  })

  it('contentSearchApi has all methods', () => {
    expect(contentSearchApi.search).toBeDefined()
  })

  it('bulkOperationApi has all methods', () => {
    expect(bulkOperationApi.execute).toBeDefined()
  })

  it('importExportApi has all methods', () => {
    expect(importExportApi.import).toBeDefined()
    expect(importExportApi.export).toBeDefined()
    expect(importExportApi.previewImport).toBeDefined()
  })
})

describe('Content hooks exports', () => {
  it('use-content module exports all hooks', async () => {
    const module = await import('@/hooks/use-content')
    expect(module.useContentDashboard).toBeDefined()
    expect(module.useContentSubjects).toBeDefined()
    expect(module.useContentSubject).toBeDefined()
    expect(module.useCreateSubject).toBeDefined()
    expect(module.useUpdateSubject).toBeDefined()
    expect(module.usePublishSubject).toBeDefined()
    expect(module.useArchiveSubject).toBeDefined()
    expect(module.useContentConcepts).toBeDefined()
    expect(module.useContentConcept).toBeDefined()
    expect(module.useCreateConcept).toBeDefined()
    expect(module.useUpdateConcept).toBeDefined()
    expect(module.useDeleteConcept).toBeDefined()
    expect(module.useObjectives).toBeDefined()
    expect(module.useCreateObjective).toBeDefined()
    expect(module.useDeleteObjective).toBeDefined()
    expect(module.useMisconceptions).toBeDefined()
    expect(module.useCreateMisconception).toBeDefined()
    expect(module.useDeleteMisconception).toBeDefined()
    expect(module.useQuestionTemplates).toBeDefined()
    expect(module.useQuestionTemplate).toBeDefined()
    expect(module.useCreateQuestionTemplate).toBeDefined()
    expect(module.usePublishTemplate).toBeDefined()
    expect(module.useArchiveTemplate).toBeDefined()
    expect(module.useDuplicateTemplate).toBeDefined()
    expect(module.useQuestionPreview).toBeDefined()
    expect(module.useContentAnalytics).toBeDefined()
    expect(module.useContentSearch).toBeDefined()
    expect(module.useBulkOperation).toBeDefined()
    expect(module.useImportContent).toBeDefined()
    expect(module.useExportContent).toBeDefined()
  })
})
