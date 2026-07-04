'use client'

import { WifiOff, RefreshCw, CloudUpload } from 'lucide-react'

import { useOfflineBanner } from '@/lib/offline/offline-provider'
import { cn } from '@/lib/cn'

export function OfflineBanner() {
  const { showBanner, showReconnecting, queuedCount } = useOfflineBanner()

  if (!showBanner && !showReconnecting) return null

  return (
    <div
      role="alert"
      aria-live="polite"
      className={cn(
        'fixed bottom-4 left-1/2 z-50 -translate-x-1/2 rounded-lg border px-4 py-3 shadow-lg',
        showBanner
          ? 'border-destructive bg-destructive text-destructive-foreground'
          : 'border-success bg-success text-success-foreground',
      )}
    >
      {showBanner ? (
        <div className="flex items-center gap-2 text-sm">
          <WifiOff className="h-4 w-4" aria-hidden="true" />
          <span>You&apos;re offline. Changes will be synced when you reconnect.</span>
        </div>
      ) : (
        <div className="flex items-center gap-2 text-sm">
          <CloudUpload className="h-4 w-4 animate-pulse" aria-hidden="true" />
          <span>Reconnecting... Syncing {queuedCount} queued action{queuedCount !== 1 ? 's' : ''}.</span>
          <RefreshCw className="h-3 w-3 animate-spin" aria-hidden="true" />
        </div>
      )}
    </div>
  )
}
