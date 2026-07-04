# Content Dashboard

> Dashboard for content editors showing live backend data.

## Widgets

| Widget | Data Source | Description |
|---|---|---|
| Subjects | Dashboard API | Total subject count |
| Draft templates | Dashboard API | Templates in draft status |
| Published templates | Dashboard API | Published template count |
| Pending reviews | Dashboard API | Templates awaiting review |
| Coverage statistics | Dashboard API | Concept/explanation/misconception coverage percentages |
| Recently edited | Dashboard API | Last 5 edited items |
| Publishing queue | Dashboard API | Items ready/awaiting publish |
| Template quality | Dashboard API | Avg discrimination, difficulty, hint count |

## States

- **Loading**: Skeleton placeholders
- **Error**: Error card with retry
- **Empty**: "No content yet" with create CTA
- **Offline**: Cached data via React Query

## Quick Actions

- Create subject → `/content/subjects/create`
- Create template → `/content/templates/create`
- View analytics → `/content/analytics`
