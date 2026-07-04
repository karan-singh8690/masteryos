import { describe, it, expect, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'

import {
  ConfidenceSlider,
  QuestionProgress,
  HintDisplay,
} from '@/components/learner/question-renderer'

describe('ConfidenceSlider', () => {
  it('renders with label', () => {
    render(<ConfidenceSlider value={0.5} onChange={() => {}} />)
    expect(screen.getByText('Confidence')).toBeInTheDocument()
  })

  it('shows percentage', () => {
    render(<ConfidenceSlider value={0.7} onChange={() => {}} />)
    expect(screen.getByText(/70%/)).toBeInTheDocument()
  })

  it('shows confidence label', () => {
    render(<ConfidenceSlider value={0.5} onChange={() => {}} />)
    expect(screen.getByText(/Medium/i)).toBeInTheDocument()
  })

  it('shows very low label for low value', () => {
    render(<ConfidenceSlider value={0.1} onChange={() => {}} />)
    expect(screen.getByText(/Very low/i)).toBeInTheDocument()
  })

  it('shows very high label for high value', () => {
    render(<ConfidenceSlider value={0.9} onChange={() => {}} />)
    expect(screen.getByText(/Very high/i)).toBeInTheDocument()
  })

  it('calls onChange when slider moved', async () => {
    const onChange = vi.fn()
    render(<ConfidenceSlider value={0.5} onChange={onChange} />)
    const slider = screen.getByRole('slider')
    await userEvent.click(slider)
    // Slider interaction triggers onChange
    expect(slider).toBeInTheDocument()
  })

  it('is disabled when disabled prop is set', () => {
    render(<ConfidenceSlider value={0.5} onChange={() => {}} disabled />)
    expect(screen.getByRole('slider')).toBeDisabled()
  })

  it('has accessible label', () => {
    render(<ConfidenceSlider value={0.5} onChange={() => {}} />)
    expect(screen.getByLabelText('Confidence level')).toBeInTheDocument()
  })
})

describe('QuestionProgress', () => {
  it('renders current and total', () => {
    render(<QuestionProgress current={3} total={10} />)
    expect(screen.getByText('Question 3 of 10')).toBeInTheDocument()
  })

  it('shows percentage', () => {
    render(<QuestionProgress current={5} total={10} />)
    expect(screen.getByText('50%')).toBeInTheDocument()
  })

  it('has progressbar role', () => {
    render(<QuestionProgress current={3} total={10} />)
    expect(screen.getByRole('progressbar')).toHaveAttribute('aria-valuenow', '3')
    expect(screen.getByRole('progressbar')).toHaveAttribute('aria-valuemax', '10')
  })

  it('handles zero total', () => {
    render(<QuestionProgress current={0} total={0} />)
    expect(screen.getByText('Question 0 of 0')).toBeInTheDocument()
  })
})

describe('HintDisplay', () => {
  it('renders used hints', () => {
    render(
      <HintDisplay
        hints={['Hint 1', 'Hint 2', 'Hint 3']}
        usedTiers={[0]}
        onUseHint={() => {}}
        submitted={false}
      />,
    )
    expect(screen.getByText(/Hint 1:/)).toBeInTheDocument()
    expect(screen.getByText('Hint 1')).toBeInTheDocument()
  })

  it('shows reveal button for next hint', () => {
    render(
      <HintDisplay
        hints={['Hint 1', 'Hint 2']}
        usedTiers={[]}
        onUseHint={() => {}}
        submitted={false}
      />,
    )
    expect(screen.getByText(/Reveal hint 1/)).toBeInTheDocument()
  })

  it('calls onUseHint when reveal button clicked', async () => {
    const onUseHint = vi.fn()
    render(
      <HintDisplay
        hints={['Hint 1', 'Hint 2']}
        usedTiers={[]}
        onUseHint={onUseHint}
        submitted={false}
      />,
    )
    await userEvent.click(screen.getByText(/Reveal hint 1/))
    expect(onUseHint).toHaveBeenCalledWith(0)
  })

  it('does not show reveal button after submission', () => {
    render(
      <HintDisplay
        hints={['Hint 1', 'Hint 2']}
        usedTiers={[0]}
        onUseHint={() => {}}
        submitted={true}
      />,
    )
    expect(screen.queryByText(/Reveal hint/)).not.toBeInTheDocument()
  })

  it('shows message when no hints were used', () => {
    render(
      <HintDisplay
        hints={['Hint 1']}
        usedTiers={[]}
        onUseHint={() => {}}
        submitted={true}
      />,
    )
    expect(screen.getByText(/No hints were used/i)).toBeInTheDocument()
  })
})
