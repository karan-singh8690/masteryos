'use client'

import type { ReactNode } from 'react'
import { QueryProvider } from '@/providers/query-provider'

/**
 * Root providers — wraps the application with all context providers.
 *
 * Currently:
 * - QueryProvider (React Query)
 *
 * Future:
 * - AuthProvider (JWT session management)
 * - ThemeProvider (dark/light mode)
 * - NotificationProvider (in-app notifications)
 */
export function Providers({ children }: { children: ReactNode }) {
  return <QueryProvider>{children}</QueryProvider>
}
