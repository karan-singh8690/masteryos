# Subject Management

> Create, edit, publish, and archive subjects.

## Pages

| Page | Route | Description |
|---|---|---|
| Subject list | `/content/subjects` | Searchable list with status badges |
| Create subject | `/content/subjects/create` | Form with auto-slug generation |
| Subject detail | `/content/subjects/[subjectId]` | Concepts + templates tabs |

## Features

### List Page
- Search by name or code
- Status badges (draft, published, archived)
- Click to view detail
- Create button

### Create Page
- Code (unique identifier)
- Name (auto-generates slug)
- Slug (lowercase, hyphenated)
- Description (optional)
- Zod validation
- Auto-slug from name

### Detail Page
- Subject header with status badge
- Publish button (for draft subjects)
- Add concept button
- Add template button
- Tabs: Concepts + Templates
- Concept list with difficulty/importance badges + delete
- Template list with type/status badges + preview link
- Delete concept confirmation dialog

## API Integration

- `GET /admin/subjects` — List subjects
- `POST /admin/subjects` — Create subject
- `GET /admin/subjects/{id}` — Get subject
- `POST /admin/subjects/{id}/publish` — Publish subject
