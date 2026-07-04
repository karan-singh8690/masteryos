'use client'

import { WifiOff, RefreshCw } from 'lucide-react'

import { Button } from '@/components/ui/button'

export default function OfflinePage() {
  return (
    <div className="flex min-h-screen flex-col items-center justify-center gap-4 px-4 text-center">
      <div className="flex h-20 w-20 items-center justify-center rounded-full bg-muted">
        <WifiOff className="h-10 w-10 text-muted-foreground" aria-hidden="true" />
      </div>
      <div className="space-y-2">
        <h1 className="text-3xl font-bold">You&apos;re offline</h1>
        <p className="max-w-md text-muted-foreground">
          Please check your internet connection and try again.
        </p>
      </div>
      <Button
        variant="outline"
        leftIcon={<RefreshCw className="h-4 w-4" />}
        onClick={() => window.location.reload()}
      >
        Try again
      </Button>
    </div>
  )
}
