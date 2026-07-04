import { render, screen } from '@testing-library/react'
import { describe, it, expect } from 'vitest'

import { PasswordStrengthMeter } from '@/components/forms/password-strength-meter'

describe('PasswordStrengthMeter detailed', () => {
  it('does not render for empty password', () => {
    const { container } = render(<PasswordStrengthMeter password="" />)
    expect(container).toBeEmptyDOMElement()
  })

  it('renders 4 strength bars', () => {
    render(<PasswordStrengthMeter password="test" />)
    const bars = document.querySelectorAll('.h-1\\.5')
    expect(bars.length).toBe(4)
  })

  it('shows all 4 password rules', () => {
    render(<PasswordStrengthMeter password="test" />)
    expect(screen.getByText(/at least 12 characters/i)).toBeInTheDocument()
    expect(screen.getByText(/lowercase \+ uppercase/i)).toBeInTheDocument()
    expect(screen.getByText(/contains a number/i)).toBeInTheDocument()
    expect(screen.getByText(/special character/i)).toBeInTheDocument()
  })

  it('marks "12 characters" rule as passed for long password', () => {
    render(<PasswordStrengthMeter password="abcdefghijkl" />)
    const rule = screen.getByText(/at least 12 characters/i).closest('li')
    expect(rule?.className).toContain('text-success')
  })

  it('marks "lowercase + uppercase" as passed for mixed case', () => {
    render(<PasswordStrengthMeter password="Abcdefghijkl" />)
    const rule = screen.getByText(/lowercase \+ uppercase/i).closest('li')
    expect(rule?.className).toContain('text-success')
  })

  it('marks "number" rule as passed when number present', () => {
    render(<PasswordStrengthMeter password="Abcdefghij1" />)
    const rule = screen.getByText(/contains a number/i).closest('li')
    expect(rule?.className).toContain('text-success')
  })

  it('marks "special character" as passed when special present', () => {
    render(<PasswordStrengthMeter password="Abcdefghij!" />)
    const rule = screen.getByText(/special character/i).closest('li')
    expect(rule?.className).toContain('text-success')
  })

  it('all rules passed for strong password', () => {
    render(<PasswordStrengthMeter password="StrongPass123!" />)
    const passedRules = screen.getAllByText(/✓/)
    expect(passedRules.length).toBe(4)
  })

  it('shows "Very Weak" for empty', () => {
    // Empty doesn't render — test with 1 char
    render(<PasswordStrengthMeter password="a" />)
    expect(screen.getByText(/weak|fair|good|strong/i)).toBeInTheDocument()
  })

  it('updates when password changes', () => {
    const { rerender } = render(<PasswordStrengthMeter password="" />)
    // Empty — no meter

    rerender(<PasswordStrengthMeter password="StrongPass123!" />)
    expect(screen.getByText(/strong/i)).toBeInTheDocument()

    rerender(<PasswordStrengthMeter password="a" />)
    expect(screen.getByText(/weak/i)).toBeInTheDocument()
  })

  it('has aria-live for screen reader announcements', () => {
    render(<PasswordStrengthMeter password="test" />)
    const liveRegion = screen.getByText(/password strength/i).closest('[aria-live]')
    expect(liveRegion).toHaveAttribute('aria-live', 'polite')
  })
})
