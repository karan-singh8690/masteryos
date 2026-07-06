'use client'

import * as React from 'react'
import { useParams, useRouter } from 'next/navigation'
import {
  GraduationCap,
  Lightbulb,
  CheckCircle2,
  XCircle,
  AlertCircle,
  ChevronRight,
  Pause,
  Play,
  X,
} from 'lucide-react'
import { toast } from 'sonner'

import { useAdaptiveQueue, useQuestion, useSubmitAnswer, useEndSession, useAbandonSession } from '@/hooks/use-learner'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { Alert, AlertDescription } from '@/components/ui/alert'
import { Progress } from '@/components/ui/progress'
import { Skeleton } from '@/components/ui/skeleton'
import { CenteredSpinner } from '@/components/ui/spinner'
import {
  QuestionRenderer,
  ConfidenceSlider,
  SessionTimer,
  QuestionProgress,
  HintDisplay,
} from '@/components/learner/question-renderer'
import { formatDuration } from '@/lib/format'
import { cn } from '@/lib/cn'
import type { SubmitAnswerResponse } from '@/types/learning'

export default function StudySessionPage() {
  const params = useParams()
  const router = useRouter()
  const sessionId = params.sessionId as string

  const { data: queue, isLoading: queueLoading } = useAdaptiveQueue(sessionId)
  const endSessionMutation = useEndSession()
  const abandonMutation = useAbandonSession()

  const [currentIndex, setCurrentIndex] = React.useState(0)
  const [answer, setAnswer] = React.useState<unknown>(null)
  const [confidence, setConfidence] = React.useState(0.5)
  const [submitted, setSubmitted] = React.useState(false)
  const [submitResult, setSubmitResult] = React.useState<SubmitAnswerResponse | null>(null)
  const [hintTiersUsed, setHintTiersUsed] = React.useState<number[]>([])
  const [startTime, setStartTime] = React.useState(Date.now())
  const [paused, setPaused] = React.useState(false)
  const [showConfirmAbandon, setShowConfirmAbandon] = React.useState(false)

  const currentItem = queue?.questions[currentIndex] || null
  const { data: question, isLoading: questionLoading } = useQuestion(
    currentItem?.question_instance_id || null,
  )

  // Reset state when moving to next question
  const goToNextQuestion = React.useCallback(() => {
    setCurrentIndex((prev) => prev + 1)
    setAnswer(null)
    setConfidence(0.5)
    setSubmitted(false)
    setSubmitResult(null)
    setHintTiersUsed([])
    setStartTime(Date.now())
  }, [])

  const submitMutation = useSubmitAnswer()

  const handleSubmit = async () => {
    if (!currentItem || !answer) return

    const timeSpent = Math.floor((Date.now() - startTime) / 1000)

    // Ensure answer is a dict (backend expects dict[str, Any], not string)
    const answerDict = typeof answer === 'string'
      ? { choice_id: answer }
      : answer as Record<string, unknown>

    try {
      const result = await submitMutation.mutateAsync({
        questionInstanceId: currentItem.question_instance_id,
        data: {
          answer: answerDict,
          answer_type: getAnswerType(question?.question_type || 'multiple_choice'),
          confidence,
          time_spent_seconds: timeSpent,
          hint_used: hintTiersUsed.length > 0,
          hint_tiers_used: hintTiersUsed,
        },
      })
      setSubmitResult(result)
      setSubmitted(true)
    } catch (err: any) {
      // Handle 409 QUESTION_ALREADY_ANSWERED — skip to next question
      const errData = err?.detail || err?.response?.data?.detail || {}
      if (errData.code === 'QUESTION_ALREADY_ANSWERED') {
        toast.info('This question was already answered. Moving to next…')
        // Auto-advance to next question
        if (queue && currentIndex < queue.questions.length - 1) {
          goToNextQuestion()
        } else {
          handleEndSession()
        }
      } else {
        toast.error(errData.message || 'Failed to submit answer. Please try again.')
      }
    }
  }

  const handleEndSession = async () => {
    try {
      await endSessionMutation.mutateAsync(sessionId)
      router.push(`/study/${sessionId}/summary`)
    } catch {
      toast.error('Failed to end session.')
    }
  }

  const handleAbandon = async () => {
    try {
      await abandonMutation.mutateAsync(sessionId)
      router.push('/dashboard')
    } catch {
      toast.error('Failed to abandon session.')
    }
  }

  // Keyboard shortcuts
  React.useEffect(() => {
    const handleKey = (e: KeyboardEvent) => {
      if (e.target instanceof HTMLInputElement || e.target instanceof HTMLTextAreaElement) return
      if (e.key === '1' || e.key === '2' || e.key === '3' || e.key === '4') {
        // Quick answer for multiple choice
        if (question?.choices && !submitted) {
          const index = parseInt(e.key) - 1
          const choice = question.choices[index]
          if (choice) setAnswer({ choice_id: choice.id })
        }
      } else if (e.key === 'Enter' && !submitted && answer) {
        handleSubmit()
      } else if (e.key === 'Enter' && submitted) {
        if (currentIndex < (queue?.questions.length || 0) - 1) {
          goToNextQuestion()
        } else {
          handleEndSession()
        }
      } else if (e.key === 'h' && !submitted) {
        // Use hint
        if (question?.metadata?.hint_tiers) {
          const nextTier = question.metadata.hint_tiers.findIndex(
            (_, i) => !hintTiersUsed.includes(i),
          )
          if (nextTier >= 0) setHintTiersUsed((prev) => [...prev, nextTier])
        }
      }
    }
    window.addEventListener('keydown', handleKey)
    return () => window.removeEventListener('keydown', handleKey)
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [question, submitted, answer, currentIndex, queue])

  if (queueLoading) {
    return <CenteredSpinner label="Loading adaptive queue..." />
  }

  if (!queue || queue.questions.length === 0) {
    return (
      <div className="mx-auto max-w-2xl">
        <Card>
          <CardContent className="pt-6 text-center">
            <p className="text-muted-foreground">No questions available in the queue.</p>
            <Button className="mt-4" onClick={() => router.push('/dashboard')}>
              Back to dashboard
            </Button>
          </CardContent>
        </Card>
      </div>
    )
  }

  // Session complete
  if (currentIndex >= queue.questions.length) {
    return (
      <div className="mx-auto max-w-2xl space-y-6">
        <Card>
          <CardContent className="pt-6 text-center">
            <div className="mx-auto flex h-16 w-16 items-center justify-center rounded-full bg-success/10">
              <CheckCircle2 className="h-8 w-8 text-success" aria-hidden="true" />
            </div>
            <h2 className="mt-4 text-2xl font-bold">Session complete!</h2>
            <p className="mt-1 text-sm text-muted-foreground">
              You answered all {queue.questions.length} questions.
            </p>
            <Button className="mt-6" size="lg" onClick={handleEndSession} loading={endSessionMutation.isPending}>
              View summary
            </Button>
          </CardContent>
        </Card>
      </div>
    )
  }

  return (
    <div className="mx-auto max-w-3xl space-y-6">
      {/* Session header */}
      <div className="flex items-center justify-between gap-4">
        <div className="flex items-center gap-4">
          <QuestionProgress current={currentIndex + 1} total={queue.questions.length} />
        </div>
        <div className="flex items-center gap-2">
          <SessionTimer startedAt={startTime} paused={paused} />
          <Button
            variant="ghost"
            size="icon"
            onClick={() => setPaused((p) => !p)}
            aria-label={paused ? 'Resume' : 'Pause'}
          >
            {paused ? <Play className="h-4 w-4" /> : <Pause className="h-4 w-4" />}
          </Button>
          <Button
            variant="ghost"
            size="icon"
            onClick={() => setShowConfirmAbandon(true)}
            aria-label="Abandon session"
          >
            <X className="h-4 w-4" />
          </Button>
        </div>
      </div>

      {/* Question card */}
      {questionLoading ? (
        <Skeleton className="h-96 w-full" />
      ) : question ? (
        <Card>
          <CardHeader>
            <div className="flex items-center justify-between">
              <Badge variant="outline" className="capitalize">
                {question.question_type.replace(/_/g, ' ')}
              </Badge>
              <Badge variant="secondary" className="capitalize">
                {question.difficulty}
              </Badge>
            </div>
            <CardTitle className="text-lg">
              {question.prompt.text}
            </CardTitle>
            {question.prompt.code && (
              <pre className="mt-2 overflow-auto rounded-md bg-muted p-4 text-sm">
                <code>{question.prompt.code}</code>
              </pre>
            )}
          </CardHeader>
          <CardContent className="space-y-6">
            {/* Answer area */}
            <QuestionRenderer
              question={question}
              answer={answer}
              onAnswerChange={setAnswer}
              submitted={submitted}
            />

            {/* Hints */}
            {question.metadata.hint_tiers && question.metadata.hint_tiers.length > 0 && !submitted && (
              <HintDisplay
                hints={question.metadata.hint_tiers as string[]}
                usedTiers={hintTiersUsed}
                onUseHint={(tier) => setHintTiersUsed((prev) => [...prev, tier])}
                submitted={submitted}
              />
            )}

            {/* Confidence slider */}
            {!submitted && (
              <ConfidenceSlider value={confidence} onChange={setConfidence} />
            )}

            {/* Submit button */}
            {!submitted ? (
              <Button
                className="w-full"
                size="lg"
                onClick={handleSubmit}
                loading={submitMutation.isPending}
                disabled={!answer || submitMutation.isPending}
              >
                Submit answer
              </Button>
            ) : (
              <SubmitResultDisplay result={submitResult} />
            )}

            {/* Next button */}
            {submitted && (
              <Button
                className="w-full"
                size="lg"
                onClick={() => {
                  if (currentIndex < queue.questions.length - 1) {
                    goToNextQuestion()
                  } else {
                    handleEndSession()
                  }
                }}
                rightIcon={<ChevronRight className="h-4 w-4" />}
              >
                {currentIndex < queue.questions.length - 1 ? 'Next question' : 'Finish session'}
              </Button>
            )}

            {/* Keyboard shortcuts hint */}
            {!submitted && (
              <p className="text-center text-xs text-muted-foreground">
                Press <kbd className="rounded border bg-muted px-1">Enter</kbd> to submit •{' '}
                <kbd className="rounded border bg-muted px-1">1-4</kbd> for quick answer •{' '}
                <kbd className="rounded border bg-muted px-1">H</kbd> for hint
              </p>
            )}
          </CardContent>
        </Card>
      ) : (
        <CenteredSpinner label="Loading question..." />
      )}

      {/* Abandon confirmation dialog */}
      {showConfirmAbandon && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/80 p-4" role="dialog" aria-modal="true">
          <Card className="max-w-md">
            <CardHeader>
              <CardTitle>Abandon session?</CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              <p className="text-sm text-muted-foreground">
                Your progress in this session will be lost. This cannot be undone.
              </p>
              <div className="flex justify-end gap-2">
                <Button variant="outline" onClick={() => setShowConfirmAbandon(false)}>
                  Cancel
                </Button>
                <Button variant="destructive" onClick={handleAbandon} loading={abandonMutation.isPending}>
                  Abandon session
                </Button>
              </div>
            </CardContent>
          </Card>
        </div>
      )}
    </div>
  )
}

// ============================================================
// Submit Result Display
// ============================================================

function SubmitResultDisplay({ result }: { result: SubmitAnswerResponse | null }) {
  if (!result) return null

  const { attempt, mastery, review, explanation, recommendation } = result
  const isCorrect = attempt.scoring_outcome === 'correct'
  const isPartial = attempt.scoring_outcome === 'partially_correct'

  return (
    <div className="space-y-4">
      {/* Result banner */}
      <div
        className={cn(
          'flex items-center gap-3 rounded-lg border p-4',
          isCorrect && 'border-success bg-success/5',
          isPartial && 'border-warning bg-warning/5',
          !isCorrect && !isPartial && 'border-destructive bg-destructive/5',
        )}
        role="status"
        aria-live="polite"
      >
        {isCorrect && <CheckCircle2 className="h-6 w-6 text-success" aria-hidden="true" />}
        {isPartial && <AlertCircle className="h-6 w-6 text-warning" aria-hidden="true" />}
        {!isCorrect && !isPartial && <XCircle className="h-6 w-6 text-destructive" aria-hidden="true" />}
        <div>
          <p className="font-medium">
            {isCorrect && 'Correct!'}
            {isPartial && `Partially correct (${Math.round((attempt.partial_credit || 0) * 100)}%)`}
            {!isCorrect && !isPartial && 'Incorrect'}
          </p>
          <p className="text-sm text-muted-foreground">
            Answered in {formatDuration(attempt.time_to_answer_ms / 1000)}
          </p>
        </div>
      </div>

      {/* Explanation */}
      <div className="rounded-lg border p-4">
        <h4 className="mb-2 flex items-center gap-2 text-sm font-medium">
          <Lightbulb className="h-4 w-4 text-primary" aria-hidden="true" />
          Explanation
        </h4>
        <p className="text-sm text-muted-foreground">{explanation.content}</p>
      </div>

      {/* Mastery update */}
      {mastery && (
        <div className="grid grid-cols-2 gap-4">
          <div className="rounded-lg border p-3">
            <p className="text-xs text-muted-foreground">Mastery score</p>
            <p className="text-lg font-bold">
              {Math.round(mastery.mastery_score_combined * 100)}%
            </p>
            <p className="text-xs capitalize text-muted-foreground">
              {mastery.concept_state.replace(/_/g, ' ')}
            </p>
          </div>
          <div className="rounded-lg border p-3">
            <p className="text-xs text-muted-foreground">Evidence count</p>
            <p className="text-lg font-bold">{mastery.evidence_count}</p>
            <p className="text-xs text-muted-foreground">attempts</p>
          </div>
        </div>
      )}

      {/* Review schedule */}
      {review && (
        <Alert>
          <AlertCircle className="h-4 w-4" />
          <AlertDescription>
            Next review scheduled in {review.interval_days} days ({review.priority} priority)
          </AlertDescription>
        </Alert>
      )}

      {/* Recommendation */}
      {recommendation && (
        <div className="rounded-lg border border-primary/50 bg-primary/5 p-3">
          <p className="text-sm">
            <span className="font-medium">Recommendation:</span> {recommendation.reason}
          </p>
        </div>
      )}
    </div>
  )
}

function getAnswerType(questionType: string): 'multiple_choice' | 'code' | 'free_response' {
  if (questionType === 'code_output') return 'code'
  if (questionType === 'short_answer' || questionType === 'fill_blank' || questionType === 'numerical') return 'free_response'
  return 'multiple_choice'
}
