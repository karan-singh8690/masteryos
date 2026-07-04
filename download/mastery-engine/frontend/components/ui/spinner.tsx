'use client'

import * as React from 'react'
import { Loader2 } from 'lucide-react'

import { cn } from '@/lib/cn'

export interface SpinnerProps extends React.HTMLAttributes<SVGSVGElement> {
  size?: 'xs' | 'sm' | 'md' | 'lg' | 'xl'
  label?: string
}

const sizeMap = {
  xs: 'h-3 w-3',
  sm: 'h-4 w-4',
  md: 'h-6 w-6',
  lg: 'h-8 w-8',
  xl: 'h-12 w-12',
}

export function Spinner({ size = 'md', label, className, ...props }: SpinnerProps) {
  return (
    <Loader2
      className={cn('animate-spin text-muted-foreground', sizeMap[size], className)}
      role="status"
      aria-label={label || 'Loading'}
      {...props}
    />
  )
}

export function FullPageSpinner({ label }: { label?: string }) {
  return (
    <div
      className="flex min-h-screen flex-col items-center justify-center gap-4"
      role="status"
      aria-live="polite"
    >
      <Spinner size="xl" />
      {label && <p className="text-muted-foreground">{label}</p>}
    </div>
  )
}

export function CenteredSpinner({ label }: { label?: string }) {
  return (
    <div
      className="flex flex-col items-center justify-center gap-2 py-8"
      role="status"
      aria-live="polite"
    >
      <Spinner size="lg" />
      {label && <p className="text-sm text-muted-foreground">{label}</p>}
    </div>
  )
}
