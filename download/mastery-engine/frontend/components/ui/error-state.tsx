'use client'

import * as React from 'react'
import { AlertTriangle, RefreshCw } from 'lucide-react'

import { cn } from '@/lib/cn'
import { Button } from '@/components/ui/button'

export interface ErrorStateProps {
  title?: string
  description?: string
  error?: Error
  onRetry?: () => void
  className?: string
}

export function ErrorState({
  title = 'Something went wrong',
  description = 'An unexpected error occurred. Please try again.',
  error,
  onRetry,
  className,
}: ErrorStateProps) {
  return (
    <div
      className={cn(
        'flex flex-col items-center justify-center gap-4 py-12 text-center',
        className,
      )}
      role="alert"
    >
      <div className="rounded-full bg-destructive/10 p-4">
        <AlertTriangle
          className="h-8 w-8 text-destructive"
          aria-hidden="true"
        />
      </div>
      <div className="space-y-1">
        <h3 className="text-lg font-semibold">{title}</h3>
        <p className="max-w-md text-sm text-muted-foreground">{description}</p>
        {error && process.env.NODE_ENV === 'development' && (
          <pre className="mt-2 max-w-md overflow-auto rounded-md bg-muted p-2 text-left text-xs text-muted-foreground">
            {error.message}
          </pre>
        )}
      </div>
      {onRetry && (
        <Button onClick={onRetry} size="sm" variant="outline" leftIcon={<RefreshCw className="h-4 w-4" />}>
          Try again
        </Button>
      )}
    </div>
  )
}
