import { render, screen } from '@testing-library/react'
import { describe, it, expect } from 'vitest'

import { PublicLayout } from '@/components/layout/public-layout'
import { AuthLayout } from '@/components/layout/auth-layout'

// Mock next-themes to avoid SSR issues
vi.mock('next-themes', () => ({
  useTheme: () => ({ theme: 'light', setTheme: vi.fn() }),
  ThemeProvider: ({ children }: { children: React.ReactNode }) => children,
}))

// Mock auth provider
vi.mock('@/providers/auth-provider', () => ({
  useAuth: () => ({ isAuthenticated: false, user: null, isLoading: false }),
  AuthProvider: ({ children }: { children: React.ReactNode }) => children,
  MfaRequiredError: class extends Error {},
}))

describe('PublicLayout', () => {
  it('renders header + footer', () => {
    render(
      <PublicLayout>
        <div>Content</div>
      </PublicLayout>,
    )
    expect(screen.getByText('Mastery Engine')).toBeInTheDocument()
    expect(screen.getByText('Content')).toBeInTheDocument()
  })

  it('shows login + signup when unauthenticated', () => {
    render(
      <PublicLayout>
        <div>Content</div>
      </PublicLayout>,
    )
    expect(screen.getByRole('link', { name: /log in/i })).toBeInTheDocument()
    expect(screen.getByRole('link', { name: /sign up/i })).toBeInTheDocument()
  })
})

describe('AuthLayout', () => {
  it('renders title + description + children', () => {
    render(
      <AuthLayout title="Test Title" description="Test Description">
        <div>Form content</div>
      </AuthLayout>,
    )
    expect(screen.getByText('Test Title')).toBeInTheDocument()
    expect(screen.getByText('Test Description')).toBeInTheDocument()
    expect(screen.getByText('Form content')).toBeInTheDocument()
  })

  it('renders footer when provided', () => {
    render(
      <AuthLayout title="Test" footer={<div>Footer content</div>}>
        <div>Content</div>
      </AuthLayout>,
    )
    expect(screen.getByText('Footer content')).toBeInTheDocument()
  })

  it('renders without title/description', () => {
    render(
      <AuthLayout>
        <div>Just content</div>
      </AuthLayout>,
    )
    expect(screen.getByText('Just content')).toBeInTheDocument()
  })
})

describe('Sidebar', () => {
  it('renders navigation items', async () => {
    const { Sidebar } = await import('@/components/layout/sidebar')
    render(<Sidebar />)
    expect(screen.getByText('Dashboard')).toBeInTheDocument()
    expect(screen.getByText('Learn')).toBeInTheDocument()
    expect(screen.getByText('Achievements')).toBeInTheDocument()
    expect(screen.getByText('Profile')).toBeInTheDocument()
    expect(screen.getByText('Security')).toBeInTheDocument()
    expect(screen.getByText('Settings')).toBeInTheDocument()
  })

  it('renders as navigation landmark', async () => {
    const { Sidebar } = await import('@/components/layout/sidebar')
    render(<Sidebar />)
    expect(screen.getByRole('navigation', { name: /main navigation/i })).toBeInTheDocument()
  })
})
