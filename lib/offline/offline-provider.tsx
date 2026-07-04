/**
 * Offline support — detection, queued mutations, background sync.
 */

'use client'

import * as React from 'react'
import { useQueryClient } from '@tanstack/react-query'

interface OfflineState {
  isOnline: boolean
  wasOffline: boolean
  queuedMutations: QueuedMutation[]
  queueMutation: (mutation: QueuedMutation) => void
  flushQueue: () => Promise<void>
}

export interface QueuedMutation {
  id: string
  mutationKey: string[]
  variables: unknown
  timestamp: string
  retryCount: number
}

const OFFLINE_QUEUE_KEY = 'mastery-offline-queue'
const MAX_QUEUE_SIZE = 50
const MAX_RETRIES = 3

const OfflineContext = React.createContext<OfflineState | null>(null)

export function OfflineProvider({ children }: { children: React.ReactNode }) {
  const [isOnline, setIsOnline] = React.useState(true)
  const [wasOffline, setWasOffline] = React.useState(false)
  const [queuedMutations, setQueuedMutations] = React.useState<QueuedMutation[]>([])
  const queryClient = useQueryClient()

  // Detect online/offline status
  React.useEffect(() => {
    const handleOnline = () => {
      setIsOnline(true)
      if (wasOffline) {
        flushQueue()
      }
    }
    const handleOffline = () => {
      setIsOnline(false)
      setWasOffline(true)
    }

    window.addEventListener('online', handleOnline)
    window.addEventListener('offline', handleOffline)
    setIsOnline(navigator.onLine)

    return () => {
      window.removeEventListener('online', handleOnline)
      window.removeEventListener('offline', handleOffline)
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [wasOffline])

  // Load queued mutations from localStorage on mount
  React.useEffect(() => {
    try {
      const stored = localStorage.getItem(OFFLINE_QUEUE_KEY)
      if (stored) {
        setQueuedMutations(JSON.parse(stored))
      }
    } catch {
      // Ignore parse errors
    }
  }, [])

  // Persist queue to localStorage
  React.useEffect(() => {
    try {
      localStorage.setItem(OFFLINE_QUEUE_KEY, JSON.stringify(queuedMutations))
    } catch {
      // Storage full — drop oldest
    }
  }, [queuedMutations])

  const queueMutation = React.useCallback((mutation: QueuedMutation) => {
    setQueuedMutations((prev) => {
      const updated = [...prev, mutation]
      if (updated.length > MAX_QUEUE_SIZE) {
        return updated.slice(-MAX_QUEUE_SIZE)
      }
      return updated
    })
  }, [])

  const flushQueue = React.useCallback(async () => {
    if (queuedMutations.length === 0) return

    const remaining: QueuedMutation[] = []
    for (const mutation of queuedMutations) {
      try {
        const mutationFn = queryClient.getMutationCache().find({
          mutationKey: mutation.mutationKey,
        })
        if (mutationFn && mutationFn.options?.mutationFn) {
          await mutationFn.options.mutationFn(mutation.variables)
        }
      } catch {
        if (mutation.retryCount < MAX_RETRIES) {
          remaining.push({ ...mutation, retryCount: mutation.retryCount + 1 })
        }
      }
    }
    setQueuedMutations(remaining)
  }, [queuedMutations, queryClient])

  const value: OfflineState = {
    isOnline,
    wasOffline,
    queuedMutations,
    queueMutation,
    flushQueue,
  }

  return <OfflineContext.Provider value={value}>{children}</OfflineContext.Provider>
}

export function useOffline() {
  const ctx = React.useContext(OfflineContext)
  if (!ctx) throw new Error('useOffline must be used within OfflineProvider')
  return ctx
}

/**
 * Hook to check if the app is currently online.
 */
export function useOnlineStatus(): boolean {
  const { isOnline } = useOffline()
  return isOnline
}

/**
 * Offline banner component state.
 */
export function useOfflineBanner() {
  const { isOnline, wasOffline, queuedMutations } = useOffline()
  return {
    showBanner: !isOnline,
    showReconnecting: wasOffline && isOnline && queuedMutations.length > 0,
    queuedCount: queuedMutations.length,
  }
}
