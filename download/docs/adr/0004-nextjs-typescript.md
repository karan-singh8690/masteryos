# ADR-0004 — Choose Next.js with TypeScript for the Frontend

---

## Title

Use Next.js (App Router) with TypeScript and Tailwind CSS as the frontend stack for the Mastery Engine.

---

## Status

Accepted

---

## Date

2026-07-02

---

## Context

The Mastery Engine frontend serves two distinct user experiences: a learner-facing application (dashboard, learning session, progress, settings) and an admin portal (content management, user support, analytics). The learner-facing application's most critical screen is the learning session, where the user answers questions in a tight loop with sub-second perceived latency. The dashboard's most critical job is to answer "what should I study next?" in under three seconds of cognitive load. The admin portal is a separate route tree with separate auth and a separate bundle.

The frontend must be SEO-friendly for marketing pages (login, landing), must support server-rendered pages for fast first paint on the dashboard, must support rich client-side interactivity for the learning session, and must generate its API client from the backend's OpenAPI spec (ADR-0014) to maintain contract consistency. The frontend must also be maintainable by a small team and must scale to a PWA for mobile learners without maintaining a separate React Native build (ASD Section 9).

The project's stack (ASD Section 1.5) specifies Next.js, TypeScript, and Tailwind CSS. This ADR formalizes that choice and explains the SSR, routing, scalability, and developer-experience rationale.

The learning session's interactivity requirements (pre-fetch next question, optimistic UI for answer submission, keyboard-first navigation, mid-session reload recovery) favor a React-based SPA-like experience, but the dashboard's read-heavy nature and SEO needs favor server rendering. Next.js's App Router supports both within one framework, eliminating the choice between SSR and SPA.

---

## Problem Statement

What frontend framework and language should the Mastery Engine use, given the requirements for server-rendered read-heavy pages, rich client-side interactivity for the learning session, SEO for marketing pages, API-client generation from OpenAPI, strong typing, PWA support for mobile, and maintainability by a small team?

---

## Decision

We will use **Next.js** (App Router, version 14+) with **TypeScript** (strict mode) and **Tailwind CSS** (version 4) as the frontend stack. The learner-facing application and the admin portal share a single Next.js application but use separate route trees (`/app/*` and `/admin/*`), separate layouts, and separate bundles (admin is code-split and lazily loaded).

We will use Next.js Server Components by default for read-heavy screens (dashboard, progress, settings) and Client Components only where interactivity requires them (learning session, forms, filters). State management is split: server state via React Query (or Next.js native fetch extensions), URL state for shareable filters, local UI state via `useState`/`useReducer`, and a small global context for the current user and tenant. No Redux or MobX.

The frontend API client is generated from the backend's OpenAPI spec (ADR-0014), so the frontend literally cannot call an endpoint the backend has not declared. The generated client is committed to the repository and updated as part of the API contract workflow.

---

## Alternatives Considered

### Alternative A: Single-Page Application (SPA) with Vite + React

- **Description:** A client-side-rendered React SPA built with Vite, with no server rendering.
- **Arguments in favor:**
  - Simpler mental model: everything is client-side.
  - Faster iteration during development (no server rendering to wait for).
  - Full control over the client experience.
- **Arguments against:**
  - No server rendering means slow first paint on the dashboard (the user sees a loading spinner while the JS bundle loads and fetches data).
  - SEO is worse for marketing pages (though the project's marketing pages are limited, they matter for acquisition).
  - The dashboard's "what next?" answer is delayed by the client-side fetch waterfall; server rendering composes the data on the server and sends HTML.
  - PWA support is more manual without Next.js's built-in conventions.
- **Why rejected:** The first-paint and SEO disadvantages are decisive for the dashboard and marketing pages. The learning session's interactivity is achievable within Next.js via Client Components; the SPA's advantages there do not outweigh its disadvantages elsewhere.

### Alternative B: Remix

- **Description:** Remix, a full-stack React framework with a focus on web standards and nested routing.
- **Arguments in favor:**
  - Excellent data loading and mutation model (loaders and actions).
  - Strong focus on web standards (forms, fetch).
  - Progressive enhancement philosophy.
- **Arguments against:**
  - Smaller ecosystem and hire pool than Next.js.
  - The project's stack (ASD Section 1.5) specifies Next.js; Remix would reverse that.
  - Next.js's App Router has adopted many of Remix's ideas (nested layouts, server-side data loading), narrowing the philosophical gap.
  - Vercel's backing of Next.js provides infrastructure and tooling that Remix's ecosystem (now part of Shopify) does not match for this project's needs.
- **Why rejected:** The ecosystem and hire-pool advantages of Next.js are decisive for a project that will be maintained for a decade. Remix is an excellent framework; the choice is close, and the deciding factor is ecosystem maturity and the team's existing Next.js expertise.

### Alternative C: Angular

- **Description:** Angular, a full-stack, opinionated TypeScript framework.
- **Arguments in favor:**
  - Strong typing and opinionated structure, good for large teams.
  - Built-in DI, routing, forms, and HTTP client.
  - MVC-style separation of concerns.
- **Arguments against:**
  - Steeper learning curve; smaller hire pool for the project's needs.
  - Less flexible than React for the learning session's custom interactivity.
  - The project's stack specifies React (via Next.js); Angular would reverse that.
  - Angular's opinionated structure can conflict with the project's own architectural opinions.
- **Why rejected:** The hire-pool and flexibility disadvantages are decisive. Angular is excellent for enterprise applications with large teams and standardized structure; it is less suited to a startup-style project with a small team and custom interactivity needs.

### Alternative D: Vue.js with Nuxt

- **Description:** Vue.js with Nuxt (Vue's SSR framework).
- **Arguments in favor:**
  - Excellent developer experience; Vue's composition API is well-regarded.
  - Nuxt provides SSR and routing comparable to Next.js.
- **Arguments against:**
  - Smaller hire pool than React in the project's target markets.
  - Smaller ecosystem of component libraries and tools.
  - The project's stack specifies React; Vue would reverse that.
- **Why rejected:** The hire-pool and ecosystem disadvantages are decisive. Vue/Nuxt is an excellent choice; the deciding factor is ecosystem size and hire pool.

---

## Pros

- **Server rendering for read-heavy screens**: the dashboard and progress pages compose data on the server and send HTML, minimizing time-to-first-meaningful-paint.
- **Client Components for interactivity**: the learning session uses Client Components for the tight interaction loop (pre-fetch, optimistic UI, keyboard nav) without sacrificing the rest of the app's SSR benefits.
- **App Router's nested layouts**: the public, app, and admin layouts are cleanly separated, with shared chrome factored into layout components.
- **SEO for marketing pages**: server-rendered HTML is crawlable; the login and landing pages benefit.
- **TypeScript strict mode**: end-to-end type safety, with the API client generated from OpenAPI providing contract-level type safety between frontend and backend.
- **Tailwind CSS**: utility-first styling that keeps CSS bundle size small and avoids the naming and scoping problems of traditional CSS; pairs well with component-based architecture.
- **PWA support**: Next.js's PWA conventions allow the learner-facing app to install on mobile without a separate React Native build, deferring native app development (ASD Section 9.11).
- **Code-splitting**: the admin portal is code-split and lazily loaded, so learner-facing users never download admin bundle weight.
- **API client generation**: the frontend API client is generated from the backend's OpenAPI spec, eliminating manual client maintenance and contract drift.
- **Vercel ecosystem**: optional deployment to Vercel provides preview deployments, edge functions, and analytics, though the project is not locked to Vercel (Docker deployment is the default, ASD Section 1.5).

---

## Cons

- **App Router maturity**: Next.js's App Router is newer than the Pages Router and has evolving conventions; some patterns are still settling. (Mitigated by following Next.js's official guidance and updating as conventions mature.)
- **Server/Client component boundary**: deciding what is a Server Component vs a Client Component requires discipline; mistakes produce unnecessary client-side JavaScript. (Mitigated by code review and by the rule "Server Component by default, Client Component only when needed.")
- **Bundle size management**: Next.js's flexibility makes it easy to import large libraries; the project's bundle size budget (250KB gzipped for learner-facing, ASD Section 9.11) requires vigilance. (Mitigated by CI bundle-size checks.)
- **Tailwind learning curve**: engineers unfamiliar with utility-first CSS need onboarding. (Mitigated by Tailwind's excellent documentation and by the team's existing expertise.)
- **Vercel coupling risk**: while Next.js is open-source and deployable anywhere, some features (Edge Functions, some image optimization) are Vercel-optimized; the project avoids Vercel-specific features to maintain portability.

---

## Consequences

- The team maintains Next.js, TypeScript, and Tailwind expertise; framework upgrades are tracked (Next.js evolves rapidly).
- TypeScript strict mode is enforced in CI; no `any` types are permitted without explicit justification.
- The API client is regenerated whenever the backend OpenAPI spec changes; the regeneration is part of the API contract workflow (ADR-0014).
- Server Components are the default; Client Components are used only for interactive elements (learning session, forms, filters).
- State management is split by purpose (server, URL, local, global context); no Redux or MobX is introduced without a new ADR justifying it.
- The admin portal is a separate route tree (`/admin/*`) with a separate layout and separate auth middleware; admin components are not imported by app components.
- PWA support is enabled for the learner-facing app; the manifest and service worker are maintained.
- Bundle size is monitored in CI; Lighthouse checks run against staging.
- The frontend is deployed as a Docker container (Next.js's standalone build), not locked to Vercel.

---

## Risks

- **App Router breaking changes**: the App Router is still evolving; breaking changes could disrupt upgrades. *Mitigation:* pin Next.js version; test upgrades in staging; follow the Next.js changelog.
- **Server/Client boundary erosion**: engineers default to Client Components for convenience, bloating the client bundle. *Mitigation:* linting rules that flag Client Components; code review; bundle-size CI checks.
- **Type-safety drift**: if the OpenAPI client generation is skipped or manual edits are made to the generated client, type safety between frontend and backend degrades. *Mitigation:* the generated client is treated as a build artifact; manual edits are forbidden; CI verifies the client matches the spec.
- **Bundle size creep**: third-party libraries inflate the bundle over time. *Mitigation:* bundle-size budget enforced in CI; periodic bundle analysis and pruning.
- **Mobile experience gap**: PWA may not match a native app's experience for some learners, creating pressure for a React Native build. *Mitigation:* PWA is the path until market pressure forces native; the decision is revisited per ASD Section 16.5.

---

## Future Review Trigger

**Review trigger:** Any of the following measurable conditions:

1. **Mobile experience demand**: more than 30% of learners use the PWA and churn rates or session-length metrics on mobile are significantly worse than desktop, indicating that a native app would materially improve retention.
2. **Bundle size ceiling**: the learner-facing bundle exceeds 350KB gzipped and cannot be reduced without sacrificing functionality, indicating that the App Router's overhead is too high.
3. **Server rendering limitation**: a future feature (e.g., real-time collaborative learning) requires a runtime model that Next.js's server rendering cannot support.
4. **Framework abandonment or stagnation**: Next.js maintenance slows significantly or the project forks, threatening long-term support.
5. **Type-safety ceiling**: the project's type-safety requirements exceed what TypeScript + generated OpenAPI clients can provide, and a full-stack TypeScript backend (e.g., tRPC) becomes attractive.

**Expected review action:** When any trigger fires, the architecture review group evaluates alternatives (a native mobile app via React Native or Expo; a different frontend framework; a full-stack TypeScript approach). The evaluation produces a new ADR. A native mobile app is the most likely future extraction; the PWA-first path defers this cost until justified.

---

## Related ADRs

- **Depends on:** ADR-0014 (API-first development) — the frontend API client is generated from the backend's OpenAPI spec.
- **Related:** ADR-0003 (FastAPI) — FastAPI generates the OpenAPI spec that Next.js's API client consumes.
- **Informs:** ADR-0015 (Documentation-first workflow) — the frontend's type safety depends on the API contract being designed before implementation.

---

## Related Architecture Sections

- ASD Section 1.5 — Why This Architecture Was Chosen (Next.js rationale).
- ASD Section 9 — Frontend Architecture (routing, layouts, state management, performance budget).
- ASD Section 9.11 — Performance Budget (bundle size, LCP, TBT targets).

---

## Related Glossary Terms

- User Profile
- Dashboard
- Learning Session
- Study Session
- Admin Portal
- Read Model

---

*End of ADR-0004.*
