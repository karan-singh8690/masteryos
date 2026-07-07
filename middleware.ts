import { NextResponse, type NextRequest } from 'next/server'

import { TOKEN_STORAGE_KEY } from '@/lib/constants'

/**
 * Route protection middleware.
 *
 * Checks for access token in localStorage (via cookie bridge) and redirects
 * unauthenticated users to /login for protected routes.
 *
 * Note: localStorage isn't available in middleware, so we use a cookie
 * that mirrors the access token presence.
 */

const PUBLIC_ROUTES = ['/', '/login', '/register', '/forgot-password', '/reset-password', '/verify-email', '/health', '/offline', '/maintenance', '/unauthorized', '/forbidden', '/session-expired', '/privacy', '/terms']

// Task 027: Public marketing/docs/support routes that don't require auth.
const PUBLIC_PREFIXES = [
  '/features',
  '/pricing',
  '/security',
  '/docs',
  '/api-explorer',
  '/status',
  '/roadmap',
  '/changelog',
  '/blog',
  '/about',
  '/contact',
  '/careers',
  '/support',
  '/legal',
  '/sdk',
  '/q/',          // Public question pages (SEO — no auth required)
  '/brand',
  '/manifest.webmanifest',
  '/robots.txt',
  '/sitemap.xml',
]

const ADMIN_ROUTES = ['/admin']

export function middleware(request: NextRequest) {
  const { pathname } = request.nextUrl

  // Allow public routes
  if (PUBLIC_ROUTES.some((route) => pathname === route || pathname.startsWith(`${route}/`))) {
    return NextResponse.next()
  }

  // Allow public prefixes (marketing, docs, blog, etc.)
  if (PUBLIC_PREFIXES.some((prefix) => pathname === prefix || pathname.startsWith(`${prefix}/`))) {
    return NextResponse.next()
  }

  // Allow API routes + static assets
  if (pathname.startsWith('/api/') || pathname.startsWith('/_next/') || pathname.includes('.')) {
    return NextResponse.next()
  }

  // Check for auth token (via cookie bridge)
  const hasToken = request.cookies.get('mastery-authenticated')?.value === 'true'

  // Protected routes
  if (!hasToken) {
    const loginUrl = new URL('/login', request.url)
    loginUrl.searchParams.set('redirect', pathname)
    return NextResponse.redirect(loginUrl)
  }

  // Admin routes — allow access if authenticated.
  // Real RBAC enforcement happens in the backend API (RequireAdmin dependency).
  // The frontend ProtectedRoute component also checks roles client-side.
  // The middleware cookie check is removed because the role cookie may not
  // be set reliably (depends on /users/me response format).

  return NextResponse.next()
}

export const config = {
  matcher: ['/((?!api|_next/static|_next/image|favicon.ico|.*\\..*).*)'],
}
