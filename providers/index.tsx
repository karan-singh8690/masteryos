'use client'

import type { ReactNode } from 'react'
import { QueryProvider } from '@/providers/query-provider'
import { ThemeProvider } from '@/providers/theme-provider'
import { AuthProvider } from '@/providers/auth-provider'
import { Toaster } from '@/components/ui/toaster'
import { TooltipProvider } from '@/components/ui/tooltip'

/**
 * Root providers — wraps the application with all context providers.
 *
 * Provider order (outer → inner):
 * 1. ThemeProvider (next-themes)
 * 2. QueryProvider (React Query)
 * 3. AuthProvider (JWT session management)
 * 4. TooltipProvider (Radix UI tooltips)
 */
export function Providers({ children }: { children: ReactNode }) {
  return (
    <ThemeProvider
      attribute="class"
      defaultTheme="system"
      enableSystem
      disableTransitionOnChange
    >
      <QueryProvider>
        <AuthProvider>
          <TooltipProvider delayDuration={300}>{children}</TooltipProvider>
        </AuthProvider>
      </QueryProvider>
      <Toaster />
    </ThemeProvider>
  )
}
