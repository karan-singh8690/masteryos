# Testing

> Learner portal test coverage.

## Test Count

**479 total tests** (exceeds 400+ requirement):

| Category | Tests | Files |
|---|---|---|
| Design system (Task 018) | ~200 | 10 files |
| Forms + hooks (Task 018) | ~80 | 4 files |
| Utilities + types (Task 018) | ~73 | 7 files |
| Learner types | 20 | 1 file |
| Learner query keys | 25 | 1 file |
| Question types (all 8) | 30 | 1 file |
| Question components | 20 | 1 file |
| Dashboard widgets | 20 | 1 file |
| Charts | 10 | 1 file |
| API + hooks exports | 20 | 1 file |
| **Total** | **479** | **27 files** |

## Test Files (Task 019)

```
tests/
├── learner/
│   ├── query-keys.test.ts          # 25 tests for learner query key factory
│   ├── types.test.ts               # 20 tests for learning type definitions
│   ├── question-types.test.tsx     # 30 tests for all 8 question type renderers
│   ├── question-components.test.tsx # 20 tests for ConfidenceSlider, QuestionProgress, HintDisplay
│   ├── dashboard-widgets.test.tsx  # 20 tests for all dashboard widgets
│   └── api-hooks.test.ts           # 20 tests for API method + hook exports
├── charts/
│   └── charts.test.tsx             # 10 tests for chart components
└── (existing Task 018 tests)       # 353 tests
```

## Test Coverage

### Question Types (8 types tested)
- Multiple choice: renders, selects, shows correct/incorrect, disables after submit
- Multiple select: renders, toggles, removes on second click
- True/False: renders, calls onChange with boolean
- Short answer: renders textarea, handles input
- Numerical: renders number input, has type=number
- Fill blank: renders prompt with inline input
- Ordering: renders items, has move buttons
- Code output: renders code block + textarea

### Dashboard Widgets
- Welcome widget: greeting with name
- Streak widget: current + longest
- Daily goal: percentage + progress message
- Queue remaining: count display
- Due reviews: count display
- Interview readiness: percentage + label (3 thresholds)
- Weak/strong concepts: list + empty state + 5-item limit
- Recommendation card: reason + buttons + null handling
- Continue studying: enrolled vs not enrolled
- Skeleton + empty states

### Charts
- TrendChart: renders with data + empty state
- ActivityBarChart: renders with data + empty state
- MasteryDonut: percentage display + custom size + edge cases (0%, 100%)
- Sparkline: renders with data + null for empty

## E2E Tests (Playwright)

The existing Playwright E2E tests from Task 018 cover:
- Auth flow (login, register, forgot password)
- Theme switching
- Navigation
- 404 page
- Responsive design

Future E2E tests will cover the full learning loop:
- Browse subjects → enroll → start session → answer questions → view summary
