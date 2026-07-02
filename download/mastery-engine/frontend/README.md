# Frontend — Mastery Engine UI

> Next.js frontend with TypeScript, Tailwind CSS, App Router.

## Structure

```
frontend/
├── app/
│   ├── layout.tsx           # Root layout (Providers, global styles)
│   ├── page.tsx             # Home page (landing)
│   └── health/
│       └── page.tsx         # Health check dashboard
├── components/              # Reusable UI components (future)
├── features/                # Feature-specific modules (future)
├── hooks/                   # Custom React hooks (future)
├── lib/
│   ├── api-client.ts        # Minimal API client (will be generated from OpenAPI)
│   └── utils.ts             # Utility functions (cn for class merging)
├── providers/
│   ├── index.tsx            # Root provider wrapper
│   └── query-provider.tsx   # React Query provider
├── styles/
│   └── globals.css          # Tailwind CSS + global styles
├── types/                   # Shared TypeScript types (future)
├── public/                  # Static assets
├── package.json
├── tsconfig.json
├── tailwind.config.js
├── postcss.config.js
├── next.config.js
├── .eslintrc.json
└── .prettierrc
```

## Development

```bash
# Install dependencies
npm install

# Run development server
npm run dev

# Build for production
npm run build

# Lint
npm run lint

# Format
npm run format

# Type check
npm run typecheck
```

## Pages

| Route | Description |
|---|---|
| `/` | Home page (landing) |
| `/health` | Health check dashboard (live + readiness) |

## Tech Stack

- **Framework**: Next.js 14+ (App Router)
- **Language**: TypeScript (strict mode)
- **Styling**: Tailwind CSS
- **Data fetching**: React Query (TanStack Query)
- **Validation**: Zod
- **Forms**: React Hook Form
- **Linting**: ESLint (next/core-web-vitals)
- **Formatting**: Prettier (with tailwind plugin)
