'use client'

import * as React from 'react'
import { useRouter, useSearchParams } from 'next/navigation'
import { GraduationCap, Clock, Target } from 'lucide-react'
import { toast } from 'sonner'

import { useEnrollments, useStartStudySession } from '@/hooks/use-learner'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { RadioGroup, RadioGroupItem } from '@/components/ui/radio-group'
import { Label } from '@/components/ui/label'
import { Skeleton } from '@/components/ui/skeleton'
import { EmptyState } from '@/components/ui/empty-state'
import { cn } from '@/lib/cn'

const SESSION_INTENTS = [
  {
    value: 'mixed' as const,
    label: 'Mixed practice',
    description: 'A balanced mix of new concepts and reviews',
    icon: Target,
  },
  {
    value: 'review' as const,
    label: 'Review session',
    description: 'Focus on due reviews and spaced repetition',
    icon: Clock,
  },
  {
    value: 'diagnostic' as const,
    label: 'Learn new concepts',
    description: 'Focus on concepts you haven\'t seen yet',
    icon: GraduationCap,
  },
  {
    value: 'drill' as const,
    label: 'Practice weak areas',
    description: 'Focus on your weakest concepts',
    icon: Target,
  },
]

const QUESTION_COUNTS = [5, 10, 15, 20]

export default function StartSessionPage() {
  const router = useRouter()
  const searchParams = useSearchParams()
  const enrollmentIdParam = searchParams.get('enrollment')

  const { data: enrollments, isLoading } = useEnrollments()
  const startMutation = useStartStudySession()

  const [selectedEnrollment, setSelectedEnrollment] = React.useState(enrollmentIdParam || '')
  const [intent, setIntent] = React.useState<'drill' | 'review' | 'diagnostic' | 'mixed'>('mixed')
  const [questionCount, setQuestionCount] = React.useState(10)

  React.useEffect(() => {
    if (enrollments && enrollments.length > 0 && !selectedEnrollment) {
      // Accept both 'active' and 'pending_onboarding' as valid for starting
      const active = enrollments.find(
        (e) => e.status === 'active' || e.status === 'pending_onboarding',
      )
      if (active) setSelectedEnrollment(active.id)
    }
  }, [enrollments, selectedEnrollment])

  const activeEnrollments = (enrollments || []).filter(
    (e) => e.status === 'active' || e.status === 'pending_onboarding',
  )

  const handleStart = async () => {
    if (!selectedEnrollment) {
      toast.error('Please select an enrollment')
      return
    }
    const intentValue = intent as 'drill' | 'review' | 'diagnostic' | 'mixed'
    try {
      const session = await startMutation.mutateAsync({
        enrollment_id: selectedEnrollment,
        intent: intentValue,
        target_question_count: questionCount,
      })
      toast.success('Study session started!')
      router.push(`/study/${session.id}`)
    } catch (err: any) {
      // Handle 409 ACTIVE_SESSION_EXISTS — resume or force-start
      // ApiError stores the full detail object in err.detail
      const errData = err?.detail || err?.response?.data?.detail || {}
      if (errData.code === 'ACTIVE_SESSION_EXISTS') {
        const existingId = errData.existing_session_id
        if (existingId) {
          // Resume the existing session
          toast.info('You have an active session. Resuming…')
          router.push(`/study/${existingId}`)
          return
        }

        // No session ID in response — try to fetch the active session
        try {
          const token = localStorage.getItem('mastery.access_token')
          const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'
          const res = await fetch(
            `${API_URL}/api/v1/study-sessions/active?enrollment_id=${selectedEnrollment}`,
            { headers: { Authorization: `Bearer ${token}` } },
          )
          if (res.ok) {
            const activeSession = await res.json()
            if (activeSession?.id) {
              toast.info('Resuming your active session…')
              router.push(`/study/${activeSession.id}`)
              return
            }
          }
        } catch {
          // ignore
        }

        // Still can't find the session — retry with force=true to clear stale session
        try {
          toast.info('Clearing stale session and starting fresh…')
          const token = localStorage.getItem('mastery.access_token')
          const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'
          const res = await fetch(
            `${API_URL}/api/v1/study-sessions?force=true`,
            {
              method: 'POST',
              headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${token}` },
              body: JSON.stringify({
                enrollment_id: selectedEnrollment,
                intent: intentValue,
                target_question_count: questionCount,
              }),
            },
          )
          if (res.ok) {
            const session = await res.json()
            if (session?.id) {
              toast.success('Study session started!')
              router.push(`/study/${session.id}`)
              return
            }
          }
        } catch {
          // ignore
        }
        toast.error('Unable to start session. Please try again.')
      } else {
        toast.error(errData.message || 'Failed to start session. Please try again.')
      }
    }
  }

  if (isLoading) {
    return (
      <div className="max-w-2xl space-y-6">
        <Skeleton className="h-8 w-48" />
        <Skeleton className="h-64 w-full" />
        <Skeleton className="h-48 w-full" />
      </div>
    )
  }

  if (!activeEnrollments || activeEnrollments.length === 0) {
    return (
      <div className="max-w-2xl">
        <EmptyState
          icon={GraduationCap}
          title="No active enrollments"
          description="Enroll in a subject to start studying."
          action={{ label: 'Browse subjects', onClick: () => router.push('/subjects') }}
        />
      </div>
    )
  }

  return (
    <div className="max-w-2xl space-y-6">
      <div>
        <h1 className="text-2xl font-bold tracking-tight">Start a study session</h1>
        <p className="text-sm text-muted-foreground">Choose what to study and how many questions</p>
      </div>

      {/* Enrollment selection */}
      {activeEnrollments.length > 1 && (
        <Card>
          <CardHeader>
            <CardTitle className="text-base">Select subject</CardTitle>
          </CardHeader>
          <CardContent>
            <RadioGroup
              value={selectedEnrollment}
              onValueChange={setSelectedEnrollment}
              className="space-y-2"
            >
              {activeEnrollments.map((enrollment) => (
                <div key={enrollment.id} className="flex items-center gap-2">
                  <RadioGroupItem value={enrollment.id} id={enrollment.id} />
                  <Label htmlFor={enrollment.id} className="flex-1 cursor-pointer">
                    <div className="flex items-center justify-between">
                      <span>{enrollment.subject_name}</span>
                      <span className="text-xs text-muted-foreground">
                        {Math.round(enrollment.mastery_score * 100)}% mastery
                      </span>
                    </div>
                  </Label>
                </div>
              ))}
            </RadioGroup>
          </CardContent>
        </Card>
      )}

      {/* Session intent */}
      <Card>
        <CardHeader>
          <CardTitle className="text-base">What do you want to focus on?</CardTitle>
        </CardHeader>
        <CardContent className="space-y-2">
          {SESSION_INTENTS.map((option) => {
            const Icon = option.icon
            return (
              <label
                key={option.value}
                className={cn(
                  'flex cursor-pointer items-start gap-3 rounded-lg border p-4 transition-colors',
                  intent === option.value
                    ? 'border-primary bg-primary/5'
                    : 'hover:bg-muted/50',
                )}
              >
                <input
                  type="radio"
                  name="intent"
                  value={option.value}
                  checked={intent === option.value}
                  onChange={() => setIntent(option.value)}
                  className="mt-1 h-4 w-4 cursor-pointer accent-primary"
                />
                <div className="flex-1">
                  <div className="flex items-center gap-2">
                    <Icon className="h-4 w-4 text-primary" aria-hidden="true" />
                    <span className="text-sm font-medium">{option.label}</span>
                  </div>
                  <p className="mt-1 text-xs text-muted-foreground">{option.description}</p>
                </div>
              </label>
            )
          })}
        </CardContent>
      </Card>

      {/* Question count */}
      <Card>
        <CardHeader>
          <CardTitle className="text-base">How many questions?</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-4 gap-2">
            {QUESTION_COUNTS.map((count) => (
              <button
                key={count}
                type="button"
                onClick={() => setQuestionCount(count)}
                className={cn(
                  'rounded-lg border p-4 text-center transition-colors',
                  questionCount === count
                    ? 'border-primary bg-primary/5'
                    : 'hover:bg-muted/50',
                )}
                aria-pressed={questionCount === count}
              >
                <span className="text-2xl font-bold">{count}</span>
                <span className="block text-xs text-muted-foreground">questions</span>
              </button>
            ))}
          </div>
        </CardContent>
      </Card>

      <Button
        className="w-full"
        size="lg"
        onClick={handleStart}
        loading={startMutation.isPending}
        disabled={startMutation.isPending || !selectedEnrollment}
      >
        Start session
      </Button>
    </div>
  )
}
