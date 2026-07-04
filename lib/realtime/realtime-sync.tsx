'use client'

import * as React from 'react'

import {
  useLiveNotifications,
  useLiveDashboard,
  useLiveAdminMetrics,
  useSessionExpirationWarning,
} from '@/lib/realtime/hooks'

/**
 * RealtimeSync — invisible component that runs all real-time update hooks.
 * Placed in the provider tree to enable live updates across the entire app.
 */
export function RealtimeSync() {
  useLiveNotifications()
  useLiveDashboard()
  useLiveAdminMetrics()
  useSessionExpirationWarning()
  return null
}
