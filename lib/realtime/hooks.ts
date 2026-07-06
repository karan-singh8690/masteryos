/**
 * Real-time hooks — subscribe to WebSocket events and auto-update React Query caches.
 */

'use client'

import { useCallback } from 'react'
import { useQueryClient } from '@tanstack/react-query'

import { useWebSocket, useWebSocketSubscription, type WSMessage } from '@/lib/realtime/websocket-provider'
import { queryKey } from '@/lib/query-keys'
import { useNotificationStore } from '@/stores/notification-store'

/**
 * Live notification updates — automatically updates the notification badge + store.
 */
export function useLiveNotifications() {
  const { incrementUnread } = useNotificationStore()
  const queryClient = useQueryClient()

  useWebSocketSubscription('notification', (msg: WSMessage) => {
    const notification = msg.payload as { id: string; title: string; priority: string }
    incrementUnread()
    queryClient.invalidateQueries({ queryKey: queryKey.learner.notifications() })
    queryClient.invalidateQueries({ queryKey: queryKey.learner.unreadNotificationCount() })

    // Show toast for urgent notifications
    if (notification.priority === 'urgent') {
      import('sonner').then(({ toast }) => {
        toast.error(notification.title, { duration: 10000 })
      })
    }
  })
}

/**
 * Live dashboard updates — invalidates dashboard query when updates arrive.
 */
export function useLiveDashboard() {
  const queryClient = useQueryClient()

  useWebSocketSubscription('dashboard_update', () => {
    queryClient.invalidateQueries({ queryKey: queryKey.learner.dashboard() })
  })

  useWebSocketSubscription('study_progress', () => {
    queryClient.invalidateQueries({ queryKey: queryKey.learner.dashboard() })
    queryClient.invalidateQueries({ queryKey: ['mastery'] })
  })

  useWebSocketSubscription('queue_update', () => {
    queryClient.invalidateQueries({ queryKey: ['learning', 'sessions'] })
  })

  useWebSocketSubscription('achievement_unlocked', (msg: WSMessage) => {
    queryClient.invalidateQueries({ queryKey: queryKey.learner.achievements() })
    import('sonner').then(({ toast }) => {
      const ach = msg.payload as { name: string; icon: string }
      toast.success(`🏆 Achievement unlocked: ${ach.name}!`)
    })
  })
}

/**
 * Live admin metrics — invalidates admin queries when updates arrive.
 */
export function useLiveAdminMetrics() {
  const queryClient = useQueryClient()

  useWebSocketSubscription('worker_metrics', () => {
    queryClient.invalidateQueries({ queryKey: queryKey.admin.workerMetrics() })
    queryClient.invalidateQueries({ queryKey: queryKey.admin.workers() })
  })

  useWebSocketSubscription('outbox_update', () => {
    queryClient.invalidateQueries({ queryKey: ['admin', 'outbox'] })
    queryClient.invalidateQueries({ queryKey: queryKey.admin.outboxStats() })
  })

  useWebSocketSubscription('scheduler_event', () => {
    queryClient.invalidateQueries({ queryKey: queryKey.admin.jobs() })
  })

  useWebSocketSubscription('security_incident', () => {
    queryClient.invalidateQueries({ queryKey: queryKey.admin.securityDashboard() })
    queryClient.invalidateQueries({ queryKey: ['admin', 'security', 'incidents'] })
  })
}

/**
 * Session expiration warning — shows a warning before session expires.
 */
export function useSessionExpirationWarning() {
  useWebSocketSubscription('session_warning', (msg: WSMessage) => {
    const payload = msg.payload as { minutes_remaining: number }
    if (payload.minutes_remaining <= 5) {
      import('sonner').then(({ toast }) => {
        toast.warning(`Your session expires in ${payload.minutes_remaining} minutes. Save your work.`, {
          duration: 10000,
        })
      })
    }
  })
}

/**
 * Combined real-time provider — wraps all live update hooks.
 * Use this in the root layout to enable real-time updates everywhere.
 */
export function useRealtimeUpdates() {
  useLiveNotifications()
  useLiveDashboard()
  useLiveAdminMetrics()
  useSessionExpirationWarning()
}

/**
 * Connection status hook for UI indicators.
 */
export function useConnectionStatus() {
  const { status } = useWebSocket()
  return {
    isConnected: status === 'connected',
    isConnecting: status === 'connecting' || status === 'reconnecting',
    isDisconnected: status === 'disconnected' || status === 'error',
    status,
  }
}
