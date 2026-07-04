# Routing

> Next.js 15 App Router with route groups + middleware protection.

## Route Groups

### `(auth)` — Authentication pages

- `/login` — Login with email/password + MFA
- `/register` — Registration with password strength
- `/forgot-password` — Request reset link
- `/reset-password` — Reset password with token
- `/verify-email` — Verify email with token
- `/mfa/setup` — Set up MFA (QR + recovery codes)
- `/mfa/verify` — Verify MFA code
- `/recovery-codes` — Use recovery code
- `/session-expired` — Session expired page

### `(app)` — Authenticated pages

- `/dashboard` — User dashboard
- `/profile` — Profile settings
- `/security` — Security dashboard (sessions, MFA, password change)
- `/settings` — App settings (theme, notifications, quiet hours)
- `/notifications` — Notification inbox

### Public pages

- `/` — Home page (marketing)
- `/unauthorized` — 401 page
- `/forbidden` — 403 page
- `/offline` — Offline page
- `/maintenance` — Maintenance page

## Route Protection

### Middleware (`middleware.ts`)

Checks for auth cookie on protected routes:

```typescript
const PUBLIC_ROUTES = ['/', '/login', '/register', ...]

export function middleware(request: NextRequest) {
  const hasToken = request.cookies.get('mastery-authenticated')?.value === 'true'
  if (!hasToken && !isPublic(pathname)) {
    return NextResponse.redirect(new URL('/login', request.url))
  }
}
```

### Client-side Protection (`ProtectedRoute`)

```tsx
import { ProtectedRoute } from '@/components/layout/route-protection'

<ProtectedRoute requireRoles={['administrator']}>
  <AdminContent />
</ProtectedRoute>
```

### Permission-based rendering

```tsx
import { PermissionGuard } from '@/components/layout/route-protection'

<PermissionGuard permission="content:create" fallback={<Unauthorized />}>
  <CreateButton />
</PermissionGuard>
```

## Layouts

- **PublicLayout** — Marketing pages with header + footer
- **AuthLayout** — Centered card for auth forms
- **AppLayout** — Sidebar + header for authenticated pages
