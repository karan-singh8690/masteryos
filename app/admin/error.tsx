'use client'

import * as React from 'react'
import { AlertTriangle, RotateCcw } from 'lucide-react'
import { Button } from '@/components/ui/button'

export default function AdminError({
  error,
  reset,
}: {
  error: Error & { digest?: string }
  reset: () => void
}) {
  React.useEffect(() => {
    console.error('Admin route error:', error)
  }, [error])

  return (
    <div className="flex min-h-screen items-center justify-center bg-[#0A0A0B] p-6">
      <div className="max-w-md space-y-4 text-center">
        <div className="mx-auto flex h-12 w-12 items-center justify-center rounded-full bg-red-500/10">
          <AlertTriangle className="h-6 w-6 text-red-500" />
        </div>
        <h2 className="text-xl font-bold text-white">Admin Error</h2>
        <p className="text-sm text-zinc-400">
          {error.message || 'An unexpected error occurred in the admin panel.'}
        </p>
        <Button onClick={reset} className="gap-2 bg-emerald-500 text-white hover:bg-emerald-600">
          <RotateCcw className="h-4 w-4" />
          Try again
        </Button>
      </div>
    </div>
  )
}
