'use client'

import * as React from 'react'
import {
  ChevronDown,
  ChevronRight,
  HeartHandshake,
  Mail,
  AlertCircle,
  Clock,
  Brain,
  CalendarOff,
  UserX,
  MailWarning,
  ThumbsDown,
} from 'lucide-react'
import { toast } from 'sonner'

import { useUserSuccess } from '@/hooks/use-beta-ops'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Skeleton } from '@/components/ui/skeleton'
import { ErrorState } from '@/components/ui/error-state'
import { EmptyState } from '@/components/ui/empty-state'
import { cn } from '@/lib/cn'
import { formatNumber, formatRelativeTime } from '@/lib/format'
import type { UserSuccessSignal } from '@/lib/beta-ops-api'

const SEVERITY_VARIANT: Record<string, 'destructive' | 'warning' | 'secondary' | 'default'> = {
  high: 'destructive',
  medium: 'warning',
  low: 'secondary',
}

const SEVERITY_ROW_COLOR: Record<string, string> = {
  high: 'border-l-destructive',
  medium: 'border-l-warning',
  low: 'border-l-primary',
}

interface SignalSectionConfig {
  key: string
  label: string
  description: string
  icon: React.ComponentType<{ className?: string }>
}

const SECTIONS: SignalSectionConfig[] = [
  {
    key: 'inactive_users',
    label: 'Inactive Users',
    description: 'Users with no platform activity in the past 30 days.',
    icon: UserX,
  },
  {
    key: 'at_risk_users',
    label: 'At-Risk Users',
    description: 'Users showing strong churn signals.',
    icon: AlertCircle,
  },
  {
    key: 'incomplete_onboarding',
    label: 'Incomplete Onboarding',
    description: 'Users who started but never finished onboarding.',
    icon: Clock,
  },
  {
    key: 'stuck_in_learning',
    label: 'Stuck in Learning',
    description: 'Users who have not progressed in their learning path.',
    icon: Brain,
  },
  {
    key: 'no_study_7_days',
    label: 'No Study in 7 Days',
    description: 'Users who have not started a study session this week.',
    icon: CalendarOff,
  },
  {
    key: 'failed_registration',
    label: 'Failed Registration',
    description: 'Users whose registration failed or stalled.',
    icon: AlertCircle,
  },
  {
    key: 'email_verification_pending',
    label: 'Email Verification Pending',
    description: 'Users who never confirmed their email address.',
    icon: MailWarning,
  },
  {
    key: 'recommendation_ignored',
    label: 'Recommendation Ignored',
    description: 'Users repeatedly dismissing adaptive recommendations.',
    icon: ThumbsDown,
  },
]

function SignalRow({ signal }: { signal: UserSuccessSignal }) {
  return (
    <tr
      className={cn(
        'border-l-4',
        SEVERITY_ROW_COLOR[signal.severity] ?? 'border-l-muted',
      )}
    >
      <td className="px-3 py-2 font-mono text-xs">{signal.email}</td>
      <td className="px-3 py-2">
        <Badge
          variant={SEVERITY_VARIANT[signal.severity] ?? 'secondary'}
          className="capitalize"
        >
          {signal.severity}
        </Badge>
      </td>
      <td className="px-3 py-2 text-sm text-muted-foreground">{signal.description}</td>
      <td className="px-3 py-2 text-xs text-muted-foreground">
        {signal.last_activity ? formatRelativeTime(signal.last_activity) : '—'}
      </td>
      <td className="px-3 py-2 text-sm">{signal.recommendation}</td>
      <td className="px-3 py-2 text-right">
        <Button
          size="sm"
          variant="outline"
          leftIcon={<Mail className="h-3 w-3" aria-hidden="true" />}
          onClick={() => toast.info('Re-engagement email coming soon')}
        >
          Re-engage
        </Button>
      </td>
    </tr>
  )
}

function SignalSection({
  config,
  signals,
}: {
  config: SignalSectionConfig
  signals: UserSuccessSignal[]
}) {
  const [open, setOpen] = React.useState(true)
  const Icon = config.icon
  const count = signals.length

  return (
    <Card>
      <CardHeader>
        <button
          type="button"
          onClick={() => setOpen((o) => !o)}
          className="flex w-full items-center justify-between text-left"
          aria-expanded={open}
          aria-controls={`section-${config.key}`}
        >
          <div className="flex items-center gap-3">
            <Icon className="h-4 w-4 text-muted-foreground" aria-hidden="true" />
            <div>
              <CardTitle className="text-base">{config.label}</CardTitle>
              <CardDescription>{config.description}</CardDescription>
            </div>
          </div>
          <div className="flex items-center gap-2">
            <Badge variant={count === 0 ? 'secondary' : 'warning'}>{count}</Badge>
            {open ? (
              <ChevronDown className="h-4 w-4 text-muted-foreground" aria-hidden="true" />
            ) : (
              <ChevronRight className="h-4 w-4 text-muted-foreground" aria-hidden="true" />
            )}
          </div>
        </button>
      </CardHeader>
      {open && (
        <CardContent id={`section-${config.key}`}>
          {count === 0 ? (
            <p className="py-4 text-center text-sm text-muted-foreground">
              No users in this category.
            </p>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-left text-sm">
                <thead>
                  <tr className="border-b text-xs uppercase tracking-wider text-muted-foreground">
                    <th scope="col" className="px-3 py-2 font-semibold">Email</th>
                    <th scope="col" className="px-3 py-2 font-semibold">Severity</th>
                    <th scope="col" className="px-3 py-2 font-semibold">Description</th>
                    <th scope="col" className="px-3 py-2 font-semibold">Last activity</th>
                    <th scope="col" className="px-3 py-2 font-semibold">Recommendation</th>
                    <th scope="col" className="px-3 py-2 text-right font-semibold">Action</th>
                  </tr>
                </thead>
                <tbody>
                  {signals.map((s) => (
                    <SignalRow key={`${s.user_id}-${s.signal_type}`} signal={s} />
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </CardContent>
      )}
    </Card>
  )
}

function SuccessSkeleton() {
  return (
    <div className="space-y-6" role="status" aria-label="Loading user success report">
      <Skeleton className="h-10 w-72" />
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        {Array.from({ length: 8 }).map((_, i) => (
          <Skeleton key={i} className="h-24 w-full" />
        ))}
      </div>
      {Array.from({ length: 4 }).map((_, i) => (
        <Skeleton key={i} className="h-40 w-full" />
      ))}
    </div>
  )
}

export default function UserSuccessPage() {
  const { data, isLoading, isError, error, refetch } = useUserSuccess()

  if (isLoading) return <SuccessSkeleton />
  if (isError || !data) {
    return (
      <ErrorState
        title="Failed to load user success report"
        description="We couldn't fetch the user success signals."
        error={error as Error | undefined}
        onRetry={() => refetch()}
      />
    )
  }

  const summary = data.summary ?? {}
  const signalsByKey: Record<string, UserSuccessSignal[]> = {
    inactive_users: data.inactive_users ?? [],
    at_risk_users: data.at_risk_users ?? [],
    incomplete_onboarding: data.incomplete_onboarding ?? [],
    stuck_in_learning: data.stuck_in_learning ?? [],
    no_study_7_days: data.no_study_7_days ?? [],
    failed_registration: data.failed_registration ?? [],
    email_verification_pending: data.email_verification_pending ?? [],
    recommendation_ignored: data.recommendation_ignored ?? [],
  }

  return (
    <div className="space-y-6">
      <header>
        <h1 className="flex items-center gap-2 text-2xl font-bold tracking-tight">
          <HeartHandshake className="h-6 w-6 text-primary" aria-hidden="true" />
          User Success Center
        </h1>
        <p className="text-sm text-muted-foreground">
          Proactive signals for at-risk and disengaged beta learners.
        </p>
      </header>

      <section
        aria-label="Summary"
        className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4"
      >
        <Card>
          <CardHeader className="pb-2">
            <CardDescription>Total users tracked</CardDescription>
            <CardTitle className="text-2xl">
              {formatNumber(summary.total_users ?? 0)}
            </CardTitle>
          </CardHeader>
        </Card>
        <Card>
          <CardHeader className="pb-2">
            <CardDescription>Inactive</CardDescription>
            <CardTitle className="text-2xl">
              {formatNumber(summary.inactive ?? (signalsByKey.inactive_users ?? []).length)}
            </CardTitle>
          </CardHeader>
        </Card>
        <Card>
          <CardHeader className="pb-2">
            <CardDescription>At risk</CardDescription>
            <CardTitle className="text-2xl text-destructive">
              {formatNumber(summary.at_risk ?? (signalsByKey.at_risk_users ?? []).length)}
            </CardTitle>
          </CardHeader>
        </Card>
        <Card>
          <CardHeader className="pb-2">
            <CardDescription>Incomplete onboarding</CardDescription>
            <CardTitle className="text-2xl text-warning">
              {formatNumber(
                summary.incomplete_onboarding ?? (signalsByKey.incomplete_onboarding ?? []).length,
              )}
            </CardTitle>
          </CardHeader>
        </Card>
        <Card>
          <CardHeader className="pb-2">
            <CardDescription>Stuck in learning</CardDescription>
            <CardTitle className="text-2xl">
              {formatNumber(summary.stuck_in_learning ?? (signalsByKey.stuck_in_learning ?? []).length)}
            </CardTitle>
          </CardHeader>
        </Card>
        <Card>
          <CardHeader className="pb-2">
            <CardDescription>No study in 7 days</CardDescription>
            <CardTitle className="text-2xl">
              {formatNumber(summary.no_study_7_days ?? (signalsByKey.no_study_7_days ?? []).length)}
            </CardTitle>
          </CardHeader>
        </Card>
        <Card>
          <CardHeader className="pb-2">
            <CardDescription>Email verification pending</CardDescription>
            <CardTitle className="text-2xl">
              {formatNumber(
                summary.email_verification_pending ??
                  (signalsByKey.email_verification_pending ?? []).length,
              )}
            </CardTitle>
          </CardHeader>
        </Card>
        <Card>
          <CardHeader className="pb-2">
            <CardDescription>Recommendation ignored</CardDescription>
            <CardTitle className="text-2xl">
              {formatNumber(
                summary.recommendation_ignored ??
                  (signalsByKey.recommendation_ignored ?? []).length,
              )}
            </CardTitle>
          </CardHeader>
        </Card>
      </section>

      <section aria-label="Signal sections" className="space-y-4">
        {SECTIONS.map((cfg) => (
          <SignalSection
            key={cfg.key}
            config={cfg}
            signals={signalsByKey[cfg.key] ?? []}
          />
        ))}
      </section>

      {SECTIONS.every((cfg) => (signalsByKey[cfg.key]?.length ?? 0) === 0) && (
        <EmptyState
          icon={HeartHandshake}
          title="No at-risk signals"
          description="Every beta learner appears healthy across all tracked signals."
        />
      )}
    </div>
  )
}
