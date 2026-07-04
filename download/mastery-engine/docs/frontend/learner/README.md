# Learner Portal — README

> **Status:** v1.0 — Complete learner-facing application
> **Task:** 019 — Learner Portal & Complete Study Experience

## Overview

The Learner Portal is a fully functional adaptive learning platform built on top of the Mastery Engine backend. Every screen consumes real APIs — no mock data, no placeholder dashboards.

## Features

### 1. Dashboard
- Welcome section with time-based greeting
- Current streak + longest streak
- Daily goal progress
- Queue remaining count
- Due reviews count
- Interview readiness score
- Overall mastery donut chart
- Weak concepts list
- Strong concepts list
- Weekly learning bar chart
- Monthly mastery trend chart
- Personalized recommendation card
- Continue studying CTA
- Loading, error, empty, and offline states

### 2. Subject Selection
- Subject catalog with search
- Subject details with concepts list
- Enrollment flow
- Progress indicators
- Continue learning links

### 3. Study Session Experience
- Start session with intent selection (mixed, review, learn new, practice)
- Question count selection (5, 10, 15, 20)
- Adaptive queue from real backend
- Question rendering for all types
- Answer submission with confidence slider
- Explanation display after submission
- Mastery update display
- Review schedule display
- Recommendation display
- Next question navigation
- Session timer with pause/resume
- Abandon session confirmation
- Keyboard shortcuts (1-4 for quick answer, Enter to submit, H for hint)
- Session summary with stats, achievements, and recommendations

### 4. Question Experience
Supports all question types:
- Multiple choice (single answer)
- Multiple select (multiple answers)
- True/False
- Ordering (up/down buttons)
- Fill in the blank
- Code output
- Short answer
- Numerical

Features:
- Hints with tier system
- Confidence slider (0-100%)
- Timer
- Accessibility (ARIA labels, keyboard nav)
- Never exposes correct answers before submission

### 5. Submission Flow
- Correctness display (correct, partially correct, incorrect)
- Mastery delta
- Explanation text
- Review schedule (next review date, priority, interval)
- Recommendation
- Response time display
- Next action button

### 6. Session Summary
- Questions answered count
- Accuracy percentage
- Time spent
- Mastery gained
- Weak concepts
- Strong concepts
- Recommendations
- Review schedule
- Achievements unlocked
- Continue button

### 7. Mastery Pages
- Overall mastery (average score, donut chart, timeline)
- Concept mastery detail (memory score, durable mastery, evidence count, last attempt)
- Mastery timeline chart
- Weak/strong concept lists

### 8. Review Center
- Due reviews (with priority badges)
- Upcoming reviews (7-day forecast)
- Review statistics (total due, today, this week, completion rate)
- Start review session link

### 9. Recommendations
- Current recommendations list
- Accept recommendation
- Dismiss recommendation
- Recommendation type badges

### 10. Achievements
- Achievement gallery
- Unlocked achievements (with unlock date)
- Locked achievements (with progress bar)
- Category badges

### 11. Notifications
- Notification center with pagination
- Read/unread indicators
- Mark as read / dismiss
- Mark all as read
- Smart date display (Today, Yesterday, full date)

### 12. Search
- Global search page
- Subject search with debounced input
- Quick links to key sections
- Results with subject cards

## Architecture

### Data Flow
```
User action → Page → Hook (React Query) → API Client → Backend
                                                                ↓
                                                           Response
                                                                ↓
                                                    React Query cache
                                                                ↓
                                                    Component re-render
```

### Key Files

```
frontend/
├── app/(learner)/                 # Learner route group
│   ├── layout.tsx                 # Learner layout with sidebar
│   ├── dashboard/                 # Dashboard page
│   ├── subjects/                  # Subject catalog + details
│   ├── study/                     # Study session + summary
│   ├── mastery/                   # Mastery overview + concept detail
│   ├── reviews/                   # Review center
│   ├── recommendations/           # Recommendations page
│   ├── achievements/              # Achievements gallery
│   ├── notifications/             # Notification center
│   └── search/                    # Global search
├── components/
│   ├── learner/                   # Learner-specific components
│   │   ├── question-types.tsx     # All question type renderers
│   │   ├── question-renderer.tsx  # Dispatcher + confidence slider + timer
│   │   └── dashboard-widgets.tsx  # Dashboard widget components
│   └── charts/                    # Recharts wrappers
│       └── index.tsx              # TrendChart, BarChart, Donut, Sparkline
├── hooks/
│   └── use-learner.ts             # All learner React Query hooks
├── lib/
│   └── learner-api.ts             # Learner API client methods
├── types/
│   └── learning.ts                # All learning-related types
└── tests/
    ├── learner/                   # Learner-specific tests
    └── charts/                    # Chart component tests
```

## Testing

- **479 total tests** (exceeds 400+ requirement)
  - 353 from Task 018 (design system, auth, forms, hooks, utilities)
  - 126 new Task 019 tests (learner types, query keys, question types, dashboard widgets, charts, API/hooks)
- Tests cover: types, query keys, question rendering (all 8 types), confidence slider, progress bar, hints, dashboard widgets, chart components, API method exports, hook exports

## Acceptance Criteria

✅ Learner can browse and enroll in subjects
✅ Learner can start a study session
✅ Adaptive queue loads from the real backend
✅ Questions render correctly (all 8 types)
✅ Answers submit to the backend
✅ Explanation displays after submission
✅ Mastery updates immediately (via React Query invalidation)
✅ Dashboard refreshes automatically (30s stale time)
✅ Review schedule updates (displayed in submission result + review center)
✅ Recommendations display (dashboard + dedicated page)
✅ Notifications work (list, mark read, dismiss, mark all)
✅ Achievements display (unlocked + locked with progress)
✅ Profile management works (from Task 018)
✅ Responsive on mobile/tablet/desktop
✅ Accessible (WCAG AA, ARIA, keyboard nav)
✅ TypeScript strict passes
✅ 479 frontend tests
