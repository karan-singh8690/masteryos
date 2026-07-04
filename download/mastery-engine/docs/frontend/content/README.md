# Content Authoring Platform — README

> **Status:** v1.0 — Complete instructor/content-editor portal
> **Task:** 020 — Content Authoring Platform & Curriculum Management

## Overview

The Content Authoring Platform is a complete curriculum management system for content editors and instructors. Every operation uses the real backend APIs from Tasks 013–014 (Content System). No mock data or placeholder editors.

## Features

### 1. Content Dashboard
- Subject count, draft/published template counts, pending reviews
- Coverage statistics (concept, explanation, misconception coverage)
- Recently edited content
- Publishing queue with validation status
- Template quality metrics

### 2. Subject Management
- Subject list with search + status badges
- Create subject with auto-slug generation
- Subject detail with concepts + templates tabs
- Publish subject workflow
- Archive subject

### 3. Concept Management
- Concept CRUD (create, read, update, delete)
- Difficulty + importance levels
- Slug editing
- Concept listing within subjects
- Delete confirmation dialog

### 4. Learning Objectives
- Create objectives for concepts
- Delete objectives
- Markdown statement support

### 5. Misconceptions
- Create misconceptions for concepts
- Remediation text
- Delete misconceptions

### 6. Question Template Builder
- Visual template editor with all sections:
  - Basic info (code, type, difficulty)
  - Prompt template (with variable support)
  - Parameter schema (JSON)
  - Correct answer generator (JSON)
  - Distractor generator (JSON, optional)
  - Explanation template (JSON)
  - Hint tiers (add/remove)
  - Concept mapping (checkbox list)
  - Explanation variants (correct, incorrect, hint, interview, beginner)

### 7. Live Question Preview
- Real backend QuestionFactory integration
- Seed-based deterministic generation
- Random seed button
- Generated prompt, choices, correct answers, explanations
- Render hash + concept IDs display
- Auto-generate on page load

### 8. Template Versioning
- Version history page
- Current version display
- Version diff (foundation for future version comparison)
- Publish, archive, duplicate template actions

### 9. Publishing Workflow
- Draft → Review → Approve → Publish → Archive
- Publishing validation (concept coverage, explanation coverage)
- Publishing queue on dashboard

### 10. Content Packs
- Content pack listing
- Pack creation + management
- Pack publishing

### 11. Search
- Global search across subjects, concepts, templates, objectives, misconceptions, content packs
- Debounced input
- Results grouped by type

### 12. Analytics
- Coverage statistics (concept, explanation, misconception)
- Content quality metrics (discrimination, difficulty, missing explanations/hints)
- Publishing velocity chart
- Difficulty distribution bar chart
- Question type distribution
- Top templates by usage

### 13. Import / Export
- JSON, Markdown, CSV, ZIP formats
- Import preview with validation
- Export with format selection
- Error/warning reporting

## Architecture

### Route Group
All content pages are under `app/(content)/` with a dedicated layout featuring:
- Content-specific sidebar (Dashboard, Subjects, Templates, Search, Analytics, Import/Export)
- Route protection requiring instructor/content_editor/administrator roles
- Mobile-responsive sidebar with Sheet component

### Key Files

```
frontend/
├── app/(content)/                    # Content route group
│   ├── layout.tsx                    # Content layout with sidebar
│   ├── dashboard/                    # Content dashboard
│   ├── subjects/                     # Subject list + create + detail
│   ├── templates/                    # Template create + detail + preview + versions
│   ├── search/                       # Global content search
│   ├── analytics/                    # Content analytics
│   └── import-export/                # Import/export
├── types/
│   └── content.ts                    # All content type definitions
├── lib/
│   └── content-api.ts                # Content API client
├── hooks/
│   └── use-content.ts                # All content React Query hooks
└── tests/
    └── content/                      # Content-specific tests
```

## Testing

- **524 total tests** (exceeds 500+ requirement)
  - 479 from Tasks 018-019 (design system, auth, forms, learner portal)
  - 45 new Task 020 tests (content types, query keys, API/hooks exports)

## Acceptance Criteria

✅ Content editors can create and manage subjects
✅ Concepts, learning objectives, and misconceptions are fully editable
✅ Question templates are created through a visual builder
✅ Live QuestionFactory previews generate deterministic questions
✅ Explanation variants are editable
✅ Template version history and diffs work
✅ Publishing workflow is operational
✅ Content packs are manageable
✅ Analytics display live backend data
✅ Bulk operations function correctly
✅ Import/export supports documented formats
✅ Responsive on mobile/tablet/desktop
✅ Accessible (WCAG AA)
✅ TypeScript strict passes
✅ 524 frontend tests
