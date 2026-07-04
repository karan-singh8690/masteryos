# Testing

> Vitest + Testing Library + Playwright.

## Test Types

| Type | Tool | Purpose | Count |
|---|---|---|---|
| Unit | Vitest | Utilities, hooks, stores | ~150 |
| Component | Vitest + Testing Library | Component rendering + interaction | ~200 |
| E2E | Playwright | Full user flows | ~10 |

## Running Tests

```bash
# All unit/component tests
npm test

# Watch mode
npm run test:watch

# With coverage
npm run test:coverage

# E2E tests
npm run test:e2e

# E2E UI mode
npm run test:e2e:ui
```

## Test Structure

```
tests/
├── components/          # Component tests
│   ├── button.test.tsx
│   ├── input.test.tsx
│   ├── ui.test.tsx
│   ├── form-controls.test.tsx
│   ├── interactive.test.tsx
│   ├── variants.test.tsx
│   ├── extra.test.tsx
│   ├── layout.test.tsx
│   └── exports.test.tsx
├── forms/               # Form tests
│   ├── form.test.tsx
│   └── password-strength.test.tsx
├── hooks/               # Hook tests
│   ├── hooks.test.ts
│   └── extra-hooks.test.ts
├── lib/                 # Utility tests
│   ├── utils.test.ts
│   ├── validations.test.ts
│   ├── schemas.test.ts
│   ├── constants.test.ts
│   ├── query-keys.test.ts
│   ├── api-client.test.ts
│   ├── api-helpers.test.ts
│   ├── format.test.ts
│   ├── types.test.ts
│   └── stores.test.ts
└── e2e/                 # Playwright E2E
    └── auth-flow.spec.ts
```

## Test Example

```tsx
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, it, expect, vi } from 'vitest'
import { Button } from '@/components/ui/button'

describe('Button', () => {
  it('handles click events', async () => {
    const onClick = vi.fn()
    render(<Button onClick={onClick}>Click</Button>)
    await userEvent.click(screen.getByRole('button'))
    expect(onClick).toHaveBeenCalledTimes(1)
  })
})
```

## Coverage

- 353 test cases
- Covers: components, forms, hooks, utilities, stores, types
- E2E: auth flow, theme switching, navigation, responsive
