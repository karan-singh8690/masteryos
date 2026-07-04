'use client'

import { AlertTriangle, RefreshCw, Home } from 'lucide-react'
import Link from 'next/link'

import { Button } from '@/components/ui/button'
import { ROUTES } from '@/lib/constants'

export default function GlobalError({
  error,
  reset,
}: {
  error: Error & { digest?: string }
  reset: () => void
}) {
  return (
    <div className="flex min-h-screen flex-col items-center justify-center gap-4 px-4 text-center">
      <div className="flex h-20 w-20 items-center justify-center rounded-full bg-destructive/10">
        <AlertTriangle className="h-10 w-10 text-destructive" aria-hidden="true" />
      </div>
      <div className="space-y-2">
        <h1 className="text-3xl font-bold">Something went wrong</h1>
        <p className="max-w-md text-muted-foreground">
          An unexpected error occurred. Our team has been notified.
        </p>
      </div>
      {process.env.NODE_ENV === 'development' && (
        <pre className="max-w-md overflow-auto rounded-md bg-muted p-4 text-left text-xs">
          {error.message}
          {error.digest && `\nDigest: ${error.digest}`}
        </pre>
      )}
      <div className="flex gap-2">
        <Button onClick={reset} leftIcon={<RefreshCw className="h-4 w-4" />}>
          Try again
        </Button>
        <Button asChild variant="outline" leftIcon={<Home className="h-4 w-4" />}>
          <Link href={ROUTES.HOME}>Home</Link>
        </Button>
      </div>
    </div>
  )
}
