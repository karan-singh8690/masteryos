# Testing

> Content authoring platform test coverage.

## Test Count

**524 total tests** (exceeds 500+ requirement):

| Category | Tests | Files |
|---|---|---|
| Design system (Task 018) | ~200 | 10 files |
| Forms + hooks (Task 018) | ~80 | 4 files |
| Utilities + types (Task 018) | ~73 | 7 files |
| Learner portal (Task 019) | ~126 | 7 files |
| Content query keys (Task 020) | 15 | 1 file |
| Content types (Task 020) | 20 | 1 file |
| Content API + hooks (Task 020) | 14 | 1 file |
| **Total** | **524** | **31 files** |

## Test Files (Task 020)

```
tests/
├── content/
│   ├── query-keys.test.ts       # 15 tests for content query key factory
│   ├── types.test.ts            # 20 tests for content type definitions
│   └── api-hooks.test.ts        # 14 tests for API method + hook exports
└── (existing Tasks 018-019 tests) # 479 tests
```

## Test Coverage

### Content Query Keys (15 tests)
- Dashboard, analytics, subjects, concepts, objectives, misconceptions
- Templates, template preview (with/without seed), search
- All keys return correct array structure

### Content Types (20 tests)
- ContentSubject, ContentConcept, LearningObjective, Misconception
- QuestionTemplate, TemplateVersion, QuestionPreview, QuestionPreviewChoice
- ContentDashboardData, ContentAnalytics, ContentSearchResult
- BulkAction (all 6 values), ContentPack, ContentVersion
- ConceptDependency, Explanation, ExplanationInput
- CreateSubjectRequest, CreateConceptRequest, CreateQuestionTemplateRequest

### Content API + Hooks (14 tests)
- All API methods exported (subjectApi, conceptApi, objectiveApi, misconceptionApi, templateApi, dashboardApi, analyticsApi, searchApi, bulkApi, importExportApi)
- All hooks exported (30 hooks covering subjects, concepts, objectives, misconceptions, templates, preview, analytics, search, bulk, import/export)

## E2E Tests (Playwright)

Existing E2E tests from Tasks 018-019 cover auth flow, theme, navigation, responsive design. Future E2E tests will cover the complete authoring workflow:
- Create subject → Add concept → Create template → Preview → Publish
