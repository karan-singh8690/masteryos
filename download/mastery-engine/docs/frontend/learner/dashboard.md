# Dashboard

> Learner dashboard with live backend data.

## Widgets

| Widget | Data Source | Description |
|---|---|---|
| Welcome | Auth provider | Time-based greeting with user name |
| Streak | `/dashboard` API | Current + longest streak |
| Daily Goal | `/dashboard` API | Progress percentage with bar |
| Queue Remaining | `/dashboard` API | Questions remaining in today's queue |
| Due Reviews | `/dashboard` API | Count of reviews due today |
| Interview Readiness | `/dashboard` API | Overall readiness score (0-100%) |
| Mastery Overview | `/dashboard` API | Donut chart with average mastery |
| Weak Concepts | `/dashboard` API | Top 5 concepts needing attention |
| Strong Concepts | `/dashboard` API | Top 5 mastered concepts |
| Weekly Learning | `/dashboard` API | Bar chart of daily activity |
| Monthly Mastery | `/dashboard` API | Area chart of mastery trend |
| Recommendation | `/recommendations` API | Top recommendation with accept/dismiss |
| Continue Studying | Enrollments | CTA to start a study session |

## States

- **Loading**: Skeleton placeholders matching widget layout
- **Error**: Error card with retry button
- **Empty**: Welcome message with "Browse subjects" CTA
- **Offline**: Handled by React Query (shows cached data)

## Refresh

- Dashboard data has a 30-second stale time
- Auto-refetches when window regains focus (React Query default)
- Invalidated after study session submission
