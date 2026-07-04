'use client'

import * as React from 'react'
import type { ReactNode } from 'react'

import { QueryProvider } from '@/providers/query-provider'
import { ThemeProvider } from '@/providers/theme-provider'
import { AuthProvider } from '@/providers/auth-provider'
import { WebSocketProvider } from '@/lib/realtime/websocket-provider'
import { OfflineProvider } from '@/lib/offline/offline-provider'
import { FeatureFlagProvider } from '@/lib/production/feature-flags'
import { TooltipProvider } from '@/components/ui/tooltip'
import { Toaster } from '@/components/ui/toaster'
import { RealtimeSync } from '@/lib/realtime/realtime-sync'

/**
 * Production providers — wraps the application with all context providers
 * for production use.
 *
 * Provider order (outer → inner):
 * 1. ThemeProvider (next-themes)
 * 2. QueryProvider (React Query)
 * 3. AuthProvider (JWT session management)
 * 4. WebSocketProvider (real-time updates)
 * 5. OfflineProvider (offline support)
 * 6. FeatureFlagProvider (dynamic feature flags)
 * 7. TooltipProvider (Radix UI tooltips)
 *
 * Also includes:
 * - Toaster (toast notifications)
 * - RealtimeSync (auto-syncs React Query cache with WebSocket events)
 */
export function ProductionProviders({ children }: { children: ReactNode }) {
  return (
    <ThemeProvider
      attribute="class"
      defaultTheme="system"
      enableSystem
      disableTransitionOnChange
    >
      <QueryProvider>
        <AuthProvider>
          <WebSocketProvider>
            <OfflineProvider>
              <FeatureFlagProvider>
                <TooltipProvider delayDuration={300}>
                  <RealtimeSync />
                  {children}
                </TooltipProvider>
              </FeatureFlagProvider>
            </OfflineProvider>
          </WebSocketProvider>
        </AuthProvider>
      </QueryProvider>
      <Toaster />
    </ThemeProvider>
  )
}
