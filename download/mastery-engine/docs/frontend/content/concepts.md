# Concept Management

> Full CRUD for concepts within subjects.

## Features

### Create Concept
- Slug (unique within subject)
- Name
- Description
- Difficulty: beginner, intermediate, advanced
- Importance: low, medium, high, critical

### View Concept
- Concept details (name, slug, description, difficulty, importance, status)
- Learning objectives list
- Misconceptions list
- Related templates

### Edit Concept
- Update any field
- Slug editing

### Delete Concept
- Confirmation dialog
- Cascading delete (objectives, misconceptions)

## Learning Objectives

- Create: Statement (Markdown supported)
- Delete: With confirmation
- List by concept

## Misconceptions

- Create: Name, description, remediation
- Delete: With confirmation
- List by concept

## API Integration

- `POST /admin/subjects/{id}/concepts` — Create concept
- `GET /admin/subjects/{id}/concepts` — List concepts
- `PATCH /admin/concepts/{id}` — Update concept
- `DELETE /admin/concepts/{id}` — Delete concept
- `POST /admin/concepts/{id}/objectives` — Create objective
- `POST /admin/concepts/{id}/misconceptions` — Create misconception
