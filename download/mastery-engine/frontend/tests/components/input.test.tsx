import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, it, expect } from 'vitest'

import { Input, PasswordInput } from '@/components/ui/input'

describe('Input', () => {
  it('renders with placeholder', () => {
    render(<Input placeholder="Enter text" />)
    expect(screen.getByPlaceholderText('Enter text')).toBeInTheDocument()
  })

  it('renders with left icon', () => {
    render(
      <Input
        placeholder="Email"
        leftIcon={<span data-testid="icon">@</span>}
      />,
    )
    expect(screen.getByTestId('icon')).toBeInTheDocument()
  })

  it('passes through input attributes', () => {
    render(
      <Input
        type="email"
        name="email"
        id="email"
        required
        aria-label="Email"
      />,
    )
    const input = screen.getByLabelText('Email')
    expect(input).toHaveAttribute('type', 'email')
    expect(input).toHaveAttribute('name', 'email')
    expect(input).toBeRequired()
  })

  it('shows error styles when hasError is true', () => {
    render(<Input hasError aria-label="test" />)
    const input = screen.getByLabelText('test')
    expect(input.className).toContain('border-destructive')
  })

  it('forwards ref', () => {
    const ref = vi.fn()
    render(<Input ref={ref} aria-label="test" />)
    expect(ref).toHaveBeenCalled()
  })

  it('handles user input', async () => {
    render(<Input aria-label="test" />)
    const input = screen.getByLabelText('test') as HTMLInputElement
    await userEvent.type(input, 'hello')
    expect(input.value).toBe('hello')
  })

  it('is disabled when disabled prop is set', () => {
    render(<Input disabled aria-label="test" />)
    expect(screen.getByLabelText('test')).toBeDisabled()
  })
})

describe('PasswordInput', () => {
  it('renders as password type by default', () => {
    render(<PasswordInput aria-label="password" />)
    expect(screen.getByLabelText('password')).toHaveAttribute('type', 'password')
  })

  it('toggles password visibility', async () => {
    render(<PasswordInput aria-label="password" />)
    const input = screen.getByLabelText('password') as HTMLInputElement
    const toggle = screen.getByRole('button', { name: /show password/i })

    expect(input.type).toBe('password')

    await userEvent.click(toggle)
    expect(input.type).toBe('text')

    await userEvent.click(toggle)
    expect(input.type).toBe('password')
  })

  it('has accessible label for toggle button', () => {
    render(<PasswordInput aria-label="password" />)
    expect(screen.getByRole('button', { name: /show password/i })).toBeInTheDocument()
  })

  it('hides toggle when showToggle is false', () => {
    render(<PasswordInput showToggle={false} aria-label="password" />)
    expect(screen.queryByRole('button', { name: /password/i })).not.toBeInTheDocument()
  })
})
