'use client'

import * as React from 'react'

import { cn } from '@/lib/cn'
import type { Question } from '@/types/learning'
import {
  MultipleChoice,
  MultipleSelect,
  TrueFalse,
  ShortAnswer,
  NumericalAnswer,
  FillBlank,
  Ordering,
  CodeOutput,
} from '@/components/learner/question-types'

// ============================================================
// Question Renderer (dispatches by question_type)
// ============================================================

export interface QuestionRendererProps {
  question: Question
  answer: unknown
  onAnswerChange: (answer: unknown) => void
  submitted: boolean
  correctAnswer?: unknown
}

export function QuestionRenderer({
  question,
  answer,
  onAnswerChange,
  submitted,
  correctAnswer,
}: QuestionRendererProps) {
  switch (question.question_type) {
    case 'multiple_choice':
      return (
        <MultipleChoice
          question={question}
          answer={answer as string | null}
          onChange={onAnswerChange}
          submitted={submitted}
          correctAnswer={correctAnswer as string[] | undefined}
        />
      )

    case 'multiple_select':
      return (
        <MultipleSelect
          question={question}
          answer={answer as string[]}
          onChange={onAnswerChange}
          submitted={submitted}
          correctAnswer={correctAnswer as string[] | undefined}
        />
      )

    case 'true_false':
      return (
        <TrueFalse
          question={question}
          answer={answer as boolean | null}
          onChange={onAnswerChange}
          submitted={submitted}
          correctAnswer={correctAnswer as boolean | undefined}
        />
      )

    case 'short_answer':
      return (
        <ShortAnswer
          question={question}
          answer={answer as string}
          onChange={onAnswerChange}
          submitted={submitted}
        />
      )

    case 'numerical':
      return (
        <NumericalAnswer
          question={question}
          answer={answer as string}
          onChange={onAnswerChange}
          submitted={submitted}
        />
      )

    case 'fill_blank':
      return (
        <FillBlank
          question={question}
          answer={answer as string}
          onChange={onAnswerChange}
          submitted={submitted}
        />
      )

    case 'ordering':
      return (
        <Ordering
          question={question}
          answer={answer as string[]}
          onChange={onAnswerChange}
          submitted={submitted}
          correctAnswer={correctAnswer as string[] | undefined}
        />
      )

    case 'code_output':
      return (
        <CodeOutput
          question={question}
          answer={answer as string}
          onChange={onAnswerChange}
          submitted={submitted}
        />
      )

    default:
      return (
        <div className="rounded-lg border border-warning bg-warning/5 p-4 text-sm text-warning">
          Unknown question type: {question.question_type}. Using free-text fallback.
        </div>
      )
  }
}

// ============================================================
// Confidence Slider
// ============================================================

export interface ConfidenceSliderProps {
  value: number
  onChange: (value: number) => void
  disabled?: boolean
}

export function ConfidenceSlider({ value, onChange, disabled }: ConfidenceSliderProps) {
  const percentage = Math.round(value * 100)
  const label = getConfidenceLabel(value)

  return (
    <div className="space-y-2">
      <div className="flex items-center justify-between">
        <label htmlFor="confidence" className="text-sm font-medium">
          Confidence
        </label>
        <span
          className={cn(
            'text-sm font-medium',
            value < 0.4 && 'text-destructive',
            value >= 0.4 && value < 0.7 && 'text-warning',
            value >= 0.7 && 'text-success',
          )}
        >
          {percentage}% — {label}
        </span>
      </div>
      <input
        id="confidence"
        type="range"
        min="0"
        max="100"
        value={percentage}
        onChange={(e) => onChange(Number(e.target.value) / 100)}
        disabled={disabled}
        className="h-2 w-full cursor-pointer appearance-none rounded-full bg-muted accent-primary"
        aria-label="Confidence level"
        aria-valuetext={`${percentage}%, ${label}`}
      />
      <div className="flex justify-between text-xs text-muted-foreground">
        <span>Just guessing</span>
        <span>Very confident</span>
      </div>
    </div>
  )
}

function getConfidenceLabel(value: number): string {
  if (value < 0.2) return 'Very low'
  if (value < 0.4) return 'Low'
  if (value < 0.6) return 'Medium'
  if (value < 0.8) return 'High'
  return 'Very high'
}

// ============================================================
// Session Timer
// ============================================================

export interface SessionTimerProps {
  startedAt: number // Unix timestamp (ms)
  paused?: boolean
  onTick?: (elapsedSeconds: number) => void
}

export function SessionTimer({ startedAt, paused, onTick }: SessionTimerProps) {
  const [elapsed, setElapsed] = React.useState(0)

  React.useEffect(() => {
    if (paused) return

    const interval = setInterval(() => {
      const seconds = Math.floor((Date.now() - startedAt) / 1000)
      setElapsed(seconds)
      onTick?.(seconds)
    }, 1000)

    return () => clearInterval(interval)
  }, [startedAt, paused, onTick])

  const minutes = Math.floor(elapsed / 60)
  const seconds = elapsed % 60

  return (
    <div
      className="flex items-center gap-2 font-mono text-sm tabular-nums"
      aria-label={`Time elapsed: ${minutes} minutes ${seconds} seconds`}
      role="timer"
    >
      <span className="text-muted-foreground">⏱</span>
      <span>
        {String(minutes).padStart(2, '0')}:{String(seconds).padStart(2, '0')}
      </span>
    </div>
  )
}

// ============================================================
// Question Progress Bar
// ============================================================

export interface QuestionProgressProps {
  current: number
  total: number
}

export function QuestionProgress({ current, total }: QuestionProgressProps) {
  const percentage = total > 0 ? (current / total) * 100 : 0

  return (
    <div className="flex-1 space-y-1">
      <div className="flex items-center justify-between gap-3 text-sm">
        <span className="whitespace-nowrap font-medium">
          Question {current} of {total}
        </span>
        <span className="whitespace-nowrap text-muted-foreground">{Math.round(percentage)}%</span>
      </div>
      <div className="h-2 w-full overflow-hidden rounded-full bg-muted">
        <div
          className="h-full rounded-full bg-primary transition-all duration-300"
          style={{ width: `${percentage}%` }}
          role="progressbar"
          aria-valuenow={current}
          aria-valuemin={0}
          aria-valuemax={total}
        />
      </div>
    </div>
  )
}

// ============================================================
// Hint Display
// ============================================================

export interface HintDisplayProps {
  hints: string[]
  usedTiers: number[]
  onUseHint: (tier: number) => void
  submitted: boolean
}

export function HintDisplay({ hints, usedTiers, onUseHint, submitted }: HintDisplayProps) {
  const availableTier = hints.findIndex((_, i) => !usedTiers.includes(i))

  return (
    <div className="space-y-2">
      {usedTiers.map((tier, index) => (
        <div
          key={tier}
          className="rounded-lg border border-warning/50 bg-warning/5 p-3 text-sm"
          role="note"
        >
          <span className="font-medium text-warning">Hint {tier + 1}:</span>{' '}
          {hints[tier]}
        </div>
      ))}
      {!submitted && availableTier >= 0 && availableTier < hints.length && (
        <button
          type="button"
          onClick={() => onUseHint(availableTier)}
          className="text-sm text-warning hover:underline"
        >
          💡 Reveal hint {availableTier + 1} (reduces mastery gain)
        </button>
      )}
      {submitted && usedTiers.length === 0 && (
        <p className="text-xs text-muted-foreground">No hints were used.</p>
      )}
    </div>
  )
}
