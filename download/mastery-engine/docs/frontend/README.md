# Frontend — README

> **Status:** v1.0 — Production frontend foundation
> **Task:** 018 — Frontend Foundation & Authentication Platform

## Overview

The Mastery Engine frontend is a production Next.js 15 application with React 19, TypeScript (strict), Tailwind CSS, React Query, React Hook Form, Zod, Zustand, Framer Motion, and comprehensive testing.

## Tech Stack

| Technology | Version | Purpose |
|---|---|---|
| Next.js | 15 | App Router, SSR, routing |
| React | 19 | UI library |
| TypeScript | 5.6 | Type safety (strict) |
| Tailwind CSS | 3.4 | Styling |
| React Query | 5.59 | Server state |
| React Hook Form | 7.53 | Forms |
| Zod | 3.23 | Validation |
| Zustand | 4.5 | Global state (minimal) |
| Framer Motion | 11.11 | Animations |
| next-themes | 0.3 | Theme switching |
| Recharts | 2.13 | Charts |
| Axios | 1.7 | HTTP client |
| Radix UI | latest | Accessible primitives |
| Vitest | 2.1 | Unit tests |
| Testing Library | 16 | Component tests |
| Playwright | 1.48 | E2E tests |

## Getting Started

```bash
# Install dependencies
npm install

# Start dev server
npm run dev

# Build for production
npm run build

# Run tests
npm test

# Run E2E tests
npm run test:e2e

# Type check
npm run typecheck

# Lint
npm run lint
```

## Project Structure

```
frontend/
├── app/                          # Next.js App Router
│   ├── (auth)/                   # Auth route group
│   │   ├── login/
│   │   ├── register/
│   │   ├── forgot-password/
│   │   ├── reset-password/
│   │   ├── verify-email/
│   │   ├── mfa/{setup,verify}/
│   │   ├── recovery-codes/
│   │   └── session-expired/
│   ├── (app)/                    # Authenticated route group
│   │   ├── dashboard/
│   │   ├── profile/
│   │   ├── security/
│   │   ├── settings/
│   │   └── notifications/
│   ├── unauthorized/
│   ├── forbidden/
│   ├── offline/
│   ├── maintenance/
│   ├── layout.tsx                # Root layout
│   ├── page.tsx                  # Home page
│   ├── loading.tsx               # Route loading
│   ├── error.tsx                 # Error boundary
│   └── not-found.tsx             # 404 page
├── components/
│   ├── ui/                       # Design system (24+ components)
│   ├── forms/                    # Form components
│   └── layout/                   # Layout components
├── features/                     # Feature modules
├── hooks/                        # Custom hooks
├── lib/                          # Utilities
│   ├── api-client.ts             # Axios + interceptors
│   ├── cn.ts                     # Class merge
│   ├── constants.ts              # App constants
│   ├── format.ts                 # Formatters
│   ├── query-keys.ts             # React Query keys
│   └── validations.ts            # Zod schemas
├── providers/                    # Context providers
├── stores/                       # Zustand stores
├── tests/                        # Test files
│   ├── components/
│   ├── forms/
│   ├── hooks/
│   ├── lib/
│   └── e2e/
├── types/                        # TypeScript types
├── styles/                       # Global CSS
├── middleware.ts                 # Route protection
├── next.config.js
├── tailwind.config.js
├── tsconfig.json
├── vitest.config.ts
└── playwright.config.ts
```

## Documentation

- [Design System](design-system.md)
- [Routing](routing.md)
- [Authentication](authentication.md)
- [State Management](state-management.md)
- [Forms](forms.md)
- [Testing](testing.md)
- [Accessibility](accessibility.md)
- [Theme](theme.md)
- [Architecture](architecture.md)

## Test Coverage

- 353 unit/component tests (Vitest + Testing Library)
- E2E tests (Playwright) — auth flow, theme, navigation, responsive
- Tests cover: components, forms, hooks, utilities, stores, types

## Acceptance Criteria

✅ User can register
✅ User can login
✅ JWT refresh works automatically (via Axios interceptor)
✅ MFA works with backend (setup, verify, recovery codes)
✅ Logout works (single + all devices)
✅ Theme switching works (light/dark/system)
✅ Responsive layouts work (mobile/tablet/desktop)
✅ Dark mode works
✅ Components are reusable (24+ design system components)
✅ Forms use React Hook Form + Zod
✅ React Query integrated
✅ No mock data
✅ No placeholder authentication
✅ TypeScript strict passes
✅ Accessible UI (WCAG AA, ARIA, keyboard nav)
