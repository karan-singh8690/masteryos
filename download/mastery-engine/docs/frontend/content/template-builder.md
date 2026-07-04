# Template Builder

> Visual question template editor with all configuration sections.

## Sections

### 1. Basic Information
- Subject selection (dropdown)
- Template code (unique identifier)
- Question type (8 types: multiple_choice, multiple_select, true_false, ordering, fill_blank, code_output, short_answer, numerical)
- Difficulty (easy, medium, hard)

### 2. Prompt Template
- Textarea for prompt text
- Supports variable interpolation: `{variable_name}`
- Supports code blocks with ```python``` syntax

### 3. Generators (JSON configuration)
- **Parameter schema**: Variable definitions (type, min, max)
- **Correct answer generator**: How to compute the correct answer
- **Distractor generator**: How to generate wrong answers (optional)
- **Explanation template**: Explanation text with variable interpolation

### 4. Hint Tiers
- Add/remove progressive hints
- Each tier reveals more information
- Reduces mastery gain when used

### 5. Concept Mapping
- Checkbox list of concepts in the subject
- Links template to concepts for mastery tracking
- Multiple concepts per template supported

### 6. Explanation Variants
- Multiple explanation types: correct, incorrect, hint, interview, beginner
- Markdown content for each variant
- Add/remove variants

## Validation

- Required fields: code, prompt
- JSON fields are validated on submit
- Subject must be selected

## Live Preview

After saving, click "Live preview" to generate questions using the backend QuestionFactory.

## API Integration

- `POST /admin/subjects/{id}/question-templates` — Create template
- `GET /admin/question-templates/{id}` — Get template detail
