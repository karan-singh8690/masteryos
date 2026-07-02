# Vertical Slice 03 — Content Factory + Question Generation System

> **Status:** v1.0 — Replaces every placeholder in the learning loop with real content.

---

## What This Is

This slice implements the complete content system that allows an administrator to build an entire Python Interview curriculum without touching code. Everything becomes data.

The result: the adaptive queue serves real questions generated from published templates, attempts reference actual concepts, and mastery updates correctly.

## Content Pipeline

```
Subject
  ↓
Content Pack
  ↓
Concept
  ↓
Learning Objective
  ↓
Misconception
  ↓
Question Template
  ↓
Template Version (immutable)
  ↓
Question Factory (deterministic generation)
  ↓
Question Instance (immutable, replayable)
  ↓
Adaptive Queue
  ↓
Attempt
  ↓
Mastery Update (references real Concepts)
```

## Architecture

```
Content Admin API (FastAPI)
  ↓
Content ORM Models (SQLAlchemy)
  ↓
PostgreSQL (content schema)
  ↓
Template Version loaded from DB
  ↓
QuestionFactory (pure domain service)
  ├── VariableGenerator (deterministic, seeded)
  ├── TemplateEngine ({{placeholder}} expansion)
  └── Correct Answer + Distractor generation
  ↓
QuestionInstance (immutable, with render_hash)
  ↓
Persisted to assessment.question_instances
  ↓
Queue Generator uses real instance IDs
  ↓
Submit flow uses real concept_ids
```

## Question Factory

The `QuestionFactory` is a **pure domain service** — no I/O, no database calls.

### Input
- `TemplateVersionData` (loaded from DB by the application layer)
- `seed` (integer, for deterministic variable generation)
- Context IDs (content_version_id, enrollment_id, session_id)

### Output
- `GeneratedQuestion` containing:
  - `question_instance` — ready to serve to a learner
  - `variables` — the generated values (for logging/analytics)
  - `render_hash` — SHA-256 hash for replay verification
  - `concept_ids` — real concept IDs (no placeholders!)

### Determinism Guarantee

Same `TemplateVersionData` + same `seed` → identical `QuestionInstance`:
- Same variables (VariableGenerator is seeded)
- Same rendered prompt (TemplateEngine is deterministic)
- Same correct answer (computed from same variables)
- Same distractors (same seed → same shuffle order)
- Same render_hash (SHA-256 of all inputs)

## Template Engine

Supports `{{variable}}` placeholders with deterministic expansion:

| Placeholder | Example | Output |
|---|---|---|
| `{{x}}` | `x=42` | `42` |
| `{{name}}` | `name="val_42"` | `val_42` |
| `{{#if flag}}...{{/if}}` | `flag=True` | content included |
| `{{#each items}}...{{/each}}` | `items=[1,2,3]` | iterated |

No runtime LLM. Pure string expansion.

## Variable Generator

Deterministic generators with seed-based reproducibility:

| Generator | Parameters | Output |
|---|---|---|
| `integer` | min, max | `42` |
| `float` | min, max, precision | `3.14` |
| `variable_name` | — | `val_42` |
| `function_name` | — | `get_data` |
| `list` | size, element_type, min, max | `[1, 5, 3, 8, 2]` |
| `dictionary` | size | `{"name": 42, "age": 30}` |
| `string` | length | `"abc_def_ghi"` |
| `boolean` | — | `True` |
| `choice` | options | `"b"` |

## Publishing Workflow

```
Draft → In Review → Published → Archived
```

| State | Learner can receive? |
|---|---|
| Draft | ❌ |
| In Review | ❌ |
| Published | ✅ |
| Archived | ❌ |

Only `Published` templates are eligible for question generation.

## Concept Mapping

Every `TemplateVersion` links to one or more `Concepts` via the `template_concepts` join table. This replaces the placeholder concept IDs used in Tasks 011–012.

When a learner submits an answer:
1. The `AttemptRecorded` event carries the real `concept_ids` from the template.
2. The `UpdateMasteryHandler` uses these IDs to update the correct `MasteryScore` aggregates.
3. Mastery updates are accurate — no more placeholder concepts.

## API Endpoints

### Content Administration

| Method | Path | Purpose |
|---|---|---|
| POST | `/api/v1/admin/subjects` | Create a subject |
| POST | `/api/v1/admin/subjects/{id}/publish` | Publish a subject |
| GET | `/api/v1/admin/subjects` | List subjects |
| POST | `/api/v1/admin/subjects/{id}/concepts` | Create a concept |
| GET | `/api/v1/admin/subjects/{id}/concepts` | List concepts |
| POST | `/api/v1/admin/concepts/{id}/objectives` | Create a learning objective |
| POST | `/api/v1/admin/concepts/{id}/misconceptions` | Create a misconception |
| POST | `/api/v1/admin/subjects/{id}/question-templates` | Create a question template |
| POST | `/api/v1/admin/question-templates/{id}/publish` | Publish a template |
| GET | `/api/v1/admin/subjects/{id}/question-templates` | List templates |
| GET | `/api/v1/admin/question-templates/{id}` | Get template detail |

## Versioning

Every `QuestionInstance` stores:
- `template_version_id` — which template version generated it
- `content_version_id` — which content version was active
- `algorithm_version_id` — which algorithm version was active
- `parameter_seed` — the seed for variable generation
- `render_hash` — SHA-256 hash for replay verification

Replay: given these 5 values, the `QuestionFactory.replay()` method reconstructs the exact same question.

## Deterministic Generation Example

```python
# Template: "What is the time complexity of dict lookup?"
# Parameter schema: {"size": {"type": "integer", "min": 100, "max": 1000000}}
# Correct answer: "O(1)"
# Distractors: ["O(n)", "O(log n)", "O(n log n)"]

factory = QuestionFactory()

# Generate with seed 42
result1 = factory.generate(template_version, seed=42, ...)
# → size=874, prompt="...874 entries...", answer="O(1)"

# Generate again with same seed
result2 = factory.generate(template_version, seed=42, ...)
# → IDENTICAL to result1 (same hash, same variables, same prompt)

# Generate with different seed
result3 = factory.generate(template_version, seed=99, ...)
# → size=3267, different prompt, but same answer "O(1)"
```

## Future Extension Points

1. **Import/Export** — JSON, Markdown, CSV import for bulk content creation
2. **Full-text search** — PostgreSQL tsvector for searching concepts and templates
3. **Analytics** — template usage, success rate, misconception frequency
4. **AI authoring** — LLM-assisted draft generation (human-reviewed, not runtime)
5. **Adaptive distractor selection** — choose distractors based on learner's suspected misconceptions
6. **Multi-language content** — localized prompts and explanations
