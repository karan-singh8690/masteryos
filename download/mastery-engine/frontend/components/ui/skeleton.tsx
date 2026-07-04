'use client'

import { cn } from '@/lib/cn'

export interface SkeletonProps extends React.HTMLAttributes<HTMLDivElement> {
  shimmer?: boolean
}

export function Skeleton({ className, shimmer = true, ...props }: SkeletonProps) {
  return (
    <div
      className={cn(
        'rounded-md bg-muted',
        shimmer && 'shimmer',
        className,
      )}
      aria-hidden="true"
      {...props}
    />
  )
}

export function SkeletonText({
  lines = 3,
  className,
  lineClassName,
}: {
  lines?: number
  className?: string
  lineClassName?: string
}) {
  return (
    <div className={cn('space-y-2', className)} aria-hidden="true">
      {Array.from({ length: lines }).map((_, i) => (
        <Skeleton
          key={i}
          className={cn('h-4', i === lines - 1 ? 'w-2/3' : 'w-full', lineClassName)}
        />
      ))}
    </div>
  )
}

export function SkeletonCard() {
  return (
    <div className="rounded-lg border p-6" aria-hidden="true">
      <Skeleton className="mb-4 h-6 w-1/3" />
      <SkeletonText lines={3} />
    </div>
  )
}
