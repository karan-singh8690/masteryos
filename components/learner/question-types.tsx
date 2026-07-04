'use client'

import * as React from 'react'
import { Check, X, ChevronUp, ChevronDown } from 'lucide-react'

import { cn } from '@/lib/cn'
import { Button } from '@/components/ui/button'
import type { Question, QuestionChoice } from '@/types/learning'

// ============================================================
// Multiple Choice (single answer)
// ============================================================

interface MultipleChoiceProps {
  question: Question
  answer: string | null
  onChange: (answer: string) => void
  submitted: boolean
  correctAnswer?: string[]
}

export function MultipleChoice({
  question,
  answer,
  onChange,
  submitted,
  correctAnswer,
}: MultipleChoiceProps) {
  const choices = question.choices || []

  return (
    <fieldset className="space-y-3" aria-label="Answer choices">
      <legend className="sr-only">Select one answer</legend>
      {choices.map((choice) => {
        const isSelected = answer === choice.id
        const isCorrect = submitted && correctAnswer?.includes(choice.id)
        const isWrong = submitted && isSelected && !isCorrect

        return (
          <label
            key={choice.id}
            className={cn(
              'flex cursor-pointer items-start gap-3 rounded-lg border p-4 transition-colors',
              isSelected && !submitted && 'border-primary bg-primary/5',
              isCorrect && 'border-success bg-success/5',
              isWrong && 'border-destructive bg-destructive/5',
              !isSelected && !submitted && 'hover:bg-muted/50',
              submitted && 'cursor-default',
            )}
          >
            <input
              type="radio"
              name={`question-${question.question_instance_id}`}
              value={choice.id}
              checked={isSelected}
              disabled={submitted}
              onChange={() => onChange(choice.id)}
              className="mt-1 h-4 w-4 cursor-pointer accent-primary"
              aria-describedby={submitted ? `choice-${choice.id}-feedback` : undefined}
            />
            <div className="flex-1">
              <div className="text-sm">{choice.text}</div>
              {choice.code && (
                <pre className="mt-2 overflow-auto rounded-md bg-muted p-2 text-xs">
                  <code>{choice.code}</code>
                </pre>
              )}
            </div>
            {submitted && isCorrect && (
              <Check className="h-5 w-5 text-success" aria-hidden="true" />
            )}
            {submitted && isWrong && (
              <X className="h-5 w-5 text-destructive" aria-hidden="true" />
            )}
            {submitted && isCorrect && choice.explanation && (
              <span id={`choice-${choice.id}-feedback`} className="sr-only">
                Correct: {choice.explanation}
              </span>
            )}
          </label>
        )
      })}
    </fieldset>
  )
}

// ============================================================
// Multiple Select (multiple answers)
// ============================================================

interface MultipleSelectProps {
  question: Question
  answer: string[]
  onChange: (answer: string[]) => void
  submitted: boolean
  correctAnswer?: string[]
}

export function MultipleSelect({
  question,
  answer,
  onChange,
  submitted,
  correctAnswer,
}: MultipleSelectProps) {
  const choices = question.choices || []

  const toggle = (id: string) => {
    if (submitted) return
    if (answer.includes(id)) {
      onChange(answer.filter((a) => a !== id))
    } else {
      onChange([...answer, id])
    }
  }

  return (
    <fieldset className="space-y-3" aria-label="Select all correct answers">
      <legend className="sr-only">Select all that apply</legend>
      {choices.map((choice) => {
        const isSelected = answer.includes(choice.id)
        const isCorrect = submitted && correctAnswer?.includes(choice.id)
        const isWrong = submitted && isSelected && !isCorrect
        const shouldHaveBeenSelected = submitted && !isSelected && isCorrect

        return (
          <label
            key={choice.id}
            className={cn(
              'flex cursor-pointer items-start gap-3 rounded-lg border p-4 transition-colors',
              isSelected && !submitted && 'border-primary bg-primary/5',
              isCorrect && 'border-success bg-success/5',
              isWrong && 'border-destructive bg-destructive/5',
              shouldHaveBeenSelected && 'border-success/50 bg-success/5',
              !isSelected && !submitted && 'hover:bg-muted/50',
              submitted && 'cursor-default',
            )}
          >
            <input
              type="checkbox"
              checked={isSelected}
              disabled={submitted}
              onChange={() => toggle(choice.id)}
              className="mt-1 h-4 w-4 cursor-pointer accent-primary"
            />
            <div className="flex-1">
              <div className="text-sm">{choice.text}</div>
              {choice.code && (
                <pre className="mt-2 overflow-auto rounded-md bg-muted p-2 text-xs">
                  <code>{choice.code}</code>
                </pre>
              )}
            </div>
            {submitted && isCorrect && (
              <Check className="h-5 w-5 text-success" aria-hidden="true" />
            )}
            {submitted && isWrong && (
              <X className="h-5 w-5 text-destructive" aria-hidden="true" />
            )}
          </label>
        )
      })}
    </fieldset>
  )
}

// ============================================================
// True / False
// ============================================================

interface TrueFalseProps {
  question: Question
  answer: boolean | null
  onChange: (answer: boolean) => void
  submitted: boolean
  correctAnswer?: boolean
}

export function TrueFalse({
  question,
  answer,
  onChange,
  submitted,
  correctAnswer,
}: TrueFalseProps) {
  return (
    <fieldset className="space-y-3" aria-label="True or False">
      <legend className="sr-only">Select True or False</legend>
      {[
        { value: true, label: 'True' },
        { value: false, label: 'False' },
      ].map((option) => {
        const isSelected = answer === option.value
        const isCorrect = submitted && correctAnswer === option.value
        const isWrong = submitted && isSelected && !isCorrect

        return (
          <label
            key={String(option.value)}
            className={cn(
              'flex cursor-pointer items-center gap-3 rounded-lg border p-4 transition-colors',
              isSelected && !submitted && 'border-primary bg-primary/5',
              isCorrect && 'border-success bg-success/5',
              isWrong && 'border-destructive bg-destructive/5',
              !isSelected && !submitted && 'hover:bg-muted/50',
              submitted && 'cursor-default',
            )}
          >
            <input
              type="radio"
              name={`question-${question.question_instance_id}`}
              checked={isSelected}
              disabled={submitted}
              onChange={() => onChange(option.value)}
              className="h-4 w-4 cursor-pointer accent-primary"
            />
            <span className="text-sm font-medium">{option.label}</span>
            {submitted && isCorrect && (
              <Check className="ml-auto h-5 w-5 text-success" aria-hidden="true" />
            )}
            {submitted && isWrong && (
              <X className="ml-auto h-5 w-5 text-destructive" aria-hidden="true" />
            )}
          </label>
        )
      })}
    </fieldset>
  )
}

// ============================================================
// Short Answer (free text)
// ============================================================

interface ShortAnswerProps {
  question: Question
  answer: string
  onChange: (answer: string) => void
  submitted: boolean
}

export function ShortAnswer({
  question,
  answer,
  onChange,
  submitted,
}: ShortAnswerProps) {
  return (
    <textarea
      className="flex min-h-[120px] w-full rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-50"
      placeholder="Type your answer here..."
      value={answer}
      onChange={(e) => onChange(e.target.value)}
      disabled={submitted}
      aria-label="Your answer"
    />
  )
}

// ============================================================
// Numerical Answer
// ============================================================

interface NumericalProps {
  question: Question
  answer: string
  onChange: (answer: string) => void
  submitted: boolean
}

export function NumericalAnswer({
  question,
  answer,
  onChange,
  submitted,
}: NumericalProps) {
  return (
    <input
      type="number"
      className="flex h-12 w-full rounded-md border border-input bg-background px-3 py-2 text-lg ring-offset-background placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-50"
      placeholder="Enter a number"
      value={answer}
      onChange={(e) => onChange(e.target.value)}
      disabled={submitted}
      aria-label="Numerical answer"
      step="any"
    />
  )
}

// ============================================================
// Fill in the Blank
// ============================================================

interface FillBlankProps {
  question: Question
  answer: string
  onChange: (answer: string) => void
  submitted: boolean
}

export function FillBlank({
  question,
  answer,
  onChange,
  submitted,
}: FillBlankProps) {
  // The prompt text contains ___ for blanks
  const promptText = question.prompt.text
  const parts = promptText.split('___')

  return (
    <div className="flex flex-wrap items-center gap-2 rounded-lg border p-4">
      {parts.map((part, index) => (
        <React.Fragment key={index}>
          <span className="text-sm">{part}</span>
          {index < parts.length - 1 && (
            <input
              type="text"
              className="inline-flex h-9 min-w-[120px] rounded-md border border-input bg-background px-3 py-1 text-sm ring-offset-background focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-50"
              placeholder="..."
              value={index === 0 ? answer : ''}
              onChange={(e) => onChange(e.target.value)}
              disabled={submitted}
              aria-label={`Blank ${index + 1}`}
            />
          )}
        </React.Fragment>
      ))}
    </div>
  )
}

// ============================================================
// Ordering (drag-free — up/down buttons)
// ============================================================

interface OrderingProps {
  question: Question
  answer: string[]
  onChange: (answer: string[]) => void
  submitted: boolean
  correctAnswer?: string[]
}

export function Ordering({
  question,
  answer,
  onChange,
  submitted,
  correctAnswer,
}: OrderingProps) {
  const items = answer.length > 0
    ? answer
    : (question.choices || []).map((c) => c.id)

  const move = (index: number, direction: 'up' | 'down') => {
    if (submitted) return
    const newIndex = direction === 'up' ? index - 1 : index + 1
    if (newIndex < 0 || newIndex >= items.length) return
    const newItems = [...items]
    const [moved] = newItems.splice(index, 1)
    newItems.splice(newIndex, 0, moved!)
    onChange(newItems)
  }

  const choicesMap = new Map((question.choices || []).map((c) => [c.id, c.text]))

  return (
    <ol className="space-y-2" aria-label="Order the items">
      {items.map((id, index) => {
        const isCorrectPosition = submitted && correctAnswer?.[index] === id
        const isWrongPosition = submitted && correctAnswer?.[index] !== id

        return (
          <li
            key={id}
            className={cn(
              'flex items-center gap-3 rounded-lg border p-3',
              isCorrectPosition && 'border-success bg-success/5',
              isWrongPosition && 'border-destructive bg-destructive/5',
            )}
          >
            <span className="flex h-6 w-6 items-center justify-center rounded-full bg-muted text-xs font-medium">
              {index + 1}
            </span>
            <span className="flex-1 text-sm">{choicesMap.get(id)}</span>
            {!submitted && (
              <div className="flex flex-col">
                <Button
                  type="button"
                  variant="ghost"
                  size="icon"
                  className="h-6 w-6"
                  onClick={() => move(index, 'up')}
                  disabled={index === 0}
                  aria-label={`Move "${choicesMap.get(id)}" up`}
                >
                  <ChevronUp className="h-3 w-3" />
                </Button>
                <Button
                  type="button"
                  variant="ghost"
                  size="icon"
                  className="h-6 w-6"
                  onClick={() => move(index, 'down')}
                  disabled={index === items.length - 1}
                  aria-label={`Move "${choicesMap.get(id)}" down`}
                >
                  <ChevronDown className="h-3 w-3" />
                </Button>
              </div>
            )}
          </li>
        )
      })}
    </ol>
  )
}

// ============================================================
// Code Output
// ============================================================

interface CodeOutputProps {
  question: Question
  answer: string
  onChange: (answer: string) => void
  submitted: boolean
}

export function CodeOutput({
  question,
  answer,
  onChange,
  submitted,
}: CodeOutputProps) {
  return (
    <div className="space-y-3">
      {question.prompt.code && (
        <pre className="overflow-auto rounded-lg bg-muted p-4 text-sm">
          <code>{question.prompt.code}</code>
        </pre>
      )}
      <textarea
        className="flex min-h-[80px] w-full rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-50"
        placeholder="What is the output?"
        value={answer}
        onChange={(e) => onChange(e.target.value)}
        disabled={submitted}
        aria-label="Code output answer"
      />
    </div>
  )
}
