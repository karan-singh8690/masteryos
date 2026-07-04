# Reviews

> Spaced repetition review center.

## Pages

### Review Center (`/reviews`)

- **Stats bar**: Due now, Today, This week, Completion rate
- **Due Reviews tab**: List of concepts due for review with:
  - Concept name
  - Subject name
  - Question count
  - Priority badge (urgent, high, medium, low)
  - "Review" button → starts a review session
- **Upcoming Reviews tab**: Concepts due in the next 7 days with relative time

## Data Sources

- `GET /reviews/due/{enrollmentId}` — Due reviews
- `GET /reviews/upcoming/{enrollmentId}?days=7` — Upcoming reviews
- `GET /reviews/stats/{enrollmentId}` — Review statistics

## Review Priorities

| Priority | Color | Meaning |
|---|---|---|
| Urgent | Destructive (red) | Overdue — review immediately |
| High | Destructive (red) | Due today |
| Medium | Warning (yellow) | Due within 2 days |
| Low | Secondary (gray) | Due within a week |

## Starting a Review

Clicking "Review" navigates to `/study/start` with the intent pre-set to "review". The adaptive queue will prioritize due review concepts.
