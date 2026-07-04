# Question Preview

> Live question generation via backend QuestionFactory.

## Overview

The preview page calls the backend's deterministic question generation pipeline to produce real question instances from a template. No client-side generation logic — the frontend only displays what the backend produces.

## Features

### Seed Control
- Default seed: 42
- Custom seed input
- Random seed button
- Same seed → same question (deterministic)

### Generated Question Display
- Prompt text (with rendered code blocks)
- Choices (with correct/incorrect indicators)
- Choice explanations
- Metadata:
  - Question type badge
  - Seed badge
  - Render hash (first 8 chars)
  - Difficulty
  - Estimated duration
  - Concept ID count

### Auto-Generation
- Preview auto-generates on page load with seed 42
- "Generate" button to regenerate with current seed
- "Random" button to use a random seed

## API Integration

- `POST /admin/question-templates/preview` — Generate preview
  - Request: `{ template_id, seed?, variables? }`
  - Response: `QuestionPreview` with prompt, choices, metadata, render_hash

## Important

The backend QuestionFactory:
1. Takes the template + seed
2. Generates variables from the parameter schema
3. Renders the prompt template with variables
4. Generates the correct answer
5. Generates distractors
6. Renders explanations
7. Returns a complete question instance (without persisting it)

The render hash ensures deterministic verification — same template + seed always produces the same hash.
