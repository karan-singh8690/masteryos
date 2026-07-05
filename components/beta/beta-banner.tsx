'use client'

import * as React from 'react'
import { FlaskConical, Bug, Rocket, Lock, Sparkles } from 'lucide-react'

import { cn } from '@/lib/cn'

interface BetaBannerProps {
  className?: string
}

interface BetaStatus {
  beta_mode: string
  is_open_beta: boolean
  is_closed_beta: boolean
  welcome_message: string | null
}

export function BetaBanner({ className }: BetaBannerProps) {
  const [status, setStatus] = React.useState<BetaStatus | null>(null)

  React.useEffect(() => {
    let cancelled = false
    const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'
    fetch(`${API_URL}/api/v1/beta/status`)
      .then((r) => (r.ok ? r.json() : null))
      .then((data) => {
        if (!cancelled && data) setStatus(data)
      })
      .catch(() => {
        // Silent fail — banner just won't show
      })
    return () => {
      cancelled = true
    }
  }, [])

  // Don't render anything if beta is off (production mode)
  if (!status || status.beta_mode === 'off') {
    return null
  }

  const isOpen = status.is_open_beta
  const Icon = isOpen ? Rocket : FlaskConical
  const label = isOpen ? 'Open Beta' : 'Closed Beta'
  const message = status.welcome_message || `You're using the ${label.toLowerCase()}. Thanks for testing!`

  return (
    <div
      className={cn(
        'flex items-center justify-center gap-2 px-4 py-2 text-center text-xs',
        isOpen
          ? 'bg-emerald-500/10 text-emerald-700 dark:text-emerald-400'
          : 'bg-amber-500/10 text-amber-700 dark:text-amber-400',
        className,
      )}
      role="banner"
      aria-label={`${label} notification`}
    >
      <Icon className="h-3.5 w-3.5 shrink-0" aria-hidden="true" />
      <span className="truncate">
        <strong>{label}</strong> · {message}
      </span>
      {isOpen && (
        <a
          href="/beta/feedback"
          className="ml-2 inline-flex items-center gap-1 rounded-full bg-emerald-500/20 px-2 py-0.5 font-medium text-emerald-700 transition-colors hover:bg-emerald-500/30 dark:text-emerald-300"
        >
          <Bug className="h-3 w-3" aria-hidden="true" />
          Feedback
        </a>
      )}
    </div>
  )
}
