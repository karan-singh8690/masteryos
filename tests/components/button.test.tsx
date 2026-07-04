import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, it, expect, vi } from 'vitest'

import { Button } from '@/components/ui/button'
import { Mail } from 'lucide-react'

describe('Button', () => {
  it('renders children', () => {
    render(<Button>Click me</Button>)
    expect(screen.getByRole('button', { name: /click me/i })).toBeInTheDocument()
  })

  it('handles click events', async () => {
    const onClick = vi.fn()
    render(<Button onClick={onClick}>Click</Button>)
    await userEvent.click(screen.getByRole('button'))
    expect(onClick).toHaveBeenCalledTimes(1)
  })

  it('shows loading spinner when loading', () => {
    render(<Button loading>Loading</Button>)
    expect(screen.getByRole('button')).toHaveAttribute('aria-busy', 'true')
    expect(screen.getByRole('button')).toBeDisabled()
  })

  it('is disabled when disabled prop is set', () => {
    render(<Button disabled>Disabled</Button>)
    expect(screen.getByRole('button')).toBeDisabled()
  })

  it('renders left icon', () => {
    render(<Button leftIcon={<Mail data-testid="icon" />}>With Icon</Button>)
    expect(screen.getByTestId('icon')).toBeInTheDocument()
  })

  it('renders right icon', () => {
    render(<Button rightIcon={<Mail data-testid="icon" />}>With Icon</Button>)
    expect(screen.getByTestId('icon')).toBeInTheDocument()
  })

  it('applies variant classes', () => {
    render(<Button variant="destructive">Delete</Button>)
    const button = screen.getByRole('button')
    expect(button.className).toContain('bg-destructive')
  })

  it('applies size classes', () => {
    render(<Button size="lg">Large</Button>)
    const button = screen.getByRole('button')
    expect(button.className).toContain('h-11')
  })

  it('renders as child when asChild is true', () => {
    render(
      <Button asChild>
        <a href="/test">Link Button</a>
      </Button>,
    )
    const link = screen.getByRole('link', { name: /link button/i })
    expect(link).toHaveAttribute('href', '/test')
  })

  it('does not fire onClick when disabled', async () => {
    const onClick = vi.fn()
    render(
      <Button disabled onClick={onClick}>
        Disabled
      </Button>,
    )
    await userEvent.click(screen.getByRole('button'))
    expect(onClick).not.toHaveBeenCalled()
  })

  it('does not fire onClick when loading', async () => {
    const onClick = vi.fn()
    render(
      <Button loading onClick={onClick}>
        Loading
      </Button>,
    )
    await userEvent.click(screen.getByRole('button'))
    expect(onClick).not.toHaveBeenCalled()
  })

  it('forwards ref', () => {
    const ref = vi.fn()
    render(<Button ref={ref}>Ref</Button>)
    expect(ref).toHaveBeenCalled()
  })

  it('has type="button" by default', () => {
    render(<Button>Default</Button>)
    expect(screen.getByRole('button')).toHaveAttribute('type', 'button')
  })

  it('supports custom type', () => {
    render(<Button type="submit">Submit</Button>)
    expect(screen.getByRole('button')).toHaveAttribute('type', 'submit')
  })
})
