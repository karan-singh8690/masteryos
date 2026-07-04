# Analytics

> Content analytics with charts and metrics.

## Metrics

### Coverage Statistics
- **Concept coverage**: Percentage of concepts with at least one template
- **Explanation coverage**: Percentage of concepts with explanations
- **Misconception coverage**: Percentage of concepts with misconceptions

### Content Quality
- **Average discrimination**: How well templates distinguish between strong/weak learners
- **Average difficulty**: Most common difficulty level
- **Missing explanations**: Count of templates without explanation variants
- **Missing hints**: Count of templates without hint tiers

### Publishing Velocity
- Bar chart showing templates published per day
- Helps track content creation pace

### Difficulty Distribution
- Horizontal bar chart showing count of templates per difficulty level
- Helps identify content gaps (e.g., too many easy, not enough hard)

### Question Type Distribution
- Badge cloud showing count per question type
- Helps ensure variety in question types

### Top Templates by Usage
- List of top 10 most-used templates
- Helps identify which content is most valuable

## Charts

Uses Recharts:
- `ActivityBarChart` — Publishing velocity
- Custom horizontal bars — Difficulty distribution
- Badge components — Question type distribution

## API Integration

- `GET /admin/content/analytics` — All analytics data
- Optional `subject_id` query parameter for subject-specific analytics
