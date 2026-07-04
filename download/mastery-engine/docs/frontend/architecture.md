# Architecture

> Frontend architecture overview.

## Layers

```
┌─────────────────────────────────────────────────┐
│                    Pages (app/)                  │
│  Route components that compose features + layout │
├─────────────────────────────────────────────────┤
│              Layout Components                   │
│  PublicLayout, AuthLayout, AppLayout             │
│  Header, Sidebar, ProfileMenu, NotificationMenu  │
├─────────────────────────────────────────────────┤
│               Features                           │
│  Feature-specific components + hooks             │
├─────────────────────────────────────────────────┤
│          Design System (components/ui)           │
│  Button, Input, Card, Dialog, etc. (24+)         │
├─────────────────────────────────────────────────┤
│               Forms (components/forms)           │
│  Form, FormField, FormLabel, FormControl         │
│  PasswordStrengthMeter                           │
├─────────────────────────────────────────────────┤
│           API Layer (lib/api-client.ts)          │
│  Axios instance + interceptors                   │
│  authApi, userApi                                │
├─────────────────────────────────────────────────┤
│          State (stores/ + providers/)            │
│  Zustand: auth, ui, notification                 │
│  Providers: Auth, Theme, React Query             │
├─────────────────────────────────────────────────┤
│             Types (types/)                       │
│  User, Auth, Common types                        │
├─────────────────────────────────────────────────┤
│            Utilities (lib/)                      │
│  cn, format, constants, query-keys, validations  │
└─────────────────────────────────────────────────┘
```

## Data Flow

```
User action → Page → Feature component → API call (lib/api-client)
                                              ↓
                                         Backend (FastAPI)
                                              ↓
                                         Response
                                              ↓
                                    React Query cache
                                              ↓
                                    Component re-render
```

## Authentication Flow

```
Login page → authApi.login() → tokens stored in localStorage
                                    ↓
                              AuthProvider fetches /users/me
                                    ↓
                              useAuth() returns user
                                    ↓
                              ProtectedRoute checks auth
```

## API Client

The API client (`lib/api-client.ts`) provides:

- **Axios instance** with base URL + JSON content type
- **Request interceptor**: adds Authorization header + correlation ID + idempotency key
- **Response interceptor**: normalizes errors + auto-refreshes on 401
- **Pagination helpers**: `paginationParams()`, `toPaginatedResponse()`
- **File upload**: `apiClient.upload()`
- **Typed API methods**: `authApi`, `userApi`

## Route Protection

1. **Middleware** (`middleware.ts`): Server-side check for auth cookie
2. **ProtectedRoute**: Client-side check for authenticated user
3. **PermissionGuard**: Component-level permission check
4. **RoleGuard**: Component-level role check

## State Management

- **Server state**: React Query (caching, invalidation)
- **Global UI state**: Zustand (auth, ui, notification)
- **Local state**: React useState

No Redux. No context for server state.

## Build

- Next.js 15 App Router
- Static generation where possible
- Server components for initial render
- Client components for interactivity (`'use client'`)

## Testing

- **Unit/Component**: Vitest + Testing Library (353 tests)
- **E2E**: Playwright (auth flow, theme, navigation, responsive)
