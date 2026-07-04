import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, it, expect } from 'vitest'

import { PasswordStrengthMeter } from '@/components/forms/password-strength-meter'

describe('PasswordStrengthMeter', () => {
  it('does not render for empty password', () => {
    const { container } = render(<PasswordStrengthMeter password="" />)
    expect(container).toBeEmptyDOMElement()
  })

  it('renders for non-empty password', () => {
    render(<PasswordStrengthMeter password="abc" />)
    expect(screen.getByText(/password strength/i)).toBeInTheDocument()
  })

  it('shows strength label', () => {
    render(<PasswordStrengthMeter password="abc" />)
    expect(screen.getByText(/weak|fair|good|strong/i)).toBeInTheDocument()
  })

  it('shows password rules', () => {
    render(<PasswordStrengthMeter password="abc" />)
    expect(screen.getByText(/at least 12 characters/i)).toBeInTheDocument()
    expect(screen.getByText(/lowercase \+ uppercase/i)).toBeInTheDocument()
    expect(screen.getByText(/contains a number/i)).toBeInTheDocument()
    expect(screen.getByText(/special character/i)).toBeInTheDocument()
  })

  it('marks passed rules', () => {
    render(<PasswordStrengthMeter password="Abc123!xyz123" />)
    // All rules should pass
    const passed = screen.getAllByText(/✓/)
    expect(passed.length).toBeGreaterThanOrEqual(4)
  })
})

describe('Breadcrumb', () => {
  it('renders items with separators', async () => {
    const { Breadcrumb } = await import('@/components/ui/breadcrumb')
    render(
      <Breadcrumb
        items={[
          { label: 'Home', href: '/' },
          { label: 'Dashboard', href: '/dashboard' },
          { label: 'Settings' },
        ]}
      />,
    )
    expect(screen.getByText('Home')).toBeInTheDocument()
    expect(screen.getByText('Dashboard')).toBeInTheDocument()
    expect(screen.getByText('Settings')).toBeInTheDocument()
  })

  it('marks last item as current page', async () => {
    const { Breadcrumb } = await import('@/components/ui/breadcrumb')
    render(
      <Breadcrumb
        items={[
          { label: 'Home', href: '/' },
          { label: 'Current' },
        ]}
      />,
    )
    const lastItem = screen.getByText('Current')
    expect(lastItem.className).toContain('font-medium')
  })
})

describe('Pagination', () => {
  it('does not render for single page', async () => {
    const { Pagination } = await import('@/components/ui/pagination')
    const { container } = render(
      <Pagination page={1} pageSize={20} total={10} onPageChange={() => {}} />,
    )
    expect(container).toBeEmptyDOMElement()
  })

  it('renders navigation buttons for multiple pages', async () => {
    const { Pagination } = await import('@/components/ui/pagination')
    render(
      <Pagination page={1} pageSize={10} total={50} onPageChange={() => {}} />,
    )
    expect(screen.getByRole('navigation')).toHaveAttribute('aria-label', 'Pagination')
  })

  it('disables previous button on first page', async () => {
    const { Pagination } = await import('@/components/ui/pagination')
    render(
      <Pagination page={1} pageSize={10} total={50} onPageChange={() => {}} />,
    )
    const prevButton = screen.getByRole('button', { name: /previous page/i })
    expect(prevButton).toBeDisabled()
  })

  it('disables next button on last page', async () => {
    const { Pagination } = await import('@/components/ui/pagination')
    render(
      <Pagination page={5} pageSize={10} total={50} onPageChange={() => {}} />,
    )
    const nextButton = screen.getByRole('button', { name: /next page/i })
    expect(nextButton).toBeDisabled()
  })

  it('calls onPageChange when clicking next', async () => {
    const onPageChange = vi.fn()
    const { Pagination } = await import('@/components/ui/pagination')
    render(
      <Pagination page={1} pageSize={10} total={50} onPageChange={onPageChange} />,
    )
    await userEvent.click(screen.getByRole('button', { name: /next page/i }))
    expect(onPageChange).toHaveBeenCalledWith(2)
  })
})
