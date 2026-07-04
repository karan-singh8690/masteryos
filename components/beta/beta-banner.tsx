'use client'

import * as React from 'react'
import { FlaskConical, Bug } from 'lucide-react'

import { cn } from '@/lib/cn'

interface BetaBannerProps {
  className?: string
}

export function BetaBanner({ className }: BetaBannerProps) {
  return (
    <div
      className={cn(
        'flex items-center justify-center gap-2 bg-primary/10 px-4 py-1.5 text-center text-xs text-primary',
        className,
      )}
      role="banner"
      aria-label="Closed beta notification"
    >
      <FlaskConical className="h-3.5 w-3.5" aria-hidden="true" />
      <span>
        <strong>Closed Beta</strong> · v1.0.0 · {process.env.NODE_ENV}
      </span>
    </div>
  )
}
