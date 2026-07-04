# Recommendations

> Personalized learning recommendations.

## Page (`/recommendations`)

- List of current recommendations
- Each recommendation shows:
  - Type badge (review_concept, practice_weakness, learn_new, take_break, advance_topic)
  - Reason text
  - Concept name (if applicable)
  - Relative creation time
  - Accept button (✓)
  - Dismiss button (✗)

## Actions

### Accept

Calls `POST /recommendations/{id}/accept`:
- Marks the recommendation as accepted
- Invalidates the recommendations + dashboard queries
- May navigate to the recommended action (e.g., start a study session)

### Dismiss

Calls `POST /recommendations/{id}/dismiss`:
- Marks the recommendation as dismissed
- Removes it from the active recommendations list
- Invalidates the recommendations query

## Data Source

- `GET /recommendations` — List all active recommendations
- `POST /recommendations/{id}/accept` — Accept
- `POST /recommendations/{id}/dismiss` — Dismiss

## Recommendation Types

| Type | Description |
|---|---|
| `review_concept` | A specific concept needs review |
| `practice_weakness` | Focus on weak areas |
| `learn_new` | Start learning a new concept |
| `take_break` | Rest to avoid burnout |
| `advance_topic` | Move to a more advanced topic |
