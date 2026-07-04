# Mastery

> Mastery tracking pages with charts.

## Pages

### Overall Mastery (`/mastery`)

- Enrollment selector (if multiple enrollments)
- Average mastery donut chart
- Weak concept count + mastered count
- Mastery timeline (area chart)
- All concepts list (sorted by mastery score, weakest first)
- Each concept links to `/mastery/[conceptId]`

### Concept Detail (`/mastery/[conceptId]`)

- Mastery donut (combined score)
- Stats grid:
  - Memory score
  - Durable mastery score
  - Evidence count
  - Last attempt time
- Concept state badge (unseen, novice, developing, proficient, mastered, decayed)
- Weakness severity badge (none, low, medium, high, critical)
- Mastery history timeline chart

## Charts

Uses Recharts:
- `MasteryDonut` — Circular progress indicator
- `TrendChart` — Area chart for mastery/memory over time
- `ActivityBarChart` — Bar chart for daily activity
- `Sparkline` — Mini line chart for inline trends

## Data Sources

- `GET /mastery/scores/{enrollmentId}` — All mastery scores for enrollment
- `GET /mastery/scores/{enrollmentId}/weak` — Weak concepts only
- `GET /mastery/timeline/{enrollmentId}` — Mastery timeline
- `GET /mastery/timeline/{enrollmentId}/{conceptId}` — Per-concept timeline

## Mastery States

| State | Description |
|---|---|
| Unseen | No attempts yet |
| Novice | Just started learning |
| Developing | Making progress |
| Proficient | Good understanding |
| Mastered | Fully mastered |
| Decayed | Was mastered, now declining (needs review) |
