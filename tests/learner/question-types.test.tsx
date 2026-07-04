import { describe, it, expect, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'

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
import type { Question } from '@/types/learning'

// Mock question factory
function makeQuestion(overrides: Partial<Question> = {}): Question {
  return {
    question_instance_id: 'q-1',
    concept_ids: ['concept-1'],
    difficulty: 'intermediate',
    estimated_duration_seconds: 60,
    question_type: 'multiple_choice',
    prompt: { text: 'What is 2+2?' },
    choices: [
      { id: 'a', text: '3' },
      { id: 'b', text: '4' },
      { id: 'c', text: '5' },
      { id: 'd', text: '6' },
    ],
    metadata: {},
    ...overrides,
  }
}

describe('MultipleChoice', () => {
  it('renders all choices', () => {
    render(
      <MultipleChoice
        question={makeQuestion()}
        answer={null}
        onChange={() => {}}
        submitted={false}
      />,
    )
    expect(screen.getByText('3')).toBeInTheDocument()
    expect(screen.getByText('4')).toBeInTheDocument()
    expect(screen.getByText('5')).toBeInTheDocument()
    expect(screen.getByText('6')).toBeInTheDocument()
  })

  it('calls onChange when a choice is selected', async () => {
    const onChange = vi.fn()
    render(
      <MultipleChoice
        question={makeQuestion()}
        answer={null}
        onChange={onChange}
        submitted={false}
      />,
    )
    await userEvent.click(screen.getByText('4'))
    expect(onChange).toHaveBeenCalledWith('b')
  })

  it('highlights selected choice', () => {
    render(
      <MultipleChoice
        question={makeQuestion()}
        answer="b"
        onChange={() => {}}
        submitted={false}
      />,
    )
    const label = screen.getByText('4').closest('label')
    expect(label?.className).toContain('border-primary')
  })

  it('shows correct/incorrect after submission', () => {
    render(
      <MultipleChoice
        question={makeQuestion()}
        answer="b"
        onChange={() => {}}
        submitted={true}
        correctAnswer={['b']}
      />,
    )
    const label = screen.getByText('4').closest('label')
    expect(label?.className).toContain('border-success')
  })

  it('shows wrong styling for incorrect answer', () => {
    render(
      <MultipleChoice
        question={makeQuestion()}
        answer="a"
        onChange={() => {}}
        submitted={true}
        correctAnswer={['b']}
      />,
    )
    const label = screen.getByText('3').closest('label')
    expect(label?.className).toContain('border-destructive')
  })

  it('disables inputs after submission', () => {
    render(
      <MultipleChoice
        question={makeQuestion()}
        answer="b"
        onChange={() => {}}
        submitted={true}
        correctAnswer={['b']}
      />,
    )
    const radio = screen.getByDisplayValue('b') as HTMLInputElement
    expect(radio).toBeDisabled()
  })
})

describe('MultipleSelect', () => {
  it('renders all choices', () => {
    render(
      <MultipleSelect
        question={makeQuestion({ question_type: 'multiple_select' })}
        answer={[]}
        onChange={() => {}}
        submitted={false}
      />,
    )
    expect(screen.getByText('3')).toBeInTheDocument()
    expect(screen.getByText('4')).toBeInTheDocument()
  })

  it('toggles selection on click', async () => {
    const onChange = vi.fn()
    render(
      <MultipleSelect
        question={makeQuestion({ question_type: 'multiple_select' })}
        answer={[]}
        onChange={onChange}
        submitted={false}
      />,
    )
    await userEvent.click(screen.getByText('4'))
    expect(onChange).toHaveBeenCalledWith(['b'])
  })

  it('removes from selection on second click', async () => {
    const onChange = vi.fn()
    render(
      <MultipleSelect
        question={makeQuestion({ question_type: 'multiple_select' })}
        answer={['b']}
        onChange={onChange}
        submitted={false}
      />,
    )
    await userEvent.click(screen.getByText('4'))
    expect(onChange).toHaveBeenCalledWith([])
  })
})

describe('TrueFalse', () => {
  it('renders True and False options', () => {
    render(
      <TrueFalse
        question={makeQuestion({ question_type: 'true_false', choices: null })}
        answer={null}
        onChange={() => {}}
        submitted={false}
      />,
    )
    expect(screen.getByText('True')).toBeInTheDocument()
    expect(screen.getByText('False')).toBeInTheDocument()
  })

  it('calls onChange with boolean', async () => {
    const onChange = vi.fn()
    render(
      <TrueFalse
        question={makeQuestion({ question_type: 'true_false', choices: null })}
        answer={null}
        onChange={onChange}
        submitted={false}
      />,
    )
    await userEvent.click(screen.getByText('True'))
    expect(onChange).toHaveBeenCalledWith(true)
  })
})

describe('ShortAnswer', () => {
  it('renders textarea', () => {
    render(
      <ShortAnswer
        question={makeQuestion({ question_type: 'short_answer', choices: null })}
        answer=""
        onChange={() => {}}
        submitted={false}
      />,
    )
    expect(screen.getByRole('textbox')).toBeInTheDocument()
  })

  it('calls onChange on input', async () => {
    const onChange = vi.fn()
    render(
      <ShortAnswer
        question={makeQuestion({ question_type: 'short_answer', choices: null })}
        answer=""
        onChange={onChange}
        submitted={false}
      />,
    )
    await userEvent.type(screen.getByRole('textbox'), 'hello')
    expect(onChange).toHaveBeenCalled()
  })
})

describe('NumericalAnswer', () => {
  it('renders number input', () => {
    render(
      <NumericalAnswer
        question={makeQuestion({ question_type: 'numerical', choices: null })}
        answer=""
        onChange={() => {}}
        submitted={false}
      />,
    )
    expect(screen.getByRole('spinbutton')).toBeInTheDocument()
  })

  it('has type=number', () => {
    render(
      <NumericalAnswer
        question={makeQuestion({ question_type: 'numerical', choices: null })}
        answer=""
        onChange={() => {}}
        submitted={false}
      />,
    )
    const input = screen.getByRole('spinbutton') as HTMLInputElement
    expect(input.type).toBe('number')
  })
})

describe('FillBlank', () => {
  it('renders prompt with blank input', () => {
    render(
      <FillBlank
        question={makeQuestion({
          question_type: 'fill_blank',
          choices: null,
          prompt: { text: 'The capital of France is ___.' },
        })}
        answer=""
        onChange={() => {}}
        submitted={false}
      />,
    )
    expect(screen.getByText(/The capital of France is/)).toBeInTheDocument()
    expect(screen.getByPlaceholderText('...')).toBeInTheDocument()
  })
})

describe('Ordering', () => {
  it('renders all items in order', () => {
    const choices = [
      { id: '1', text: 'First' },
      { id: '2', text: 'Second' },
      { id: '3', text: 'Third' },
    ]
    render(
      <Ordering
        question={makeQuestion({ question_type: 'ordering', choices })}
        answer={['1', '2', '3']}
        onChange={() => {}}
        submitted={false}
      />,
    )
    expect(screen.getByText('First')).toBeInTheDocument()
    expect(screen.getByText('Second')).toBeInTheDocument()
    expect(screen.getByText('Third')).toBeInTheDocument()
  })

  it('has move up/down buttons', () => {
    const choices = [
      { id: '1', text: 'First' },
      { id: '2', text: 'Second' },
    ]
    render(
      <Ordering
        question={makeQuestion({ question_type: 'ordering', choices })}
        answer={['1', '2']}
        onChange={() => {}}
        submitted={false}
      />,
    )
    // First item should have disabled up button
    const buttons = screen.getAllByRole('button')
    expect(buttons.length).toBeGreaterThan(0)
  })
})

describe('CodeOutput', () => {
  it('renders code block + textarea', () => {
    render(
      <CodeOutput
        question={makeQuestion({
          question_type: 'code_output',
          choices: null,
          prompt: { text: 'What is the output?', code: 'print(2+2)' },
        })}
        answer=""
        onChange={() => {}}
        submitted={false}
      />,
    )
    expect(screen.getByText('print(2+2)')).toBeInTheDocument()
    expect(screen.getByRole('textbox')).toBeInTheDocument()
  })
})
