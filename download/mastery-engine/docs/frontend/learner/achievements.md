# Achievements

> Achievement gallery with unlocked + locked achievements.

## Page (`/achievements`)

- Header showing "X of Y unlocked"
- **Unlocked section**: Grid of achievement cards with:
  - Icon
  - Name
  - Description
  - Unlock date (relative time)
  - Success border styling
- **Locked section**: Grid of achievement cards with:
  - Lock icon (grayscale)
  - Name
  - Description
  - Progress bar (current / target)
  - Percentage
  - Reduced opacity

## Achievement Fields

```typescript
interface Achievement {
  id: UUID
  name: string
  description: string
  category: 'learning' | 'streak' | 'mastery' | 'social' | 'special'
  icon: string
  unlocked_at: ISO8601 | null
  progress: number
  target: number
  is_unlocked: boolean
}
```

## Categories

| Category | Description |
|---|---|
| Learning | Completing questions, sessions |
| Streak | Daily streak milestones |
| Mastery | Reaching mastery thresholds |
| Social | Leaderboard, sharing |
| Special | Limited-time or hidden achievements |

## Data Source

- `GET /achievements` — List all achievements (unlocked + locked)

## Session Summary

Achievements unlocked during a study session are also displayed in the session summary page with a celebratory card.
